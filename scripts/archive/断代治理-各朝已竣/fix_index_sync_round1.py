#!/usr/bin/env python3
"""同步 Work 檔案與 index/works 分片。

本輪只處理低風險索引結構問題：
- 刪除 index/works 中 path 已不存在的 stale entry
- 補入已存在但未入索引的 Work
- 將 index author 同步為 Work.authors[0].name

不修改 Work 正文資料。
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"


def shard_of(id_str: str) -> str:
    h = 0
    for c in id_str:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return f"{h % 16:x}"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def first_author(work: dict):
    authors = work.get("authors") or []
    return authors[0] if authors else {}


def index_entry(path: Path, work: dict) -> dict:
    author = first_author(work)
    entry = {
        "id": work["id"],
        "title": work.get("title"),
        "type": "Work",
        "path": path.relative_to(ROOT).as_posix(),
    }
    if author.get("name") is not None:
        entry["author"] = author.get("name")
    if work.get("dynasty") is not None:
        entry["dynasty"] = work.get("dynasty")
    elif author.get("dynasty") is not None:
        entry["dynasty"] = author.get("dynasty")
    if author.get("role") is not None:
        entry["role"] = author.get("role")
    juan_count = work.get("juan_count")
    if isinstance(juan_count, dict) and juan_count.get("number") is not None:
        entry["juan_count"] = juan_count.get("number")
    if work.get("measure_info") is not None:
        entry["measure_info"] = work.get("measure_info")
    resource_types = set()
    for resource in work.get("resources") or []:
        if isinstance(resource, dict):
            if resource.get("type"):
                resource_types.add(resource["type"])
            resource_types.update(resource.get("types") or [])
    if "text" in resource_types:
        entry["has_text"] = True
    if "image" in resource_types:
        entry["has_image"] = True
    if work.get("period") is not None:
        entry["period"] = work.get("period")
    return entry


def main():
    shard_data = {
        s: load_json(ROOT / "index" / "works" / f"{s}.json") for s in SHARDS
    }
    index = {}
    for data in shard_data.values():
        index.update(data)

    removed = []
    author_synced = []
    added = []

    for work_id, entry in list(index.items()):
        if not (ROOT / entry.get("path", "")).exists():
            del shard_data[shard_of(work_id)][work_id]
            del index[work_id]
            removed.append((work_id, entry.get("title"), entry.get("path")))

    for path in ROOT.glob("Work/*/*/*/*.json"):
        work = load_json(path)
        work_id = work.get("id")
        if not work_id:
            continue
        rel_path = path.relative_to(ROOT).as_posix()
        if work_id not in index:
            entry = index_entry(path, work)
            shard_data[shard_of(work_id)][work_id] = entry
            index[work_id] = entry
            added.append((work_id, work.get("title"), rel_path))
            continue
        entry = index[work_id]
        author = first_author(work).get("name")
        if author and entry.get("author") != author:
            author_synced.append((work_id, work.get("title"), entry.get("author"), author))
            entry["author"] = author
        if entry.get("path") != rel_path:
            entry["path"] = rel_path
        if entry.get("title") != work.get("title"):
            entry["title"] = work.get("title")

    for s in SHARDS:
        dump_json(ROOT / "index" / "works" / f"{s}.json", shard_data[s])

    report = {
        "removed_stale_index_entries": removed,
        "added_missing_work_index_entries": added,
        "synced_author_fields": author_synced,
        "counts": {
            "removed": len(removed),
            "added": len(added),
            "author_synced": len(author_synced),
        },
    }
    out = ROOT / ".claude" / "known-issues" / "索引同步_round1已修復.json"
    dump_json(out, report)
    print(json.dumps(report["counts"], ensure_ascii=False, indent=2))
    print(out.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
