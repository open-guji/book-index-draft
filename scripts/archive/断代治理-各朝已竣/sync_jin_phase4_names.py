#!/usr/bin/env python3
"""晉朝探勘分期第四階段：續核殘留高頻／有內證人物三例，一組Entity
分裂合併。

直接訂正：
  - 盧湛（1j96hfeurfpc0）：著錄載「司空從事中郎盧湛」，外部查證確認
    即盧諶（子諒），劉琨（270-318）從事中郎，劉琨歿於西晉滅亡
    （311年洛陽陷落）後仍在北方奮戰至318年，盧諶主要仕歷屬西晉
    末年，訂正為西晉。
  - 華嶤（1j96kegekjls0，即華嶠）：著錄載「本書九十七卷，經永嘉之
    亂，僅存五十餘卷」——永嘉之亂（311年）為書成後方遭殘缺，可證
    原書成於亂前，即西晉史家華嶠（叔駿）撰《後漢書》，訂正為西晉。

Entity 分裂合併：
  - 荀綽：1j96hjwlyaf4k（晉後略記）與1j96hfdqooum8（冀州記）皆載
    「荀綽」，核與史實相符（荀綽字彥舒，西晉學者，撰《晉後略》
    《兗州記》《冀州記》等地志與晉末史事），書目不相排斥，逕予
    合併，訂正為西晉。
"""
import json
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

DIRECT_ENTITY_FIX = {
    "1j96hfeurfpc0": ("西晉", "盧湛（盧諶）：劉琨從事中郎，仕歷屬西晉末年"),
    "1j96kegekjls0": ("西晉", "華嶤（華嶠）：著錄載原書成於永嘉之亂（311）前"),
}

MERGES = [
    ("1j96hjwlyaf4k", ["1j96hfdqooum8"], "西晉",
     "荀綽：字彥舒，西晉學者，撰晉後略/兗州記/冀州記等，書目不相排斥"),
]


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
    for f in glob.glob(str(ROOT / "Entity" / "**" / "*.json"), recursive=True):
        try:
            j = load(Path(f))
        except Exception:
            continue
        if isinstance(j, dict) and j.get("id"):
            idx[j["id"]] = Path(f)
    return idx


def delete_entity(eid, ent_path):
    ent_path.unlink()
    s = shard_of(eid)
    p = ROOT / "index" / "entities" / f"{s:x}.json"
    d = load(p)
    if eid in d:
        del d[eid]
        save(p, d, indent=get_indent(p))


def sync_by_entity_id(widx, eid, target_dyn, note):
    """依 authors[].entity_id 直接掃描 works 索引，不依賴 Entity.works[]
    （避免二者脫鏈導致遺漏，第三階段已發現此問題）。"""
    fixed = 0
    for wid, path in widx.items():
        try:
            j = load(path)
        except Exception:
            continue
        if j.get("period") != "jin":
            continue
        a = j.get("authors")
        if not a or not isinstance(a, list):
            continue
        changed = False
        for au in a:
            if isinstance(au, dict) and au.get("entity_id") == eid and au.get("dynasty") == "晉":
                au["dynasty"] = target_dyn
                changed = True
        if changed:
            if j.get("dynasty") == "晉":
                j["dynasty"] = target_dyn
            j["period_basis"] = f"據 authors[].dynasty「{target_dyn}」（原作籠統「晉」，2026-08-11 晉朝探勘分期第四階段訂正：{note}）"
            save(path, j, get_indent(path))
            fixed += 1
    return fixed


def main():
    widx = build_work_index()
    eidx = build_entity_index()

    fixed_works = 0
    fixed_entities = 0

    for eid, (target_dyn, note) in DIRECT_ENTITY_FIX.items():
        ent_path = eidx[eid]
        ent = load(ent_path)
        ent["dynasty"] = target_dyn
        ent["ai_note"] = ent.get("ai_note", "") + f" 2026-08-11：晉朝探勘分期第四階段訂正——{note}，dynasty改為「{target_dyn}」。"
        save(ent_path, ent, get_indent(ent_path))
        fixed_entities += 1
        fixed_works += sync_by_entity_id(widx, eid, target_dyn, note)

    for base_eid, donor_eids, target_dyn, note in MERGES:
        base_p = eidx[base_eid]
        base = load(base_p)
        base_works = {w["work_id"]: w for w in base.get("works", [])}
        base["dynasty"] = target_dyn

        for did in donor_eids:
            donor_p = eidx[did]
            donor = load(donor_p)
            for w in donor.get("works", []):
                base_works.setdefault(w["work_id"], w)
            delete_entity(did, donor_p)

        base["works"] = list(base_works.values())
        base["ai_note"] = base.get("ai_note", "") + f" 2026-08-11：晉朝探勘分期第四階段查出同名分裂——{note}，已合併。"
        save(base_p, base, get_indent(base_p))
        fixed_entities += 1

        for wid in base_works:
            p = widx.get(wid)
            if not p:
                continue
            j = load(p)
            changed = False
            for au in j.get("authors", []) or []:
                if isinstance(au, dict) and au.get("entity_id") in donor_eids:
                    au["entity_id"] = base_eid
                    au["dynasty"] = target_dyn
                    changed = True
                elif isinstance(au, dict) and au.get("entity_id") == base_eid and au.get("dynasty") == "晉":
                    au["dynasty"] = target_dyn
                    changed = True
            if changed:
                if j.get("dynasty") in ("晉", None):
                    j["dynasty"] = target_dyn
                j["period_basis"] = f"據 authors[].dynasty「{target_dyn}」（2026-08-11 晉朝探勘分期第四階段：{note}）"
                save(p, j, get_indent(p))
                fixed_works += 1

        # 亦以entity_id掃描補齊任何脫鏈殘留
        fixed_works += sync_by_entity_id(widx, base_eid, target_dyn, note)

    print(f"fixed_works={fixed_works}, fixed_entities={fixed_entities}")


if __name__ == "__main__":
    main()
