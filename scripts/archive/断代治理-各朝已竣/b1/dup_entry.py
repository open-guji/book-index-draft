# -*- coding: utf-8 -*-
"""B1 續：組內兩條若其 indexed_by 有完全同源同文的著錄（source+title_info 全同，
且 title_info 帶卷數或另有撰人／限定語，非裸書名），是同一著錄匯入兩次。只讀不寫。"""
import json, sys, itertools, re

GS = json.load(open(sys.argv[1], encoding='utf-8'))

def specific(t, title):
    if not t: return False
    bare = {title, '《'+title+'》'}
    if t.strip() in bare: return False
    return bool(re.search(r'[0-9〇一二三四五六七八九十百千卷（(]', t))

def key(e):
    return (e.get('source'), (e.get('title_info') or '').strip())

rows = []
for G in GS:
    R = G['records']
    for x, y in itertools.combinations(R, 2):
        kx = {key(e) for e in x['indexed_by'] if specific(e.get('title_info'), G['title'])}
        ky = {key(e) for e in y['indexed_by'] if specific(e.get('title_info'), G['title'])}
        common = kx & ky
        if common:
            rows.append({'title': G['title'], 'a': x['id'], 'b': y['id'], 'common': list(common),
                        'an': [aa['name'] for aa in x['authors']], 'bn': [bb['name'] for bb in y['authors']]})
json.dump(rows, sys.stdout, ensure_ascii=False, indent=1)
