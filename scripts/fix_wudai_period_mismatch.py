#!/usr/bin/env python3
"""五代十國探勘：修復period=five-dynasties範圍內Entity/Work之
period不一致與CBDB誤配。

延續隋唐探勘之方法論，本輪查出：

  1. 「漢」「晉」二字之朝代同形碰撞：五代十國政權「後漢」
     （947-951）與「後晉」（936-947）之簡稱，恰與更早之古漢朝
     （東漢/西漢）、司馬氏晉朝同形，若歸戶邏輯未能正確辨識上下文，
     即可能將period判為錯誤之更早朝代（qin-han/jin）而非
     five-dynasties，或反向誤植。本輪查出3組：蘇逢吉（後漢，Entity
     period誤判為qin-han）、劉昫等（後晉，Entity period誤判為jin）、
     李瀚（五代／後晉語境，Entity period誤判為jin）——三者皆為
     Entity自身dynasty欄位早已正確，僅period欄位未同步或遭誤判，
     逕依dynasty訂正period。

  2. 反向：Entity遭CBDB「pending_accept」誤配污染，將本屬更早朝代
     （東漢／三國魏）之人物period誤植為five-dynasties：
       - 郭憲（漢武洞冥記/别國洞冥記）：欽定四庫全書總目明載「後漢
         郭憲撰...官至光祿勳...事蹟具後漢書方術傳」，確為東漢
         （25-220）人，非五代「後漢」（947-951）——同屬上述「漢」
         字跨七百餘年同形碰撞，惟方向相反。
       - 韋寬（蜀志）：國史經籍志載「後漢韋寬」，同屬東漢人物。
       - 王昶（兵書/王昶集）：三國藝文志/隋書經籍志明載「魏司空
         王昶集...嘉平初,太傅司馬宣王旣誅曹爽」，確為三國魏司空
         王昶（?-259），Entity卻遭CBDB誤配至十國「閩」政權
         （pending_accept，弱信度比對）。

  3. 「單一斷代志代填period」啟發式對回溯型志書失效之再現：陽休之
     《韻略》，清史稿藝文志原文本身即明載「北齊陽休之韻略」，period
     卻誤填為「清」；其Entity另遭一條語意混亂之pending_accept
     污染（備註雖引「北齊」卻填入period=five-dynasties/dynasty=
     後漢）。實際上陽休之（509-582）為北齊人，應歸period=
     nanbeichao，並非five-dynasties亦非qing——此case橫跨兩輪探勘
     （隋唐/五代十國）之範圍，一併訂正。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, data, indent=2):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
        f.write("\n")


def get_indent(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    lines = raw.split("\n")
    if len(lines) > 1:
        cand = len(lines[1]) - len(lines[1].lstrip(" "))
        if cand > 0:
            return cand
    return 2


def build_work_index():
    idx = {}
    for s in SHARDS:
        d = load(ROOT / "index" / "works" / f"{s}.json")
        for wid, entry in d.items():
            idx[wid] = ROOT / entry["path"]
    return idx


def build_entity_index():
    idx = {}
    for f in Path(ROOT / "Entity").rglob("*.json"):
        try:
            j = load(f)
        except Exception:
            continue
        if isinstance(j, dict) and j.get("id"):
            idx[j["id"]] = f
    return idx


# (entity_id, correct_name_or_None, correct_dynasty, correct_period, note, clear_cbdb)
ENTITY_FIXES = [
    ("1j96hjwlylnpe", None, "後漢", "five-dynasties",
     "蘇逢吉：dynasty已正確（後漢，五代政權），period欄位未同步", False),
    ("1j96kfl8v39c0", None, "後晉", "five-dynasties",
     "劉昫等奉敕：dynasty已正確（後晉，五代政權），period欄位未同步", False),
    ("1j96hlhu2zf28", None, "後晉", "five-dynasties",
     "劉昫：同上", False),
    ("1j96hhvcrjvgs", None, "五代", "five-dynasties",
     "李瀚：欽定四庫全書總目載「晉李瀚撰...晉高祖以為浮薄」，即後晉語境，period欄位誤判為jin，訂正", False),
    ("1j96hlb4wllog", None, "東漢", "qin-han",
     "郭憲：欽定四庫全書總目明載「後漢郭憲撰...事蹟具後漢書方術傳」，確為東漢人（與五代「後漢」同形碰撞），訂正dynasty為「東漢」以消歧義，period訂正為qin-han", True),
    ("1j96hftweo2kg", None, "東漢", "qin-han",
     "韋寬：國史經籍志載「後漢韋寬」，同屬東漢人物（與五代「後漢」同形碰撞），訂正", True),
    ("1j96hhvcrjvhz", None, "三國魏", "three-kingdoms",
     "王昶：三國藝文志/隋書經籍志明載「魏司空王昶集...嘉平初,太傅司馬宣王旣誅曹爽」，確為三國魏司空王昶，Entity遭CBDB誤配至十國「閩」政權，訂正", True),
    ("1j96a3rlxwt8l", None, "北齊", "nanbeichao",
     "陽休之：清史稿藝文志/國史經籍志皆確認為北齊人（509-582），Entity遭一條語意混亂之CBDB污染誤植為五代/後漢，訂正", True),
]


def sync_works_for_entity(eid, dyn, period, note, widx, ent):
    fixed = 0
    for w in ent.get("works", []):
        wid = w.get("work_id")
        p = widx.get(wid)
        if not p:
            continue
        j = load(p)
        a = j.get("authors")
        if not a or not isinstance(a, list) or not isinstance(a[0], dict):
            continue
        if a[0].get("entity_id") != eid:
            continue
        a[0]["dynasty"] = dyn
        a[0].pop("dynasty_basis", None)
        if j.get("dynasty") is not None:
            j["dynasty"] = dyn
        j["period"] = period
        j["period_basis"] = f"據 authors[0].dynasty「{dyn}」（2026-08-13 五代十國探勘：{note}）"
        save(p, j, get_indent(p))
        fixed += 1
    return fixed


def main():
    widx = build_work_index()
    eidx = build_entity_index()
    fixed_works = 0
    fixed_entities = 0

    for eid, name, dyn, period, note, clear_cbdb in ENTITY_FIXES:
        ent_p = eidx[eid]
        ent = load(ent_p)
        if name:
            ent["primary_name"] = name
        ent["dynasty"] = dyn
        ent["period"] = period
        ent["period_basis"] = f"據 dynasty「{dyn}」（2026-08-13 五代十國探勘：{note}）"
        ent["ai_note"] = ent.get("ai_note", "") + f" 2026-08-13：{note}"
        if clear_cbdb:
            ent["ai_note"] += f"（原cbdb_source: {ent.get('external_ids',{}).get('cbdb_source','')}，已卸除）"
            ent["external_ids"] = {}
        ent.pop("dynasty_basis", None)
        ent.pop("birth_year", None)
        ent.pop("death_year", None)
        save(ent_p, ent, get_indent(ent_p))
        fixed_entities += 1
        fixed_works += sync_works_for_entity(eid, dyn, period, note, widx, ent)

    print(f"fixed_entities={fixed_entities}, fixed_works={fixed_works}")


if __name__ == "__main__":
    main()
