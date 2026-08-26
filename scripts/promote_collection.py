#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collection 之升格（draft → production）。

**升格不可逆**：一條記錄升格即成墓碑，此後不得再 curate。故本檔預設只驗不寫，
非加 --apply 不動一字。方案與其推導見 `.claude/plans/Collection升格方案.md`。

與 Work／Entity 之升格同其大體，惟四事為 Collection 所獨有：

  一、**入向改繫有七種欄形**（entity 只 `authors[].entity_id` 一種）：
        Book／Work  `contained_in[].id`
        Work        `related_works[].id`（relation 多作 collected_in）
        Work        `collections[]`
        Collection  `contained_in[]`（字串陣列）
        Collection  `related_collections[].collection_id`
        Collection  `contains[].collection_id`
        整理本      `sections[].collection_id`
      漏一種即一批靜默積欠——entity 那一輪的教訓（見 SKILL〈併條工具只掃 draft〉）。

  二、**先鑄全部號，再寫檔**。`contained_in` 所指是同批之兄弟（出土簡帛 ⊃ 十三家、
      武英殿刻書 ⊃ 三家…），邊鑄邊寫則先寫者改不到後鑄之號。
      `promote_entity.py` 邊鑄邊寫無妨，是因 entity 之間本不相引。

  三、**`contained_in` 是單向的**：兩倉 Book 反指 Collection 三萬八千餘處，
      而 Collection 之 `books` 止四百餘（大叢編不逐一列其書）。
      改繫只改指標，**不補那一側**——此與人物↔作品之雙向正相反。

  四、**索引不分片**（`index/collections.json` 單檔），且 production 之條帶
      展示欄（author／year／holder／role／subtype／edition／juan_count／
      additional_titles／has_text／has_image），須自記錄檔重算。
      記錄檔用 `_has_text`／`_has_image`（帶底線），索引用不帶底線的。

用法：
    python3 scripts/promote_collection.py                       # 只驗
    python3 scripts/promote_collection.py --list
    python3 scripts/promote_collection.py --apply [--ids a,b] [--exclude c,d]
"""
import json, os, sys, glob, time, argparse, collections, subprocess

DIG = '0123456789abcdefghijklmnopqrstuvwxyz'
SH_ST, SH_TY, SH_TS, SH_M = 62, 59, 19, 8
T_COLLECTION, ST_OFFICIAL, ST_DRAFT = 2, 0, 1
PROD = next((r for r in ('../book-index', '/home/user/book-index')
             if os.path.isdir(os.path.join(r, 'Work'))), None)
IDXF = 'index/collections.json'


def b36(n):
    s = ''
    while n:
        s = DIG[n % 36] + s; n //= 36
    return s or '0'


def u36(s):
    n = 0
    for c in s:
        if c not in DIG: return None
        n = n * 36 + DIG.index(c)
    return n


def parse_id(s):
    v = u36(s)
    if v is None: return None, None
    return (v >> SH_ST) & 1, (v >> SH_TY) & 7


def jwrite(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2); f.write('\n')


def load(root, t):
    """回傳 {id: (記錄, 路徑)}。"""
    out = {}
    for p in glob.glob(f'{root}/{t}/*/*/*/*.json'):
        try: d = json.load(open(p))
        except Exception: continue
        if isinstance(d, dict) and d.get('id'): out[d['id']] = (d, p)
    return out


def idx_entry(d, path):
    """production 索引之條——展示欄自記錄檔重算。"""
    e = {'id': d['id'], 'title': d.get('title'), 'type': 'Collection', 'path': path}
    au = (d.get('authors') or [{}])[0]
    if au.get('name'): e['author'] = au['name']
    if (d.get('publication_info') or {}).get('year'): e['year'] = d['publication_info']['year']
    if au.get('role'): e['role'] = au['role']
    if au.get('dynasty'): e['dynasty'] = au['dynasty']
    if (d.get('current_location') or {}).get('name'): e['holder'] = d['current_location']['name']
    if d.get('additional_titles'): e['additional_titles'] = d['additional_titles']
    if d.get('edition'): e['edition'] = d['edition']
    if (d.get('juan_count') or {}).get('number'): e['juan_count'] = d['juan_count']['number']
    if d.get('work_id'): e['work_id'] = d['work_id']
    if d.get('_has_text'): e['has_text'] = True
    if d.get('_has_image'): e['has_image'] = True
    if d.get('subtype'): e['subtype'] = d['subtype']
    return e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--ids'); ap.add_argument('--exclude')
    a = ap.parse_args()
    if not PROD:
        print('未見 production 庫（../book-index）——升格須兩倉俱在。'); return 2

    # ── 閘一：chk_collection 甲級為零 ──
    chk = '.claude/skills/hanzhi-curation/scripts/chk_collection.py'
    r = subprocess.run([sys.executable, chk], capture_output=True, text=True)
    ln = [x for x in r.stdout.split('\n') if x.startswith('【甲】')]
    if not ln or not ln[0].rstrip().endswith('0 條'):
        print('閘一：chk_collection 甲級不為零，不得升格：'); print('  ' + (ln[0] if ln else r.stdout[-400:]))
        return 1
    print('閘一：chk_collection 甲級為零 ✓')

    PRm = json.load(open('promotions.json'))
    promo = PRm['promotions']
    d2p = {k: v['production_id'] for k, v in promo.items()}
    dc = load('.', 'Collection'); pc = load(PROD, 'Collection')
    IXd = json.load(open(IDXF))
    IXp = json.load(open(os.path.join(PROD, IDXF)))
    pwl = set(load(PROD, 'Work')); pbl = set(load(PROD, 'Book'))
    dwl = {i for i, (d, _) in load('.', 'Work').items() if not d.get('_promoted_to')}
    dbl = {i for i, (d, _) in load('.', 'Book').items() if not d.get('_promoted_to')}

    # ── 閘二：逐條 ──
    ok = []; rej = collections.Counter()
    allc = set(dc) | set(pc)
    for i, (d, p) in dc.items():
        if d.get('_promoted_to') or i in promo: rej['已升格'] += 1; continue
        st, ty = parse_id(i)
        if st != ST_DRAFT or ty != T_COLLECTION: rej['id 之位非 draft/collection'] += 1; continue
        if not d.get('title'): rej['無 title'] += 1; continue
        if not d.get('subtype'): rej['無 subtype'] += 1; continue
        dead = []
        for w in (d.get('contained_works') or []):
            if isinstance(w, dict) and w.get('id') not in pwl and w['id'] not in dwl: dead.append(w['id'])
        for b in (d.get('books') or []):
            bi = b.get('id') if isinstance(b, dict) else b
            if bi not in pbl and bi not in dbl: dead.append(bi)
        for x in (d.get('contained_in') or []):
            xi = x if isinstance(x, str) else (x or {}).get('id')
            if xi not in allc: dead.append(xi)
        for c in (d.get('related_collections') or []):
            ci = c.get('collection_id') if isinstance(c, dict) else c
            if ci and ci not in allc: dead.append(ci)
        if d.get('work_id') and d['work_id'] not in pwl and d['work_id'] not in dwl: dead.append(d['work_id'])
        if dead: rej['成員或巢狀有懸空'] += 1; continue
        ok.append(i)
    if a.ids: ok = [i for i in ok if i in set(a.ids.split(','))]
    if a.exclude: ok = [i for i in ok if i not in set(a.exclude.split(','))]
    ok.sort()
    print(f'閘二：逐條之閘——可升 {len(ok)}')
    for k, v in rej.most_common(): print(f'   不可升 {v:6d}  {k}')
    if a.list:
        for i in ok:
            d = dc[i][0]
            print(f'   {i} {d.get("title")}　{d.get("subtype")}　'
                  f'works={len(d.get("contained_works") or [])} books={len(d.get("books") or [])}')
    if not a.apply:
        print('\n（只驗未寫；加 --apply 方升）'); return 0

    # ── 先鑄全部號（本型獨有，見篇首〈二〉）──
    used = set(IXd) | set(IXp) | set(d2p.values()) | set(promo) | set(pc)
    base_ts = int(time.time()); n = 0
    D2P = {}
    for i in ok:
        while True:
            seq = n & 0xff; mac = 1 + ((n >> 8) % 2047); ts = base_ts + (n >> 8) // 2047
            n += 1
            v = (ST_OFFICIAL << SH_ST) | (T_COLLECTION << SH_TY) | \
                ((ts & ((1 << 40) - 1)) << SH_TS) | ((mac & 0x7ff) << SH_M) | seq
            s = b36(v)
            if s not in used: used.add(s); D2P[i] = s; break

    at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    done = []
    for i in ok:
        d, p = dc[i]; P = D2P[i]
        prod = json.loads(json.dumps(d))
        prod['id'] = P
        prod.pop('_promoted_to', None); prod.pop('_promoted_at', None)
        # 出向：成員過 promotions（work／book 之 D→P），巢狀過本批之表
        for w in (prod.get('contained_works') or []):
            if isinstance(w, dict) and w.get('id') in d2p: w['id'] = d2p[w['id']]
        if prod.get('books'):
            # books[] 之元素或為 Book id 字串，或為 {id, volume_index, …} 之物件，兩式並存
            prod['books'] = [dict(b, id=d2p.get(b.get('id'), b.get('id'))) if isinstance(b, dict)
                             else d2p.get(b, b) for b in prod['books']]
        if prod.get('work_id'): prod['work_id'] = d2p.get(prod['work_id'], prod['work_id'])
        if prod.get('related_books'):
            prod['related_books'] = [d2p.get(x, x) for x in prod['related_books']]
        if prod.get('contained_in'):
            prod['contained_in'] = [(D2P.get(x, x) if isinstance(x, str)
                                     else dict(x, id=D2P.get(x.get('id'), x.get('id'))))
                                    for x in prod['contained_in']]
        for c in (prod.get('related_collections') or []):
            if isinstance(c, dict) and c.get('collection_id') in D2P:
                c['collection_id'] = D2P[c['collection_id']]
        for c in (prod.get('contains') or []):
            if not isinstance(c, dict): continue
            for k, tbl in (('work_id', d2p), ('book_id', d2p), ('collection_id', D2P)):
                if c.get(k) in tbl: c[k] = tbl[c[k]]
        for s in (prod.get('indexed_by') or []):
            if isinstance(s, dict) and s.get('source_bid') in d2p: s['source_bid'] = d2p[s['source_bid']]

        base = os.path.basename(p).split('-', 1)[1] if '-' in os.path.basename(p) else (prod['title'] + '.json')
        ppath = f'Collection/{P[-3]}/{P[-2]}/{P[-1]}/{P}-{base}'
        jwrite(os.path.join(PROD, ppath), prod)
        IXp[P] = idx_entry(prod, ppath)
        tomb = {'schema_version': d.get('schema_version', 1), 'id': i, 'type': 'collection',
                'title': d.get('title'), '_promoted_to': P, '_promoted_at': at}
        jwrite(p, tomb)
        IXd[i] = {'id': i, 'title': d.get('title'), 'type': 'Collection',
                  'path': os.path.relpath(p, '.').replace(os.sep, '/'), 'promoted_to': P}
        promo[i] = {'production_id': P, 'type': 'collection', 'promoted_at': at}
        done.append((i, P, d.get('title')))

    # ── 入向改繫：七種欄形，兩倉一趟掃完 ──
    nref = collections.Counter()
    for root in ('.', PROD):
        for t in ('Work', 'Book', 'Collection'):
            for p in glob.glob(f'{root}/{t}/*/*/*/*.json'):
                try: d = json.load(open(p))
                except Exception: continue
                if not isinstance(d, dict): continue
                ch = False
                # contained_in：Book／Work 用 {id, volume_index, …} 物件，
                # Collection 用純字串陣列——兩式都要認。
                if d.get('contained_in'):
                    nw = []
                    for c in d['contained_in']:
                        if isinstance(c, dict) and c.get('id') in D2P:
                            nw.append(dict(c, id=D2P[c['id']])); ch = True; nref['contained_in{}'] += 1
                        elif isinstance(c, str) and c in D2P:
                            nw.append(D2P[c]); ch = True; nref['contained_in[str]'] += 1
                        else: nw.append(c)
                    d['contained_in'] = nw
                for r in (d.get('related_works') or []):
                    if isinstance(r, dict) and r.get('id') in D2P:
                        r['id'] = D2P[r['id']]; ch = True; nref['related_works'] += 1
                if d.get('collections'):
                    nw = [D2P.get(x, x) for x in d['collections']]
                    if nw != d['collections']:
                        nref['collections'] += sum(1 for x, y in zip(nw, d['collections']) if x != y)
                        d['collections'] = nw; ch = True
                for r in (d.get('related_collections') or []):
                    if isinstance(r, dict) and r.get('collection_id') in D2P:
                        r['collection_id'] = D2P[r['collection_id']]; ch = True; nref['related_collections'] += 1
                for c in (d.get('contains') or []):
                    if isinstance(c, dict) and c.get('collection_id') in D2P:
                        c['collection_id'] = D2P[c['collection_id']]; ch = True; nref['contains'] += 1
                if ch and d.get('id') not in D2P: jwrite(p, d)
        for p in glob.glob(f'{root}/Work/*/*/*/*/collated_edition/*.json'):
            try: d = json.load(open(p))
            except Exception: continue
            secs = d.get('sections') if isinstance(d, dict) else (d if isinstance(d, list) else [])
            ch = False
            for s in (secs or []):
                if isinstance(s, dict) and s.get('collection_id') in D2P:
                    s['collection_id'] = D2P[s['collection_id']]; ch = True; nref['整理本 collection_id'] += 1
            if ch: jwrite(p, d)

    with open(IDXF, 'w', encoding='utf-8') as f:
        json.dump({k: IXd[k] for k in sorted(IXd)}, f, ensure_ascii=False, indent=2); f.write('\n')
    with open(os.path.join(PROD, IDXF), 'w', encoding='utf-8') as f:
        json.dump({k: IXp[k] for k in sorted(IXp)}, f, ensure_ascii=False, indent=2); f.write('\n')
    with open('promotions.json', 'w', encoding='utf-8') as f:
        json.dump({'version': PRm.get('version', 1),
                   'promotions': {k: promo[k] for k in sorted(promo)}}, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'\n升格 {len(done)} 條；入向改繫 {sum(nref.values())} 處（兩倉）')
    for k, v in nref.most_common(): print(f'   {k:24} {v}')
    for i, P, t in done[:10]: print(f'   {i} → {P}　{t}')
    if len(done) > 10: print(f'   …餘 {len(done)-10}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
