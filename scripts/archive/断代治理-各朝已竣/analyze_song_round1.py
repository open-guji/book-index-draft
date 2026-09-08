#!/usr/bin/env python3
"""
analyze_song_round1.py — 宋代朝代拆分第一轮只读分析

目标：找出 dynasty=宋 中可高置信拆为 北宋/南宋 的条目。
只读输出，不修改数据。
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / ".claude" / "known-issues" / "cbdb_dy_cache.json"
OUT_PATH = ROOT / ".claude" / "known-issues" / "宋代拆分_round1_分析.json"


def load_json(fp: Path):
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None


def iter_work_files():
    return sorted(ROOT.glob("Work/?/?/?/*.json"))


def iter_entity_files():
    return sorted(ROOT.glob("Entity/?/?/?/*.json"))


def cbdb_song_split(entry: dict, birth_year=None, death_year=None):
    """仅用 CBDB 的北/南宋名与年份作只读判定。"""
    if not entry:
        return None, "no_cbdb_entry"
    cdy = str(entry.get("dynasty_id", ""))
    birth_name = entry.get("dynasty_birth_name") or ""
    death_name = entry.get("dynasty_death_name") or ""
    if cdy != "15":
        return None, f"cbdb:c_dy={cdy}, 非赵宋"
    if "南宋" in death_name:
        return "南宋", "cbdb:death_name=南宋"
    if "南宋" in birth_name and "北宋" not in birth_name:
        return "南宋", "cbdb:birth_name=南宋"
    if "北宋" in birth_name and "南宋" not in death_name:
        return "北宋", "cbdb:birth_name=北宋"
    if "北宋" in death_name and "南宋" not in death_name:
        return "北宋", "cbdb:death_name=北宋"

    years = []
    for key in ("index_year", "IndexYear", "year_birth", "year_death"):
        v = entry.get(key)
        try:
            if v is not None and str(v).strip() and int(v) > 0:
                years.append(int(v))
        except Exception:
            pass
    for v in (birth_year, death_year):
        try:
            if v is not None and int(v) > 0:
                years.append(int(v))
        except Exception:
            pass
    if years:
        earliest = min(years)
        latest = max(years)
        if earliest >= 1127 and earliest < 1279:
            return "南宋", f"year={earliest}→南宋"
        if 960 <= earliest < 1127 and latest < 1127:
            return "北宋", f"year={earliest}-{latest}→北宋"
        if 960 <= earliest < 1127 <= latest < 1279:
            return "南宋", f"year={earliest}-{latest}跨南北宋，按卒年归南宋"
    return None, "cbdb:c_dy=15 但无北/南宋信号"


def main():
    cbdb_cache = load_json(CACHE_PATH) or {}
    works = {}
    entities = {}
    eid_to_works = defaultdict(list)

    for fp in iter_work_files():
        d = load_json(fp)
        if d:
            works[d.get("id", fp.stem)] = d
    for fp in iter_entity_files():
        d = load_json(fp)
        if d:
            entities[d.get("id", fp.stem)] = d

    for wid, w in works.items():
        for a in w.get("authors", []) or []:
            if isinstance(a, dict) and a.get("entity_id"):
                eid_to_works[a["entity_id"]].append(w)

    work_period_by_dyn = Counter()
    author_period_by_dyn = Counter()
    entity_period_by_dyn = Counter()
    entity_cbdb_split = Counter()
    entity_year_split = Counter()
    candidates = []

    for w in works.values():
        if w.get("dynasty") == "宋":
            work_period_by_dyn[w.get("period") or "null"] += 1
        for a in w.get("authors", []) or []:
            if isinstance(a, dict) and a.get("dynasty") == "宋":
                author_period_by_dyn[w.get("period") or "null"] += 1

    for eid, e in entities.items():
        if e.get("dynasty") != "宋":
            continue
        entity_period_by_dyn[e.get("period") or "null"] += 1
        ext = e.get("external_ids", {})
        cbdb_id = ext.get("cbdb_id") if isinstance(ext, dict) else None
        entry = cbdb_cache.get(str(cbdb_id)) if cbdb_id else None
        split, basis = cbdb_song_split(entry, e.get("birth_year"), e.get("death_year"))
        entity_cbdb_split[split or "unresolved"] += 1
        if basis.startswith("year="):
            entity_year_split[split or "unresolved"] += 1
        if split:
            related_periods = Counter(w.get("period") or "null" for w in eid_to_works.get(eid, []))
            candidates.append({
                "entity_id": eid,
                "name": e.get("primary_name"),
                "current_dynasty": e.get("dynasty"),
                "current_period": e.get("period"),
                "suggested_dynasty": split,
                "basis": basis,
                "birth_year": e.get("birth_year"),
                "death_year": e.get("death_year"),
                "cbdb_id": cbdb_id,
                "related_work_periods": dict(related_periods.most_common()),
            })

    out = {
        "summary": {
            "work_dynasty_song_by_period": dict(work_period_by_dyn.most_common()),
            "author_dynasty_song_by_work_period": dict(author_period_by_dyn.most_common()),
            "entity_dynasty_song_by_period": dict(entity_period_by_dyn.most_common()),
            "entity_cbdb_split": dict(entity_cbdb_split.most_common()),
            "entity_year_split": dict(entity_year_split.most_common()),
            "candidate_count": len(candidates),
        },
        "candidates": candidates,
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("=== 宋代拆分 Round 1 分析 ===")
    print(f"Work 总数: {len(works)}")
    print(f"Entity 总数: {len(entities)}")
    print("\nWork.dynasty=宋 按 period:")
    for k, v in work_period_by_dyn.most_common():
        print(f"  {k:20s} {v:>6}")
    print("\nAuthor.dynasty=宋 按 Work.period:")
    for k, v in author_period_by_dyn.most_common():
        print(f"  {k:20s} {v:>6}")
    print("\nEntity.dynasty=宋 按 period:")
    for k, v in entity_period_by_dyn.most_common():
        print(f"  {k:20s} {v:>6}")
    print("\nEntity CBDB/年份可拆:")
    for k, v in entity_cbdb_split.most_common():
        print(f"  {k:20s} {v:>6}")
    print(f"\n候选数: {len(candidates)}")
    print(f"输出: {OUT_PATH}")


if __name__ == "__main__":
    main()
