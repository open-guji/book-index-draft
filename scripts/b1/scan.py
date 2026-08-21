# -*- coding: utf-8 -*-
"""B1（同名異書 size>=4）掃描：把 393 組的全部欄位攤平成 JSON，供逐組裁決。
只讀不寫。用法：python3 scripts/b1/scan.py > .claude/known-issues/b1_groups.json"""
import json, glob, collections, sys, os

IW = {}
for f in glob.glob('index/works/*.json'):
    IW.update(json.load(open(f, encoding='utf-8')))

g = collections.defaultdict(list)
for k, v in IW.items():
    if v.get('title') and not v.get('promoted_to'):
        g[v['title']].append(k)
groups = {t: ks for t, ks in g.items() if len(ks) >= 4}

def load(wid):
    p = IW[wid]['path']
    return json.load(open(p, encoding='utf-8'))

out = []
for t, ks in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0])):
    recs = []
    for wid in sorted(ks):
        d = load(wid)
        idx = []
        for e in (d.get('indexed_by') or []):
            idx.append({
                'source': e.get('source_title') or e.get('source') or e.get('source_bid'),
                'title_info': e.get('title_info'),
                'author_info': e.get('author_info'),
                'category': e.get('category') or e.get('category_path'),
            })
        recs.append({
            'id': wid,
            'authors': [{'name': a.get('name'), 'role': a.get('role'), 'dynasty': a.get('dynasty'),
                         'entity_id': a.get('entity_id')} for a in (d.get('authors') or [])],
            'juan': (d.get('juan_count') or {}).get('number'),
            'juan_desc': (d.get('juan_count') or {}).get('description'),
            'measure_info': d.get('measure_info'),
            'dynasty': d.get('dynasty'),
            'period': d.get('period'),
            'period_upper': d.get('period_upper'),
            'loss_status': d.get('loss_status'),
            'original_title': d.get('original_title'),
            'additional_titles': d.get('additional_titles'),
            'n_books': len(d.get('books') or []),
            'n_related': len(d.get('related_works') or []),
            'related': [{'id': r.get('id'), 'title': r.get('title'), 'relation': r.get('relation')}
                        for r in (d.get('related_works') or [])],
            'indexed_by': idx,
            'n_emend': len(d.get('emendated_by') or []),
            'desc': (json.dumps(d.get('description'), ensure_ascii=False)[:400]
                     if d.get('description') else None),
            'ai_note': (d.get('ai_note') or '')[:300] or None,
        })
    out.append({'title': t, 'size': len(recs), 'records': recs})

json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
sys.stdout.write('\n')
