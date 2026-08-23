# -*- coding: utf-8 -*-
"""B1 分流：把 393 組按「組內是否存在可疑重出對」排出優先序。只讀不寫。"""
import json, sys, itertools, collections

GS = json.load(open(sys.argv[1], encoding='utf-8'))

def norm(n):
    if not n: return ''
    s = n.strip()
    for junk in ('撰','注','編','輯','著','集解','解','傳','等','奉敕'):
        if s.endswith(junk) and len(s) > len(junk)+1: s = s[:-len(junk)]
    return s.strip()

def names(r):
    return {norm(a['name']) for a in r['authors'] if a.get('name')}

def one_char_diff(a, b):
    if len(a) != len(b) or len(a) < 2 or a == b: return False
    return sum(1 for x, y in zip(a, b) if x != y) == 1

rows = []
for gidx, G in enumerate(GS):
    pairs = []
    R = G['records']
    for x, y in itertools.combinations(R, 2):
        nx, ny = names(x), names(y)
        jx, jy = x['juan'], y['juan']
        sig = None
        if nx and ny and (nx & ny):
            sig = 'same-author'
        elif nx and ny and any(one_char_diff(p, q) for p in nx for q in ny):
            sig = 'author-1char'
        elif (not nx) != (not ny) and jx and jy and jx == jy:
            sig = 'one-noauthor-samejuan'
        elif not nx and not ny and jx and jy and jx == jy:
            sig = 'both-noauthor-samejuan'
        if sig:
            pairs.append({'a': x['id'], 'b': y['id'], 'sig': sig,
                          'an': sorted(nx), 'bn': sorted(ny), 'aj': jx, 'bj': jy})
    rank = {'same-author': 0, 'author-1char': 1, 'one-noauthor-samejuan': 2,
            'both-noauthor-samejuan': 3}
    best = min([rank[p['sig']] for p in pairs], default=9)
    rows.append({'title': G['title'], 'size': G['size'], 'n_pairs': len(pairs),
                 'best': best, 'pairs': pairs})

rows.sort(key=lambda r: (r['best'], -r['n_pairs'], -r['size']))
c = collections.Counter(r['best'] for r in rows)
print('# 分流計數（0 同撰人 / 1 撰人一字之差 / 2 一方無撰人而卷數同 / 3 兩無撰人而卷數同 / 9 無信號）',
      dict(sorted(c.items())), file=sys.stderr)
json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)
