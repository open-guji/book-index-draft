#!/usr/bin/env python3
"""C1：為「無 period 而上限 ≤元」者補 period。

只走 SCHEMA〈period〉所許之三判準，**不以 period_upper 充當 period**
（SCHEMA：「首次著錄之志不可當下限用……此點須守死」）。

三路：
  A 撰人朝代明確且無歧義 → DYNASTY_PERIOD
  B 撰人朝代歧義，而上限排除其晚解者（如「宋」而上限 sui-tang → 必劉宋）
  C 撰人無朝代，而其 Entity 有 period／dynasty → 傳播

三路皆以 period_upper 覆驗：所定之值起年不得晚於上限之終年。相斥者不寫，出清單。
role 為舊題撰／託名者不取其朝代（SCHEMA：舊題撰人 ≠ 實際撰人）。

用法：python3 scripts/c1_period_from_entity.py [--apply]
"""
import json, glob, os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from period_bounds import DYNASTY_PERIOD, AMBIGUOUS, PERIOD_YEARS

PRE = ['pre-qin','qin-han','three-kingdoms','jin','nanbeichao','sui-tang',
       'five-dynasties','song','liao-jin-yuan']
BAD_ROLE = {'舊題撰','託名','舊題','偽託'}
READ = {'宋':['nanbeichao','song'],'魏':['three-kingdoms','nanbeichao'],
        '周':['pre-qin','nanbeichao','five-dynasties'],
        '吳':['pre-qin','three-kingdoms','five-dynasties'],
        '蜀':['three-kingdoms','five-dynasties'],'齊':['pre-qin','nanbeichao'],
        '梁':['nanbeichao','five-dynasties'],'陳':['pre-qin','nanbeichao'],
        '燕':['pre-qin','jin'],'涼':['jin']}
TODAY = '2026-08-22'


def compatible(period, upper):
    """所定之值不得晚於上限——比年份區間，不比 ORD 之序（song×liao-jin-yuan 全重疊）。"""
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
        if d.get('period') or d.get('period_upper') not in PRE:
            continue
        ub = d['period_upper']
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
                basis = f'據撰人朝代「{"／".join(sorted(dys))}」；上限 {ub} 覆驗不相斥（{TODAY} C1）'
        elif len(dys) == 1 and (dys & set(READ)):
            w = dys.copy().pop()
            ok = [r for r in READ[w] if compatible(r, ub)]
            if len(ok) == 1:
                got = ok[0]
                basis = (f'撰人朝代「{w}」有歧義，而上限 {ub} 排除其晚解，'
                         f'故必 {got}（{TODAY} C1）')
        elif not dys:
            eids = [a['entity_id'] for a in auth if a.get('entity_id')]
            pes = {IE[e].get('period') for e in eids if e in IE and IE[e].get('period')}
            eds = {IE[e].get('dynasty') for e in eids if e in IE and IE[e].get('dynasty')}
            nm = '／'.join(sorted({IE[e].get('primary_name','?') for e in eids if e in IE}))
            if len(pes) == 1:
                got = pes.pop()
                basis = (f'撰人朝代闕，據其 Entity「{nm}」之 period 傳播；'
                         f'上限 {ub} 覆驗不相斥（{TODAY} C1）')
            elif len(eds) == 1 and eds.copy().pop() in DYNASTY_PERIOD:
                dd = eds.pop()
                got = DYNASTY_PERIOD[dd]
                basis = (f'撰人朝代闕，據其 Entity「{nm}」之 dynasty「{dd}」傳播；'
                         f'上限 {ub} 覆驗不相斥（{TODAY} C1）')
        if not got:
            continue
        if not compatible(got, ub):
            conflicts.append({'id': d['id'], 'title': d.get('title'), '故': '與上限相斥',
                              '擬定': got, 'period_upper': ub, 'path': p})
            continue
        # 跨代人物：撰人卒年晚於所判 period 之終年者，其書未必成於該代
        # （《隋開皇歷》李德林歷北齊入隋、《漢隱帝實錄》張昭實五代人）。不寫，出清單。
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

    print(f'可定 {len(picks)}　與上限相斥而不寫 {len(conflicts)}')
    from collections import Counter
    print(' 分代：', dict(Counter(g for _, _, g, _ in picks).most_common()))

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
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write('\n')
        e = IW[shard(d['id'])].get(d['id'])
        if e is not None:
            e['period'] = got
    for s, obj in IW.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write('\n')
    with open('.claude/known-issues/C1-entity期與上限相斥.json', 'w', encoding='utf-8') as f:
        json.dump({'_說明': 'C1 依撰人／Entity 推得之 period 與 period_upper 相斥者。'
                            '非可逕改——或 entity_id 繫錯人，或該 Entity 之朝代本身有誤，'
                            '須逐條查。不寫入 period。',
                   '條目': conflicts}, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('已寫入')


if __name__ == '__main__':
    main()
