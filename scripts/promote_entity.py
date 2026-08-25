#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""entity 之升格（draft → production）。

**升格不可逆**：一條記錄升格即成墓碑，此後不得再 curate
（見 .claude/plans/升格並行方案.md〈一〉）。故本檔預設只驗不寫，
非加 --apply 不動一字。

與 Work 之升格同其契約，惟三事為 entity 所獨有：

  一、**works[] 之改繫**。entity.works[] 所指多是 draft 之 work id；
      其 work 若已升格，production 側之 entity 當指 production id。
      故拷貝入 production 之時，逐條以 promotions.json 改之。
  二、**authors[].entity_id 之改繫**。兩倉之 work 皆以此欄繫人，
      升格之後須全庫改 D→P，draft 與 production 並改。
  三、**孤懸者不升**。works 為空之 entity，production 無一物繫之，
      升之徒增死條；留在 draft，俟其有繫。

用法：
    python3 scripts/promote_entity.py --gate                 # 只跑閘，報可升之數
    python3 scripts/promote_entity.py --list [--period qing] # 列可升者
    python3 scripts/promote_entity.py --apply --limit 50 [--period qing] [--ids a,b]
"""
import json, os, sys, glob, time, shutil, argparse, collections

DIG = '0123456789abcdefghijklmnopqrstuvwxyz'
SH_ST, SH_TY, SH_TS, SH_M = 62, 59, 19, 8
T_ENTITY, ST_OFFICIAL, ST_DRAFT = 4, 0, 1
PROD = next((r for r in ('../book-index', '/home/user/book-index')
             if os.path.isdir(os.path.join(r, 'Work'))), None)


def b36(n):
    s = ''
    while n:
        s = DIG[n % 36] + s; n //= 36
    return s or '0'


def parse_id(s):
    v = int(s, 36)
    return ((v >> SH_ST) & 1, (v >> SH_TY) & 7)


def shard(i):
    h = 0
    for c in i: h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return '%x' % (h % 16)


def load_idx(root, kind):
    out = {}
    for s in DIG[:16]:
        fp = os.path.join(root, f'index/{kind}/{s}.json')
        if os.path.exists(fp): out.update(json.load(open(fp)))
    return out


def save_shards(root, kind, data):
    buck = collections.defaultdict(dict)
    for k, v in data.items(): buck[shard(k)][k] = v
    for s in DIG[:16]:
        fp = os.path.join(root, f'index/{kind}/{s}.json')
        o = buck.get(s, {})
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump({k: o[k] for k in sorted(o)}, f, ensure_ascii=False, indent=2)
            f.write('\n')


def jwrite(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2); f.write('\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--gate', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--period', default=None)
    ap.add_argument('--ids', default=None)
    a = ap.parse_args()
    if not PROD:
        print('production 庫未掛（須 ../book-index 或 /home/user/book-index）'); return 2

    # ── 全域閘：chk_entity 甲級須為零 ──
    import subprocess
    r = subprocess.run([sys.executable, '.claude/skills/hanzhi-curation/scripts/chk_entity.py'],
                       capture_output=True, text=True)
    ga = [l for l in r.stdout.splitlines() if l.startswith('【甲】')]
    if ga and not ga[0].endswith('　0 條'):
        print('閘不過：chk_entity 甲級非零——' + ga[0]); 
        print('升格不可逆，甲級未清不得升。'); return 1
    print('閘一：chk_entity 甲級為零 ✓')

    PRm = json.load(open('promotions.json'))
    promo = PRm['promotions']
    d2p = {k: v['production_id'] for k, v in promo.items()}
    IEd = load_idx('.', 'entities')
    IEp = load_idx(PROD, 'entities')
    IWd = load_idx('.', 'works')
    PWids = set()
    for p in glob.glob(os.path.join(PROD, 'Work/*/*/*/*.json')):
        try: PWids.add(json.load(open(p))['id'])
        except Exception: pass

    ents = {}; paths = {}
    for p in glob.glob('Entity/*/*/*/*.json'):
        d = json.load(open(p))
        if isinstance(d, dict) and d.get('id'): ents[d['id']] = d; paths[d['id']] = p
    byname = collections.defaultdict(list)
    for i, d in ents.items():
        if d.get('primary_name'): byname[d['primary_name']].append(i)

    # ── 逐條之閘 ──
    ok = []; rej = collections.Counter()
    for i, d in ents.items():
        if d.get('_promoted_to') or i in promo: rej['已升格'] += 1; continue
        st, ty = parse_id(i)
        if st != ST_DRAFT or ty != T_ENTITY: rej['id 之位非 draft/entity'] += 1; continue
        ws = [w for w in (d.get('works') or []) if isinstance(w, dict) and w.get('work_id')]
        if not ws: rej['孤懸（works 空）——升之無所繫，留 draft'] += 1; continue
        dead = [w['work_id'] for w in ws
                if w['work_id'] not in IWd and w['work_id'] not in PWids
                and w['work_id'] not in set(d2p.values())]
        if dead: rej['works 有懸空'] += 1; continue
        nm = d.get('primary_name')
        if not nm: rej['無 primary_name'] += 1; continue
        # 同名組須整組同時定案（比照 work 之規矩）
        if len(byname[nm]) > 1: rej['在同名組中——須整組同時定案'] += 1; continue
        if a.period and d.get('period') != a.period: rej['非本批之代'] += 1; continue
        ok.append(i)

    if a.ids:
        want = set(a.ids.split(','))
        ok = [i for i in ok if i in want]
    ok.sort()
    if a.limit: ok = ok[:a.limit]

    print(f'閘二：逐條之閘——可升 {len(ok)}')
    for k, v in rej.most_common(): print(f'   不可升 {v:6d}  {k}')
    if a.list:
        for i in ok[:60]:
            d = ents[i]
            print(f'   {i} {d.get("primary_name")}　代={d.get("period")}　works={len(d.get("works") or [])}')
        if len(ok) > 60: print(f'   …餘 {len(ok)-60}')
    if a.gate or not a.apply:
        print('\n（只驗未寫；加 --apply 方升）'); return 0

    # ── 升 ──
    used = set(IEd) | set(IEp) | set(d2p.values()) | set(promo)
    seq = 0; base_ts = int(time.time())
    def mint():
        nonlocal seq
        while True:
            v = (ST_OFFICIAL << SH_ST) | (T_ENTITY << SH_TY) | \
                ((base_ts & ((1 << 40) - 1)) << SH_TS) | ((1 & 0x7ff) << SH_M) | (seq & 0xff)
            seq += 1
            if seq > 255:
                seq = 0
                globals()['__t'] = None
            s = b36(v)
            if s not in used: used.add(s); return s

    mapping = {}; done = []
    for i in ok:
        d = ents[i]; P = mint()
        prod = json.loads(json.dumps(d))
        prod['id'] = P
        prod.pop('_promoted_to', None); prod.pop('_promoted_at', None)
        # works[]：draft work id → production id（已升格者）
        for w in (prod.get('works') or []):
            if isinstance(w, dict) and w.get('work_id') in d2p:
                w['work_id'] = d2p[w['work_id']]
        nm = prod.get('primary_name')
        # 2026-08-25 分片改制：目錄取 id 之**末**三字（舊制取首三字）
        ppath = os.path.join(PROD, f'Entity/{P[-3]}/{P[-2]}/{P[-1]}/{P}-{nm}.json')
        jwrite(ppath, prod)
        IEp[P] = {'id': P, 'type': 'entity', 'subtype': prod.get('subtype'),
                  'primary_name': nm, 'path': os.path.relpath(ppath, PROD)}
        for k in ('dynasty', 'period'):
            if prod.get(k): IEp[P][k] = prod[k]
        if (prod.get('external_ids') or {}).get('cbdb_id') is not None:
            IEp[P]['cbdb_id'] = prod['external_ids']['cbdb_id']
        # draft 墓碑
        at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        tomb = {'schema_version': d.get('schema_version', 1), 'id': i, 'type': 'entity',
                'primary_name': nm, '_promoted_to': P, '_promoted_at': at}
        jwrite(paths[i], tomb)
        # 墓碑之索引條比照 work 之例：只留 id／名／type／path＋promoted_to，
        # 不帶 subtype／dynasty／period——墓碑本身已無此三欄，帶之則索引與記錄檔不符。
        if i in IEd:
            IEd[i] = {'id': i, 'type': 'entity', 'primary_name': nm,
                      'path': paths[i], 'promoted_to': P}
        promo[i] = {'production_id': P, 'type': 'entity', 'promoted_at': at}
        mapping[i] = P; done.append((i, P, nm))

    # ── 改引用：兩倉之 authors[].entity_id ──
    nref = 0
    for root in ('.', PROD):
        for p in glob.glob(os.path.join(root, 'Work/*/*/*/*.json')):
            try: d = json.load(open(p))
            except Exception: continue
            if not isinstance(d, dict): continue
            ch = False
            for au in (d.get('authors') or []):
                if isinstance(au, dict) and au.get('entity_id') in mapping:
                    au['entity_id'] = mapping[au['entity_id']]; ch = True; nref += 1
            if ch: jwrite(p, d)

    save_shards('.', 'entities', IEd)
    save_shards(PROD, 'entities', IEp)
    with open('promotions.json', 'w', encoding='utf-8') as f:
        json.dump({'version': PRm.get('version', 1),
                   'promotions': {k: promo[k] for k in sorted(promo)}},
                  f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'\n升格 {len(done)} 人；改 authors[].entity_id {nref} 處（兩倉）')
    for i, P, nm in done[:10]: print(f'   {i} → {P}　{nm}')
    if len(done) > 10: print(f'   …餘 {len(done)-10}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
