# -*- coding: utf-8 -*-
"""B2（同名異書 size=3）掃描：把 622 組的全部欄位攤平成 JSON，供逐組裁決。
只讀不寫。用法：python3 scripts/b2/scan.py > /tmp/.../b2_groups.json"""
import json, glob, collections, sys

IW = {}
for f in glob.glob('index/works/*.json'):
    IW.update(json.load(open(f, encoding='utf-8')))

g = collections.defaultdict(list)
for k, v in IW.items():
    if v.get('title') and not v.get('promoted_to'):
        g[v['title']].append(k)
groups = {t: ks for t, ks in g.items() if len(ks) == 3}

def load(wid):
    return json.load(open(IW[wid]['path'], encoding='utf-8'))

out = []
for t, ks in sorted(groups.items()):
    recs = []
    for wid in sorted(ks):
        d = load(wid)
        idx = []
        for e in (d.get('indexed_by') or []):
            idx.append({
                'source': e.get('source_title') or e.get('source') or e.get('source_bid'),
                'title_info': e.get('title_info'),
                'author_info': e.get('author_info'),
            })
        recs.append({
            'id': wid,
            'authors': [{'name': a.get('name'), 'role': a.get('role'), 'dynasty': a.get('dynasty'),
                         'entity_id': a.get('entity_id')} for a in (d.get('authors') or [])],
            'juan': (d.get('juan_count') or {}).get('number'),
            'measure_info': d.get('measure_info'),
            'dynasty': d.get('dynasty'),
            'period': d.get('period'),
            'loss_status': d.get('loss_status'),
            'n_books': len(d.get('books') or []),
            'n_related': len(d.get('related_works') or []),
            'indexed_by': idx,
            'desc': (json.dumps(d.get('description'), ensure_ascii=False)[:300]
                     if d.get('description') else None),
        })
    out.append({'title': t, 'size': len(recs), 'records': recs})

json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
sys.stdout.write('\n')
