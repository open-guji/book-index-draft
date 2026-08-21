# -*- coding: utf-8 -*-
"""B2 版之收窄同源著錄重出偵測：同 B1 dup_entry2.py。只讀不寫。"""
import json, sys, collections, re

GS = json.load(open(sys.argv[1], encoding='utf-8'))

def key(e):
    t = (e.get('title_info') or '').strip()
    return (e.get('source'), t)

rows = []
for G in GS:
    R = G['records']
    by_key = collections.defaultdict(list)
    for r in R:
        for e in r['indexed_by']:
            t = (e.get('title_info') or '').strip()
            if not t or t in (G['title'], '《'+G['title']+'》'): continue
            if not re.search(r'[0-9〇一二三四五六七八九十百千卷（(]', t): continue
            by_key[key(e)].append(r['id'])
    for k, ids in by_key.items():
        uids = sorted(set(ids))
        if len(uids) == 2:
            recs = {r['id']: r for r in R}
            a, b = [recs[i] for i in uids]
            rows.append({'title': G['title'], 'src_title_info': k, 'a': a['id'], 'b': b['id'],
                        'an': [x['name'] for x in a['authors']], 'bn': [x['name'] for x in b['authors']]})
json.dump(rows, sys.stdout, ensure_ascii=False, indent=1)
