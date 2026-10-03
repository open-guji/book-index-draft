# -*- coding: utf-8 -*-
# HBCC 對比之三：反向——本庫有著錄而 HBCC 十四家同源目錄查無對應題名者
# 見 .claude/plans/HBCC對比-20260826.md〈六、反向比對方法〉
# 用法：先跑 hbcc_cmp.py 生出 diff-*.json，再 SP=<同一目錄> python3 scripts/hbcc_reverse.py
#       需本庫已建 entity_names.json（production Entity 之 primary_name＋alt_names 全集）
import json, glob, sys, os, collections, re

SP = os.environ['SP']
sys.path.insert(0, SP)
sys.path.insert(0, '/home/user/pku-hbcc-data/scripts/hbcc')
import hbcc_cmp as C
import parse as hp

H = '/home/user/pku-hbcc-data/data/hbcc/harvest_export/records/'
ROLE = ('撰', '注', '解', '疏', '述', '編', '修', '纂', '譯', '傳', '集解', '章句', '音義', '正義', '集注', '撰集', '考訂')
ROLE_RE = re.compile('(' + '|'.join(ROLE) + ')$')


def ed1(a, b):
    la, lb = len(a), len(b)
    if abs(la - lb) > 1: return False
    if la == lb: return sum(1 for x, y in zip(a, b) if x != y) == 1
    if la > lb: a, b, la, lb = b, a, lb, la
    i = 0
    while i < la and a[i] == b[i]: i += 1
    return a[i:] == b[i + 1:]


def hbcc_titles(prefixes):
    out = set()
    for pre in prefixes:
        for f in sorted(glob.glob(H + pre + '-*.tsv')):
            with open(f, encoding='utf-8') as fh:
                next(fh)
                for line in fh:
                    a = line.rstrip('\n').split('\t')
                    if len(a) < 4: continue
                    n = C.norm(hp.parse(a[3])['書名'])
                    if n: out.add(n)
    return out


def ours(src):
    out = set()
    for root in ['.', '../book-index']:
        for p in glob.glob(root + '/Work/*/*/*/*.json'):
            d = json.load(open(p))
            if d.get('_promoted_to'): continue
            for s in (d.get('indexed_by') or []):
                if s.get('source') != src: continue
                keys = set()
                for t in (d.get('title'), s.get('title_info')):
                    if not t: continue
                    n = C.norm(t)
                    if n: keys.add(n)
                    m = re.match(r'^[^《》]{1,8}《([^》]+)》', t or '')
                    if m: keys.add(C.norm(m.group(1)))
                    if ' ' in (t or ''): keys.add(C.norm(t.split(' ', 1)[1]))
                if keys: out.add((frozenset(keys), d['id'], d.get('title')))
    return out


def build_entity_names():
    """production Entity 之 primary_name＋alt_names 全集，寫入 SP/entity_names.json。"""
    names = set()
    for p in glob.glob('../book-index/Entity/*/*/*/*.json'):
        d = json.load(open(p))
        if d.get('primary_name'): names.add(d['primary_name'])
        for a in (d.get('alt_names') or []):
            nm = a.get('name') if isinstance(a, dict) else a
            if nm: names.add(nm)
    json.dump(sorted(names), open(SP + '/entity_names.json', 'w'), ensure_ascii=False)
    return names


def main():
    ef = SP + '/entity_names.json'
    names = set(json.load(open(ef))) if os.path.exists(ef) else build_entity_names()
    names = {C.norm(n) for n in names if n}

    per_cat = {src: hbcc_titles(pre) for src, (hn, pre) in C.MAP.items()}
    ALL_HBCC = set().union(*per_cat.values())
    print('HBCC 十四家題名總表', len(ALL_HBCC))

    RESULT = {}
    for src, (hn, pre) in C.MAP.items():
        hset = per_cat[src]
        only = [(ks, wid, t) for ks, wid, t in ours(src) if not (ks & hset)]
        bylen = collections.defaultdict(list)
        for k in ALL_HBCC: bylen[len(k)].append(k)

        exact = near = round1 = round2 = 0
        still = []
        for ks, wid, t in only:
            k = sorted(ks, key=len)[0]
            if k in ALL_HBCC: exact += 1; continue
            found = any(ed1(k, c) for L in (len(k) - 1, len(k), len(k) + 1) for c in bylen.get(L, []))
            if found: near += 1; continue
            # 第一輪：撰人名黏題首
            r1 = False
            for L in range(2, min(6, len(k) - 1) + 1):
                pre_, rest = k[:L], k[L:]
                if len(rest) >= 2 and pre_ in names and rest in hset: r1 = True; break
            if r1: round1 += 1; continue
            # 第二輪：題末綴撰人+役式
            m = ROLE_RE.search(k)
            r2 = False
            if m:
                role = m.group(1); rest = k[:-len(role)]
                for L in range(2, min(5, len(rest) - 1) + 1):
                    head = rest[:len(rest) - L]
                    if len(head) >= 2 and head in hset: r2 = True; break
            if r2: round2 += 1; continue
            still.append({'id': wid, 'title': t, '鑰': k})

        RESULT[src] = {'本庫獨有': len(only), 'exact_HBCC別目有': exact, 'near_疑同': near,
                        '撰人黏題首而誤判': round1, '題末綴撰人式而誤判': round2,
                        '真absent': len(still), '條': still}
        print(f'{src:10} 獨有{len(only):5} exact{exact:5} near{near:5} '
              f'黏題首{round1:5} 綴題末{round2:5} 真absent{len(still):5}')

    json.dump(RESULT, open(SP + '/reverse_final2.json', 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
