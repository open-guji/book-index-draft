#!/usr/bin/env python
"""文淵閣四庫本雙錄歸併。

同一部書常掛兩部 Book：
  A `欽定四庫全書·文淵閣本`  —— 繫叢編 Collection 8rlb6yi1ecqo，記 volume_index，資源為維基共享影印
  B `清乾隆間寫文淵閣四庫全書本` —— 繫故宮 Collection 1ahwlq4d3tjwg，記 npm 館藏號

文淵閣《四庫全書》寫本原藏台北故宮，二者指同一實物之同一版本，非兩個版本實例。
依本庫體例（Book = 版本實例，數位來源歸 resources）應併為一條。
詳見 .claude/known-issues/文淵閣四庫本雙錄.md

用法：
    python merge-siku-dual-books.py                        # dry-run 全庫
    python merge-siku-dual-books.py --period song --apply  # 按朝代施行
    python merge-siku-dual-books.py --by-title --apply     # 一側多部者按題名精確配對
"""
import json, glob, os, sys, collections

D = '/workspace/book-index-draft'
P = '/workspace/book-index'
A = '欽定四庫全書·文淵閣本'
B = '清乾隆間寫文淵閣四庫全書本'
APPLY = '--apply' in sys.argv
BYTITLE = '--by-title' in sys.argv
PERIOD = sys.argv[sys.argv.index('--period') + 1] if '--period' in sys.argv else None


def save(path, d):
    if APPLY:
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(json.dumps({k: v for k, v in d.items() if not k.startswith('__')},
                                ensure_ascii=False, indent=2))


BK, W = {}, {}
for root in (D, P):
    for f in glob.glob(f'{root}/Book/*/*/*/*.json'):
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        d['__f'] = f
        BK[d['id']] = d
    for f in glob.glob(f'{root}/Work/*/*/*/*.json'):
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        d['__f'] = f
        W[d['id']] = d

byw = collections.defaultdict(list)
for d in BK.values():
    if d.get('work_id'):
        byw[d['work_id']].append(d)


def merge_one(w, a, b):
    """把 B 併入 A：contained_in / resources / section / metadata / additional_titles。"""
    ci = {json.dumps(x, ensure_ascii=False, sort_keys=True) for x in (a.get('contained_in') or [])}
    a['contained_in'] = (a.get('contained_in') or []) + [
        x for x in (b.get('contained_in') or [])
        if json.dumps(x, ensure_ascii=False, sort_keys=True) not in ci]
    ri = {(x.get('id'), x.get('url')) for x in (a.get('resources') or [])}
    a['resources'] = (a.get('resources') or []) + [
        x for x in (b.get('resources') or []) if (x.get('id'), x.get('url')) not in ri]
    for k in ('section', 'metadata'):
        if b.get(k) and not a.get(k):
            a[k] = b[k]
    ats = set(a.get('additional_titles') or []) | set(b.get('additional_titles') or [])
    if b.get('title') and b['title'] != a.get('title'):
        ats.add(b['title'])
    if ats:
        a['additional_titles'] = sorted(ats)
    a['merged_from'] = sorted(set((a.get('merged_from') or []) + [b['id']]))
    npm = (b.get('metadata') or {}).get('npm_item_id', '')
    a['ai_note'] = ((a.get('ai_note') or '') + f' 2026-08-21 文淵閣四庫本雙錄歸併：Book {b["id"]}'
                    f'（edition「{B}」，繫《國立故宮博物院善本舊籍》1ahwlq4d3tjwg，帶故宮著錄號 {npm}）併入本條。'
                    f'二者非兩部書——文淵閣《四庫全書》寫本原藏台北故宮，本條之 edition「{A}」著錄其於叢編中之冊次'
                    f'並繫維基共享影印，彼條著錄同一實物之故宮館藏，故合為一 Book，兩處著錄各存為 contained_in／resources。'
                    ).strip()
    save(a['__f'], a)
    ww = W.get(w)
    if ww:
        ww['books'] = [x for x in (ww.get('books') or []) if x != b['id']]
        ww['ai_note'] = ((ww.get('ai_note') or '') + f' 2026-08-21 文淵閣四庫本雙錄歸併：'
                         f'所掛 Book {b["id"]} 與 {a["id"]} 同指文淵閣寫本一實物，今併於後者。').strip()
        save(ww['__f'], ww)
    if APPLY and os.path.exists(b['__f']):
        os.remove(b['__f'])


done = skip = 0
for w, bs in byw.items():
    ea = [x for x in bs if x.get('edition') == A]
    eb = [x for x in bs if x.get('edition') == B]
    if not (ea and eb):
        continue
    if PERIOD and (W.get(w, {}).get('period') or '(空)') != PERIOD:
        continue
    title = W.get(w, {}).get('title')
    if len(ea) == 1 and len(eb) == 1:
        merge_one(w, ea[0], eb[0])
        print(f'  ✓ {title}  {eb[0]["id"]} → {ea[0]["id"]}')
        done += 1
        continue
    if not BYTITLE:
        print(f'  ⤬ 跳过 {w} 《{title}》 A×{len(ea)} B×{len(eb)}（一侧多部，需人工）')
        skip += 1
        continue
    # 一側多部：按題名精確配對，兩側該題名皆唯一者才配
    ta, tb = collections.defaultdict(list), collections.defaultdict(list)
    for x in ea:
        ta[x.get('title')].append(x)
    for x in eb:
        tb[x.get('title')].append(x)
    pairs = [(ta[t][0], tb[t][0]) for t in set(ta) & set(tb)
             if len(ta[t]) == 1 and len(tb[t]) == 1]
    if not pairs:
        print(f'  ⤬ 跳过 {w} 《{title}》 A×{len(ea)} B×{len(eb)}（題名無可配者）')
        skip += 1
        continue
    paired = {id(y) for pr in pairs for y in pr}
    left = [x.get('title') for x in ea + eb if id(x) not in paired]
    for a, b in pairs:
        merge_one(w, a, b)
    done += len(pairs)
    print(f'  ◐ {title} A×{len(ea)} B×{len(eb)} → 按題名配 {len(pairs)} 對，餘 {left}')

print(f'\n归并 {done} 组，跳过 {skip} 组' + ('' if APPLY else '  (dry-run)'))
