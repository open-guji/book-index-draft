#!/usr/bin/env python3
"""
一次性迁移：将所有 collated_edition_index.json 中的 text_quality.grade
从旧 ABCD 字母映射到新 enum，并删除 grade_label 字段。

映射规则：
  A -> fine    （通读无障碍，错误率 <= 1%）
  B -> rough   （文意基本正确，错误率 <= 3%）
  C -> rough   （同上；旧 B/C 本质都是人工粗校）
  D -> ocr     （机器识别，错误率 <= 10%）

新 enum: published / fine / rough / ocr

同一 Work 下外层 {id}/collated_edition_index.json 与内层
{id}/collated_edition/collated_edition_index.json 均会处理。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

LEGACY_MAP = {
    'A': 'fine',
    'B': 'rough',
    'C': 'rough',
    'D': 'ocr',
}

NEW_GRADES = {'published', 'fine', 'rough', 'ocr'}


def migrate_file(path: Path) -> str:
    """返回动作: 'migrated' / 'already' / 'no-quality' / 'unknown'"""
    raw = path.read_text(encoding='utf-8')
    data = json.loads(raw)
    tq = data.get('text_quality')
    if not isinstance(tq, dict):
        return 'no-quality'

    grade = tq.get('grade')
    changed = False

    if grade in LEGACY_MAP:
        tq['grade'] = LEGACY_MAP[grade]
        changed = True
    elif grade in NEW_GRADES:
        pass
    else:
        print(f'  [WARN] unknown grade {grade!r} in {path}', file=sys.stderr)
        return 'unknown'

    if 'grade_label' in tq:
        del tq['grade_label']
        changed = True

    if changed:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        return 'migrated'
    return 'already'


def main() -> int:
    root = Path(__file__).resolve().parent.parent / 'Work'
    if not root.exists():
        print(f'Work root not found: {root}', file=sys.stderr)
        return 1

    stats = {'migrated': 0, 'already': 0, 'no-quality': 0, 'unknown': 0}
    for path in root.rglob('collated_edition_index.json'):
        action = migrate_file(path)
        stats[action] += 1
        if action == 'migrated':
            print(f'  [OK] {path.relative_to(root.parent)}')

    print()
    print(f"迁移完成: migrated={stats['migrated']}, "
          f"already-new={stats['already']}, "
          f"no-text_quality={stats['no-quality']}, "
          f"unknown={stats['unknown']}")
    return 0 if stats['unknown'] == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
