#!/usr/bin/env python
"""標記錯掛之著錄節：`indexed_by[].misattached`。

catalog_bound 覆驗查出一批 Work 之 period 逾其著錄志之上限，而該志之著錄語與本條
撰人全不相干——是同題異書被併為一條。實測其中絕大多數早志之節只有光禿禿的書名
與卷數（「法喜集二卷」「明良集五百卷」），連撰人都無，除題名外無從配對，
而題名相同正是當初誤併之由。

**不新建 Work。** 節之所指究竟何書，僅憑一題一卷數無從知曉；為之新建二百餘條
極薄之 Work，與 main 正在做的「撤薄條目」相反，且不可逆。改以標記存之：

    "misattached": true,
    "misattached_note": "……何以判為錯掛"

標記者：
- 計 period_upper 時跳過，故不再與 period 相斥
- 資訊全存，隨時可升格為獨立 Work
- 出清單於 known-issues/著錄錯掛待建.json

用法：python mark_misattached_nodes.py [--apply]
"""
import json, glob, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from period_bounds import BOUND, I  # noqa: E402

APPLY = '--apply' in sys.argv
ROOTS = ('/workspace/book-index-draft', '/workspace/book-index')


def main():
    marked = 0
    lst = []
    for root in ROOTS:
        for f in glob.glob(f'{root}/Work/*/*/*/*.json'):
            try:
                d = json.load(open(f, encoding='utf-8'))
            except Exception:
                continue
            if d.get('_promoted_to') or not d.get('period'):
                continue
            nm = (d.get('authors') or [{}])[0].get('name')
            hit = [r for r in d.get('indexed_by') or []
                   if r.get('source') in BOUND
                   and I[BOUND[r['source']][0]] < I[d['period']]
                   and not r.get('misattached')]
            if not hit:
                continue
            # A 類（著錄語含本條撰人名）不屬本專項——那是撰人朝代錯或志書誤收
            if any(nm and nm in (str(r.get('summary') or '') + str(r.get('author_info') or ''))
                   for r in hit):
                continue
            for r in hit:
                ub = BOUND[r['source']][0]
                r['misattached'] = True
                r['misattached_note'] = (
                    f'2026-08-21 catalog_bound 覆驗：本節出《{r["source"]}》（上限 {ub}），'
                    f'而本條為 {d["period"]} 之作、撰人{nm or "闕"}，著錄語與之全不相干——'
                    f'係同題異書誤併。所指何書，僅憑題名卷數無從斷，未別立 Work，'
                    f'記於 known-issues/著錄錯掛待建.json 待考。')
                lst.append({'原繫': d['id'], '原繫題名': d.get('title'),
                            '原繫period': d['period'], '撰人': nm,
                            '志': r.get('source'), '該志上限': ub,
                            '著錄題': r.get('title_info'),
                            '著錄語': str(r.get('summary') or '')[:200]})
                marked += 1
            d['ai_note'] = ((d.get('ai_note') or '') +
                            f'\n\n2026-08-21 著錄錯掛標記：本條所繫 {len(hit)} 節出於'
                            f'{"、".join(sorted({r["source"] for r in hit}))}，其上限早於本條之 period，'
                            f'且著錄語與本條撰人全不相干，判為同題異書誤併，已標 misattached。'
                            f'計 period_upper 時跳之。').strip()
            if APPLY:
                with open(f, 'w', encoding='utf-8', newline='\n') as fh:
                    fh.write(json.dumps(d, ensure_ascii=False, indent=2))
    print(f'標記 {marked} 節，涉 {len({x["原繫"] for x in lst})} 條 Work')
    if APPLY:
        json.dump(lst, open('/workspace/book-index-draft/.claude/known-issues/著錄錯掛待建.json',
                            'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
