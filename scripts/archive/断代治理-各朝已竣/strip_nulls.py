"""批量清理 JSON 文件中的 null 值，节省存储空间。"""

import json
import os
import sys


def strip_nulls(obj):
    """递归移除 dict 中值为 None/null 的字段。"""
    if isinstance(obj, dict):
        return {k: strip_nulls(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [strip_nulls(item) for item in obj]
    return obj


def process_file(filepath, dry_run=False):
    """处理单个 JSON 文件，返回是否有变更。"""
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()
        data = json.loads(original)

    cleaned = strip_nulls(data)
    new_content = json.dumps(cleaned, ensure_ascii=False, indent=2)

    if original.rstrip() == new_content.rstrip():
        return False

    if dry_run:
        print(f"  [dry-run] 会清理: {filepath}")
    else:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  已清理: {filepath}")
    return True


def main():
    dry_run = '--dry-run' in sys.argv

    # 从脚本所在目录的上级开始扫描
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(script_dir)

    total = 0
    cleaned = 0

    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if not fname.endswith('.json') or fname == 'index.json':
                continue
            filepath = os.path.join(dirpath, fname)
            total += 1
            if process_file(filepath, dry_run):
                cleaned += 1

    mode = "[dry-run] " if dry_run else ""
    print(f"\n{mode}共扫描 {total} 个文件，{cleaned} 个含 null 已清理。")


if __name__ == '__main__':
    main()
