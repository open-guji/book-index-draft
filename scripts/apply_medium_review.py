#!/usr/bin/env python3
"""A1：medium 置信條之複審結果落庫（2026-08-24）。

R3 引文定代留下 618 條 medium（未寫庫）。複審逐條裁「採」或「棄」，
判準見會話 scratchpad medium_review/REVIEW_SPEC.md，其要：
跨代人物取仕宦主要期、志書組內推位有錨點、知名人物身份明確者可採；
僅版本年、僅書目著錄、兩說並存、同名異人未辨、推斷逾兩跳者棄。

只寫 adopt=true 者，落庫前再以 period_upper 年份區間覆驗。

用法：python3 scripts/apply_medium_review.py <results_dir> [--prefix P] [--apply]
      --prefix 批次檔名前綴，預設 mrev（第二輪之批用 m2）
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
    pref = 'mrev'
    if '--prefix' in sys.argv:
        pref = sys.argv[sys.argv.index('--prefix') + 1]

    src = {}
    for f in sorted(glob.glob(os.path.join(rdir, f'{pref}_*.json'))):
        if f.endswith('.result.json'):
            continue
        for e in json.load(open(f)):
            src[e['id']] = e
    dec = {}
    for f in sorted(glob.glob(os.path.join(rdir, f'{pref}_*.result.json'))):
        for r in json.load(open(f)):
            dec[r['id']] = r
    print(f'原 medium {len(src)}　複審結果 {len(dec)}')

    picks, dropped = [], []
    for wid, r in dec.items():
        if not r.get('adopt'):
            dropped.append({'id': wid, 'title': (src.get(wid) or {}).get('title'),
                            'reason': r.get('reason')})
            continue
        per = r.get('period')
        if per not in ORD or per == 'modern' and False:
            dropped.append({'id': wid, '故': f'period 不合法：{per}'})
            continue
        hits = glob.glob(f'Work/{wid[0]}/{wid[1]}/{wid[2]}/{wid}-*.json')
        if not hits:
            dropped.append({'id': wid, '故': '檔不見'})
            continue
        d = json.load(open(hits[0], encoding='utf-8'))
        if d.get('period') or d.get('_promoted_to'):
            continue
        if not compatible(per, d.get('period_upper')):
            dropped.append({'id': wid, 'title': d.get('title'),
                            '故': f'與上限 {d.get("period_upper")} 相斥', '擬定': per})
            continue
        picks.append((hits[0], d, r))

    print(f'採 {len(picks)}　棄 {len(dropped)}')
    print(' 分代：', dict(collections.Counter(r['period'] for _, _, r in picks).most_common()))
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

    for p, d, r in picks:
        o = src.get(d['id']) or {}
        d['period'] = r['period']
        d['period_basis'] = (f'{o.get("basis") or ""}'
                             f'　複審採納：{r.get("reason") or ""}'
                             f'（2026-08-24 {"A1" if pref == "mrev" else "B1"} medium 複審）')
        d['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
        e = IW[shard(d['id'])].get(d['id'])
        if e is not None:
            e['period'] = r['period']
    for s, obj in IW.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    tag = 'A1' if pref == 'mrev' else 'B1'
    with open(f'.claude/known-issues/{tag}-medium複審棄置.json', 'w', encoding='utf-8') as f:
        json.dump({'_說明': 'A1 複審裁定不採者。棄因多為：僅版本年（版本之年只證上限）、'
                            '僅書目著錄、兩說並存、注本與本文層次不分（斷代之的不明）、'
                            '師承單跳推代、明清或清民之際主要期難定、同名異人未辨。',
                   '條目': dropped}, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'已寫入 {len(picks)}')


if __name__ == '__main__':
    main()
