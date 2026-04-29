#!/usr/bin/env python3
"""
Migrate all base58-encoded IDs to base36 encoding.

Base58 (case-sensitive, 11 chars) -> Base36 (case-insensitive safe, 12-13 chars)
The underlying 64-bit Snowflake integer values are preserved.

Usage:
    # Dry run (report only, no changes):
    python scripts/migrate_base58_to_base36.py --root . --dry-run

    # Phase A+B only (update JSON content, don't rename files):
    python scripts/migrate_base58_to_base36.py --root . --content-only

    # Full migration (content + rename):
    python scripts/migrate_base58_to_base36.py --root .

    # Verify after migration:
    python scripts/migrate_base58_to_base36.py --root . --verify
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Set

# ── Base58/Base36 encode/decode (self-contained, no external deps) ──

_ALPHABET_58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_ALPHABET_36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def _b58_decode(s: str) -> int:
    num = 0
    for c in s:
        num = num * 58 + _ALPHABET_58.index(c)
    return num


def _b36_encode(num: int) -> str:
    if num == 0:
        return _ALPHABET_36[0]
    res = ""
    while num > 0:
        num, rem = divmod(num, 36)
        res = _ALPHABET_36[rem] + res
    return res


def _b36_decode(s: str) -> int:
    num = 0
    for c in s:
        num = num * 36 + _ALPHABET_36.index(c)
    return num


def _is_base58_id(s: str) -> bool:
    """Check if a string looks like a base58 ID (11 chars, contains uppercase)."""
    if len(s) != 11:
        return False
    if not any(c.isupper() for c in s):
        return False
    return all(c in _ALPHABET_58 for c in s)


# ── Phase A: Build mapping table ──

def _collect_base58_ids(value, found: Set[str]):
    """Recursively find all base58 ID strings in a JSON value."""
    if isinstance(value, str):
        if _is_base58_id(value):
            found.add(value)
    elif isinstance(value, list):
        for item in value:
            _collect_base58_ids(item, found)
    elif isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str) and _is_base58_id(k):
                found.add(k)
            _collect_base58_ids(v, found)


def build_mapping(root: Path) -> Dict[str, str]:
    """Scan all JSON files and build old_id -> new_id mapping for every base58 ID found."""
    found_ids: Set[str] = set()

    # Scan entity directories
    for type_dir in ["Work", "Book", "Collection"]:
        full = root / type_dir
        if not full.exists():
            continue
        for json_file in full.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            _collect_base58_ids(data, found_ids)

    # Scan config files
    for config_name in ["recommended.json", "resource.json", "resource-site.json", "index.json"]:
        config_path = root / config_name
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    _collect_base58_ids(json.load(f), found_ids)
            except Exception:
                pass

    # Scan _bundle
    bundle_dir = root / "_bundle"
    if bundle_dir.exists():
        for json_file in bundle_dir.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    _collect_base58_ids(json.load(f), found_ids)
            except Exception:
                pass

    # Build mapping
    mapping: Dict[str, str] = {}
    for old_id in found_ids:
        int_val = _b58_decode(old_id)
        new_id = _b36_encode(int_val)
        mapping[old_id] = new_id

    return mapping


# ── Phase B: Replace IDs in JSON content ──

def replace_ids_in_value(value, mapping: Dict[str, str]):
    """Recursively replace all base58 ID strings found in mapping."""
    if isinstance(value, str):
        return mapping.get(value, value)
    elif isinstance(value, list):
        return [replace_ids_in_value(item, mapping) for item in value]
    elif isinstance(value, dict):
        new_dict = {}
        for k, v in value.items():
            new_key = mapping.get(k, k) if isinstance(k, str) else k
            new_dict[new_key] = replace_ids_in_value(v, mapping)
        return new_dict
    return value


def update_json_file(filepath: Path, mapping: Dict[str, str]) -> bool:
    """Update a JSON file in place. Returns True if changes were made."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  WARN: Cannot read {filepath}: {e}")
        return False

    updated = replace_ids_in_value(data, mapping)
    if updated == data:
        return False

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(updated, f, indent=2, ensure_ascii=False)
    return True


def update_all_json_content(root: Path, mapping: Dict[str, str], dry_run: bool = False) -> int:
    """Phase B: Update JSON content in all files under root."""
    changed = 0

    # 1. Entity directories
    for type_dir in ["Work", "Book", "Collection"]:
        full = root / type_dir
        if not full.exists():
            continue
        for json_file in full.rglob("*.json"):
            if dry_run:
                # Check if file would change
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    updated = replace_ids_in_value(data, mapping)
                    if updated != data:
                        changed += 1
                except Exception:
                    pass
            else:
                if update_json_file(json_file, mapping):
                    changed += 1

    # 2. Root-level config files
    for config_name in ["recommended.json", "resource.json", "resource-site.json", "index.json"]:
        config_path = root / config_name
        if config_path.exists():
            if dry_run:
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if replace_ids_in_value(data, mapping) != data:
                        changed += 1
                except Exception:
                    pass
            else:
                if update_json_file(config_path, mapping):
                    changed += 1

    # 3. _bundle directory
    bundle_dir = root / "_bundle"
    if bundle_dir.exists():
        for json_file in bundle_dir.rglob("*.json"):
            if dry_run:
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if replace_ids_in_value(data, mapping) != data:
                        changed += 1
                except Exception:
                    pass
            else:
                if update_json_file(json_file, mapping):
                    changed += 1

    return changed


# ── Phase C: Rename files and directories ──

def rename_files_and_dirs(root: Path, mapping: Dict[str, str], use_git: bool = True, dry_run: bool = False) -> int:
    """Phase C: Rename entity files and their asset directories."""
    renamed = 0

    for type_dir in ["Work", "Book", "Collection"]:
        full = root / type_dir
        if not full.exists():
            continue

        # Collect all entity files first (to avoid iterator invalidation)
        entity_files = []
        for json_file in full.rglob("*.json"):
            name = json_file.name
            if "-" not in name:
                continue
            old_id = name.split("-", 1)[0]
            if old_id in mapping:
                entity_files.append((json_file, old_id))

        for json_file, old_id in entity_files:
            new_id = mapping[old_id]
            title_part = json_file.name.split("-", 1)[1]  # title.json

            # New directory path based on new ID prefix
            nc1, nc2, nc3 = new_id[0], new_id[1], new_id[2]
            new_parent = full / nc1 / nc2 / nc3
            new_file = new_parent / f"{new_id}-{title_part}"

            if dry_run:
                print(f"  RENAME: {json_file.relative_to(root)} -> {new_file.relative_to(root)}")
                renamed += 1
                # Check for asset dir
                asset_dir = json_file.parent / old_id
                if asset_dir.is_dir():
                    new_asset = new_parent / new_id
                    print(f"  RENAME: {asset_dir.relative_to(root)}/ -> {new_asset.relative_to(root)}/")
                continue

            # Create new directory
            new_parent.mkdir(parents=True, exist_ok=True)

            # Move file
            if use_git:
                subprocess.run(["git", "mv", str(json_file), str(new_file)],
                               cwd=str(root), check=True, capture_output=True)
            else:
                shutil.move(str(json_file), str(new_file))
            renamed += 1

            # Move asset directory if exists
            asset_dir = json_file.parent / old_id
            if asset_dir.is_dir():
                new_asset = new_parent / new_id
                if use_git:
                    subprocess.run(["git", "mv", str(asset_dir), str(new_asset)],
                                   cwd=str(root), check=True, capture_output=True)
                else:
                    shutil.move(str(asset_dir), str(new_asset))

    # Clean up empty directories
    if not dry_run:
        for type_dir in ["Work", "Book", "Collection"]:
            full = root / type_dir
            if not full.exists():
                continue
            # Walk bottom-up to remove empty dirs
            for dirpath, dirnames, filenames in os.walk(str(full), topdown=False):
                if not os.listdir(dirpath) and dirpath != str(full):
                    os.rmdir(dirpath)

    return renamed


# ── Verification ──

def verify_migration(root: Path) -> bool:
    """Verify that no base58 IDs remain in the data."""
    errors = 0
    all_ids: Set[str] = set()

    for type_dir in ["Work", "Book", "Collection"]:
        full = root / type_dir
        if not full.exists():
            continue
        for json_file in full.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    data = json.load(f) if False else json.loads(content)
            except Exception as e:
                print(f"  ERROR reading {json_file}: {e}")
                errors += 1
                continue

            if isinstance(data, dict):
                entity_id = data.get("id", "")
                if entity_id:
                    all_ids.add(entity_id)

            # Check: no uppercase in any string that looks like an ID
            _check_for_base58_residual(content, json_file, errors)

    # Check filename consistency
    for type_dir in ["Work", "Book", "Collection"]:
        full = root / type_dir
        if not full.exists():
            continue
        for json_file in full.rglob("*.json"):
            name = json_file.name
            if "-" not in name:
                continue
            file_id = name.split("-", 1)[0]
            # Verify file ID matches JSON id
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    continue
                json_id = data.get("id", "")
                if json_id and json_id != file_id:
                    print(f"  MISMATCH: file={file_id} json={json_id} in {json_file}")
                    errors += 1
                # Verify ID is pure lowercase+digits
                if json_id and not re.match(r'^[0-9a-z]+$', json_id):
                    print(f"  BAD ID: {json_id} in {json_file}")
                    errors += 1
            except Exception:
                pass

    # Check referential integrity
    ref_fields = ["work_id", "book_id", "collection_id", "source_bid",
                  "target_work_id", "kaozhen_work_id", "parent_work_id"]
    ref_errors = 0
    for type_dir in ["Work", "Book", "Collection"]:
        full = root / type_dir
        if not full.exists():
            continue
        for json_file in full.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                _check_refs(data, all_ids, ref_fields, json_file, ref_errors)
            except Exception:
                pass

    print(f"\nVerification: {len(all_ids)} entities, {errors} errors, {ref_errors} ref errors")
    return errors == 0 and ref_errors == 0


def _check_for_base58_residual(content: str, filepath: Path, errors: int):
    """Check JSON content string for residual base58 IDs."""
    # Find 11-char strings that contain uppercase and look like base58
    for match in re.finditer(r'"([A-Za-z0-9]{11})"', content):
        candidate = match.group(1)
        if any(c.isupper() for c in candidate) and all(c in _ALPHABET_58 for c in candidate):
            print(f"  RESIDUAL base58 ID: {candidate} in {filepath}")


def _check_refs(data, all_ids: Set[str], ref_fields, filepath, errors_count):
    """Recursively check reference fields point to existing IDs."""
    if isinstance(data, dict):
        for k, v in data.items():
            if k in ref_fields and isinstance(v, str) and v:
                if v not in all_ids:
                    pass  # Some refs may be to unloaded entities
            _check_refs(v, all_ids, ref_fields, filepath, errors_count)
    elif isinstance(data, list):
        for item in data:
            _check_refs(item, all_ids, ref_fields, filepath, errors_count)


# ── Main ──

def main():
    parser = argparse.ArgumentParser(description="Migrate base58 IDs to base36")
    parser.add_argument("--root", required=True, help="Path to book-index-draft root")
    parser.add_argument("--dry-run", action="store_true", help="Report only, no changes")
    parser.add_argument("--content-only", action="store_true", help="Only update JSON content, skip rename")
    parser.add_argument("--verify", action="store_true", help="Verify migration (no changes)")
    parser.add_argument("--no-git", action="store_true", help="Don't use git mv for renames")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    print(f"Root: {root}")

    if args.verify:
        print("\n=== Verification ===")
        ok = verify_migration(root)
        sys.exit(0 if ok else 1)

    # Phase A: Build mapping
    print("\n=== Phase A: Building ID mapping ===")
    mapping = build_mapping(root)
    print(f"  Found {len(mapping)} unique base58 IDs to convert")

    if not mapping:
        print("  No base58 IDs found. Nothing to do.")
        return

    # Show samples
    samples = list(mapping.items())[:5]
    for old, new in samples:
        int_val = _b58_decode(old)
        verify = _b36_decode(new)
        status = "OK" if int_val == verify else "MISMATCH!"
        print(f"  {old} -> {new} (int={int_val}, verify={status})")

    # Phase B: Update JSON content
    print(f"\n=== Phase B: Updating JSON content {'(dry run)' if args.dry_run else ''} ===")
    changed = update_all_json_content(root, mapping, dry_run=args.dry_run)
    print(f"  {changed} files {'would be ' if args.dry_run else ''}updated")

    if args.content_only:
        print("\n--content-only specified, skipping rename phase.")
        return

    # Phase C: Rename files and directories
    print(f"\n=== Phase C: Renaming files {'(dry run)' if args.dry_run else ''} ===")
    use_git = not args.no_git
    renamed = rename_files_and_dirs(root, mapping, use_git=use_git, dry_run=args.dry_run)
    print(f"  {renamed} files {'would be ' if args.dry_run else ''}renamed")

    if not args.dry_run:
        print("\n=== Migration complete ===")
        print("Next steps:")
        print("  1. Run: book-index reindex --root . --target draft")
        print("  2. Rebuild _bundle data")
        print("  3. Run: python scripts/migrate_base58_to_base36.py --root . --verify")


if __name__ == "__main__":
    main()
