#!/usr/bin/env python3
"""
fix_qing_round1.py — 清朝整理首轮高置信修复

处理范围：
- 只处理 Work 顶层 dynasty 为空、period=qing、且非通用作者 dynasty 唯一为「清」的条目。
- 为这些 Work 补 `dynasty=清`，并同步 `index/works` 分片。

安全边界：
- 不处理 period 为空或非 qing 的 Work，避免书名所指时代与作者时代混淆。
- 不处理 Entity.dynasty=清 但 period 缺失/冲突者；这些样本混有同名异人与旧批次疑点，留未决清单。
- 不修改作者层 dynasty；本轮只补 Work 顶层 dynasty。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / ".claude" / "known-issues" / "清朝整理_round1_未決.json"

GENERIC_NAMES = {"佚名", "不著撰人", "□□", "", None}


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


def author_dynasties(w):
    dyns = set()
    for a in w.get("authors", []) or []:
        if not isinstance(a, dict):
            continue
        if a.get("name") in GENERIC_NAMES:
            continue
        if a.get("dynasty"):
            dyns.add(a.get("dynasty"))
    return dyns


def author_names(w):
    return [a.get("name") for a in w.get("authors", []) or [] if isinstance(a, dict)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    commit = args.commit or not args.dry_run

    works = {}
    work_paths = {}
    entities = {}
    stats = Counter()
    changed_work_ids = set()

    for fp in iter_work_files():
        w = load_json(fp)
        wid = w.get("id", fp.stem)
        works[wid] = w
        work_paths[wid] = fp
    for fp in iter_entity_files():
        e = load_json(fp)
        eid = e.get("id", fp.stem)
        entities[eid] = e

    unresolved = {
        "description": "清朝整理 Round 1 后未决清单",
        "scope": "只机械补全 period=qing 且非通用作者 dynasty 唯一为清的 Work.dynasty",
        "remaining_work_empty_dynasty_authors_all_qing_non_qing_period": [],
        "remaining_entity_qing_period_missing": [],
        "remaining_entity_qing_period_conflict": [],
        "stats": {},
    }

    # A. Work 顶层 dynasty 补全
    for wid, w in works.items():
        if w.get("dynasty"):
            continue
        dyns = author_dynasties(w)
        if dyns != {"清"}:
            continue
        if w.get("period") == "qing":
            w["dynasty"] = "清"
            w["dynasty_basis"] = "qing_round1:period=qing 且非通用作者 dynasty 唯一为「清」"
            w["updated_at"] = now_iso()
            changed_work_ids.add(wid)
            stats["A.work.dynasty_empty->清"] += 1
        else:
            unresolved["remaining_work_empty_dynasty_authors_all_qing_non_qing_period"].append({
                "work_id": wid,
                "title": w.get("title"),
                "period": w.get("period"),
                "authors": author_names(w),
            })

    # B. Entity 疑点只列未决，不机械修改
    for eid, e in entities.items():
        if e.get("dynasty") != "清":
            continue
        if not e.get("period"):
            unresolved["remaining_entity_qing_period_missing"].append({
                "entity_id": eid,
                "name": e.get("primary_name"),
                "cbdb_id": (e.get("external_ids") or {}).get("cbdb_id") if isinstance(e.get("external_ids"), dict) else None,
                "works": e.get("works", []),
            })
        elif e.get("period") != "qing":
            unresolved["remaining_entity_qing_period_conflict"].append({
                "entity_id": eid,
                "name": e.get("primary_name"),
                "period": e.get("period"),
                "cbdb_id": (e.get("external_ids") or {}).get("cbdb_id") if isinstance(e.get("external_ids"), dict) else None,
                "works": e.get("works", []),
            })

    # C. 写回 Work 与同步 index/works
    if commit:
        for wid in changed_work_ids:
            write_json(work_paths[wid], works[wid])

        for shard_fp in sorted((ROOT / "index" / "works").glob("*.json")):
            shard = load_json(shard_fp)
            changed = False
            for wid, entry in shard.items():
                if not isinstance(entry, dict) or wid not in changed_work_ids:
                    continue
                w = works[wid]
                if entry.get("dynasty") != w.get("dynasty"):
                    entry["dynasty"] = w.get("dynasty")
                    stats["B.index.work.dynasty_sync"] += 1
                    changed = True
                if entry.get("period") != w.get("period"):
                    entry["period"] = w.get("period")
                    stats["B.index.work.period_sync"] += 1
                    changed = True
            if changed:
                write_json(shard_fp, shard)
                stats["B.index.work.shards_changed"] += 1

        unresolved["stats"] = dict(stats)
        write_json(OUT_PATH, unresolved)
    else:
        unresolved["stats"] = dict(stats)

    print("=== 清朝整理 Round 1 统计 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:44s} {v:>8}")
    print("\n未决：")
    print(
        "  Work.dynasty 空且作者均清但 period 非 qing: "
        f"{len(unresolved['remaining_work_empty_dynasty_authors_all_qing_non_qing_period'])}"
    )
    print(f"  Entity.dynasty=清 且 period 缺失: {len(unresolved['remaining_entity_qing_period_missing'])}")
    print(f"  Entity.dynasty=清 且 period 冲突: {len(unresolved['remaining_entity_qing_period_conflict'])}")
    print(f"  输出: {OUT_PATH}")


if __name__ == "__main__":
    main()
