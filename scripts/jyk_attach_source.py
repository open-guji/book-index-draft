#!/usr/bin/env python3
"""甲層掛源：為庫中已有之書補《經義考》一源

只動 Work 之 `indexed_by[]`，不動 `loss_status`、不動 `period`、不動
`authors[]`——與 A／B／C 諸道無欄位之爭。

朱彝尊之存佚判入 `attested_status`，**不改本庫之 `loss_status`**：四庫御製
題已論「所注闕佚未見者，今四庫所録往往其書尚存」，其判是十七世紀一人之
見聞；「未見」尤非亡佚，是朱氏未見其書。

掛源之對象：
  甲1 題與撰人俱合
  甲2 撰人同而題名互為子串（「易洞林」對「周易洞林」）
      ＋庫方題名夾撰人者（「王文獻孝經詳解」對「王氏（文獻）孝經詳解」）
  甲4 撰人同而其名嵌於庫題之中（「春秋左氏傳王朗注」對「春秋左氏傳注」）

一條對庫中二書以上者一律不掛，另出待覈之目——同題同撰而庫有二條，是庫
中重出之疑，當先併而後掛，不可兩邊各掛一源。
"""
import json, os, sys, collections, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import nz, load_index, embedded_author

DATA = '.claude/known-issues/經義考待裁.json'
AMBIG = '.claude/known-issues/經義考掛源待覈.json'
SRC = '經義考'
SRC_BID = '1ev3bb43bv4lc'
STATUS = {'佚': 'lost', '存': 'extant', '未見': 'not_seen', '闕': 'partial'}
NOTE = ('此是朱彝尊所判，非本庫之判，故不改本記錄之 loss_status。'
        '四庫御製題論此書曰「所注闕佚未見者，今四庫所録往往其書尚存」'
        '——其判是十七世紀一人之見聞。「未見」尤非亡佚，是朱氏未見其書。')


def targets(d, by_title, by_author, works):
    """回傳本條所指之 work id 列（空＝不掛，長度>1＝待覈）"""
    ja, jt = nz(d.get('author')), nz(d.get('title'))
    if d['tier'] == '甲1':
        return [w['id'] for w in by_title.get(jt, []) if nz(w.get('author')) == ja]
    if d['tier'] == '甲4':
        # 庫題以「經名＋撰人＋役」立題，撰人之名嵌於題中（《春秋左氏傳王朗注》
        # 對《春秋左氏傳注》）。2026-08-23 補立之閘，見 jyk_triage。
        return [w['id'] for w in embedded_author(jt, ja, by_author)]
    if d['tier'] == '甲2':
        if d.get('same_author_sub'):
            return [x[0] for x in d['same_author_sub']]
        # 庫方題名夾撰人
        out = []
        for x in (d.get('loose') or []):
            w = works.get(x[1])
            if not w or not ja or len(jt) < 2:
                continue
            nt = nz(w['title'])
            if ja in nt and jt in nt and len(nt) <= len(ja) + len(jt) + 4:
                out.append(w['id'])
        return out
    return []


def main():
    apply = '--apply' in sys.argv
    works = load_index('works')
    by_title, by_author = collections.defaultdict(list), collections.defaultdict(list)
    for v in works.values():
        by_title[nz(v.get('title'))].append(v)
        if v.get('author'):
            by_author[nz(v['author'])].append(v)

    D = json.load(open(DATA))
    plan, ambig = collections.defaultdict(list), []
    for d in D:
        if d['tier'] not in ('甲1', '甲2', '甲4'):
            continue
        ids = targets(d, by_title, by_author, works)
        if not ids:
            ambig.append({'why': '無對象', **{k: d[k] for k in ('head', 'author', 'title', 'tier', 'juan', 'page')}})
        elif len(ids) > 1:
            ambig.append({'why': '庫中二條以上', 'ids': ids,
                          **{k: d[k] for k in ('head', 'author', 'title', 'tier', 'juan', 'page')}})
        else:
            plan[ids[0]].append(d)

    n_add = n_skip = n_file = 0
    for wid, ds in plan.items():
        path = works[wid]['path']
        w = json.load(open(path))
        idx = w.setdefault('indexed_by', [])
        seen = {(e.get('source'), e.get('page')) for e in idx}
        added = False
        for d in ds:
            if (SRC, d['page']) in seen:
                n_skip += 1
                continue
            ti = f"《{d['title']}》" + (f"（{d['author']}）" if d.get('author') else '')
            rec = {'source': SRC, 'source_bid': SRC_BID, 'title_info': ti,
                   'summary': '；'.join(d['attest']) if d['attest'] else '',
                   'section': d['lei'], 'juan': d['juan'], 'page': d['page'],
                   'attested_status': STATUS[d['status']],
                   'attested_status_raw': d['status'],
                   'attested_status_note': NOTE}
            idx.append(rec)
            seen.add((SRC, d['page']))
            n_add += 1
            added = True
        if added and apply:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(w, f, ensure_ascii=False, indent=2)
                f.write('\n')
            n_file += 1
        elif added:
            n_file += 1

    print(f'掛源 {n_add} 條，涉 work {n_file} 個；已有而跳過 {n_skip}；待覈 {len(ambig)}')
    print(collections.Counter(a['why'] for a in ambig))
    if apply:
        json.dump(ambig, open(AMBIG, 'w'), ensure_ascii=False, indent=1)
        for d in D:
            if d['tier'] in ('甲1', '甲2', '甲4'):
                ids = targets(d, by_title, by_author, works)
                if len(ids) == 1:
                    d['attached_to'] = ids[0]
        json.dump(D, open(DATA, 'w'), ensure_ascii=False, indent=1)
    else:
        print('（乾跑。加 --apply 方寫檔）')


if __name__ == '__main__':
    main()
