#!/usr/bin/env python3
"""依 SCHEMA.md §period 規則2「著錄之志為時代上限」核出 period 過晚的條目。
注本 period 取注者朝代却继承原典的早期志书著录，属假阳性，以 derived_from_annotator 标出。"""
import json, glob, os, collections
os.chdir('/workspace/book-index-draft')
ORDER = ['pre-qin','qin-han','three-kingdoms','jin','nanbeichao','sui-tang',
         'five-dynasties','song','liao-jin-yuan','ming','qing','modern']
RANK = {p: i for i, p in enumerate(ORDER)}
BOUND = {'漢書藝文志':'qin-han','漢藝文志考證':'song','後漢藝文志':'qing','三國藝文志':'qing',
 '補晉書藝文志':'qing','隋書經籍志':'sui-tang','隋書經籍志考證':'qing','舊唐書經籍志':'five-dynasties',
 '新唐書藝文志':'song','崇文總目':'song','郡齋讀書志':'song','直齋書錄解題':'song','通志藝文略':'song',
 '宋史藝文志':'liao-jin-yuan','國史經籍志':'ming','明史藝文志':'qing','欽定四庫全書總目':'qing',
 '書目答問':'qing','清史稿藝文志':'modern','續修四庫全書':'modern'}
ZHU = {'注','傳','疏','章句','集解','義疏','附註','箋','集注','音義','注疏','校','輯','編','纂'}
idx = {}
for f in glob.glob('index/works/*.json'):
    idx.update(json.load(open(f, encoding='utf-8')))
rows = []
for k, v in idx.items():
    d = json.load(open(v['path'], encoding='utf-8'))
    p = d.get('period')
    if p not in RANK:
        continue
    ibs = [ib.get('source') for ib in (d.get('indexed_by') or []) if isinstance(ib, dict)]
    bounds = [BOUND[s] for s in ibs if s in BOUND]
    if not bounds:
        continue
    tight = min(bounds, key=lambda b: RANK[b])
    if RANK[p] <= RANK[tight]:
        continue
    au = d.get('authors') or []
    role = au[0].get('role') if au and isinstance(au[0], dict) else None
    rows.append(dict(id=k, title=d.get('title'), period=p, bound=tight,
                     author=(au[0].get('name') if au else None), role=role,
                     derived_from_annotator=bool(role and any(z in role for z in ZHU)),
                     catalogs=sorted(set(s for s in ibs if s in BOUND)),
                     period_basis=(d.get('period_basis') or '')[:120], path=v['path']))
rows.sort(key=lambda r: (r['derived_from_annotator'], -(RANK[r['period']] - RANK[r['bound']])))
real = [r for r in rows if not r['derived_from_annotator']]
out = '.claude/known-issues/period-著錄志上限衝突.json'
json.dump({'generated': '2026-08-19',
           'rule': 'SCHEMA.md §period 規則2「著錄之志為時代上限」',
           'note': 'derived_from_annotator=true 者為注本假陽性：注本 period 取注者朝代，'
                   '却继承原典的早期志書著錄（如逸周書孔晁注 period=jin 正確）',
           'total': len(rows), 'likely_real': len(real),
           'likely_false_positive_annotator': len(rows) - len(real),
           'items': rows}, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'{out}: 总 {len(rows)}，疑真 {len(real)}，注本假阳性 {len(rows)-len(real)}')
print(collections.Counter((r['period'], r['bound']) for r in real).most_common(6))
