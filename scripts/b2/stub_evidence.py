# -*- coding: utf-8 -*-
"""B2 版之 stub_evidence：找「整理本另立之無撰人 stub」與其同組同卷之有撰人條
配對，並以該 stub 所繫整理本 section 之正文是否書有候選之撰人名為證。只讀不寫。"""
import json, glob, sys, collections

GS = json.load(open(sys.argv[1], encoding='utf-8'))
IW = {}
for f in glob.glob('index/works/*.json'): IW.update(json.load(open(f, encoding='utf-8')))

sec = collections.defaultdict(list)
for p in glob.glob('Work/*/*/*/*/collated_edition/*.json'):
    try: d = json.load(open(p, encoding='utf-8'))
    except Exception: continue
    for s in (d.get('sections') if isinstance(d, dict) else []) or []:
        if not isinstance(s, dict): continue
        for wid in ([s['work_id']] if s.get('work_id') else []) + (s.get('work_ids') or []):
            sec[wid].append((p, s.get('title'), s.get('content') or ''))

out = []
for G in GS:
    R = G['records']
    for s in R:
        if s['authors']: continue
        cand = [r for r in R if r['authors'] and r['juan'] and s['juan'] and r['juan'] == s['juan']]
        if len(cand) != 1: continue
        c = cand[0]
        names = [a['name'] for a in c['authors'] if a.get('name')]
        hits = []
        for p, t, body in sec.get(s['id'], []):
            for n in names:
                if n and n in body: hits.append((p.split('/')[-1], t, n, body[:150]))
        if hits:
            out.append({'title': G['title'], 'stub': s['id'], 'juan': s['juan'],
                        'keeper': c['id'], 'names': names, 'evidence': hits})
json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
