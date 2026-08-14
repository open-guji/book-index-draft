#!/usr/bin/env python3
"""明朝探勘：大規模修復Entity遭CBDB「pending_accept」（或其他弱信度
比對）誤配至完全不相干之他代同名人物，導致period由ming誤植為qing
或song之案例。

判定方法：
  1. 篩選出period=ming範圍內，Work（authors[0]即該Entity本人，非
     僅引用關係）與其entity_id所指Entity之period不一致，且Entity.
     period為qing或song者。
  2. 排除具「明末/清初/入清/仕清/降清」等明確過渡身分備註，或
     death_year落於1620-1700合理明清之際區間者（此類保留為真正
     朝代邊界人物，不予變動，比照三國魏晉/南北朝/隋唐/五代十國/
     遼金元五輪探勘之既有原則）。
  3. 排除該Entity名下**其他**作品已獨立支持其誤配朝代者（如張廷玉
     17作品中16作品確為清雍正名臣，僅1作品誤植，此類需逐一查核
     work層級之歸屬而非entity層級之dynasty，不宜整體回復；馮時行/
     李衡/胡宏三例亦屬此類，另案處理）。
  4. 對剩餘候選（同名同代之孤證CBDB配對，且無任何其他作品佐證其
     誤配朝代），逐一抽查indexed_by引文，確認皆為「萬曆/嘉靖/正德/
     崇禎」等明代紀年或「明史藝文志/欽定四庫全書總目」載其明代
     生平，而其CBDB配對之死亡年份（如1829/1857/1896等）與著錄內容
     顯不相容，判定為姓名巧合之誤配，逕予回復。

本輪共查出並修復 94組（period本誤植為qing）+ 20組（誤植為song）
之Entity，回復period為ming。
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


BOUNDARY_KEYWORDS = ["明末", "清初", "入清", "仕清", "降清"]
EXCLUDE_ENTITIES = {"1j967bgl8kqwr", "1j967afjb6aew", "1j967avzlck05"}  # 馮時行/李衡/胡宏，另案處理


def find_candidates(widx, eidx_data, target_period):
    fwd = set()
    for wid, path in widx.items():
        try:
            j = load(path)
        except Exception:
            continue
        if j.get("period") != "ming":
            continue
        a = j.get("authors")
        if not a or not isinstance(a, list) or not isinstance(a[0], dict):
            continue
        eid = a[0].get("entity_id")
        if not eid or eid not in eidx_data:
            continue
        if eidx_data[eid].get("period") == target_period:
            fwd.add(eid)

    candidates = []
    for eid in fwd:
        if eid in EXCLUDE_ENTITIES:
            continue
        e = eidx_data[eid]
        src = (e.get("external_ids") or {}).get("cbdb_source", "") or ""
        death = e.get("death_year")
        if any(kw in src for kw in BOUNDARY_KEYWORDS):
            continue
        if death and 1620 <= death <= 1700:
            continue
        works = e.get("works", [])
        supported = False
        for w in works:
            p = widx.get(w.get("work_id"))
            if not p:
                continue
            j = load(p)
            if j.get("period") == target_period:
                supported = True
                break
        if not supported:
            candidates.append(eid)
    return candidates


def main():
    widx = build_work_index()
    eidx_paths = build_entity_index()
    eidx_data = {eid: load(p) for eid, p in eidx_paths.items()}

    qing_candidates = find_candidates(widx, eidx_data, "qing")
    song_candidates = find_candidates(widx, eidx_data, "song")

    print(f"qing candidates: {len(qing_candidates)}")
    print(f"song candidates: {len(song_candidates)}")

    fixed_entities = 0
    fixed_works = 0

    for eid in qing_candidates + song_candidates:
        ent_p = eidx_paths[eid]
        ent = load(ent_p)
        note = f"{ent.get('primary_name')}：Entity遭CBDB弱信度比對誤配至完全不相干之他代同名人物（原cbdb_source: {ent.get('external_ids',{}).get('cbdb_source','')}），其所繫作品之著錄（明史藝文志／欽定四庫全書總目等）皆明確指向明代，訂正period為ming"
        ent["dynasty"] = "明"
        ent["period"] = "ming"
        ent["period_basis"] = f"據 dynasty「明」（2026-08-13 明朝探勘：{note}）"
        ent["ai_note"] = ent.get("ai_note", "") + f" 2026-08-13：{note}"
        ent["external_ids"] = {}
        ent.pop("dynasty_basis", None)
        ent.pop("birth_year", None)
        ent.pop("death_year", None)
        save(ent_p, ent, get_indent(ent_p))
        fixed_entities += 1

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
            a[0]["dynasty"] = "明"
            a[0].pop("dynasty_basis", None)
            if j.get("dynasty") is not None:
                j["dynasty"] = "明"
            if j.get("period") != "ming":
                j["period"] = "ming"
                j["period_basis"] = f"據 authors[0].dynasty「明」（2026-08-13 明朝探勘：{note}）"
                save(p, j, get_indent(p))
                fixed_works += 1

    print(f"fixed_entities={fixed_entities}, fixed_works(period changed)={fixed_works}")


if __name__ == "__main__":
    main()
