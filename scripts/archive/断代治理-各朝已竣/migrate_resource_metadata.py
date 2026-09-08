#!/usr/bin/env python3
"""迁移资源字段：quality → metadata，清理冗余 details。

处理规则：
1. resources[].quality dict → resources[].metadata（映射 edition/version/has_translation）
2. resources[].details 中形如 "（朝代）作者" 的冗余信息 → 清空
3. 清理空的 details 字段

用法：
    python migrate_resource_metadata.py [--dry-run] [ROOT_DIR]

默认 ROOT_DIR = D:\\workspace\\book-index-draft
"""

import json
import re
import sys
from pathlib import Path

# 匹配 "（朝代）作者" 格式的 details（全角括号，可能带英文朝代名）
# 示例：（西汉）司馬遷、裴駰  /  （Han）司馬遷  /  （Western Han）司馬遷
REDUNDANT_DETAILS_RE = re.compile(
    r"^（[^）]+）[\w\s,，、·]+$"
)


def should_clear_details(details: str) -> bool:
    """判断 details 是否为冗余的朝代+作者信息。"""
    if not details or not details.strip():
        return True
    return bool(REDUNDANT_DETAILS_RE.match(details.strip()))


def migrate_quality_to_metadata(quality: dict) -> dict:
    """将 quality dict 转换为 metadata dict。"""
    metadata = {}
    if quality.get("edition"):
        metadata["edition"] = str(quality["edition"])
    version = quality.get("version", 0)
    if version:
        metadata["quality"] = f"v{version}"
    if quality.get("has_translation"):
        metadata["note"] = "有翻译"
    return metadata


def process_file(filepath: Path, dry_run: bool) -> dict:
    """处理单个 JSON 文件，返回统计信息。"""
    stats = {
        "quality_migrated": 0,
        "details_cleared": 0,
        "modified": False,
    }

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return stats

    resources = data.get("resources")
    if not resources or not isinstance(resources, list):
        return stats

    changed = False
    for r in resources:
        # 1. quality → metadata
        quality = r.pop("quality", None)
        if quality:
            metadata = migrate_quality_to_metadata(quality)
            if metadata:
                existing = r.get("metadata", {})
                existing.update(metadata)
                r["metadata"] = existing
            stats["quality_migrated"] += 1
            changed = True

        # 2. 清理冗余 details
        details = r.get("details", "")
        if should_clear_details(details):
            if "details" in r:
                del r["details"]
                if details:  # 只有非空的才计数
                    stats["details_cleared"] += 1
                changed = True

    if changed:
        stats["modified"] = True
        if not dry_run:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")

    return stats


def main():
    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = Path(args[0]) if args else Path(r"D:\workspace\book-index-draft")

    if not root.exists():
        print(f"Error: {root} does not exist")
        sys.exit(1)

    totals = {
        "files_scanned": 0,
        "files_modified": 0,
        "quality_migrated": 0,
        "details_cleared": 0,
    }

    # 遍历 Work, Book, Collection 目录
    for type_dir in ["Work", "Book", "Collection"]:
        base = root / type_dir
        if not base.exists():
            continue
        for filepath in sorted(base.rglob("*.json")):
            if filepath.name == "index.json":
                continue
            totals["files_scanned"] += 1
            stats = process_file(filepath, dry_run)
            if stats["modified"]:
                totals["files_modified"] += 1
            totals["quality_migrated"] += stats["quality_migrated"]
            totals["details_cleared"] += stats["details_cleared"]

    mode = "[DRY RUN] " if dry_run else ""
    print(f"{mode}Migration complete:")
    print(f"  Files scanned:      {totals['files_scanned']}")
    print(f"  Files modified:     {totals['files_modified']}")
    print(f"  quality -> metadata: {totals['quality_migrated']}")
    print(f"  details cleared:    {totals['details_cleared']}")


if __name__ == "__main__":
    main()
