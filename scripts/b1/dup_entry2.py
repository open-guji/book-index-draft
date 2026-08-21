# -*- coding: utf-8 -*-
"""B1 續（收窄版）：只取「組內同 source+title_info 恰好命中兩條」者——命中三條以上
多是志書本身在同一標題卷數之下臚列數家（如《周易注》十卷歷數十餘家），非重出。
只讀不寫。"""
import json, sys, collections

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
            import re
            if not re.search(r'[0-9〇一二三四五六七八九十百千卷（(]', t): continue
            by_key[key(e)].append(r['id'])
    for k, ids in by_key.items():
        uids = sorted(set(ids))
        if len(uids) == 2:
            recs = {r['id']: r for r in R}
            a, b = [recs[i] for i in uids]
            rows.append({'title': G['title'], 'src_title_info': k, 'a': a['id'], 'b': b['id'],
                        'an': [x['name'] for x in a['authors']], 'bn': [x['name'] for x in b['authors']],
                        'aj': a['juan'], 'bj': b['juan']})
json.dump(rows, sys.stdout, ensure_ascii=False, indent=1)
