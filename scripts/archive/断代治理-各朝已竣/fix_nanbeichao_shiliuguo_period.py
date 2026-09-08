#!/usr/bin/env python3
"""南北朝探勘：修復「十六國政權人物之作品被歸入period=nanbeichao」
之內部不一致問題。

鳩摩羅什（後秦，344-413）、曇無讖（北涼，385-433）、竺佛念（後秦）、
僧肇（東晉，384-414，鳩摩羅什弟子）、王嘉（前秦，?-390）等十六國
／東晉政權人物，其authors[0].dynasty正確標為所屬政權，但period卻
歸入nanbeichao——與同一人物之其他作品（period=jin）自相矛盾。此非
period定義本身之判斷問題（詳見探勘報告「十六國政權人物period歸屬」
一節，留待獨立立項），而是單純之欄位同步遺漏，逕予訂正。

另附帶處理：
  - 僧肇兩個重複Entity（1j96ha8xfybcw／1j96ha8x0noqo，後者
    primary_name殘缺為單字「僧」）合併。
  - 王嘉：發現《拾遺記》（1ev3bckcsrbpc）誤繫入另一位元代同名人物
    王嘉之Entity（1j96hjwlyaf4l，該Entity正確持有《春秋類義》，
    與前秦王嘉無關），今改繫至前秦王嘉之既有正確Entity
    （1j97244uq4gzk，已持有《拾遺錄》，疑與《拾遺記》《王子年
    拾遺記》為同書異題）。
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


def shard_of(id_str, n=16):
    h = 0
    for c in id_str:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return h % n


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


def delete_entity(eid, ent_path):
    ent_path.unlink()
    s = shard_of(eid)
    p = ROOT / "index" / "entities" / f"{s:x}.json"
    d = load(p)
    if eid in d:
        del d[eid]
        save(p, d, indent=get_indent(p))


def fix_period_only(j, path, note):
    j["period"] = "jin"
    j["period_basis"] = f"據 authors[0].dynasty（十六國／東晉政權）（2026-08-13 南北朝探勘：{note}）"
    save(path, j, get_indent(path))


def main():
    widx = build_work_index()
    eidx = build_entity_index()
    fixed = 0

    # A. 鳩摩羅什：entity_id已正確繫連者，僅需訂正period
    kumarajiva_ids = ["1evkpo5prat4w", "1evkaeh3hf7k0", "1evkaejvl5yww",
                       "1evgpqf6u2lts", "1evcsxq885kw0"]
    for wid in kumarajiva_ids:
        j = load(widx[wid])
        fix_period_only(j, widx[wid], "鳩摩羅什，後秦，其Entity（1j96ad6hy8kqo）period本已為jin")
        fixed += 1

    # B. 鳩摩羅什：entity_id缺失者，補繫並訂正period
    kumarajiva_noid = ["1evkpo60exgqo", "1evjy5c62qjuo"]
    ent_p = eidx["1j96ad6hy8kqo"]
    ent = load(ent_p)
    ent_works = {w["work_id"]: w for w in ent.get("works", [])}
    for wid in kumarajiva_noid:
        j = load(widx[wid])
        j["authors"][0]["entity_id"] = "1j96ad6hy8kqo"
        fix_period_only(j, widx[wid], "鳩摩羅什，後秦，補繫既有Entity並訂正period")
        ent_works.setdefault(wid, {"work_id": wid, "role": "譯"})
        fixed += 1
    ent["works"] = list(ent_works.values())
    save(ent_p, ent, get_indent(ent_p))

    # C. 曇無讖：無既有Entity，逕行訂正period
    tanwuchen_ids = ["1evgpqdn0gsn4", "1evkaeiay7uo0", "1evkaejsbsqo0", "1evfteyp99eyo"]
    for wid in tanwuchen_ids:
        j = load(widx[wid])
        fix_period_only(j, widx[wid], "曇無讖，北涼，無既有Entity，逕行訂正period")
        fixed += 1

    # D. 竺佛念：無既有Entity，逕行訂正period
    j = load(widx["1evgpszkikmio"])
    fix_period_only(j, widx["1evgpszkikmio"], "竺佛念，後秦，無既有Entity，逕行訂正period")
    fixed += 1

    # E. 僧肇：兩Entity合併，並補繫nanbeichao殘留一條
    base_p = eidx["1j96ha8xfybcw"]
    base = load(base_p)
    base_works = {w["work_id"]: w for w in base.get("works", [])}
    donor_p = eidx["1j96ha8x0noqo"]
    donor = load(donor_p)
    for w in donor.get("works", []):
        base_works.setdefault(w["work_id"], w)
    delete_entity("1j96ha8x0noqo", donor_p)

    sengzhao_wid = "1evjr6ug6rjeo"
    j = load(widx[sengzhao_wid])
    j["authors"][0]["name"] = "僧肇"
    j["authors"][0]["dynasty"] = "東晉"
    j["authors"][0]["entity_id"] = "1j96ha8xfybcw"
    fix_period_only(j, widx[sengzhao_wid], "僧肇，東晉（384-414，鳩摩羅什弟子），dynasty原誤植「後秦」，合併僧肇兩重複Entity並訂正")
    base_works.setdefault(sengzhao_wid, {"work_id": sengzhao_wid, "role": "撰"})
    fixed += 1

    base["works"] = list(base_works.values())
    base["ai_note"] = base.get("ai_note", "") + " 2026-08-13：南北朝探勘查出同名分裂Entity「僧」（1j96ha8x0noqo，primary_name殘缺）併入本條。"
    save(base_p, base, get_indent(base_p))

    # F. 王嘉：拾遺記誤繫入元代同名人物Entity，改繫前秦王嘉之既有正確Entity
    wrong_p = eidx["1j96hjwlyaf4l"]
    wrong = load(wrong_p)
    wrong["works"] = [w for w in wrong.get("works", []) if w["work_id"] != "1ev3bckcsrbpc"]
    save(wrong_p, wrong, get_indent(wrong_p))

    correct_p = eidx["1j97244uq4gzk"]
    correct = load(correct_p)
    correct_works = {w["work_id"]: w for w in correct.get("works", [])}

    j = load(widx["1ev3bckcsrbpc"])
    j["authors"][0]["entity_id"] = "1j97244uq4gzk"
    fix_period_only(j, widx["1ev3bckcsrbpc"], "王嘉《拾遺記》，前秦，原誤繫入另一位元代同名人物之Entity，今改繫前秦王嘉之既有正確Entity")
    correct_works.setdefault("1ev3bckcsrbpc", {"work_id": "1ev3bckcsrbpc", "role": "撰"})
    fixed += 1

    j = load(widx["1evka9y5bkdmo"])
    j["authors"][0]["entity_id"] = "1j97244uq4gzk"
    fix_period_only(j, widx["1evka9y5bkdmo"], "王嘉《王子年拾遺記》，前秦，補繫既有正確Entity")
    correct_works.setdefault("1evka9y5bkdmo", {"work_id": "1evka9y5bkdmo", "role": "撰"})
    fixed += 1

    correct["dynasty"] = "前秦"
    correct["works"] = list(correct_works.values())
    correct["ai_note"] = correct.get("ai_note", "") + " 2026-08-13：南北朝探勘：dynasty由籠統「晉」訂正為「前秦」（?-390，字子年，苻秦方士），並補繫誤繫他處之《拾遺記》《王子年拾遺記》二work。"
    save(correct_p, correct, get_indent(correct_p))

    print(f"fixed={fixed}")


if __name__ == "__main__":
    main()
