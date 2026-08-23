# -*- coding: utf-8 -*-
"""B1 續：把指定組的全部條目印成緊湊一行，供批量目視篩查。只讀不寫。"""
import json, sys
G = {g['title']: g for g in json.load(open(sys.argv[1], encoding='utf-8'))}
for t in sys.argv[2:]:
    if t not in G: continue
    print('##', t)
    for r in G[t]['records']:
        names = ','.join(a['name'] for a in r['authors']) or '—'
        srcs = ';'.join(f"{e['source']}:{(e.get('title_info') or (e.get('summary') or '')[:40])}" for e in r['indexed_by'])
        print(f"   {r['id']} [{names}] j{r['juan']} {srcs}")
