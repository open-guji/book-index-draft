import json,glob,os,sys,collections
D='/workspace/book-index-draft'; P='/workspace/book-index'
A='欽定四庫全書·文淵閣本'; B='清乾隆間寫文淵閣四庫全書本'
APPLY='--apply' in sys.argv
PERIOD=sys.argv[sys.argv.index('--period')+1] if '--period' in sys.argv else None
def save(p,d):
    if APPLY: open(p,'w',encoding='utf-8',newline='\n').write(json.dumps(d,ensure_ascii=False,indent=2))
BK={}; W={}
for root in (D,P):
    for f in glob.glob(f'{root}/Book/*/*/*/*.json'):
        try: d=json.load(open(f,encoding='utf-8'))
        except: continue
        d['__f']=f; BK[d['id']]=d
    for f in glob.glob(f'{root}/Work/*/*/*/*.json'):
        try: d=json.load(open(f,encoding='utf-8'))
        except: continue
        d['__f']=f; W[d['id']]=d
byw=collections.defaultdict(list)
for d in BK.values():
    if d.get('work_id'): byw[d['work_id']].append(d)
done=0; skip=0
for w,bs in byw.items():
    ea=[x for x in bs if x.get('edition')==A]; eb=[x for x in bs if x.get('edition')==B]
    if not (ea and eb): continue
    if PERIOD and (W.get(w,{}).get('period') or '(空)')!=PERIOD: continue
    if len(ea)!=1 or len(eb)!=1: print(f'  ⤬ 跳过 {w} 《{W.get(w,{}).get("title")}》 A×{len(ea)} B×{len(eb)}（一侧多部，需人工）'); skip+=1; continue
    a,b=ea[0],eb[0]
    ci={json.dumps(x,ensure_ascii=False,sort_keys=True) for x in (a.get('contained_in') or [])}
    a['contained_in']=(a.get('contained_in') or [])+[x for x in (b.get('contained_in') or []) if json.dumps(x,ensure_ascii=False,sort_keys=True) not in ci]
    ri={(x.get('id'),x.get('url')) for x in (a.get('resources') or [])}
    a['resources']=(a.get('resources') or [])+[x for x in (b.get('resources') or []) if (x.get('id'),x.get('url')) not in ri]
    for k in ('section','metadata'):
        if b.get(k) and not a.get(k): a[k]=b[k]
    ats=set(a.get('additional_titles') or [])|set(b.get('additional_titles') or [])
    if b.get('title') and b['title']!=a.get('title'): ats.add(b['title'])
    if ats: a['additional_titles']=sorted(ats)
    a['merged_from']=sorted(set((a.get('merged_from') or [])+[b['id']]))
    a['ai_note']=((a.get('ai_note') or '')+f' 2026-08-21 文淵閣四庫本雙錄歸併：Book {b["id"]}（edition「{B}」，繫《國立故宮博物院善本舊籍》1ahwlq4d3tjwg，帶故宮著錄號 {(b.get("metadata") or {}).get("npm_item_id","")}）併入本條。二者非兩部書——文淵閣《四庫全書》寫本原藏台北故宮，本條之 edition「{A}」著錄其於叢編中之冊次並繫維基共享影印，彼條著錄同一實物之故宮館藏，故合為一 Book，兩處著錄各存為 contained_in／resources。').strip()
    save(a['__f'],{k:v for k,v in a.items() if not k.startswith('__')})
    ww=W.get(w)
    if ww:
        ww['books']=[x for x in (ww.get('books') or []) if x!=b['id']]
        ww['ai_note']=((ww.get('ai_note') or '')+f' 2026-08-21 文淵閣四庫本雙錄歸併：所掛 Book {b["id"]} 與 {a["id"]} 同指文淵閣寫本一實物，今併於後者。').strip()
        save(ww['__f'],{k:v for k,v in ww.items() if not k.startswith('__')})
    if APPLY and os.path.exists(b['__f']): os.remove(b['__f'])
    print(f'  ✓ {W.get(w,{}).get("title")}  {b["id"]} → {a["id"]}')
    done+=1
print(f'\n归并 {done} 组，跳过 {skip} 组'+('' if APPLY else '  (dry-run)'))
