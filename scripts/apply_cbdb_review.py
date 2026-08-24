#!/usr/bin/env python3
"""A2：CBDB 匹配之**複審結果**落庫（2026-08-24）。

不逕用 apply_cbdb_dynasty.py 之機器結果——本地 CBDB SQLite 不在遠端容器，
改走公開 API 按人名查詢，而 name-only 匹配有硬傷：**CBDB 中之同名異人**。

實測誤配（皆為複審所擋）：
  孫炎——《爾雅孫氏注》之孫炎是三國魏鄭玄門人，CBDB 配元至正間孫炎（朱元璋幕僚）
  李恕——引文楊士奇稱「廬陵李省中先生名恕」，明初人，CBDB 配唐人（卒 823）
  李鼎——《學庸大旨》，「學庸」是宋以後之合稱，唐人不能撰
  張洪——《四書解義》，「四書」之名起於朱子以後，北宋初人不能撰
  陳銓——隋志所著錄之注者，晉宋間禮家，CBDB 配明成化間人

複審 209 條中弃 65（誤配率 31%）——若逕落機器結果，四百餘條中約百三十條是錯的。
故本腳本只讀複審之 adopt=true 者。

用法：python3 scripts/apply_cbdb_review.py <review_dir> [--apply]
"""
import json, glob, os, sys, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from period_bounds import PERIOD_YEARS, ORD


def compatible(period, upper):
    if not upper:
        return True
    a, b = PERIOD_YEARS.get(period), PERIOD_YEARS.get(upper)
    if not a or not b:
        return True
    return a[0] <= b[1]


def main():
    rdir = sys.argv[1]
    apply_ = '--apply' in sys.argv

    src = {}
    for f in sorted(glob.glob(os.path.join(rdir, 'cr_*.json'))):
        if f.endswith('.result.json'):
            continue
        for e in json.load(open(f)):
            src[e['id']] = e
    dec = {}
    for f in sorted(glob.glob(os.path.join(rdir, 'cr_*.result.json'))):
        for r in json.load(open(f)):
            dec[r['id']] = r
    print(f'機器候選 {len(src)}　複審結果 {len(dec)}')

    picks, dropped, changed = [], [], 0
    for wid, r in dec.items():
        o = src.get(wid) or {}
        if not r.get('adopt'):
            dropped.append({'id': wid, 'title': o.get('title'),
                            'authors': o.get('authors'),
                            'cbdb擬定': o.get('cbdb_period'), 'reason': r.get('reason')})
            continue
        per = r.get('period')
        if per not in ORD:
            dropped.append({'id': wid, '故': f'period 不合法 {per}'})
            continue
        hits = glob.glob(f'Work/{wid[0]}/{wid[1]}/{wid[2]}/{wid}-*.json')
        if not hits:
            continue
        d = json.load(open(hits[0], encoding='utf-8'))
        if d.get('period') or d.get('_promoted_to'):
            continue
        if not compatible(per, d.get('period_upper')):
            dropped.append({'id': wid, 'title': d.get('title'),
                            '故': f'與上限 {d.get("period_upper")} 相斥', '擬定': per})
            continue
        if per != o.get('cbdb_period'):
            changed += 1
        picks.append((hits[0], d, r, o))

    print(f'採 {len(picks)}（其中複審改正機器擬定值 {changed}）　棄 {len(dropped)}')
    print(' 分代：', dict(collections.Counter(r['period'] for _, _, r, _ in picks).most_common()))
    if not apply_:
        print('（dry-run，加 --apply 方寫入）')
        return

    IW = {}
    for s in '0123456789abcdef':
        IW[s] = json.load(open(f'index/works/{s}.json'))

    def shard(i):
        h = 0
        for c in i:
            h = ((h * 31) + ord(c)) & 0xFFFFFFFF
        return '%x' % (h % 16)

    for p, d, r, o in picks:
        d['period'] = r['period']
        names = '、'.join(o.get('authors') or [])
        d['period_basis'] = (f'撰人朝代闕，據 CBDB 查其人（{names}）並經人審覈其確為本書之撰者'
                             f'——{r.get("reason") or ""}'
                             + (f'；上限 {d["period_upper"]} 覆驗不相斥'
                                if d.get('period_upper') else '')
                             + '（2026-08-24 A2 CBDB＋複審）')
        d['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
        e = IW[shard(d['id'])].get(d['id'])
        if e is not None:
            e['period'] = r['period']
    for s, obj in IW.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    with open('.claude/known-issues/A2-CBDB複審棄置.json', 'w', encoding='utf-8') as f:
        json.dump({'_說明': 'CBDB 按名匹配而複審判為不可採者。多為同名異人'
                            '（CBDB 之名不能自證其為同一人），或 CBDB 僅一條孤證而別無旁證。'
                            '此清單亦是 name-only 匹配之誤配樣本，可供日後改進判準。',
                   '條目': dropped}, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'已寫入 {len(picks)}')


if __name__ == '__main__':
    main()
