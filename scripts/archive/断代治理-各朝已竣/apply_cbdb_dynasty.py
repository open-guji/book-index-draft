#!/usr/bin/env python3
"""據 CBDB API 之查詢結果補 Entity 朝代，並級聯定 Work 之 period。

輸入 cbdb_api_lookup.py 所落之 cache（名 → CBDB 人物列表）。

**只取無歧義者**，三重門：
  1. 該名在 CBDB 只有一人，或雖多人而朝代唯一（同名同代者不害）；
  2. 其朝代可映射入本庫 period 軸（DYNASTY_PERIOD／CBDB_DY）；
  3. 所得之 period 與該 Work 之 period_upper 年份區間不相斥。

同名而朝代不一者一概不用——同名異人是本庫既有之患（見 D2-人名相符而實二事），
CBDB 之名亦不能自證其為同一人。此類出清單待人審。

用法：python3 scripts/apply_cbdb_dynasty.py <cache.json> [--apply]
"""
import json, glob, os, re, sys, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from period_bounds import DYNASTY_PERIOD, PERIOD_YEARS

# CBDB 朝代名 → 本庫 period（CBDB 之名與本庫寫法不盡同）
CBDB_PERIOD = {
    '周': 'pre-qin', '春秋': 'pre-qin', '戰國': 'pre-qin', '秦': 'qin-han',
    '秦漢': 'qin-han', '漢': 'qin-han', '西漢': 'qin-han', '東漢': 'qin-han',
    '三國': 'three-kingdoms', '魏': 'three-kingdoms', '蜀漢': 'three-kingdoms',
    '吳': 'three-kingdoms',
    '晉': 'jin', '西晉': 'jin', '東晉': 'jin', '十六國': 'jin',
    '南北朝': 'nanbeichao', '宋（南朝）': 'nanbeichao', '齊': 'nanbeichao',
    '梁': 'nanbeichao', '陳': 'nanbeichao', '北魏': 'nanbeichao',
    '北齊': 'nanbeichao', '北周': 'nanbeichao',
    '隋': 'sui-tang', '唐': 'sui-tang',
    '五代十國': 'five-dynasties', '五代': 'five-dynasties',
    '宋': 'song', '北宋': 'song', '南宋': 'song',
    '遼': 'liao-jin-yuan', '金': 'liao-jin-yuan', '元': 'liao-jin-yuan',
    '明': 'ming', '清': 'qing',
    '民國': 'modern', '中華民國': 'modern',
}
SKIP = {'未詳', '', None}


def compatible(period, upper):
    if not upper:
        return True
    a, b = PERIOD_YEARS.get(period), PERIOD_YEARS.get(upper)
    if not a or not b:
        return True
    return a[0] <= b[1]


def resolve(entries):
    """一名之 CBDB 諸人 → (period, 判語) 或 None。"""
    dys = {e.get('dynasty') for e in entries if e.get('dynasty') not in SKIP}
    if not dys:
        return None
    ps = set()
    for d in dys:
        p = CBDB_PERIOD.get(d) or DYNASTY_PERIOD.get(d)
        if not p:
            return None            # 有不可映射之朝代，不冒進
        ps.add(p)
    if len(ps) != 1:
        return None                # 同名而異代——不用
    p = ps.pop()
    n = len(entries)
    who = '、'.join(sorted({e.get('dynasty') for e in entries
                            if e.get('dynasty') not in SKIP}))
    return p, (f'CBDB 作「{who}」（該名 CBDB 有 {n} 人，朝代唯一）' if n > 1
               else f'CBDB 作「{who}」')


def main():
    cache = json.load(open(sys.argv[1]))
    apply_ = '--apply' in sys.argv

    IE = {}
    for s in '0123456789abcdef':
        IE.update(json.load(open(f'index/entities/{s}.json')))

    picks, amb, conflict = [], [], []
    for p in glob.glob('Work/*/*/*/*.json'):
        if not re.match(r'^1[a-z0-9]{12}-', os.path.basename(p)):
            continue
        d = json.load(open(p, encoding='utf-8'))
        if d.get('type') != 'work' or d.get('_promoted_to') or d.get('period'):
            continue
        auth = [a for a in (d.get('authors') or [])
                if isinstance(a, dict) and a.get('role') not in
                {'舊題撰', '託名', '舊題', '偽託'}]
        if not auth or any(a.get('dynasty') for a in auth):
            continue
        # 撰人之名：本欄之名，或其 entity 之名
        names = set()
        for a in auth:
            if a.get('name'):
                names.add(a['name'])
            eid = a.get('entity_id')
            if eid and eid in IE:
                nm = IE[eid].get('primary_name') or IE[eid].get('name')
                if nm:
                    names.add(nm)
        got = set()
        whys = []
        unresolved = False
        for n in names:
            ent = cache.get(n)
            if not ent:
                continue
            r = resolve(ent)
            if r is None:
                unresolved = True
                continue
            got.add(r[0])
            whys.append(f'{n}：{r[1]}')
        if not got:
            if unresolved:
                amb.append({'id': d['id'], 'title': d.get('title'),
                            'names': sorted(names), '故': 'CBDB 同名異代或朝代不可映射'})
            continue
        if len(got) > 1:
            amb.append({'id': d['id'], 'title': d.get('title'),
                        'names': sorted(names), '故': '諸撰人之代不一', '諸解': sorted(got)})
            continue
        per = got.pop()
        ub = d.get('period_upper')
        if not compatible(per, ub):
            conflict.append({'id': d['id'], 'title': d.get('title'), '擬定': per,
                             'period_upper': ub, '判語': '；'.join(whys)})
            continue
        picks.append((p, d, per, '；'.join(whys)))

    print(f'可定 {len(picks)}　同名異代/不可映射 {len(amb)}　與上限相斥 {len(conflict)}')
    print(' 分代：', dict(collections.Counter(x[2] for x in picks).most_common()))
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

    for p, d, per, why in picks:
        d['period'] = per
        d['period_basis'] = (f'撰人朝代闕，據 CBDB 補——{why}'
                             + (f'；上限 {d["period_upper"]} 覆驗不相斥'
                                if d.get('period_upper') else '')
                             + '（2026-08-24 A2 CBDB API）')
        d['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
        e = IW[shard(d['id'])].get(d['id'])
        if e is not None:
            e['period'] = per
    for s, obj in IW.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    with open('.claude/known-issues/A2-CBDB定代未採.json', 'w', encoding='utf-8') as f:
        json.dump({'_說明': 'A2 走 CBDB API 定代時不採者。同名異代一類須人辨'
                            '（CBDB 之名不能自證其為同一人）；相斥一類或 entity 繫錯人。',
                   '同名異代或不可映射': amb, '與上限相斥': conflict},
                  f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'已寫入 {len(picks)}')


if __name__ == '__main__':
    main()
