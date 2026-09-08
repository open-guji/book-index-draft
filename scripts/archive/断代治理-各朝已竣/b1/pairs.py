# -*- coding: utf-8 -*-
"""B1 第三檔：無撰人之條與同組唯一同卷數之有撰人條配對，印其著錄原文供裁決。只讀不寫。"""
import json, sys, collections
GS = json.load(open(sys.argv[1], encoding='utf-8'))
want = set(sys.argv[2:]) or None
for G in GS:
    if want and G['title'] not in want: continue
    R = G['records']
    noa = [r for r in R if not r['authors']]
    for s in noa:
        cand = [r for r in R if r['authors'] and r['juan'] and s['juan'] and r['juan'] == s['juan']]
        if len(cand) != 1: continue
        c = cand[0]
        print('##', G['title'], '　無撰人條', s['id'], 'j'+str(s['juan']))
        for e in s['indexed_by']:
            print('   [', e['source'], ']', e['title_info'], '||', (e.get('title_info') or ''), '::',
                  (json.dumps(e, ensure_ascii=False)[:0] or ''))
        print('   摘要：', ' ／ '.join((x or '')[:200] for x in [s.get('desc')]))
        print('  → 唯一同卷候選', c['id'], [a['name'] for a in c['authors']], 'j'+str(c['juan']),
              [e['source'] for e in c['indexed_by']])
