#!/usr/bin/env python3
"""把《經義考》之論斷填入各 work 之 `indexed_by[].summary`

前此 summary 只放著錄語（「宋志十卷」），是解析截斷之餘；朱彝尊於每條下所輯
諸家論斷（劉歆曰、崇文總目、中興書目、某人志墓……）一概未入。今補。

**體例**：`summary` = 著錄語 ＋ 換行 ＋ 論斷。論斷逾 500 字者截之，綴以省略
號並指其全文所在——全文已入《經義考》之整理本
`Work/1/e/v/1ev3bb43bv4lc/collated_edition/{類}.json`，以 `page` 為鍵可覆。

**繫連之法**：以 `page` 與 `title_info` 之題比對原文標目，一頁一中者取之。
一頁數條而題皆可通者不取——頁次不足以定條，寧闕勿誤。
"""
import json, glob, os, re, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import nz

SRC = '.claude/known-issues/經義考論斷.json'
LIMIT = 500
TAIL = '……（下略。全文見《經義考》整理本 collated_edition/{lei}.json，頁 {page}）'


def main():
    apply = '--apply' in sys.argv
    src = json.load(open(SRC))
    by_page = collections.defaultdict(list)
    for x in src:
        by_page[x['page']].append(x)

    n_file = n_rec = n_fill = n_amb = n_nolun = n_same = 0
    trunc = 0
    for p in glob.glob('Work/*/*/*/*.json'):
        d = json.load(open(p))
        hit = False
        for e in (d.get('indexed_by') or []):
            if e.get('source') != '經義考' or not e.get('page'):
                continue
            n_rec += 1
            m = re.match(r'《(.+?)》', e.get('title_info') or '')
            t = nz(m.group(1)) if m else ''
            cand = [x for x in by_page.get(e['page'], []) if t and t in nz(x['head'])]
            if len(cand) != 1:
                n_amb += 1
                continue
            lun = cand[0]['lun']
            if not lun:
                n_nolun += 1
                continue
            zhu = cand[0]['zhu'] or e.get('summary') or ''
            if len(lun) > LIMIT:
                lun = lun[:LIMIT] + TAIL.format(lei=cand[0]['lei'], page=e['page'])
                trunc += 1
            new = (zhu + '\n' + lun) if zhu else lun
            new = new.strip()
            if e.get('summary') == new:
                n_same += 1
                continue
            e['summary'] = new
            n_fill += 1
            hit = True
        if hit:
            n_file += 1
            if apply:
                with open(p, 'w', encoding='utf-8') as f:
                    json.dump(d, f, ensure_ascii=False, indent=2)
                    f.write('\n')
    print(f'經義考記錄 {n_rec}：填 {n_fill}（涉 work {n_file}，其中截斷 {trunc}），'
          f'原文無論斷 {n_nolun}，頁中數條不能定 {n_amb}，已同 {n_same}')
    if not apply:
        print('（乾跑。加 --apply 方寫檔）')


if __name__ == '__main__':
    main()
