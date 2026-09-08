#!/usr/bin/env python3
"""period 回填 Round 2（2026-08-24）：C1 三路判準泛化到全上限段。

C1（scripts/c1_period_from_entity.py，2026-08-22）只處理上限 ≤ liao-jin-yuan 者。
本輪同三路，擴到上限為 ming/qing 或**無上限**者（無上限則 A/C 路不覆驗、B 路不可走）：

  A 撰人朝代明確且無歧義 → DYNASTY_PERIOD
  B 撰人朝代歧義，而上限排除其晚解者（如「梁」而上限 nanbeichao → 必南朝梁——
    隋志注亡書批次上限本日收緊後新開出的口子）
  C 撰人無朝代，而其 Entity 有 period／dynasty → 傳播
    （C 路 Entity dynasty 歧義者，同 B 以上限消歧）

皆以 period_upper 年份區間覆驗；相斥者不寫，出清單。
role 為舊題撰／託名者不取其朝代。撰人卒年晚於所判 period 終年者不寫（跨代人物）。

用法：python3 scripts/period_backfill_round2_20260824.py [--apply]
"""
import json, glob, os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from period_bounds import DYNASTY_PERIOD, AMBIGUOUS, PERIOD_YEARS

BAD_ROLE = {'舊題撰', '託名', '舊題', '偽託'}
READ = {'宋': ['nanbeichao', 'song'], '魏': ['three-kingdoms', 'nanbeichao'],
        '周': ['pre-qin', 'nanbeichao', 'five-dynasties'],
        '吳': ['pre-qin', 'three-kingdoms', 'five-dynasties'],
        '蜀': ['three-kingdoms', 'five-dynasties'], '齊': ['pre-qin', 'nanbeichao'],
        '梁': ['nanbeichao', 'five-dynasties'], '陳': ['pre-qin', 'nanbeichao'],
        '燕': ['pre-qin', 'jin'], '涼': ['jin']}
TODAY = '2026-08-24'


def compatible(period, upper):
    if not upper:
        return True
    a, b = PERIOD_YEARS.get(period), PERIOD_YEARS.get(upper)
    if not a or not b:
        return True
    return a[0] <= b[1]


def main():
    apply_ = '--apply' in sys.argv
    IE = {}
    for s in '0123456789abcdef':
        IE.update(json.load(open(f'index/entities/{s}.json')))

    picks, conflicts = [], []
    for p in glob.glob('Work/*/*/*/*.json'):
        d = json.load(open(p, encoding='utf-8'))
        if d.get('_promoted_to') or d.get('promoted_to'):
            continue
        if d.get('period'):
            continue
        ub = d.get('period_upper')
        auth = [a for a in (d.get('authors') or [])
                if isinstance(a, dict) and a.get('role') not in BAD_ROLE]
        if not auth:
            continue
        dys = {a['dynasty'] for a in auth if a.get('dynasty')}
        got = basis = None

        if dys and not (dys & AMBIGUOUS) and all(x in DYNASTY_PERIOD for x in dys):
            ps = {DYNASTY_PERIOD[x] for x in dys}
            if len(ps) == 1:
                got = ps.pop()
                basis = (f'據撰人朝代「{"／".join(sorted(dys))}」'
                         + (f'；上限 {ub} 覆驗不相斥' if ub else '')
                         + f'（{TODAY} R2）')
        elif len(dys) == 1 and (dys & set(READ)) and ub:
            w = dys.copy().pop()
            ok = [r for r in READ[w] if compatible(r, ub)]
            if len(ok) == 1:
                got = ok[0]
                basis = (f'撰人朝代「{w}」有歧義，而上限 {ub} 排除其晚解，'
                         f'故必 {got}（{TODAY} R2）')
        elif not dys:
            eids = [a['entity_id'] for a in auth if a.get('entity_id')]
            pes = {IE[e].get('period') for e in eids if e in IE and IE[e].get('period')}
            eds = {IE[e].get('dynasty') for e in eids if e in IE and IE[e].get('dynasty')}
            nm = '／'.join(sorted({IE[e].get('primary_name', '?') for e in eids if e in IE}))
            if len(pes) == 1:
                got = pes.pop()
                basis = (f'撰人朝代闕，據其 Entity「{nm}」之 period 傳播'
                         + (f'；上限 {ub} 覆驗不相斥' if ub else '')
                         + f'（{TODAY} R2）')
            elif len(eds) == 1:
                dd = eds.copy().pop()
                if dd in DYNASTY_PERIOD:
                    got = DYNASTY_PERIOD[dd]
                    basis = (f'撰人朝代闕，據其 Entity「{nm}」之 dynasty「{dd}」傳播'
                             + (f'；上限 {ub} 覆驗不相斥' if ub else '')
                             + f'（{TODAY} R2）')
                elif dd in READ and ub:
                    ok = [r for r in READ[dd] if compatible(r, ub)]
                    if len(ok) == 1:
                        got = ok[0]
                        basis = (f'撰人朝代闕，其 Entity「{nm}」之 dynasty「{dd}」有歧義，'
                                 f'而上限 {ub} 排除其晚解，故必 {got}（{TODAY} R2）')
        if not got:
            continue
        if got == 'modern':
            # 近現代之判交近代軸，不在本輪
            continue
        if not compatible(got, ub):
            conflicts.append({'id': d['id'], 'title': d.get('title'), '故': '與上限相斥',
                              '擬定': got, 'period_upper': ub, 'path': p})
            continue
        eids2 = [a['entity_id'] for a in auth if a.get('entity_id')]
        dys2 = [IE[e].get('death_year') for e in eids2
                if e in IE and IE[e].get('death_year')]
        rng = PERIOD_YEARS.get(got)
        if dys2 and rng and max(dys2) > rng[1]:
            conflicts.append({'id': d['id'], 'title': d.get('title'), '故': '撰人跨代',
                              '擬定': got, 'period_upper': ub, '撰人卒年': max(dys2),
                              'path': p})
            continue
        picks.append((p, d, got, basis))

    print(f'可定 {len(picks)}　相斥/跨代而不寫 {len(conflicts)}')
    from collections import Counter
    print(' 分代：', dict(Counter(g for _, _, g, _ in picks).most_common()))
    print(' 相斥樣本：', conflicts[:5])

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

    for p, d, got, basis in picks:
        d['period'] = got
        d['period_basis'] = basis
        d['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
        e = IW[shard(d['id'])].get(d['id'])
        if e is not None:
            e['period'] = got
    for s, obj in IW.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    with open('.claude/known-issues/R2-period回填相斥-20260824.json', 'w',
              encoding='utf-8') as f:
        json.dump({'_說明': 'R2 依撰人／Entity 推得之 period 與 period_upper 相斥'
                            '或撰人跨代者。非可逕改——或 entity_id 繫錯人，或其朝代'
                            '本身有誤，須逐條查。不寫入 period。',
                   '條目': conflicts}, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('已寫入')


if __name__ == '__main__':
    main()
