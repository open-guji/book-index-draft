#!/usr/bin/env python3
"""收集無 cbdb_id 的歧義 entity，特別是 dynasty=宋 中可能的南朝宋人物。"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

AMBIGUOUS = {"宋", "晉", "梁", "周", "齊", "魏", "吳", "蜀", "陳", "三國", "南北朝", "南朝", "北朝"}


def iter_entity_files():
    return sorted(ROOT.glob("Entity/?/?/?/*.json"))


def iter_work_files():
    return sorted(ROOT.glob("Work/?/?/?/*.json"))


def main():
    entities = {}
    for fp in iter_entity_files():
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        entities[d.get("id", fp.stem)] = d

    works = {}
    for fp in iter_work_files():
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        works[d.get("id", fp.stem)] = d

    eid_to_works = defaultdict(list)
    for wid, w in works.items():
        for a in w.get("authors", []) or []:
            if isinstance(a, dict):
                eid = a.get("entity_id")
                if eid:
                    eid_to_works[eid].append(w)

    # 收集無 cbdb_id 的歧義 entity
    no_cbdb = defaultdict(list)
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn not in AMBIGUOUS:
            continue
        ext = e.get("external_ids", {})
        cbdb_id = ext.get("cbdb_id") if isinstance(ext, dict) else None
        if cbdb_id:
            continue
        no_cbdb[dyn].append(e)

    print("=== 無 cbdb_id 的歧義 entity 統計 ===")
    for dyn, lst in sorted(no_cbdb.items(), key=lambda x: -len(x[1])):
        print(f"  dynasty={dyn:8s} {len(lst):>5}")

    # 對 dynasty=宋 無 cbdb_id 的，看 Work.period 分布
    print("\n=== dynasty=宋 無 cbdb_id 的 Work.period 分布 ===")
    song_no_cbdb = no_cbdb.get("宋", [])
    period_dist = Counter()
    for e in song_no_cbdb:
        ws = eid_to_works.get(e.get("id"), [])
        if not ws:
            period_dist["無 Work"] += 1
            continue
        ps = Counter(w.get("period") or "null" for w in ws)
        if len(ps) == 1:
            period_dist[list(ps.keys())[0]] += 1
        else:
            period_dist["multiple"] += 1
    for k, v in period_dist.most_common():
        print(f"  {k:20s} {v:>5}")

    # 列出 dynasty=宋 無 cbdb_id 的 entity（可能南朝宋的）
    print("\n=== dynasty=宋 無 cbdb_id 的 entity 列表 ===")
    for e in song_no_cbdb:
        by = e.get("birth_year")
        dy = e.get("death_year")
        ws = eid_to_works.get(e.get("id"), [])
        # 看 Work 是否見於隋志
        has_suizhi = False
        work_titles = []
        for w in ws[:3]:
            work_titles.append(w.get("title", ""))
            for item in w.get("indexed_by", []) or []:
                if isinstance(item, dict) and item.get("source") == "隋書經籍志":
                    has_suizhi = True
        years = f"{by or '?'}-{dy or '?'}"
        suizhi = "隋志" if has_suizhi else ""
        titles = "/".join(work_titles[:2]) if work_titles else "(無Work)"
        print(f"  {e.get('primary_name'):10s} ({years:12s}) {suizhi:4s} | {titles}")

    # dynasty=晉 無 cbdb_id
    print(f"\n=== dynasty=晉 無 cbdb_id 的 entity ({len(no_cbdb.get('晉', []))}) ===")
    for e in no_cbdb.get("晉", [])[:30]:
        by = e.get("birth_year")
        dy = e.get("death_year")
        ws = eid_to_works.get(e.get("id"), [])
        work_titles = [w.get("title", "") for w in ws[:2]]
        years = f"{by or '?'}-{dy or '?'}"
        titles = "/".join(work_titles) if work_titles else "(無Work)"
        print(f"  {e.get('primary_name'):10s} ({years:12s}) | {titles}")
    if len(no_cbdb.get("晉", [])) > 30:
        print(f"  ... 還有 {len(no_cbdb.get('晉', [])) - 30} 條")

    # dynasty=梁 無 cbdb_id
    print(f"\n=== dynasty=梁 無 cbdb_id 的 entity ({len(no_cbdb.get('梁', []))}) ===")
    for e in no_cbdb.get("梁", []):
        by = e.get("birth_year")
        dy = e.get("death_year")
        ws = eid_to_works.get(e.get("id"), [])
        work_titles = [w.get("title", "") for w in ws[:2]]
        years = f"{by or '?'}-{dy or '?'}"
        titles = "/".join(work_titles) if work_titles else "(無Work)"
        print(f"  {e.get('primary_name'):10s} ({years:12s}) | {titles}")

    # dynasty=周 無 cbdb_id
    print(f"\n=== dynasty=周 無 cbdb_id 的 entity ({len(no_cbdb.get('周', []))}) ===")
    for e in no_cbdb.get("周", []):
        by = e.get("birth_year")
        dy = e.get("death_year")
        ws = eid_to_works.get(e.get("id"), [])
        work_titles = [w.get("title", "") for w in ws[:2]]
        years = f"{by or '?'}-{dy or '?'}"
        titles = "/".join(work_titles) if work_titles else "(無Work)"
        print(f"  {e.get('primary_name'):10s} ({years:12s}) | {titles}")

    # dynasty=齊 無 cbdb_id
    print(f"\n=== dynasty=齊 無 cbdb_id 的 entity ({len(no_cbdb.get('齊', []))}) ===")
    for e in no_cbdb.get("齊", []):
        by = e.get("birth_year")
        dy = e.get("death_year")
        ws = eid_to_works.get(e.get("id"), [])
        work_titles = [w.get("title", "") for w in ws[:2]]
        years = f"{by or '?'}-{dy or '?'}"
        titles = "/".join(work_titles) if work_titles else "(無Work)"
        print(f"  {e.get('primary_name'):10s} ({years:12s}) | {titles}")

    # dynasty=魏 吳 蜀 陳 無 cbdb_id
    for dyn in ["魏", "吳", "蜀", "陳", "三國", "南北朝"]:
        lst = no_cbdb.get(dyn, [])
        if not lst:
            continue
        print(f"\n=== dynasty={dyn} 無 cbdb_id 的 entity ({len(lst)}) ===")
        for e in lst:
            by = e.get("birth_year")
            dy = e.get("death_year")
            ws = eid_to_works.get(e.get("id"), [])
            work_titles = [w.get("title", "") for w in ws[:2]]
            years = f"{by or '?'}-{dy or '?'}"
            titles = "/".join(work_titles) if work_titles else "(無Work)"
            print(f"  {e.get('primary_name'):10s} ({years:12s}) | {titles}")


if __name__ == "__main__":
    main()
