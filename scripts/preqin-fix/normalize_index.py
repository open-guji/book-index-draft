#!/usr/bin/env python3
"""修复 save_item 对 index shard 的两处副作用：
  1. build_index_entry 不输出 period（SCHEMA §period 要求 period 亦入 index/works/*.json）
     -> 从条目文件回填
  2. 写入用 indent=2，而仓库既有格式是 indent=1 -> 归一化回 indent=1
只处理 git 报告被修改的 shard。
"""
import json, os, subprocess, sys

DRAFT = '/workspace/book-index-draft'
os.chdir(DRAFT)
changed = subprocess.run(['git', 'diff', '--name-only', 'HEAD', '--', 'index/'],
                         capture_output=True, text=True).stdout.split()
total_backfill = 0
for rel in changed:
    d = json.load(open(rel, encoding='utf-8'))
    n = 0
    for wid, entry in d.items():
        p = entry.get('path')
        if not p or not os.path.exists(p):
            continue
        try:
            meta = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        per = meta.get('period')
        if per and entry.get('period') != per:
            entry['period'] = per
            n += 1
        elif not per and 'period' in entry:
            del entry['period']
            n += 1
    with open(rel, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)

    total_backfill += n
    print(f'{rel}: period 回填/同步 {n} 条')
print('total', total_backfill)
