"""
Backfill missing title_info and summary in Work indexed_by entries
by looking up collated_edition data from the source catalog.
"""

import json
import glob
import os
import sys


def load_collated_index(catalog_dir):
    """Build work_id -> [{title, summary/content, ...}] from collated_edition."""
    ce_dir = os.path.join(catalog_dir, "collated_edition")
    if not os.path.isdir(ce_dir):
        return {}

    index = {}  # work_id -> list of entries
    for fp in glob.glob(os.path.join(ce_dir, "*.json")):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        if not isinstance(data, dict):
            continue

        for section in data.get("sections", []):
            wid = section.get("work_id")
            if not wid:
                continue

            title = section.get("title", "")
            # 四庫總目 uses "summary", 漢書藝文志 uses "content"
            summary = section.get("summary", "") or section.get("content", "")

            if wid not in index:
                index[wid] = []
            index[wid].append({
                "title": title,
                "summary": summary,
            })

    return index


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    work_root = os.path.join(root, "Work")
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("=== DRY RUN MODE ===\n")

    # Discover all catalog source_bids used in indexed_by
    # and their Work directories
    catalog_dirs = {}
    for fp in glob.glob(os.path.join(work_root, "**", "collated_edition"), recursive=True):
        parent = os.path.dirname(fp)
        bid = os.path.basename(parent).split("-")[0]
        catalog_dirs[bid] = parent

    print(f"Found {len(catalog_dirs)} catalogs with collated_edition:")
    for bid, d in catalog_dirs.items():
        print(f"  {bid}: {os.path.basename(d)}")
    print()

    # Build collated index for each catalog
    collated = {}
    for bid, d in catalog_dirs.items():
        idx = load_collated_index(d)
        collated[bid] = idx
        print(f"  {bid}: {len(idx)} work entries indexed")
    print()

    # Scan all Work files and backfill
    fixed = 0
    fixed_title = 0
    fixed_summary = 0
    total_checked = 0
    not_found = []

    for fp in glob.glob(os.path.join(work_root, "**", "*.json"), recursive=True):
        if "collated_edition" in fp or "ctext" in fp or "wikimedia" in fp:
            continue

        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        if data.get("type") != "work":
            continue

        indexed_by = data.get("indexed_by")
        if not indexed_by:
            continue

        file_changed = False
        work_id = data.get("id", "")
        work_title = data.get("title", "")

        for entry in indexed_by:
            source_bid = entry.get("source_bid", "")
            if source_bid not in collated:
                continue

            has_title = bool(entry.get("title_info", "").strip())
            has_summary = bool(entry.get("summary", "").strip())

            if has_title and has_summary:
                continue

            total_checked += 1

            # Look up in collated edition
            ce_entries = collated[source_bid].get(work_id, [])
            if not ce_entries:
                not_found.append((work_title, work_id, entry.get("source", "")))
                continue

            # If multiple matches, try to find the best one
            ce = ce_entries[0]
            if len(ce_entries) > 1:
                # Prefer the one whose title matches most closely
                for candidate in ce_entries:
                    if work_title in candidate["title"]:
                        ce = candidate
                        break

            if not has_title and ce["title"]:
                entry["title_info"] = ce["title"]
                fixed_title += 1
                file_changed = True

            if not has_summary and ce["summary"]:
                entry["summary"] = ce["summary"]
                fixed_summary += 1
                file_changed = True

        if file_changed:
            fixed += 1
            if dry_run:
                print(f"  WOULD FIX: {work_title} ({work_id})")
                for entry in indexed_by:
                    source_bid = entry.get("source_bid", "")
                    print(f"    {entry.get('source','')}: title_info={entry.get('title_info','')[:40]}")
            else:
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.write("\n")

    print(f"\nTotal entries needing backfill: {total_checked}")
    print(f"Files {'would be ' if dry_run else ''}fixed: {fixed}")
    print(f"  title_info filled: {fixed_title}")
    print(f"  summary filled: {fixed_summary}")

    if not_found:
        print(f"\nNot found in collated_edition ({len(not_found)}):")
        for title, wid, src in not_found[:20]:
            print(f"  {title} ({wid}) <- {src}")


if __name__ == "__main__":
    main()
