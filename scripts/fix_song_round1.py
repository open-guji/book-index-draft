#!/usr/bin/env python3
"""
fix_song_round1.py — 宋代整理第一轮

高置信范围：
1. Entity.dynasty 已是 北宋/南宋，但 period 为空 → 补 period=song。
2. Work 的 authors[].dynasty 唯一且为 北宋/南宋，Work 顶层 period/dynasty 为空
   → 补 Work.period=song 与 Work.dynasty=北宋/南宋。

不处理：
- dynasty=宋 的北/南宋拆分（仍需进一步查证）。
- Author.dynasty=宋 的大批残留。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / ".claude" / "known-issues" / "宋代整理_round1_未決.json"
SONG_DYNASTIES = {"北宋", "南宋"}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def load_json(fp: Path):
    return json.loads(fp.read_text(encoding="utf-8"))


def write_json(fp: Path, data):
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iter_work_files():
    return sorted(ROOT.glob("Work/?/?/?/*.json"))


def iter_entity_files():
    return sorted(ROOT.glob("Entity/?/?/?/*.json"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    commit = args.commit or not args.dry_run

    works = {}
    work_paths = {}
    entities = {}
    entity_paths = {}
    stats = Counter()
    changed_work_ids = set()
    changed_entity_ids = set()

    for fp in iter_work_files():
        d = load_json(fp)
        works[d.get("id", fp.stem)] = d
        work_paths[d.get("id", fp.stem)] = fp
    for fp in iter_entity_files():
        d = load_json(fp)
        entities[d.get("id", fp.stem)] = d
        entity_paths[d.get("id", fp.stem)] = fp

    # A. Entity period 补齐
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn in SONG_DYNASTIES and not e.get("period"):
            e["period"] = "song"
            e["period_basis"] = f"据 dynasty「{dyn}」自动归并"
            e["updated_at"] = now_iso()
            changed_entity_ids.add(eid)
            stats[f"A.entity.period_filled.{dyn}"] += 1

    # B. Work 顶层 period/dynasty 补齐
    for wid, w in works.items():
        # 只处理 period 为空或已是 song 的 Work；其他 period 不在本轮范围内
        if w.get("period") not in (None, "song"):
            continue
        author_dyns = set()
        for a in w.get("authors", []) or []:
            if isinstance(a, dict) and a.get("dynasty") in SONG_DYNASTIES:
                author_dyns.add(a["dynasty"])
        if len(author_dyns) != 1:
            continue
        new_dyn = next(iter(author_dyns))
        changed = False
        if not w.get("dynasty"):
            w["dynasty"] = new_dyn
            w["dynasty_basis"] = f"据唯一 author.dynasty「{new_dyn}」补全"
            stats[f"B.work.dynasty_filled.{new_dyn}"] += 1
            changed = True
        if not w.get("period"):
            w["period"] = "song"
            w["period_basis"] = f"据唯一 author.dynasty「{new_dyn}」自动归并"
            stats[f"B.work.period_filled.{new_dyn}"] += 1
            changed = True
        if changed:
            w["updated_at"] = now_iso()
            changed_work_ids.add(wid)

    # C. 生成未决清单
    unresolved = {
        "description": "宋代整理 Round 1 后未决清单",
        "remaining_work_dynasty_song": [],
        "remaining_author_dynasty_song": [],
        "remaining_entity_dynasty_song": [],
        "stats": dict(stats),
    }
    for wid, w in works.items():
        if w.get("dynasty") == "宋":
            unresolved["remaining_work_dynasty_song"].append({
                "work_id": wid,
                "title": w.get("title"),
                "period": w.get("period"),
                "authors": [
                    {"name": a.get("name"), "dynasty": a.get("dynasty"), "entity_id": a.get("entity_id")}
                    for a in w.get("authors", []) or []
                    if isinstance(a, dict)
                ],
            })
        for a in w.get("authors", []) or []:
            if isinstance(a, dict) and a.get("dynasty") == "宋":
                unresolved["remaining_author_dynasty_song"].append({
                    "work_id": wid,
                    "title": w.get("title"),
                    "work_period": w.get("period"),
                    "work_dynasty": w.get("dynasty"),
                    "author_name": a.get("name"),
                    "entity_id": a.get("entity_id"),
                })
    for eid, e in entities.items():
        if e.get("dynasty") == "宋":
            unresolved["remaining_entity_dynasty_song"].append({
                "entity_id": eid,
                "name": e.get("primary_name"),
                "period": e.get("period"),
                "birth_year": e.get("birth_year"),
                "death_year": e.get("death_year"),
                "cbdb_id": (e.get("external_ids") or {}).get("cbdb_id") if isinstance(e.get("external_ids"), dict) else None,
            })

    if commit:
        for wid in changed_work_ids:
            write_json(work_paths[wid], works[wid])
        for eid in changed_entity_ids:
            write_json(entity_paths[eid], entities[eid])
        write_json(OUT_PATH, unresolved)

        idx_dir = ROOT / "index"
        for shard_fp in sorted((idx_dir / "works").glob("*.json")):
            shard = load_json(shard_fp)
            changed = False
            for wid, entry in shard.items():
                if not isinstance(entry, dict) or wid not in changed_work_ids:
                    continue
                w = works[wid]
                if entry.get("dynasty") != w.get("dynasty"):
                    entry["dynasty"] = w.get("dynasty")
                    stats["C.index.work.dynasty_sync"] += 1
                    changed = True
                if entry.get("period") != w.get("period"):
                    entry["period"] = w.get("period")
                    stats["C.index.work.period_sync"] += 1
                    changed = True
            if changed:
                write_json(shard_fp, shard)
                stats["C.index.work.shards_changed"] += 1

        for shard_fp in sorted((idx_dir / "entities").glob("*.json")):
            shard = load_json(shard_fp)
            changed = False
            for eid, entry in shard.items():
                if not isinstance(entry, dict) or eid not in changed_entity_ids:
                    continue
                e = entities[eid]
                if entry.get("period") != e.get("period"):
                    entry["period"] = e.get("period")
                    stats["C.index.entity.period_sync"] += 1
                    changed = True
                if entry.get("dynasty") != e.get("dynasty"):
                    entry["dynasty"] = e.get("dynasty")
                    stats["C.index.entity.dynasty_sync"] += 1
                    changed = True
            if changed:
                write_json(shard_fp, shard)
                stats["C.index.entity.shards_changed"] += 1

        # index 同步统计回写到未决清单
        unresolved["stats"] = dict(stats)
        write_json(OUT_PATH, unresolved)

    print("=== 宋代整理 Round 1 统计 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:42s} {v:>6}")
    print("\n未决：")
    print(f"  Work.dynasty=宋: {len(unresolved['remaining_work_dynasty_song'])}")
    print(f"  Author.dynasty=宋: {len(unresolved['remaining_author_dynasty_song'])}")
    print(f"  Entity.dynasty=宋: {len(unresolved['remaining_entity_dynasty_song'])}")
    print(f"  输出: {OUT_PATH}")


if __name__ == "__main__":
    main()
