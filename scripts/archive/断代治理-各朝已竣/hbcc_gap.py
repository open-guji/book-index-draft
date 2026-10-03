# -*- coding: utf-8 -*-
# HBCC 對比之二：把 HBCC 獨有者分 exact／near／absent 三等
# 用法：先跑 hbcc_cmp.py 生出各 diff-*.json，再 SP=<同一目錄> python3 scripts/hbcc_gap.py
# -*- coding: utf-8 -*-
"""HBCC 獨有之著錄，逐條分三等：exact／near（疑同，待覈）／absent（庫中無其影）。

near 之判準三條，皆只認高信度者：
  一、差一字（編輯距離 1，且長度 ≥3）——異體字、形訛、脫字之屬
  二、本庫之題含 HBCC 之題為其真前綴或真後綴，且多出者 ≤3 字
     （「晉泰始起居注」⊃「泰始起居注」、「黃帝九鼎神丹經訣」⊃「黃帝九鼎神丹經」）
  三、反之，HBCC 之題含本庫之題，條件同上
"""
import json,glob,sys,os,re,collections
sys.path.insert(0,os.environ['SP']); sys.path.insert(0,'/home/user/pku-hbcc-data/scripts/hbcc')
import cmp as C, parse as hp
H='/home/user/pku-hbcc-data/data/hbcc/harvest_export/records/'

def ed1(a,b):
    """編輯距離 ≤1？"""
    la,lb=len(a),len(b)
    if abs(la-lb)>1: return False
    if la==lb:
        return sum(1 for x,y in zip(a,b) if x!=y)==1
    if la>lb: a,b,la,lb=b,a,lb,la
    i=0
    while i<la and a[i]==b[i]: i+=1
    return a[i:]==b[i+1:]

def build_lib():
    T=collections.defaultdict(list)   # 正規化題 → [(id,title,來源們)]
    for root in ['.','../book-index']:
        for p in glob.glob(root+'/Work/*/*/*/*.json'):
            d=json.load(open(p))
            if d.get('_promoted_to'): continue
            srcs=[s.get('source') for s in (d.get('indexed_by') or [])]
            cand=[d.get('title')]+[s.get('title_info') for s in (d.get('indexed_by') or [])]+list(d.get('additional_titles') or [])
            for t in cand:
                if not t: continue
                n=C.norm(t)
                if n: T[n].append((d['id'],d.get('title'),srcs))
                m=re.match(r'^[^《》]{1,8}《([^》]+)》',t)
                if m:
                    n2=C.norm(m.group(1))
                    if n2: T[n2].append((d['id'],d.get('title'),srcs))
    return T

def main():
    T=build_lib()
    keys=list(T)
    bylen=collections.defaultdict(list)
    for k in keys: bylen[len(k)].append(k)
    pref=collections.defaultdict(list)
    for k in keys:
        for L in range(2,min(len(k),8)+1): pref[k[:L]].append(k)
    suf=collections.defaultdict(list)
    for k in keys:
        for L in range(2,min(len(k),8)+1): suf[k[-L:]].append(k)
    print('本庫題名索引',len(keys))
    OUT={}
    for src,pre in C.MAP.items():
        hn,prefixes=pre
        d=json.load(open(os.environ['SP']+'/diff-%s.json'%src))
        stat=collections.Counter(); rows=[]
        for k,cnt in d['only_hbcc']:
            if k in T: stat['exact']+=cnt; continue
            near=None
            for c in bylen[len(k)]+bylen[len(k)-1]+bylen[len(k)+1]:
                if ed1(k,c): near=('差一字',c); break
            if not near and len(k)>=3:
                for c in pref.get(k[:min(len(k),8)],[]):
                    if c!=k and c.startswith(k) and len(c)-len(k)<=3: near=('本庫之題多出尾字',c); break
                if not near:
                    for c in suf.get(k[-min(len(k),8):],[]):
                        if c!=k and c.endswith(k) and len(c)-len(k)<=3: near=('本庫之題多出首字',c); break
                if not near:
                    for L in range(len(k)-1,max(2,len(k)-4),-1):
                        if k[:L] in T: near=('HBCC 之題多出尾字',k[:L]); break
                        if k[-L:] in T: near=('HBCC 之題多出首字',k[-L:]); break
            if near: stat['near']+=cnt; rows.append(('near',k,cnt,near[0],near[1]))
            else: stat['absent']+=cnt; rows.append(('absent',k,cnt,'',''))
        OUT[src]={'stat':dict(stat),'rows':rows}
        tot=sum(stat.values())
        print(f'  {src:10} HBCC 獨有 {tot:6}　exact {stat["exact"]:5}　near(疑同) {stat["near"]:5}　absent(真缺) {stat["absent"]:5}'
              f'　真缺率 {100*stat["absent"]/max(1,tot):4.1f}%')
    json.dump(OUT,open(os.environ['SP']+'/gap.json','w'),ensure_ascii=False)
    A=sum(v['stat'].get('absent',0) for v in OUT.values())
    N=sum(v['stat'].get('near',0) for v in OUT.values())
    E=sum(v['stat'].get('exact',0) for v in OUT.values())
    print(f'  合計：exact {E}　near {N}　absent {A}')

main()
