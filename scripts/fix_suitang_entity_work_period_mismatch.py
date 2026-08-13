#!/usr/bin/env python3
"""隋唐探勘：修復period=sui-tang範圍內Entity.period與Work.period
不一致之案例。

系統性全查後發現多種成因：

  A. 「單一斷代志代填period」啟發式誤用：部分Work之period係依
     「撰人朝代闕，而所著錄之志唯一且為斷代志...故據之」規則，
     以著錄來源書目本身之朝代（而非人物真實朝代）代填。此規則對
     專屬斷代志（如補晉書藝文志、後漢藝文志）較可靠，但對「清史稿
     藝文志」一類回溯型、涵蓋歷代亡佚書之志書則不成立——清史稿
     藝文志本身即收錄隋唐人著作，若逕以「清」代填即成系統性錯誤。
     王邵/杜寶/成伯璵/崔覲（entity一度誤植primary_name「秦朝儉」）
     四例皆屬此類，其Entity本已正確（唐/隋，sui-tang），僅Work.period
     需訂正。

  B. Entity遭CBDB「pending_accept」未確認配對污染，導致period被
     誤植為sui-tang，然其Work自身之著錄內證（多引補晉書藝文志／
     元史藝文志／欽定四庫全書總目等）明確指向完全不同之朝代——
     劉寶（晉）、張詮（晉）、張方（晉）、王繪（金）、宋幹（後周）、
     尉遲偓（南唐——「唐」字碰撞之另一種型態，容易與正朔「唐」
     混淆）、韋轂（後蜀）、張行簡（金，8作品）、楊孚（東漢）、
     樊光（漢）、李復（北宋，著錄有完整生平可考）、周捨（南朝梁，
     多方引文一致，經義考「唐志五十卷」僅指唐代目錄著錄此書，
     非謂周捨本人為唐人）。張光另涉姓名截斷（實為「張光祖」，
     元代人）。

  C. 濮王：Entity遭CBDB誤配至同名（諡號濮王）之北宋宗室趙允讓
     （995-1059），然本條著錄明載「唐濮王泰」，實為唐太宗子李泰，
     著《括地誌》，Entity應訂正為李泰、唐、sui-tang。

  D. 虞荔《古今𪔂錄》：Work層authors[0].dynasty誤植「隋」（單一
     來源「國史經籍志」用字或有訛誤），然虞荔（503-561）確為南朝
     陳人（卒於陳朝，未及見隋代），且其Entity（已據較完整證據
     訂為南朝陳／nanbeichao）與其另一作品一致，故以Entity為準，
     訂正Work之dynasty/period。

  唐仲友（友帝王經世圖譜）：先前一輪已訂正其name（唐仲→唐仲友）
  與dynasty，然漏未同步Work.period（仍為sui-tang），本輪補正為song。

真正之「朝代邊界過渡人物」（生平跨兩朝代，Entity之period與部分
Work之period不同屬合理判斷差異，非bug）則不予變動，包括：徐鉉
（南唐入宋）、荊浩（唐末五代畫家）、庾季才（梁入隋天文家）、
王松年（五代道士）——此類人物之Entity.period與其少量Work.period
不一致，反映史學上對其斷代慣例之寬容，不宜比照本輪其餘明確錯誤
逕行同步。

鄭廑（巴蜀耆舊傳／蜀本紀）：Work引後漢藝文志（暗示漢代），Entity
之CBDB配對雖標「pending_accept」但候選本身即為「唐鄭廑」，兩方
證據皆非決定性，本輪不予處理，留待未來查核。
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


# Group A+B+C+D: (entity_id, correct_name_or_None, correct_dynasty, correct_period, note)
ENTITY_FIXES = [
    ("1j96h8rw6xrun", None, "唐", "sui-tang", "王邵：清史稿藝文志本身即明載「隋王邵讀書記」，period誤依來源志書「清」代填，Entity本已正確，訂正Work"),
    ("1j967afjav1wp", None, "唐", "sui-tang", "杜寶：清史稿藝文志本身即明載「隋杜寶水飾」，period誤依來源志書「清」代填，Entity本已正確，訂正Work"),
    ("1j96ha59ki1og", None, "唐", "sui-tang", "成伯璵：唐代禮學家，period誤依來源志書「清」代填，Entity本已正確，訂正Work"),
    ("1j96h8rw6xruq", "崔覲", "唐", "sui-tang", "秦朝儉→崔覲：Entity primary_name遭誤植，著錄（經義考「隋志十三卷」）確認為隋人崔覲《周易注》，period誤依來源志書「清」代填，訂正Entity/Work"),
    ("1j96h8rw7k8wo", None, "晉", "jin", "劉寶：隋書經籍志/補晉書藝文志皆明載「晉安北將軍劉寶撰」，Entity遭CBDB誤配（pending_accept cbdb_dy=6, 600-665）"),
    ("1j96h8rw7k8xe", None, "晉", "jin", "張詮：補晉書藝文志載「燕尚書郎張詮」（南燕，十六國政權，比照本庫既有慣例歸period=jin），Entity遭CBDB誤配"),
    ("1j96h8rw7k8ww", None, "晉", "jin", "張方：隋書經籍志明載「晉張方撰」，Entity遭CBDB誤配"),
    ("1j96hjwlyaf71", None, "金", "liao-jin-yuan", "王繪：補遼金元藝文志/元史藝文志皆明載「金王繪」，Entity遭CBDB誤配至唐"),
    ("1j96hjwlylnqe", None, "後周", "five-dynasties", "宋幹：國史經籍志明載「後周宋幹集」，Entity遭CBDB誤配至唐"),
    ("1j967da978dhk", None, "南唐", "five-dynasties", "尉遲偓：欽定四庫全書總目明載「南唐尉遲偓撰」（「唐」字與正朔唐易混淆），Entity遭CBDB誤配"),
    ("1j96hgeei87b4", None, "後蜀", "five-dynasties", "韋轂：才調集編者，Work層authors[0].dynasty已確立為「後蜀」，Entity遭CBDB誤配至唐"),
    ("1j96hhvcrjvgi", None, "金", "liao-jin-yuan", "張行簡：欽定四庫全書總目/元史藝文志皆明載「金張行簡撰...大定十九年進士...事蹟具金史本傳」，Entity遭CBDB誤配至唐（8作品）"),
    ("1j96h8rw7k8wg", None, "東漢", "qin-han", "楊孚：交州異物志/董卓別傳/臨海水土記之撰人，東漢楊孚，Entity遭CBDB誤配至唐（3作品）"),
    ("1j967cp1zdr2h", None, "漢", "qin-han", "樊光：國史經籍志明載「漢樊光注」爾雅，Entity遭CBDB誤配至唐"),
    ("1j96hhvcrv409", None, "南朝梁", "nanbeichao", "周捨：國史經籍志/隋書經籍志/清史稿藝文志皆明載「梁周舍/周捨」，經義考「唐志五十卷」僅指唐代目錄著錄此書，非謂其人為唐人，Entity遭CBDB誤配"),
    ("1j96hjwlxny2c", None, "北宋", "song", "李復：欽定四庫全書總目載其完整生平「宋李複撰...登元豐二年進士」，確為北宋人，Entity遭CBDB誤配至唐"),
    ("1j96h8rw6xrtu", "張光祖", "元", "liao-jin-yuan", "張光→張光祖：清史稿藝文志載「元張光祖祖言行龜鑒」，name原缺一「祖」字，且Entity遭CBDB誤配至唐"),
    ("1j96hjwlx1gy9", "李泰", "唐", "sui-tang", "濮王：Entity遭CBDB誤配至同諡號之北宋宗室趙允讓（995-1059），著錄明載「唐濮王泰」，實為唐太宗子李泰，著括地誌"),
]

# (work_id, correct_dynasty, correct_period, note) — 僅Work需訂正
WORK_ONLY_FIXES = [
    ("1evgpi0ouk16o", "南朝陳", "nanbeichao", "虞荔：Work層authors[0].dynasty誤植「隋」（來源「國史經籍志」用字或有訛誤），虞荔（503-561）確為南朝陳人，未及見隋代，以Entity既有正確分類（南朝陳/nanbeichao）為準"),
    ("1evgoqhl08etc", "南朝梁", "nanbeichao", "周捨《禮疑義》：Work層authors[0].dynasty原誤植「唐」（entity_propagation_r2），訂正為南朝梁"),
    ("1evr5e3mc6kj9", None, "song", "唐仲友《友帝王經世圖譜》：先前一輪已訂正name/dynasty，然漏未同步period，本輪補正"),
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
        j["period_basis"] = f"據 authors[0].dynasty「{dyn}」（2026-08-13 隋唐探勘：{note}）"
        save(p, j, get_indent(p))
        fixed += 1
    return fixed


def main():
    widx = build_work_index()
    eidx = build_entity_index()
    fixed_works = 0
    fixed_entities = 0

    for eid, name, dyn, period, note in ENTITY_FIXES:
        ent_p = eidx[eid]
        ent = load(ent_p)
        if name:
            ent["primary_name"] = name
        ent["dynasty"] = dyn
        ent["period"] = period
        ent["period_basis"] = f"據 dynasty「{dyn}」（2026-08-13 隋唐探勘：{note}）"
        ent["ai_note"] = ent.get("ai_note", "") + f" 2026-08-13：CBDB配對卸除／period訂正（原cbdb_source: {ent.get('external_ids',{}).get('cbdb_source','')}），{note}。"
        ent["external_ids"] = {}
        ent.pop("dynasty_basis", None)
        ent.pop("birth_year", None)
        ent.pop("death_year", None)
        save(ent_p, ent, get_indent(ent_p))
        fixed_entities += 1
        fixed_works += sync_works_for_entity(eid, dyn, period, note, widx, ent)

    for wid, dyn, period, note in WORK_ONLY_FIXES:
        p = widx[wid]
        j = load(p)
        if dyn:
            j["authors"][0]["dynasty"] = dyn
            j["authors"][0].pop("dynasty_basis", None)
            if j.get("dynasty") is not None:
                j["dynasty"] = dyn
        j["period"] = period
        j["period_basis"] = f"（2026-08-13 隋唐探勘：{note}）"
        save(p, j, get_indent(p))
        fixed_works += 1

    print(f"fixed_entities={fixed_entities}, fixed_works={fixed_works}")


if __name__ == "__main__":
    main()
