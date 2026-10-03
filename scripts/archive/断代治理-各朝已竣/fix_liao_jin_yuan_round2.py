#!/usr/bin/env python3
"""
fix_liao_jin_yuan_round2.py — 遼金元未決 Round 2：328 no_author 的 gazetteer_propagation

Round 1 已由 author.dynasty 補 3898 Work.dynasty。剩 328 條 period=liao-jin-yuan
且 dynasty 空的 Work 俱為 authors=[]（no_author）。本輪針對 no_author 應用：

規則（參 SCHEMA §「以庫中資料自驗」）：
  indexed_by 來源集合是「遼金元斷代志」子集且不為空 → Work.dynasty = 遼金元
  · 遼金元斷代志 = {元史藝文志, 補遼金元藝文志, 遼史藝文志, 金史藝文志}（庫中自驗 96%）
  · 若來源含非斷代志（如國史經籍志=明焦竑通代志、隋書經籍志）則棄權

寫入：
  Work.dynasty = 遼金元
  Work.dynasty_basis = gazetteer_propagation
  Work.updated_at
  Work.ai_note 記錄依據的志
同步 index/works 分片（dynasty 欄位）。

Round 1 的其他處置（王厚之移出遼金元、李康 override、Entity.period 等）不重複。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LJY_GAZETTEERS = {"元史藝文志", "補遼金元藝文志", "遼史藝文志", "金史藝文志"}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def load_json(fp: Path):
    return json.loads(fp.read_text(encoding="utf-8"))


def write_json(fp: Path, data):
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iter_work_files():
    return sorted(ROOT.glob("Work/?/?/?/*.json"))


def append_note(obj: dict, text: str):
    old = obj.get("ai_note") or ""
    marker = f"[ljy-round2: {text}]"
    if marker not in old:
        obj["ai_note"] = (old + " " + marker).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    commit = not args.dry_run

    stats = Counter()
    changed_work_ids = set()
    skipped = []

    works = {}
    work_paths = {}
    for fp in iter_work_files():
        d = load_json(fp)
        works[d.get("id", fp.stem)] = d
        work_paths[d.get("id", fp.stem)] = fp

    for wid, w in works.items():
        # Round 2 只處理：period=liao-jin-yuan + dynasty 空 + authors 空
        if w.get("period") != "liao-jin-yuan":
            continue
        if w.get("dynasty"):
            continue
        authors = [a for a in (w.get("authors", []) or []) if isinstance(a, dict)]
        if authors:
            continue  # Round 1 應已處理，不重複

        srcs = set()
        for item in w.get("indexed_by", []) or []:
            if isinstance(item, dict) and item.get("source"):
                srcs.add(item["source"])
        if not srcs:
            stats["skipped.no_source"] += 1
            skipped.append({"work_id": wid, "title": w.get("title"), "reason": "indexed_by 空"})
            continue

        non_gaz = srcs - LJY_GAZETTEERS
        if non_gaz:
            stats["skipped.mixed_source"] += 1
            skipped.append({
                "work_id": wid, "title": w.get("title"),
                "reason": f"來源含非遼金元斷代志: {sorted(non_gaz)}",
                "sources": sorted(srcs),
            })
            continue

        if not (srcs & LJY_GAZETTEERS):
            stats["skipped.no_gazetteer"] += 1
            skipped.append({"work_id": wid, "title": w.get("title"), "reason": "無遼金元斷代志來源"})
            continue

        # 通過：來源集合是 LJY_GAZETTEERS 子集且不為空
        w["dynasty"] = "遼金元"
        w["dynasty_basis"] = "gazetteer_propagation"
        append_note(w, "dynasty null→遼金元; 來源=" + ",".join(sorted(srcs)))
        w["updated_at"] = now_iso()
        changed_work_ids.add(wid)
        stats["filled.by_gazetteer"] += 1

    if commit:
        for wid in changed_work_ids:
            write_json(work_paths[wid], works[wid])

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
                    stats["index.work.dynasty_sync"] += 1
            if changed:
                write_json(shard_fp, shard)
                stats["index.work.shards_changed"] += 1

    print("=== 遼金元未決 Round 2 統計 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:42s} {v:>5}")

    remaining = []
    for w in works.values():
        if w.get("period") == "liao-jin-yuan" and not w.get("dynasty"):
            remaining.append((w.get("id"), w.get("title")))
    print(f"\nperiod=liao-jin-yuan 但 dynasty 仍空的 Work: {len(remaining)} (Round 2 應 = 11 skipped.mixed_source)")
    for wid, title in remaining[:15]:
        print(f"  {wid} {title}")

    print(f"\n棄權 ({len(skipped)}):")
    for s in skipped[:12]:
        print(f"  {s['work_id']} {s['title']} — {s['reason']}")


if __name__ == "__main__":
    main()
