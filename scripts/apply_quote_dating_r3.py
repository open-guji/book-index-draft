#!/usr/bin/env python3
"""R3 引文定代（2026-08-24）：落庫 LLM 批量判讀之結果。

輸入：scratchpad/quote_batches/batch_*.json（原條目，含 upper/cat/amb）
　　　scratchpad/quote_batches/batch_*.result.json（判讀結果）

只採 confidence == high 者，且過三重門：
  1. period 在枚舉內；
  2. 與 period_upper 年份區間不相斥（起年 ≤ 上限訖年）；
  3. cat=AMB 者，所判必須是該歧義字的合法讀法之一
     （amb=宋 只能判 nanbeichao|song，判出 ming 即與撰人欄相牴，不寫）。

不過門的 high、以及全部 medium，入待覈清單
`.claude/known-issues/R3-引文定代-待覈.json`。low/null 不記（無據）。
已寫入者記 `.claude/known-issues/R3-引文定代-已寫入.json`。

用法：python3 scripts/apply_quote_dating_r3.py <batches_dir> [--apply]
"""
import json, glob, os, re, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from period_bounds import PERIOD_YEARS, ORD

READ = {'宋': ['nanbeichao', 'song'], '魏': ['three-kingdoms', 'nanbeichao'],
        '周': ['pre-qin', 'nanbeichao', 'five-dynasties'],
        '吳': ['pre-qin', 'three-kingdoms', 'five-dynasties'],
        '蜀': ['three-kingdoms', 'five-dynasties'], '齊': ['pre-qin', 'nanbeichao'],
        '梁': ['nanbeichao', 'five-dynasties'], '陳': ['pre-qin', 'nanbeichao'],
        '燕': ['pre-qin', 'jin'], '涼': ['jin']}


def compatible(period, upper):
    if not upper:
        return True
    a, b = PERIOD_YEARS.get(period), PERIOD_YEARS.get(upper)
    if not a or not b:
        return True
    return a[0] <= b[1]


def main():
    bdir = sys.argv[1]
    apply_ = '--apply' in sys.argv

    inputs = {}
    for f in sorted(glob.glob(os.path.join(bdir, 'batch_*.json'))):
        if f.endswith('.result.json'):
            continue
        for e in json.load(open(f)):
            inputs[e['id']] = e
    results = {}
    for f in sorted(glob.glob(os.path.join(bdir, 'batch_*.result.json'))):
        for r in json.load(open(f)):
            results[r['id']] = r
    print(f'輸入 {len(inputs)}　結果 {len(results)}')

    picks, review = [], []
    from collections import Counter
    conf = Counter()
    for wid, r in results.items():
        src = inputs.get(wid)
        if not src:
            continue
        c = (r.get('confidence') or 'low').lower()
        got = r.get('period')
        conf[c] += 1
        if got not in ORD:
            got = None
        if c == 'high' and got:
            why = None
            if not compatible(got, src.get('upper')):
                why = f'與上限 {src.get("upper")} 相斥'
            elif src.get('cat') == 'AMB' and got not in READ.get(src.get('amb'), ORD):
                why = f'與撰人欄歧義字「{src.get("amb")}」諸讀法相牴'
            if why:
                review.append({**r, 'title': src.get('title'), '故': why,
                               'upper': src.get('upper'), 'cat': src.get('cat')})
            else:
                picks.append((wid, src, r, got))
        elif c == 'medium' and got:
            review.append({**r, 'title': src.get('title'), '故': 'medium 置信',
                           'upper': src.get('upper'), 'cat': src.get('cat')})

    print(f'置信分布：{dict(conf)}')
    print(f'可寫 {len(picks)}　待覈 {len(review)}')
    print(' 分代：', dict(Counter(g for *_, g in picks).most_common()))

    if not apply_:
        print('（dry-run，加 --apply 方寫入）')
        return

    IW = {}
    for s in '0123456789abcdef':
        IW[s] = json.load(open(f'index/works/{s}.json'))

    def shard(i):
        h = 0
        for ch in i:
            h = ((h * 31) + ord(ch)) & 0xFFFFFFFF
        return '%x' % (h % 16)

    applied = []
    n_missing = 0
    for wid, src, r, got in picks:
        hits = glob.glob(f'Work/{wid[0]}/{wid[1]}/{wid[2]}/{wid}-*.json')
        if not hits:
            n_missing += 1
            continue
        p = hits[0]
        d = json.load(open(p, encoding='utf-8'))
        if d.get('period'):
            continue
        basis = r.get('basis') or ''
        d['period'] = got
        d['period_basis'] = f'{basis}（2026-08-24 R3 引文定代）'
        d['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
        e = IW[shard(wid)].get(wid)
        if e is not None:
            e['period'] = got
        applied.append({'id': wid, 'title': d.get('title'), 'period': got,
                        'basis': d['period_basis']})
    for s, obj in IW.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    with open('.claude/known-issues/R3-引文定代-已寫入.json', 'w', encoding='utf-8') as f:
        json.dump({'_說明': 'R3 據志書引文（科第年號／朝代表述／師承）判讀而寫入之 period。'
                            '判語存 period_basis，逐條可驗。',
                   '條目': applied}, f, ensure_ascii=False, indent=2)
        f.write('\n')
    with open('.claude/known-issues/R3-引文定代-待覈.json', 'w', encoding='utf-8') as f:
        json.dump({'_說明': 'R3 引文判讀 medium 置信、或 high 而與上限／撰人欄相牴者。'
                            '未寫入 period，須逐條人工覈。',
                   '條目': review}, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'已寫入 {len(applied)}（檔不見 {n_missing}）；待覈 {len(review)} 條已出清單')


if __name__ == '__main__':
    main()
