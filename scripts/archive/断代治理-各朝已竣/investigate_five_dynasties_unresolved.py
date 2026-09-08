#!/usr/bin/env python3
"""
investigate_five_dynasties_unresolved.py — 五代十國未決項深度調查（只讀）

目的：
1. 從當前 main 數據中找出 period=five-dynasties 的真實未決項。
2. 區分「五代十國本輪可處理」與「應交由隋唐/秦漢/宋/晉等進程處理」。
3. 輸出可人工覆核的候選清單，不直接修改 Work/Entity/index。
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / ".claude" / "known-issues" / "cbdb_dy_cache.json"
OUT_PATH = ROOT / ".claude" / "known-issues" / "五代十國未決_深查.json"

AMBIGUOUS = {"宋", "晉", "梁", "周", "齊", "魏", "吳", "蜀", "陳", "漢", "唐", "三國", "南北朝", "南朝", "北朝"}
FD_CANON = {"後梁", "後唐", "後晉", "後漢", "後周", "五代", "前蜀", "後蜀", "楊吳", "南唐", "吳越", "閩"}
FD_RELEVANT_AMBIG = {"梁", "周", "吳", "蜀", "漢", "唐"}

CDY_TO_CANON = {
    "34": "後梁",
    "47": "後唐",
    "48": "後晉",
    "52": "後漢",
    "49": "後周",
    "7": "五代",
    "53": "三國蜀",
    "42": "三國吳",
    "44": "南朝梁",
    "31": "北周",
    "25": "東漢",
    "29": "西漢",
    "6": "唐",
    "13": "唐",
    "15": "宋",
}


def load_json(fp: Path):
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None


def iter_work_files():
    return sorted(ROOT.glob("Work/?/?/?/*.json"))


def iter_entity_files():
    return sorted(ROOT.glob("Entity/?/?/?/*.json"))


def sources_of(work: dict) -> list[str]:
    out = []
    for item in work.get("indexed_by", []) or []:
        if isinstance(item, dict) and item.get("source"):
            out.append(item["source"])
    return sorted(set(out))


def is_fd_cdy(entity: dict, cbdb_cache: dict) -> tuple[bool, str | None, str | None]:
    ext = entity.get("external_ids", {})
    cbdb_id = ext.get("cbdb_id") if isinstance(ext, dict) else None
    if not cbdb_id:
        return False, None, None
    entry = cbdb_cache.get(str(cbdb_id))
    if not entry or "error" in entry:
        return False, str(cbdb_id), None
    cdy = str(entry.get("dynasty_id", ""))
    return cdy in {"34", "47", "48", "52", "49", "7"}, str(cbdb_id), cdy


def classify_candidate(work: dict, author: dict, entity: dict | None, cbdb_cache: dict) -> tuple[str, str]:
    """回傳 (bucket, reason)。bucket 用於後續人工覆核分組。"""
    adyn = author.get("dynasty")
    wd = work.get("dynasty")
    wp = work.get("period")
    name = author.get("name", "")

    if wp == "five-dynasties" and wd in FD_CANON and adyn in FD_RELEVANT_AMBIG:
        if adyn == "唐" and wd == "後唐":
            return "high_confidence_fd", "Work.dynasty=後唐 且 author.dynasty=唐，可判後唐"
        if adyn == "漢" and wd == "後漢":
            return "high_confidence_fd", "Work.dynasty=後漢 且 author.dynasty=漢，可判後漢"
        if adyn == "梁" and wd == "後梁":
            return "high_confidence_fd", "Work.dynasty=後梁 且 author.dynasty=梁，可判後梁"
        if adyn == "周" and wd == "後周":
            return "high_confidence_fd", "Work.dynasty=後周 且 author.dynasty=周，可判後周"
        if adyn == "吳" and wd == "楊吳":
            return "high_confidence_fd", "Work.dynasty=楊吳 且 author.dynasty=吳，可判楊吳"
        if adyn == "蜀" and wd in {"前蜀", "後蜀"}:
            return "high_confidence_fd", f"Work.dynasty={wd} 且 author.dynasty=蜀，可判{wd}"

    if entity:
        is_fd, cbdb_id, cdy = is_fd_cdy(entity, cbdb_cache)
        if is_fd:
            return "high_confidence_fd", f"CBDB c_dy={cdy}->{CDY_TO_CANON.get(cdy)}"
        if cdy and cdy in CDY_TO_CANON and CDY_TO_CANON[cdy] not in FD_CANON:
            return "other_period_by_cbdb", f"CBDB c_dy={cdy}->{CDY_TO_CANON.get(cdy)}，非五代"

    if wp == "five-dynasties" and adyn in FD_RELEVANT_AMBIG:
        if adyn == "蜀":
            return "manual_fd_split", "Work.period=five-dynasties 且 author.dynasty=蜀，但需分前蜀/後蜀"
        if adyn in {"唐", "漢"}:
            return "manual_high_risk", f"Work.period=five-dynasties 且 author.dynasty={adyn}，同名異人風險高，需查人"
        return "manual_fd_split", f"Work.period=five-dynasties 且 author.dynasty={adyn}，需人工判定"

    if adyn in {"唐", "漢"}:
        return "handoff_other_process", f"author.dynasty={adyn} 大量殘留，應由隋唐/秦漢進程處理"

    return "other_unresolved", "非五代核心未決"


def main():
    works = {}
    entities = {}
    cbdb_cache = load_json(CACHE_PATH) or {}

    for fp in iter_work_files():
        d = load_json(fp)
        if d:
            works[d.get("id", fp.stem)] = d
    for fp in iter_entity_files():
        d = load_json(fp)
        if d:
            entities[d.get("id", fp.stem)] = d

    fd_works = [w for w in works.values() if w.get("period") == "five-dynasties"]

    summary = {
        "work_total": len(works),
        "entity_total": len(entities),
        "five_dynasties_work_total": len(fd_works),
        "five_dynasties_work_dynasty_distribution": Counter(w.get("dynasty") or "null" for w in fd_works),
        "five_dynasties_author_dynasty_distribution": Counter(),
    }

    candidates = []
    by_bucket = defaultdict(list)
    work_without_dynasty = []

    for w in fd_works:
        if not w.get("dynasty"):
            work_without_dynasty.append({
                "work_id": w.get("id"),
                "title": w.get("title"),
                "authors": [a.get("name") for a in w.get("authors", []) or [] if isinstance(a, dict)],
                "sources": sources_of(w),
            })
        for a in w.get("authors", []) or []:
            if not isinstance(a, dict):
                continue
            adyn = a.get("dynasty") or "null"
            summary["five_dynasties_author_dynasty_distribution"][adyn] += 1
            if adyn not in AMBIGUOUS:
                continue
            eid = a.get("entity_id")
            entity = entities.get(eid) if eid else None
            bucket, reason = classify_candidate(w, a, entity, cbdb_cache)
            rec = {
                "bucket": bucket,
                "reason": reason,
                "work_id": w.get("id"),
                "title": w.get("title"),
                "work_dynasty": w.get("dynasty"),
                "work_period": w.get("period"),
                "sources": sources_of(w),
                "author_name": a.get("name"),
                "author_dynasty": a.get("dynasty"),
                "author_entity_id": eid,
                "entity_dynasty": entity.get("dynasty") if entity else None,
                "entity_period": entity.get("period") if entity else None,
                "entity_birth_year": entity.get("birth_year") if entity else None,
                "entity_death_year": entity.get("death_year") if entity else None,
                "entity_has_cbdb": bool(entity and isinstance(entity.get("external_ids"), dict) and entity["external_ids"].get("cbdb_id")),
            }
            candidates.append(rec)
            by_bucket[bucket].append(rec)

    out = {
        "description": "五代十國未決項深度調查（只讀輸出）",
        "summary": {
            "work_total": summary["work_total"],
            "entity_total": summary["entity_total"],
            "five_dynasties_work_total": summary["five_dynasties_work_total"],
            "five_dynasties_work_dynasty_distribution": dict(summary["five_dynasties_work_dynasty_distribution"].most_common()),
            "five_dynasties_author_dynasty_distribution": dict(summary["five_dynasties_author_dynasty_distribution"].most_common()),
            "candidate_bucket_counts": {k: len(v) for k, v in sorted(by_bucket.items())},
            "work_without_dynasty_count": len(work_without_dynasty),
        },
        "work_without_dynasty": work_without_dynasty,
        "candidates": candidates,
        "by_bucket": {k: v for k, v in sorted(by_bucket.items())},
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("=== 五代十國未決深查 ===")
    print(f"Work 總數: {summary['work_total']}")
    print(f"Entity 總數: {summary['entity_total']}")
    print(f"period=five-dynasties Work: {len(fd_works)}")
    print("\nWork.dynasty 分布:")
    for k, v in summary["five_dynasties_work_dynasty_distribution"].most_common(20):
        print(f"  {k:12s} {v:>5}")
    print("\nAuthor.dynasty 分布:")
    for k, v in summary["five_dynasties_author_dynasty_distribution"].most_common(30):
        print(f"  {k:12s} {v:>5}")
    print("\n候選分組:")
    for k, v in sorted(by_bucket.items()):
        print(f"  {k:24s} {len(v):>5}")
    print(f"\n五代 Work 無 dynasty: {len(work_without_dynasty)}")
    print(f"輸出: {OUT_PATH}")


if __name__ == "__main__":
    main()
