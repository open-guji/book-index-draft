#!/usr/bin/env python3
"""
fix_sui_tang_round1.py — 隋唐未決項高置信修復（Round 1）

處理兩類高置信問題：
1. period=sui-tang 且 authors[].dynasty 俱屬 {隋,唐,隋唐} 的 Work，補 Work.dynasty。
   - 單值 → 該值；多值混合 → 隋唐。
2. Entity.dynasty 為 隋/唐 但 period 為空者，補 period=sui-tang（dynasty→period 派生）。

不處理（棄權，留待人工）：
- author.dynasty 含非隋唐值（如 北宋）之 period=sui-tang Work（manual_mixed）。
- 同名異人判定、Entity 合併（本輪只補 dynasty/period，不做去重）。

依據 SCHEMA：隋(c_dy=12)→sui-tang、唐(c_dy=13)→sui-tang、隋唐→sui-tang。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ST_CANON = {"隋", "唐", "隋唐"}
# dynasty → period 派生映射（隋唐相關）
DYN_TO_PERIOD = {"隋": "sui-tang", "唐": "sui-tang", "隋唐": "sui-tang"}


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


def append_note(obj: dict, text: str):
    old = obj.get("ai_note") or ""
    marker = f"[sui-tang-round1: {text}]"
    if marker not in old:
        obj["ai_note"] = (old + " " + marker).strip()


def compute_work_dynasty(work: dict) -> tuple[str | None, str | None]:
    """據 author.dynasty 推 Work.dynasty。回傳 (dynasty, reason)。
    含非隋唐值或全空時回傳 (None, reason)。"""
    authors = [a for a in (work.get("authors", []) or []) if isinstance(a, dict)]
    dyns = set()
    for a in authors:
        ad = a.get("dynasty")
        if ad:
            dyns.add(ad)
    if not dyns:
        return None, "authors 俱無 dynasty"
    if not dyns <= ST_CANON:
        return None, f"author.dynasty={dyns} 含非隋唐值，棄權"
    if len(dyns) == 1:
        d0 = next(iter(dyns))
        return d0, f"據唯一 author.dynasty「{d0}」補全"
    return "隋唐", f"據多作者 author.dynasty={dyns} 補全為隋唐"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    commit = args.commit or not args.dry_run

    stats = Counter()
    changed_work_ids = set()
    changed_entity_ids = set()
    skipped = []

    works = {}
    work_paths = {}
    for fp in iter_work_files():
        d = load_json(fp)
        works[d.get("id", fp.stem)] = d
        work_paths[d.get("id", fp.stem)] = fp

    entities = {}
    entity_paths = {}
    for fp in iter_entity_files():
        d = load_json(fp)
        entities[d.get("id", fp.stem)] = d
        entity_paths[d.get("id", fp.stem)] = fp

    # A. 補 period=sui-tang Work 之 dynasty
    for wid, w in works.items():
        if w.get("period") != "sui-tang":
            continue
        if w.get("dynasty"):
            continue  # 已有 dynasty
        new_dyn, reason = compute_work_dynasty(w)
        if not new_dyn:
            stats["A.work.skipped"] += 1
            skipped.append({
                "work_id": wid,
                "title": w.get("title"),
                "reason": reason,
                "authors": [{"name": a.get("name"), "dynasty": a.get("dynasty")}
                            for a in (w.get("authors", []) or []) if isinstance(a, dict)],
            })
            continue
        w["dynasty"] = new_dyn
        w["dynasty_basis"] = "author_propagation"
        append_note(w, f"dynasty null->{new_dyn}; {reason}")
        w["updated_at"] = now_iso()
        stats[f"A.work.dynasty_filled.{new_dyn}"] += 1
        changed_work_ids.add(wid)

    # B. 補 Entity 之 period（dynasty=隋/唐 但 period 空）
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn not in DYN_TO_PERIOD:
            continue
        if e.get("period"):
            continue  # 已有 period
        new_per = DYN_TO_PERIOD[dyn]
        e["period"] = new_per
        e["period_basis"] = "synonym"
        append_note(e, f"period null->{new_per}; 據 dynasty={dyn} 派生")
        e["updated_at"] = now_iso()
        stats[f"B.entity.period_filled.{dyn}"] += 1
        changed_entity_ids.add(eid)

    # C. 同步 index 分片
    if commit:
        for wid, w in works.items():
            write_json(work_paths[wid], w)
        for eid, e in entities.items():
            write_json(entity_paths[eid], e)

        idx_dir = ROOT / "index"
        for shard_fp in sorted((idx_dir / "works").glob("*.json")):
            shard = load_json(shard_fp)
            changed = False
            for wid, entry in shard.items():
                if not isinstance(entry, dict) or wid not in changed_work_ids or wid not in works:
                    continue
                w = works[wid]
                if entry.get("dynasty") != w.get("dynasty"):
                    entry["dynasty"] = w.get("dynasty")
                    changed = True
                    stats["C.index.work.dynasty_sync"] += 1
            if changed:
                write_json(shard_fp, shard)
                stats["C.index.work.shards_changed"] += 1

        for shard_fp in sorted((idx_dir / "entities").glob("*.json")):
            shard = load_json(shard_fp)
            changed = False
            for eid, entry in shard.items():
                if not isinstance(entry, dict) or eid not in changed_entity_ids or eid not in entities:
                    continue
                e = entities[eid]
                if entry.get("period") != e.get("period"):
                    entry["period"] = e.get("period")
                    changed = True
                    stats["C.index.entity.period_sync"] += 1
            if changed:
                write_json(shard_fp, shard)
                stats["C.index.entity.shards_changed"] += 1

    print("=== 隋唐未決 Round 1 統計 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:42s} {v:>5}")

    # 驗證：sui-tang 仍無 dynasty 的 Work
    remaining = []
    for w in works.values():
        if w.get("period") == "sui-tang" and not w.get("dynasty"):
            remaining.append((w.get("id"), w.get("title")))
    print(f"\nperiod=sui-tang 但 dynasty 仍空的 Work: {len(remaining)}")
    for wid, title in remaining[:20]:
        print(f"  {wid} {title}")

    print(f"\n棄權（manual）: {len(skipped)}")
    for s in skipped[:20]:
        print(f"  {s['work_id']} {s['title']} — {s['reason']}")


if __name__ == "__main__":
    main()
