#!/usr/bin/env python3
"""補齊整理本 section -> Work 後，Work 側漏記整理本來源的回鏈。"""

import ast
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"
TODAY = "2026-08-09"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_work_index():
    idx = {}
    for s in SHARDS:
        idx.update(load_json(ROOT / "index" / "works" / f"{s}.json"))
    return idx


def section_work_ids(section):
    value = section.get("work_ids")
    if isinstance(value, str):
        return ast.literal_eval(value)
    if value:
        return value
    return []


def main():
    index = load_work_index()
    source_titles = {}
    candidates = defaultdict(list)

    for file in ROOT.glob("Work/*/*/*/*/collated_edition/*.json"):
        if file.name == "collated_edition_index.json":
            continue
        try:
            collated = load_json(file)
        except Exception:
            continue
        if not isinstance(collated, dict):
            continue
        source_bid = file.parts[-3]
        if source_bid not in source_titles:
            source_entry = index.get(source_bid)
            source_titles[source_bid] = (
                source_entry.get("title") if source_entry else source_bid
            )
        for section_index, section in enumerate(collated.get("sections") or []):
            if not isinstance(section, dict):
                continue
            section_title = (
                section.get("title")
                or section.get("title_info")
                or section.get("name")
                or ""
            )
            for work_id in section_work_ids(section):
                entry = index.get(work_id)
                if not entry:
                    continue
                work = load_json(ROOT / entry["path"])
                sources = (work.get("emendated_by") or []) + (work.get("indexed_by") or [])
                if any(source.get("source_bid") == source_bid for source in sources):
                    continue
                candidates[(work_id, source_bid)].append(
                    {
                        "file": file.relative_to(ROOT).as_posix(),
                        "section_index": section_index,
                        "section_title": section_title,
                    }
                )

    fixed = []
    for (work_id, source_bid), sections in sorted(candidates.items()):
        entry = index[work_id]
        path = ROOT / entry["path"]
        work = load_json(path)
        title_infos = []
        for item in sections:
            if item["section_title"] and item["section_title"] not in title_infos:
                title_infos.append(item["section_title"])
        title_info = "；".join(title_infos)
        record = {
            "source": source_titles[source_bid],
            "source_bid": source_bid,
            "title_info": title_info,
            "summary": title_info,
        }
        if not isinstance(work.get("emendated_by"), list):
            work["emendated_by"] = []
        work["emendated_by"].append(record)
        work["updated_at"] = TODAY
        dump_json(path, work)
        fixed.append(
            {
                "work_id": work_id,
                "work_title": work.get("title"),
                "work_path": path.relative_to(ROOT).as_posix(),
                "source": source_titles[source_bid],
                "source_bid": source_bid,
                "sections": sections,
                "emendated_by_added": record,
            }
        )

    report = {
        "date": TODAY,
        "issue": "collated_edition section 已指向 Work，但 Work.indexed_by/emendated_by 未記同一 source_bid。",
        "fixed_count": len(fixed),
        "fixed": fixed,
    }
    out = ROOT / ".claude" / "known-issues" / "整理本Work側回鏈_round1已修復.json"
    dump_json(out, report)
    print(json.dumps({"fixed": len(fixed)}, ensure_ascii=False))
    print(out.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
