#!/usr/bin/env python3
"""补掉 merge 脚本漏改的引用形态：
  - collated_edition sections[].work_ids （复数数组，原脚本只处理 work_id）
  - Entity.works 数组
  - 其它任何字符串/字符串数组字段
ai_note 里的合并溯源记述刻意保留，不改。
"""
import json, os, sys

DRAFT = '/workspace/book-index-draft'
PAIRS = {
    '1evincino4a9s': '1ev3bbf491j40',
    '1evjr3lt3ydq8': '1ev3bbf36ncao',
    '1evcmncjvyvwg': '1ev3bbf3pdkw0',
    '1evjr3k5q21a8': '1ev7xm2khqigw',
    '1evr5e3miqk1o': '1ev3bck7g5wjk',
}
SKIP_KEYS = {'ai_note', 'note', 'description', 'summary', 'text', 'title_info'}
APPLY = '--apply' in sys.argv
report = []


def fix(obj, key=None):
    """就地替换；返回改动次数。字符串正文类字段跳过。"""
    n = 0
    if isinstance(obj, dict):
        for k, v in obj.items():
            n += fix(v, k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, str) and v in PAIRS and key not in SKIP_KEYS:
                obj[i] = PAIRS[v]; n += 1
            else:
                n += fix(v, key)
    return n


def fix_scalars(d):
    n = 0
    stack = [d]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            for k, v in list(o.items()):
                if isinstance(v, str) and v in PAIRS and k not in SKIP_KEYS:
                    o[k] = PAIRS[v]; n += 1
                elif isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(o, list):
            for v in o:
                if isinstance(v, (dict, list)):
                    stack.append(v)
    return n


for sub in ('Work', 'Book', 'Collection', 'Entity'):
    base = os.path.join(DRAFT, sub)
    for dp, _, fns in os.walk(base):
        for fn in fns:
            if not fn.endswith('.json'):
                continue
            fp = os.path.join(dp, fn)
            try:
                raw = open(fp, encoding='utf-8').read()
            except Exception:
                continue
            if not any(s in raw for s in PAIRS):
                continue
            try:
                d = json.loads(raw)
            except Exception:
                continue
            n = fix(d) + fix_scalars(d)
            if n:
                # Entity.works / Work.books 去重
                for arr in ('works', 'books'):
                    if isinstance(d.get(arr), list):
                        seen, out = set(), []
                        for x in d[arr]:
                            if not isinstance(x, str):
                                out.append(x); continue
                            if x not in seen:
                                seen.add(x); out.append(x)
                        d[arr] = out
                report.append((os.path.relpath(fp, DRAFT), n))
                if APPLY:
                    json.dump(d, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print(('APPLY' if APPLY else 'DRY-RUN'), len(report), '个文件')
for f, n in report:
    print(f'  {f}  ({n})')
