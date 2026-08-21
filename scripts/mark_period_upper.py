#!/usr/bin/env python
"""標 period_upper——合 catalog_bound（著錄之志）與 edition_bound（存世之本）二源，取其緊者。

只標於 `period` 為空或與上限相斥者（SCHEMA〈period_upper〉）。

相斥之判用**年份區間**而非 ORD 之序：`period` 是政權軸，song 與 liao-jin-yuan
全重疊 319 年，序上比會把遼人之書（有宋刻本者）誤判為相斥。

用法：python mark_period_upper.py [--apply]
"""
import json, glob, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from period_bounds import (BOUND, I, tightest, edition_bound,  # noqa: E402
                           conflicts_with_bound)

APPLY = '--apply' in sys.argv
ROOTS = ('/workspace/book-index-draft', '/workspace/book-index')


def main():
    BK = {}
    for root in ROOTS:
        for f in glob.glob(f'{root}/Book/*/*/*/*.json'):
            try:
                b = json.load(open(f, encoding='utf-8'))
            except Exception:
                continue
            BK[b['id']] = b

    n_cat = n_ed = n_conf = n_rm = 0
    for root in ROOTS:
        for f in glob.glob(f'{root}/Work/*/*/*/*.json'):
            try:
                d = json.load(open(f, encoding='utf-8'))
            except Exception:
                continue
            if d.get('_promoted_to'):
                continue
            nodes = d.get('indexed_by') or []
            cb = tightest(nodes)
            eb_pairs = [(edition_bound((BK.get(b) or {}).get('edition')),
                         (BK.get(b) or {}).get('edition'))
                        for b in d.get('books') or []]
            eb_pairs = [x for x in eb_pairs if x[0]]
            eb, ed = (min(eb_pairs, key=lambda x: I[x[0]]) if eb_pairs else (None, None))

            src = None
            if cb and eb:
                if I[cb] <= I[eb]:
                    ub, src = cb, 'catalog'
                else:
                    ub, src = eb, 'edition'
            elif cb:
                ub, src = cb, 'catalog'
            elif eb:
                ub, src = eb, 'edition'
            else:
                ub = None

            p = d.get('period')
            old = d.get('period_upper')
            if not ub or (ub == 'modern' and not p):
                if old is not None:
                    d.pop('period_upper', None)
                    d.pop('period_upper_basis', None)
                    n_rm += 1
                else:
                    continue
            else:
                if src == 'catalog':
                    w = [r.get('source') for r in nodes if not r.get('misattached')
                         and r.get('source') in BOUND and BOUND[r['source']][0] == ub]
                    basis = (f'catalog_bound：所繫諸志中最緊者為《{w[0]}》'
                             f'（{BOUND[w[0]][1]}），故不晚於 {ub}')
                else:
                    basis = (f'edition_bound：所掛版本中最早者為「{ed}」——'
                             f'版本之年不早於成書之年，故不晚於 {ub}')
                if p and conflicts_with_bound(p, ub):
                    d['period_upper'] = ub
                    d['period_upper_basis'] = basis + '　**與現判之 period 相斥，存疑待覈**'
                    n_conf += 1
                elif not p:
                    d['period_upper'] = ub
                    d['period_upper_basis'] = basis
                    if src == 'catalog':
                        n_cat += 1
                    else:
                        n_ed += 1
                elif old is not None:
                    d.pop('period_upper', None)
                    d.pop('period_upper_basis', None)
                    n_rm += 1
                else:
                    continue
            if APPLY:
                with open(f, 'w', encoding='utf-8', newline='\n') as fh:
                    fh.write(json.dumps(d, ensure_ascii=False, indent=2))
    print(f'標 period_upper：據志 {n_cat}，據版本 {n_ed}，相斥存疑 {n_conf}，撤除 {n_rm}'
          + ('' if APPLY else '  (dry-run)'))


if __name__ == '__main__':
    main()
