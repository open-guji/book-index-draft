#!/usr/bin/env python3
"""題名重出 Round 1：合併 8 組低風險「題名+撰人」式空殼 Work。

約束：
- 舊 Work 無 books/resources/fragments/collated。
- 只改命中舊 ID 的引用檔；大型整理本用原文替換，不重排 JSON。
- 舊 Work 檔由外層刪除。
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".claude" / "known-issues" / "題名重出_round1已合併.json"

PAIRS = [
    ("1evc5peeyakn4", "1evftehvk711c", "辯釋名韋昭撰 → 辯釋名"),
    ("1evc5pef3adc0", "1evfubxt4iebk", "五經音徐邈撰 → 五經音"),
    ("1evc5perrnbi8", "1evfubyqlef40", "吳章陸機撰 → 吳章"),
    ("1evc5pes1bocg", "1evfubz0qxb7k", "少學楊方撰 → 少學"),
    ("1evc5pex4jz7k", "1evgordf7ybcw", "字宗薛立撰 → 字宗"),
    ("1evc5pey3ik1s", "1evgorfk6kow0", "聲韻周研撰 → 聲韻"),
    ("1evc5pezmgbnk", "1evcpjzuz169s", "四聲沈約撰 → 四聲"),
    ("1evc5pf00i03k", "1evgorg5qknb4", "韻英釋靜洪撰 → 韻英"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def work_index() -> dict:
    idx = {}
    for shard in "0123456789abcdef":
        idx.update(load_json(ROOT / "index" / "works" / f"{shard}.json"))
    return idx


def unique_dicts(items, keys):
    out = []
    seen = set()
    for item in items or []:
        if not isinstance(item, dict):
            continue
        key = tuple(item.get(k) for k in keys)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def merge_dict_list(dst, src, keys, stats, stat_key):
    before = len(dst)
    dst[:] = unique_dicts((dst or []) + (src or []), keys)
    stats[stat_key] += len(dst) - before


def merge_keep(old, keep, old_id, reason, stats):
    keep.setdefault("additional_titles", [])
    for title in (old.get("title"), old.get("original_title")):
        if title and title != keep.get("title") and title not in keep["additional_titles"]:
            keep["additional_titles"].append(title)
            stats["work.additional_titles"] += 1

    merge_dict_list(
        keep.setdefault("indexed_by", []),
        old.get("indexed_by") or [],
        ("source", "source_bid", "title_info", "summary"),
        stats,
        "work.indexed_by_merged",
    )
    merge_dict_list(
        keep.setdefault("emendated_by", []),
        old.get("emendated_by") or [],
        ("source", "source_bid", "title_info", "summary"),
        stats,
        "work.emendated_by_merged",
    )
    for key in ("juan_count", "measures", "measure_info", "description", "loss_status"):
        if keep.get(key) in (None, [], {}) and old.get(key) not in (None, [], {}):
            keep[key] = old[key]
            stats[f"work.{key}_filled"] += 1

    keep["ai_note"] = (
        (keep.get("ai_note") or "")
        + f"\n\n2026-08-09 題名重出 Round 1：合併空殼 Work {old_id}（{old.get('title')}）入本條；判準：{reason}。"
    ).strip()
    keep["updated_at"] = now_iso()


def replace_text_refs(idx, old_id, keep_id, old_paths, stats):
    roots = [ROOT / x for x in ("Work", "Book", "Collection", "Entity")]
    for base in roots:
        for path in base.rglob("*.json"):
            rel = path.relative_to(ROOT).as_posix()
            if rel in old_paths:
                continue
            text = path.read_text(encoding="utf-8")
            if old_id not in text:
                continue
            new_text = text.replace(f'"{old_id}"', f'"{keep_id}"')
            if new_text != text:
                path.write_text(new_text, encoding="utf-8")
                stats["ref_files_text_replaced"] += 1


def dedupe_entity_work_lists(stats):
    for path in (ROOT / "Entity").rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        if not any(keep_id in text for _old_id, keep_id, _reason in PAIRS):
            continue
        data = load_json(path)
        works = data.get("works")
        if not isinstance(works, list):
            continue
        new = unique_dicts(works, ("work_id", "role"))
        if len(new) != len(works):
            data["works"] = new
            data["updated_at"] = now_iso()
            write_json(path, data)
            stats["entity.works_deduped"] += 1


def sync_index(changed, deleted, stats):
    for shard_path in sorted((ROOT / "index" / "works").glob("*.json")):
        shard = load_json(shard_path)
        modified = False
        for old_id in list(shard):
            if old_id in deleted:
                del shard[old_id]
                modified = True
                stats["index.deleted"] += 1
        for keep_id, keep in changed.items():
            if keep_id not in shard:
                continue
            first = (keep.get("authors") or [{}])[0] if keep.get("authors") else {}
            fields = {
                "title": keep.get("title"),
                "author": first.get("name"),
                "role": first.get("role"),
                "dynasty": keep.get("dynasty"),
                "period": keep.get("period"),
            }
            for key, value in fields.items():
                if shard[keep_id].get(key) != value:
                    shard[keep_id][key] = value
                    modified = True
                    stats[f"index.{key}_synced"] += 1
        if modified:
            write_json(shard_path, shard)
            stats["index.shards_changed"] += 1


def main():
    idx = work_index()
    stats = Counter()
    changed = {}
    deleted = set()
    old_paths = set()
    merged = []

    for old_id, keep_id, reason in PAIRS:
        old_path = ROOT / idx[old_id]["path"]
        keep_path = ROOT / idx[keep_id]["path"]
        old = load_json(old_path)
        keep = load_json(keep_path)
        old_dir = old_path.parent / old_id
        if old.get("books") or old.get("resources") or (old_dir / "fragments").exists() or (old_dir / "collated_edition").exists():
            raise RuntimeError(f"{old_id} is not a safe empty shell")
        merge_keep(old, keep, old_id, reason, stats)
        write_json(keep_path, keep)
        changed[keep_id] = keep
        deleted.add(old_id)
        old_paths.add(idx[old_id]["path"])
        merged.append({
            "deleted": old_id,
            "deleted_path": idx[old_id]["path"],
            "title": old.get("title"),
            "superseded_by": keep_id,
            "target_title": keep.get("title"),
            "reason": reason,
        })
        stats["work.merged"] += 1

    for old_id, keep_id, _reason in PAIRS:
        replace_text_refs(idx, old_id, keep_id, old_paths, stats)
    dedupe_entity_work_lists(stats)
    sync_index(changed, deleted, stats)

    report = {
        "date": "2026-08-09",
        "issue": "題名重出：長題為短題加撰人/注者，且撰人相容。",
        "principle": "僅合併舊 Work 無 books/resources/fragments/collated 的空殼；保留規範短題，遷入著錄，原文替換庫內引用。",
        "merged_count": len(merged),
        "merged": merged,
        "delete_paths": sorted(old_paths),
        "stats": dict(stats),
    }
    write_json(OUT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
