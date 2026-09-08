#!/usr/bin/env python3
"""
fix_five_dynasties_unresolved_round2.py — 五代十國未決項深查後修復

處理兩類高置信問題：
1. period=five-dynasties 且 authors[].dynasty 已是五代規範值的 Work，補 Work.dynasty。
2. 誤標為 five-dynasties 的北周/隋志相關條目，移出 five-dynasties。

不處理：
- dynasty=唐/漢 的大批殘留（交由隋唐/秦漢進程）。
- Entity 合併（本輪只修正朝代/period，不做去重）。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FD_CANON = {"後梁", "後唐", "後晉", "後漢", "後周", "五代", "前蜀", "後蜀", "楊吳", "南唐", "吳越", "閩"}

# 誤入 five-dynasties 的 Work：深查後可安全移出
WORK_PERIOD_FIXES = {
    # 隋書經籍志著錄，作者「釋亡名」不可作五代後周；具體朝代待考，先移出五代
    "1evc5p8qzyj9c": {
        "period": None,
        "dynasty": None,
        "author_dynasty": None,
        "reason": "釋亡名《周易私記》見於隋書經籍志，非五代後周；具體朝代待考",
    },
    # 樊深，字文深，北周經學家；《隋書經籍志》徑稱樊文深
    "1evgor4uysnpc": {
        "period": "nanbeichao",
        "dynasty": "北周",
        "author_dynasty": "北周",
        "reason": "樊文深即樊深，字文深，北周經學家，非五代後周",
    },
    # 盧辨，北周人（《周書》有傳），非五代後周
    "1evgor9k1czr4": {
        "period": "nanbeichao",
        "dynasty": "北周",
        "author_dynasty": "北周",
        "reason": "盧辨為北周人，非五代後周",
    },
    # 「周沈重」中的「周」為北周朝代前綴
    "1evr5e3mezpiz": {
        "period": "nanbeichao",
        "dynasty": "北周",
        "author_dynasty": "北周",
        "reason": "周沈重之「周」為北周朝代前綴，非五代後周",
    },
    # 「周熊安生」中的「周」為北周朝代前綴
    "1evr5e3mezpj0": {
        "period": "nanbeichao",
        "dynasty": "北周",
        "author_dynasty": "北周",
        "reason": "周熊安生之「周」為北周朝代前綴，非五代後周",
    },
}

# 上述 Work 所連到的 Entity，也一併修正 dynasty/period
ENTITY_FIXES = {
    "1j96heygyjb40": {
        "dynasty": None,
        "period": None,
        "reason": "釋亡名見於隋書經籍志，非五代後周；具體朝代待考",
    },
    "1j96hfopi0l4w": {
        "dynasty": "北周",
        "period": "nanbeichao",
        "reason": "樊文深即樊深，北周經學家",
    },
    "1j96hfotnj9c0": {
        "dynasty": "北周",
        "period": "nanbeichao",
        "reason": "盧辨為北周人",
    },
    "1j96hehpxary8": {
        "dynasty": "北周",
        "period": "nanbeichao",
        "reason": "周沈重之「周」為北周朝代前綴",
    },
    "1j96hehqe5la8": {
        "dynasty": "北周",
        "period": "nanbeichao",
        "reason": "周熊安生之「周」為北周朝代前綴",
    },
}


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
    marker = f"[five-dynasties-round2: {text}]"
    if marker not in old:
        obj["ai_note"] = (old + " " + marker).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    commit = args.commit or not args.dry_run

    stats = Counter()
    changed_work_ids = set()
    changed_entity_ids = set()

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

    # A. 先修正誤入五代的 Work
    for wid, fix in WORK_PERIOD_FIXES.items():
        w = works.get(wid)
        if not w:
            continue
        old_period = w.get("period")
        old_dynasty = w.get("dynasty")
        w["period"] = fix["period"]
        w["dynasty"] = fix["dynasty"]
        w["period_basis"] = fix["reason"] if fix["period"] else None
        if fix["dynasty"]:
            w["dynasty_basis"] = fix["reason"]
        else:
            w.pop("dynasty_basis", None)
        changed_author = False
        for a in w.get("authors", []) or []:
            if isinstance(a, dict):
                if a.get("dynasty") != fix["author_dynasty"]:
                    a["dynasty"] = fix["author_dynasty"]
                    if fix["author_dynasty"]:
                        a["dynasty_basis"] = fix["reason"]
                    else:
                        a.pop("dynasty_basis", None)
                    changed_author = True
        append_note(w, f"period {old_period}->{fix['period']}, dynasty {old_dynasty}->{fix['dynasty']}; {fix['reason']}")
        w["updated_at"] = now_iso()
        stats[f"A.work.period_fix.{fix['dynasty'] or 'null'}"] += 1
        changed_work_ids.add(wid)
        if changed_author:
            stats["A.work.author_dynasty_fixed"] += 1

    # B. 五代 Work.dynasty 補全（排除已被 A 移出五代者）
    for wid, w in works.items():
        if w.get("period") == "five-dynasties" and w.get("dynasty") in FD_CANON:
            # 即使 Work 已在前次執行中補好，也要納入 index 同步集合
            changed_work_ids.add(wid)
        if w.get("period") != "five-dynasties" or w.get("dynasty"):
            continue
        author_dyns = set()
        for a in w.get("authors", []) or []:
            if isinstance(a, dict) and a.get("dynasty") in FD_CANON:
                author_dyns.add(a.get("dynasty"))
        if len(author_dyns) == 1:
            new_dyn = author_dyns.pop()
            w["dynasty"] = new_dyn
            w["dynasty_basis"] = f"據唯一五代 author.dynasty「{new_dyn}」補全"
            w["updated_at"] = now_iso()
            stats[f"B.work.dynasty_filled.{new_dyn}"] += 1
            changed_work_ids.add(wid)

    # C. 修正相關 Entity
    for eid, fix in ENTITY_FIXES.items():
        e = entities.get(eid)
        if not e:
            continue
        old_dynasty = e.get("dynasty")
        old_period = e.get("period")
        e["dynasty"] = fix["dynasty"]
        e["period"] = fix["period"]
        if fix["dynasty"]:
            e["dynasty_basis"] = fix["reason"]
        else:
            e.pop("dynasty_basis", None)
        if fix["period"]:
            e["period_basis"] = fix["reason"]
        else:
            e.pop("period_basis", None)
        e["updated_at"] = now_iso()
        stats[f"C.entity.fixed.{fix['dynasty'] or 'null'}"] += 1
        changed_entity_ids.add(eid)
        if old_dynasty != fix["dynasty"] or old_period != fix["period"]:
            stats["C.entity.changed"] += 1

    # D. 同步 index 分片
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
                    stats["D.index.work.dynasty_sync"] += 1
                if entry.get("period") != w.get("period"):
                    entry["period"] = w.get("period")
                    changed = True
                    stats["D.index.work.period_sync"] += 1
            if changed:
                write_json(shard_fp, shard)
                stats["D.index.work.shards_changed"] += 1

        for shard_fp in sorted((idx_dir / "entities").glob("*.json")):
            shard = load_json(shard_fp)
            changed = False
            for eid, entry in shard.items():
                if not isinstance(entry, dict) or eid not in changed_entity_ids or eid not in entities:
                    continue
                e = entities[eid]
                if entry.get("dynasty") != e.get("dynasty"):
                    entry["dynasty"] = e.get("dynasty")
                    changed = True
                    stats["D.index.entity.dynasty_sync"] += 1
                if entry.get("period") != e.get("period"):
                    entry["period"] = e.get("period")
                    changed = True
                    stats["D.index.entity.period_sync"] += 1
            if changed:
                write_json(shard_fp, shard)
                stats["D.index.entity.shards_changed"] += 1

    print("=== 五代十國未決 Round 2 統計 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:42s} {v:>5}")

    remaining_fd_no_dyn = []
    for w in works.values():
        if w.get("period") == "five-dynasties" and not w.get("dynasty"):
            remaining_fd_no_dyn.append((w.get("id"), w.get("title")))
    print(f"\nperiod=five-dynasties 但 dynasty 仍空的 Work: {len(remaining_fd_no_dyn)}")
    for wid, title in remaining_fd_no_dyn[:20]:
        print(f"  {wid} {title}")


if __name__ == "__main__":
    main()
