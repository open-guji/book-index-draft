#!/usr/bin/env python3
"""
validate_entries.py - 校验 book-index-draft 仓库中所有 JSON 条目的数据规范性。

用法:
    python validate_entries.py [--type work|book|collection|all] [--fix]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# 简体 -> 繁体 映射表，用于检测 title 中的简体字
SIMPLIFIED_TO_TRADITIONAL = {
    "书": "書", "经": "經", "传": "傳", "记": "記", "论": "論",
    "语": "語", "学": "學", "说": "說", "义": "義", "类": "類",
    "编": "編", "纪": "紀", "录": "錄", "谱": "譜", "图": "圖",
    "证": "證", "补": "補", "续": "續", "选": "選", "评": "評",
    "订": "訂", "钦": "欽", "赞": "贊", "韵": "韻", "问": "問",
    "对": "對",
}

# index.json 中的分类键 -> 文件系统目录名 / 期望 type 值
CATEGORY_MAP = {
    "works":       ("Work",       "work"),
    "books":       ("Book",       "book"),
    "collections": ("Collection", "collection"),
}

# 目录名 -> index.json 中的分类键
DIR_TO_CATEGORY = {v[0]: k for k, v in CATEGORY_MAP.items()}


class ValidationResult:
    """收集所有校验消息。"""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.infos: list[str] = []
        self.fixes: list[str] = []
        self.counts = {
            "files_scanned": 0,
            "errors": 0,
            "warnings": 0,
            "fixes": 0,
        }

    def error(self, path: str, msg: str):
        self.errors.append(f"ERROR  [{path}] {msg}")
        self.counts["errors"] += 1

    def warn(self, path: str, msg: str):
        self.warnings.append(f"WARN   [{path}] {msg}")
        self.counts["warnings"] += 1

    def info(self, msg: str):
        self.infos.append(f"INFO   {msg}")

    def fixed(self, path: str, msg: str):
        self.fixes.append(f"FIXED  [{path}] {msg}")
        self.counts["fixes"] += 1

    def print_report(self):
        for line in self.errors:
            print(line)
        for line in self.warnings:
            print(line)
        for line in self.fixes:
            print(line)
        print()
        for line in self.infos:
            print(line)
        print()
        print("=" * 60)
        print("汇总统计")
        print(f"  扫描文件数: {self.counts['files_scanned']}")
        print(f"  ERROR:      {self.counts['errors']}")
        print(f"  WARN:       {self.counts['warnings']}")
        print(f"  已修复:     {self.counts['fixes']}")
        print("=" * 60)


def get_repo_root() -> Path:
    """返回仓库根目录（即本脚本所在 scripts/ 的上级）。"""
    return Path(__file__).resolve().parent.parent


def collect_entry_files(repo_root: Path, type_filter: str) -> list[tuple[str, Path]]:
    """
    遍历 Work / Book / Collection 三层目录下的 {ID}-{title}.json 或 {ID}.json 文件。
    排除 {id}/ 子目录下的资源文件。

    三层目录结构: <Category>/<a>/<b>/<c>/<file>.json
    其中 <a><b><c> 是 id 的前三个字符。

    返回 [(category_dir_name, file_path), ...]
    """
    dirs_to_scan = []
    if type_filter == "all":
        dirs_to_scan = ["Work", "Book", "Collection"]
    else:
        for cat_key, (dir_name, type_val) in CATEGORY_MAP.items():
            if type_val == type_filter:
                dirs_to_scan.append(dir_name)
                break

    results = []
    for dir_name in dirs_to_scan:
        base = repo_root / dir_name
        if not base.exists():
            continue
        # 遍历三层目录: base / L1 / L2 / L3 /
        for l1 in sorted(base.iterdir()):
            if not l1.is_dir():
                continue
            for l2 in sorted(l1.iterdir()):
                if not l2.is_dir():
                    continue
                for l3 in sorted(l2.iterdir()):
                    if not l3.is_dir():
                        continue
                    # 在 l3 目录下，只取直接的 .json 文件（排除子目录中的）
                    for f in sorted(l3.iterdir()):
                        if f.is_file() and f.suffix == ".json":
                            results.append((dir_name, f))
    return results


def check_crlf(file_path: Path, result: ValidationResult, fix: bool) -> bool:
    """检查文件是否含有 CRLF 行尾。如果 --fix 则自动修复。返回是否有问题。"""
    raw = file_path.read_bytes()
    if b"\r\n" in raw:
        if fix:
            fixed_content = raw.replace(b"\r\n", b"\n")
            file_path.write_bytes(fixed_content)
            result.fixed(str(file_path.name), "CRLF -> LF 行尾已修复")
        else:
            result.error(str(file_path.name), "文件包含 CRLF 行尾（应为 LF）")
        return True
    if b"\r" in raw:
        result.error(str(file_path.name), "文件包含 CR 行尾（应为 LF）")
        return True
    return False


def check_simplified_chars(title: str, file_name: str, result: ValidationResult):
    """检查 title 中是否包含简体字。"""
    found = []
    for simp, trad in SIMPLIFIED_TO_TRADITIONAL.items():
        if simp in title:
            found.append(f"'{simp}'(应为'{trad}')")
    if found:
        result.warn(file_name, f"title 包含简体字: {', '.join(found)}  title=\"{title}\"")


def validate_common(data: dict, file_name: str, result: ValidationResult):
    """通用字段校验。"""
    for field in ("id", "type", "title"):
        if field not in data:
            result.error(file_name, f"缺少必填字段: {field}")

    title = data.get("title", "")
    if title:
        check_simplified_chars(title, file_name, result)


def validate_work(data: dict, file_name: str, result: ValidationResult):
    """Work 类型特定校验。"""
    if data.get("type") != "work":
        result.error(file_name, f"Work 目录下的 type 应为 'work'，实际为 '{data.get('type')}'")

    authors = data.get("authors")
    if authors is None:
        result.warn(file_name, "缺少 authors 字段")
    elif not isinstance(authors, list):
        result.error(file_name, f"authors 应为数组，实际为 {type(authors).__name__}")

    juan_count = data.get("juan_count")
    if juan_count is not None:
        if isinstance(juan_count, dict):
            num = juan_count.get("number")
            if num is None:
                result.error(file_name, "juan_count 存在但缺少 number 字段")
            elif not isinstance(num, (int, float)) or num <= 0:
                result.warn(file_name, f"juan_count.number 应 > 0，实际为 {num}")
        else:
            result.error(file_name, f"juan_count 应为对象，实际为 {type(juan_count).__name__}")


def validate_book(data: dict, file_name: str, result: ValidationResult):
    """Book 类型特定校验。"""
    if data.get("type") != "book":
        result.error(file_name, f"Book 目录下的 type 应为 'book'，实际为 '{data.get('type')}'")

    if "work_id" not in data:
        result.warn(file_name, "缺少 work_id 字段")

    resources = data.get("resources")
    if resources is None:
        result.error(file_name, "缺少 resources 字段")
    elif not isinstance(resources, list):
        result.error(file_name, f"resources 应为数组，实际为 {type(resources).__name__}")
    elif len(resources) == 0:
        result.warn(file_name, "resources 数组为空")


def validate_collection(data: dict, file_name: str, result: ValidationResult):
    """Collection 类型特定校验。"""
    if data.get("type") != "collection":
        result.error(file_name, f"Collection 目录下的 type 应为 'collection'，实际为 '{data.get('type')}'")

    if "volume_count" in data:
        result.error(file_name, "不应有 volume_count 字段（应使用 juan_count）")


TYPE_VALIDATORS = {
    "Work":       validate_work,
    "Book":       validate_book,
    "Collection": validate_collection,
}


def validate_index_json(repo_root: Path, entry_files: list[tuple[str, Path]],
                        result: ValidationResult):
    """
    校验 index.json 与实际文件的一致性:
    1. 每个扫描到的条目文件应存在于 index.json 中
    2. index.json 中的每个 path 应指向实际存在的文件
    """
    index_path = repo_root / "index.json"
    if not index_path.exists():
        result.error("index.json", "index.json 文件不存在")
        return

    try:
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        result.error("index.json", f"index.json 解析失败: {e}")
        return

    # 收集 index.json 中所有已注册的 id -> path
    indexed_ids: dict[str, str] = {}    # id -> path (相对于 repo_root)
    indexed_paths: dict[str, str] = {}  # path -> id
    for cat_key in ("books", "collections", "works"):
        section = index_data.get(cat_key, {})
        for entry_id, entry_info in section.items():
            path_val = entry_info.get("path", "")
            indexed_ids[entry_id] = path_val
            if path_val:
                # 统一使用正斜杠
                normalized = path_val.replace("\\", "/")
                indexed_paths[normalized] = entry_id

    # 检查: 每个文件对应的条目是否在 index.json 中
    for dir_name, fpath in entry_files:
        # 读取文件获取 id
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue  # 解析错误已在主校验中报告
        entry_id = data.get("id")
        if entry_id and entry_id not in indexed_ids:
            result.error(fpath.name, f"条目 id='{entry_id}' 未在 index.json 中注册")

    # 检查: index.json 中的 path 是否都指向存在的文件
    for path_val, entry_id in indexed_paths.items():
        full_path = repo_root / Path(path_val)
        if not full_path.exists():
            result.error("index.json", f"path '{path_val}' (id={entry_id}) 指向的文件不存在")


def main():
    parser = argparse.ArgumentParser(description="校验 book-index-draft 仓库中的 JSON 条目")
    parser.add_argument(
        "--type", dest="entry_type", default="all",
        choices=["work", "book", "collection", "all"],
        help="要校验的条目类型 (默认: all)"
    )
    parser.add_argument(
        "--fix", action="store_true",
        help="自动修复可修复的问题（如 CRLF -> LF）"
    )
    args = parser.parse_args()

    repo_root = get_repo_root()
    result = ValidationResult()

    result.info(f"仓库根目录: {repo_root}")
    result.info(f"校验类型: {args.entry_type}")
    result.info(f"自动修复: {'是' if args.fix else '否'}")

    # 收集文件
    entry_files = collect_entry_files(repo_root, args.entry_type)
    result.info(f"共发现 {len(entry_files)} 个条目文件")

    type_counts = {"Work": 0, "Book": 0, "Collection": 0}

    for dir_name, fpath in entry_files:
        result.counts["files_scanned"] += 1
        type_counts[dir_name] = type_counts.get(dir_name, 0) + 1
        file_name = fpath.name

        # 1. CRLF 检查
        check_crlf(fpath, result, args.fix)

        # 2. 解析 JSON
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            result.error(file_name, f"JSON 解析失败: {e}")
            continue
        except UnicodeDecodeError as e:
            result.error(file_name, f"编码错误 (应为 UTF-8): {e}")
            continue

        if not isinstance(data, dict):
            result.error(file_name, f"JSON 根元素应为对象，实际为 {type(data).__name__}")
            continue

        # 3. 通用校验
        validate_common(data, file_name, result)

        # 4. 类型特定校验
        validator = TYPE_VALIDATORS.get(dir_name)
        if validator:
            validator(data, file_name, result)

    # 5. index.json 一致性检查
    validate_index_json(repo_root, entry_files, result)

    # 统计信息
    for dir_name, count in type_counts.items():
        if count > 0:
            result.info(f"  {dir_name}: {count} 个文件")

    # 输出报告
    print()
    result.print_report()

    # 返回码: 有 ERROR 时返回 1
    sys.exit(1 if result.counts["errors"] > 0 else 0)


if __name__ == "__main__":
    main()
