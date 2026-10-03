#!/usr/bin/env python3
"""
analyze_qing_round1.py — 清朝整理首轮只读分析

目标：
1. 统计 Work / Author / Entity 中 dynasty=清、period=qing、period 缺失的分布。
2. 找出可高置信机械修复的候选：
   - Work.dynasty=清 但 period 缺失或非 qing。
   - Entity.dynasty=清 但 period 缺失或非 qing。
   - Work 顶层 dynasty 缺失，但非通用作者 dynasty 唯一为清。
3. 检查 Work / Entity 与 index 分片的 dynasty/period 不一致。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GENERIC_NAMES = {"佚名", "不著撰人", "□□", "", None}


def load_json(fp: Path):
    return json.loads(fp.read_text(encoding="utf-8"))


def iter_work_files():
    return sorted(ROOT.glob("Work/?/?/?/*.json"))


def iter_entity_files():
    return sorted(ROOT.glob("Entity/?/?/?/*.json"))


def value_key(v):
    return v if v not in ("", None) else "<empty>"


def main():
    works = {}
    entities = {}
    stats = Counter()
    samples: dict[str, list[dict]] = {
        "work_qing_period_missing": [],
        "work_qing_period_conflict": [],
        "work_dynasty_empty_authors_all_qing": [],
        "entity_qing_period_missing": [],
        "entity_qing_period_conflict": [],
        "work_index_mismatch": [],
        "entity_index_mismatch": [],
    }

    for fp in iter_work_files():
        w = load_json(fp)
        wid = w.get("id", fp.stem)
        works[wid] = w
        dyn = w.get("dynasty")
        per = w.get("period")
        stats[f"work.dynasty.{value_key(dyn)}"] += 1
        stats[f"work.period.{value_key(per)}"] += 1
        if dyn == "清":
            stats["work.dynasty_qing.total"] += 1
            if not per:
                stats["candidate.work_qing_period_missing"] += 1
                if len(samples["work_qing_period_missing"]) < 30:
                    samples["work_qing_period_missing"].append({"work_id": wid, "title": w.get("title")})
            elif per != "qing":
                stats["candidate.work_qing_period_conflict"] += 1
                if len(samples["work_qing_period_conflict"]) < 30:
                    samples["work_qing_period_conflict"].append({"work_id": wid, "title": w.get("title"), "period": per})

        author_dyns = set()
        for a in w.get("authors", []) or []:
            if not isinstance(a, dict):
                continue
            ad = a.get("dynasty")
            stats[f"author.dynasty.{value_key(ad)}"] += 1
            if a.get("name") not in GENERIC_NAMES and ad:
                author_dyns.add(ad)
        if (not dyn) and author_dyns == {"清"}:
            stats["candidate.work_dynasty_empty_authors_all_qing"] += 1
            if len(samples["work_dynasty_empty_authors_all_qing"]) < 30:
                samples["work_dynasty_empty_authors_all_qing"].append({
                    "work_id": wid,
                    "title": w.get("title"),
                    "period": per,
                    "authors": [a.get("name") for a in w.get("authors", []) if isinstance(a, dict)],
                })

    for fp in iter_entity_files():
        e = load_json(fp)
        eid = e.get("id", fp.stem)
        entities[eid] = e
        dyn = e.get("dynasty")
        per = e.get("period")
        stats[f"entity.dynasty.{value_key(dyn)}"] += 1
        stats[f"entity.period.{value_key(per)}"] += 1
        if dyn == "清":
            stats["entity.dynasty_qing.total"] += 1
            if not per:
                stats["candidate.entity_qing_period_missing"] += 1
                if len(samples["entity_qing_period_missing"]) < 30:
                    samples["entity_qing_period_missing"].append({
                        "entity_id": eid,
                        "name": e.get("primary_name"),
                        "cbdb_id": (e.get("external_ids") or {}).get("cbdb_id") if isinstance(e.get("external_ids"), dict) else None,
                    })
            elif per != "qing":
                stats["candidate.entity_qing_period_conflict"] += 1
                if len(samples["entity_qing_period_conflict"]) < 30:
                    samples["entity_qing_period_conflict"].append({"entity_id": eid, "name": e.get("primary_name"), "period": per})

    idx_dir = ROOT / "index"
    for shard_fp in sorted((idx_dir / "works").glob("*.json")):
        shard = load_json(shard_fp)
        for wid, entry in shard.items():
            if not isinstance(entry, dict) or wid not in works:
                continue
            w = works[wid]
            if entry.get("dynasty") != w.get("dynasty") or entry.get("period") != w.get("period"):
                stats["index.work_mismatch"] += 1
                if len(samples["work_index_mismatch"]) < 30:
                    samples["work_index_mismatch"].append({
                        "work_id": wid,
                        "title": w.get("title"),
                        "file_dynasty": w.get("dynasty"),
                        "index_dynasty": entry.get("dynasty"),
                        "file_period": w.get("period"),
                        "index_period": entry.get("period"),
                    })

    for shard_fp in sorted((idx_dir / "entities").glob("*.json")):
        shard = load_json(shard_fp)
        for eid, entry in shard.items():
            if not isinstance(entry, dict) or eid not in entities:
                continue
            e = entities[eid]
            if entry.get("dynasty") != e.get("dynasty") or entry.get("period") != e.get("period"):
                stats["index.entity_mismatch"] += 1
                if len(samples["entity_index_mismatch"]) < 30:
                    samples["entity_index_mismatch"].append({
                        "entity_id": eid,
                        "name": e.get("primary_name"),
                        "file_dynasty": e.get("dynasty"),
                        "index_dynasty": entry.get("dynasty"),
                        "file_period": e.get("period"),
                        "index_period": entry.get("period"),
                    })

    print("=== 清朝整理 Round 1 只读分析 ===")
    for key in [
        "work.dynasty_qing.total",
        "entity.dynasty_qing.total",
        "candidate.work_qing_period_missing",
        "candidate.work_qing_period_conflict",
        "candidate.entity_qing_period_missing",
        "candidate.entity_qing_period_conflict",
        "candidate.work_dynasty_empty_authors_all_qing",
        "index.work_mismatch",
        "index.entity_mismatch",
    ]:
        print(f"{key:48s} {stats.get(key, 0):>8}")

    print("\nTop work.period:")
    for k, v in stats.items():
        if k.startswith("work.period."):
            print(f"  {k[12:]:24s} {v:>8}")

    print("\nTop entity.period:")
    for k, v in stats.items():
        if k.startswith("entity.period."):
            print(f"  {k[14:]:24s} {v:>8}")

    print("\nSamples:")
    print(json.dumps(samples, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
