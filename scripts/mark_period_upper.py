#!/usr/bin/env python
"""標 period_upper——合 catalog_bound（著錄之志）與 edition_bound（存世之本）二源，取其緊者。

只標於 `period` 為空或與上限相斥者（SCHEMA〈period_upper〉）。

相斥之判用**年份區間**而非 ORD 之序：`period` 是政權軸，song 與 liao-jin-yuan
全重疊 319 年，序上比會把遼人之書（有宋刻本者）誤判為相斥。

用法：python mark_period_upper.py [--apply]
"""
import json, glob, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from period_bounds import (BOUND, I, ORD, tightest, edition_bound,  # noqa: E402
                           conflicts_with_bound, excavation_bound,
                           catalog_section_bound, desc_edition,
                           collection_bound, ambiguous_dynasty_bound)

APPLY = '--apply' in sys.argv
# 未掛 production 倉（../book-index）時，其側 Book 之 edition 讀不到，
# 上限遂算不出而落入「撤除」一支——那是假陽性，會刪掉本來對的上限。
# --only-missing：只補未標者，一概不改、不撤已標之值。
ONLY_MISSING = '--only-missing' in sys.argv
# 倉根自本檔推得，不寫死容器路徑（舊值 /workspace/... 在別的容器佈局下寫成，
# 移倉之後即掃不到任何檔，遂使此後新建之 work 一概未標上限）
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOTS = (_R, os.path.join(os.path.dirname(_R), 'book-index'))


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
    n_x = n_sec = n_fix = n_col = n_amb = 0
    for root in ROOTS:
        for f in glob.glob(f'{root}/Work/*/*/*/*.json'):
            try:
                d = json.load(open(f, encoding='utf-8'))
            except Exception:
                continue
            if d.get('_promoted_to'):
                continue
            if ONLY_MISSING and d.get('period_upper') is not None:
                continue
            nodes = d.get('indexed_by') or []
            cb = tightest(nodes)
            eb_pairs = [(edition_bound((BK.get(b) or {}).get('edition')),
                         (BK.get(b) or {}).get('edition'))
                        for b in d.get('books') or []]
            eb_pairs = [x for x in eb_pairs if x[0]]
            eb, ed = (min(eb_pairs, key=lambda x: I[x[0]]) if eb_pairs else (None, None))

            desc = d.get('description') or {}
            dtext = desc.get('text') or ''
            dsrcs = desc.get('sources') or []
            # 描述末之版本語（有本無 Book 者）——與 Book.edition 同為 edition_bound
            de = desc_edition(dtext)
            deb = edition_bound(de) if de else None
            if deb and (not eb or I[deb] < I[eb]):
                eb, ed = deb, de
            # 出土批次
            xb, xname = excavation_bound(
                dtext + ' ' + ' '.join(x if isinstance(x, str) else (x.get('title') or '')
                                       for x in dsrcs),
                d.get('title'))
            # 志書子目之斷代
            sb, sname = catalog_section_bound(dsrcs)
            # 叢編之收書範圍（描述或案語所記）
            lb, lname, lwhy = collection_bound(dtext + ' ' + (d.get('ai_note') or ''))
            # 歧義朝代名取諸解中最晚者
            ab, aname = None, None
            for a in d.get('authors') or []:
                v = ambiguous_dynasty_bound(a.get('dynasty'))
                if v and (not ab or I[v] > I[ab]):
                    ab, aname = v, a.get('dynasty')

            cands = [(cb, 'catalog'), (eb, 'edition'), (xb, 'excavation'),
                     (sb, 'section'), (lb, 'collection'), (ab, 'ambiguous')]
            cands = [c for c in cands if c[0]]
            if cands:
                ub, src = min(cands, key=lambda c: I[c[0]])
            else:
                ub, src = None, None

            p = d.get('period')
            old = d.get('period_upper')
            if not ub or (ub == 'modern' and not p):
                if old is not None and not ONLY_MISSING:
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
                elif src == 'excavation':
                    basis = (f'excavation_bound：本書出於{xname}——'
                             f'簡帛抄寫之年不早於成書之年，故不晚於 {ub}')
                elif src == 'collection':
                    basis = (f'collection_bound：本書收入《{lname}》——{lwhy}，'
                             f'故不晚於 {ub}')
                elif src == 'ambiguous':
                    basis = (f'撰人朝代作「{aname}」，歧而未決；諸解中最晚者為 {ub}，'
                             f'無論何解皆不晚於此')
                elif src == 'section':
                    basis = (f'catalog_bound：{sname}自標所收之代，故不晚於 {ub}')
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
                    n_cat += src == 'catalog'
                    n_ed += src == 'edition'
                    n_x += src == 'excavation'
                    n_sec += src == 'section'
                    n_col += src == 'collection'
                    n_amb += src == 'ambiguous'
                    # 上限至軸首者即成定判：無更早之代可容，逕定 period
                    if ub == ORD[0]:
                        d['period'] = ub
                        d['period_basis'] = basis.replace('故不晚於', '故定為')
                        d.pop('period_upper', None)
                        d.pop('period_upper_basis', None)
                        n_fix += 1
                elif old is not None and not ONLY_MISSING:
                    d.pop('period_upper', None)
                    d.pop('period_upper_basis', None)
                    n_rm += 1
                else:
                    continue
            if APPLY:
                with open(f, 'w', encoding='utf-8', newline='\n') as fh:
                    # 檔尾須有換行——chk〈JSON 缺檔尾換行〉基線為 0
                    fh.write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
    print(f'標 period_upper：據志 {n_cat}，據版本 {n_ed}，據出土 {n_x}，'
          f'據子目 {n_sec}，據叢編 {n_col}，據歧義朝代 {n_amb}，'
          f'相斥存疑 {n_conf}，撤除 {n_rm}；'
          f'其中上限至軸首而逕定 period 者 {n_fix}'
          + ('' if APPLY else '  (dry-run)'))


if __name__ == '__main__':
    main()
