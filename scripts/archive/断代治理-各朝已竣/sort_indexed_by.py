"""
Sort the indexed_by array in all Work JSON files by chronological order of the source catalogs.
"""

import json
import glob
import os
import sys

# Chronological order of catalog sources
SOURCE_ORDER = {
    "漢書藝文志": 0,
    "隋書經籍志": 1,
    "舊唐書經籍志": 2,
    "新唐書藝文志": 3,
    "宋史藝文志": 4,
    "明史藝文志": 5,
    "欽定四庫全書總目": 6,
    "四庫全書總目": 6,  # same era as 欽定四庫全書總目
    "src_manual": 99,
}

def sort_key(entry):
    source = entry.get("source", "")
    return SOURCE_ORDER.get(source, 50)

def process_file(filepath, dry_run=False):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    indexed_by = data.get("indexed_by")
    if not indexed_by or len(indexed_by) <= 1:
        return False

    sorted_list = sorted(indexed_by, key=sort_key)

    # Check if order actually changed
    if sorted_list == indexed_by:
        return False

    if not dry_run:
        data["indexed_by"] = sorted_list
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")

    return True


def main():
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Work")
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("=== DRY RUN MODE ===")

    pattern = os.path.join(root, "**", "*.json")
    changed = 0
    total = 0
    errors = 0

    for filepath in glob.glob(pattern, recursive=True):
        # Skip collated_edition and other subdirectories
        if "collated_edition" in filepath or "ctext" in filepath or "wikimedia" in filepath:
            continue

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        if data.get("type") != "work":
            continue

        total += 1

        try:
            if process_file(filepath, dry_run=dry_run):
                changed += 1
                if dry_run:
                    name = os.path.basename(filepath)
                    indexed_by = data.get("indexed_by", [])
                    sources = [e.get("source", "?") for e in indexed_by]
                    print(f"  WOULD SORT: {name}: {sources}")
        except Exception as e:
            errors += 1
            print(f"  ERROR: {filepath}: {e}", file=sys.stderr)

    print(f"\nTotal Work files: {total}")
    print(f"Files {'would be ' if dry_run else ''}reordered: {changed}")
    if errors:
        print(f"Errors: {errors}")


if __name__ == "__main__":
    main()
