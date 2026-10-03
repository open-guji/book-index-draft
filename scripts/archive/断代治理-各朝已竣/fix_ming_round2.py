#!/usr/bin/env python3
"""
fix_ming_round2.py — 明朝未決 Round 2：383 條的 gazetteer_propagation

Round 1 遺留 383 條 period=ming 且 dynasty 空：
  - 380 no_author（authors=[]）
  - 3 mixed_sources（有 author 但 author/entity 無結論，來源混合國史經籍志/經義考/四庫）

普查結果：383 條 **100%** 含「明史藝文志」來源（明本朝斷代志，SCHEMA 自驗證 99% 屬明）。
  302 = 唯一志=明史藝文志 → 高置信 gazetteer_propagation 補 dynasty=明
  81 = 明史 + 其他志（宋史藝文志 / 四庫 / 國史經籍志 / 崇文總目 / 新唐書等）
        → 仍以本朝斷代志為主，補明並標註 `needs-review` 供人工覆核

同步 index/works。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MING_GAZETTEER = {"明史藝文志"}  # 明本朝斷代志


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def load_json(fp: Path):
    return json.loads(fp.read_text(encoding="utf-8"))


def write_json(fp: Path, data):
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iter_work_files(): return sorted(ROOT.glob("Work/?/?/?/*.json"))


def append_note(obj, text):
    old = obj.get("ai_note") or ""
    marker = f"[ming-round2: {text}]"
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

    works = {}; work_paths = {}
    for fp in iter_work_files():
        d = load_json(fp); works[d.get("id", fp.stem)] = d; work_paths[d.get("id", fp.stem)] = fp

    for wid, w in works.items():
        if w.get("period") != "ming": continue
        if w.get("dynasty"): continue

        srcs = set()
        for s in (w.get("indexed_by") or []):
            if isinstance(s, dict) and s.get("source"): srcs.add(s["source"])

        if not srcs:
            stats["skipped.no_source"] += 1
            skipped.append({"work_id": wid, "title": w.get("title"), "reason": "indexed_by 空"})
            continue

        if not (srcs & MING_GAZETTEER):
            stats["skipped.no_ming_gazetteer"] += 1
            skipped.append({"work_id": wid, "title": w.get("title"),
                            "reason": f"不含明史藝文志，sources={sorted(srcs)}"})
            continue

        w["dynasty"] = "明"
        if srcs <= MING_GAZETTEER:
            w["dynasty_basis"] = "gazetteer_propagation"
            append_note(w, "dynasty null→明; 唯一志=明史藝文志 (本朝斷代志 gazetteer_propagation)")
            stats["filled.only_ming_gazetteer"] += 1
        else:
            w["dynasty_basis"] = "gazetteer_propagation"
            others = sorted(srcs - MING_GAZETTEER)
            append_note(w,
                f"dynasty null→明; 主志=明史藝文志, 混他志={others} needs-review (gazetteer_propagation)")
            stats["filled.mixed_gazetteer"] += 1
        w["updated_at"] = now_iso()
        changed_work_ids.add(wid)

    if commit:
        for wid in changed_work_ids:
            write_json(work_paths[wid], works[wid])

        idx_dir = ROOT / "index"
        for shard_fp in sorted((idx_dir / "works").glob("*.json")):
            shard = load_json(shard_fp)
            changed_idx = False
            for wid, entry in shard.items():
                if not isinstance(entry, dict) or wid not in changed_work_ids or wid not in works: continue
                wk = works[wid]
                if entry.get("dynasty") != wk.get("dynasty"):
                    entry["dynasty"] = wk.get("dynasty")
                    changed_idx = True
                    stats["index.work.dynasty_sync"] += 1
            if changed_idx:
                write_json(shard_fp, shard)
                stats["index.work.shards_changed"] += 1

    print("=== 明朝未決 Round 2 統計 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:46s} {v:>5}")
    remaining = [(w.get("id"), w.get("title")) for w in works.values()
                 if w.get("period") == "ming" and not w.get("dynasty")]
    print(f"\nperiod=ming 仍空 dynasty: {len(remaining)} (應=0)")
    for wid, title in remaining[:5]: print(f"  {wid} {title}")
    print(f"\n棄權: {len(skipped)}")
    for s in skipped[:5]: print(f"  {s['work_id']} {s['title']} — {s['reason']}")


if __name__ == "__main__":
    main()
