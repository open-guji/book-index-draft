"""校驗電池：每批整理之後必跑，比對基線數字。
用法：在庫根目錄執行 python3 .claude/skills/hanzhi-curation/scripts/chk.py"""
import json,os,glob
def li(k):
    d={}
    for s in '0123456789abcdef': d.update(json.load(open(f'index/{k}s/{s}.json')))
    return d
IW,IB=li('work'),li('book'); IC=json.load(open('index/collections.json'))
# Production ID ↔ Draft ID：庫中之互指有用 Production ID 者，比對前兩側俱須正規化。
# 不正規化則 Book→Work、Work→Book 之單向數全為假象（曾誤判二次）。
_PR=json.load(open('promotions.json'))['promotions']
P2D={v['production_id']:k for k,v in _PR.items()}
def nz(i): return P2D.get(i,i)
def shard(i):
    h=0
    for c in i: h=((h*31)+ord(c))&0xFFFFFFFF
    return '%x'%(h%16)
SW={s:set(json.load(open(f'index/works/{s}.json'))) for s in '0123456789abcdef'}
SB={s:set(json.load(open(f'index/books/{s}.json'))) for s in '0123456789abcdef'}
print('索引 Work',len(IW),'Book',len(IB),'Collection',len(IC))
print('分片錯置 Work',sum(1 for k in IW if k not in SW[shard(k)]),
      ' Book',sum(1 for k in IB if k not in SB[shard(k)]))
print('索引指向不存在檔案',sum(1 for v in list(IW.values())+list(IB.values())+list(IC.values()) if not os.path.exists(v['path'])))
prod={v['production_id'] for v in json.load(open('promotions.json'))['promotions'].values()}
ents=set()
for p in glob.glob('Entity/*/*/*/*.json'):
    try: ents.add(json.load(open(p))['id'])
    except Exception: pass
allids=set(IW)|set(IB)|set(IC)|prod|ents
selfref=nullrel=0; dang=[]; notidx=[]; mism=[]; parse=[]
b2w={}; w2b={}
for kind,pat,idx in (('W','Work/*/*/*/*.json',IW),('B','Book/*/*/*/*.json',IB)):
    for p in glob.glob(pat):
        try: d=json.load(open(p))
        except Exception as e: parse.append((p,str(e))); continue
        i=d.get('id'); e=idx.get(i)
        if e is None: notidx.append(p); continue
        if e['path']!=p: mism.append(('path',i,e['path'],p))
        if e.get('title')!=d.get('title'): mism.append(('title',i,e.get('title'),d.get('title')))
        if d.get('authors') and e.get('author')!=d['authors'][0].get('name'):
            mism.append(('author',i,e.get('author'),d['authors'][0].get('name')))
        if kind=='W':
            for r in d.get('related_works') or []:
                if not r or not r.get('id') or not r.get('relation'): nullrel+=1; continue
                if r['id']==i: selfref+=1
                if r['id'] not in allids: dang.append((p,r['id'],r.get('title')))
            for b in d.get('books') or []: w2b.setdefault(b,set()).add(i)
        else:
            if d.get('work_id'): b2w[i]=d['work_id']
print('解析失敗',len(parse),'檔案未入索引',len(notidx),'索引欄位不符',len(mism))
for x in notidx[:10]: print('  未入索引',x)
for x in mism[:15]: print('  不符',x)
print('自我關聯',selfref,'空關聯',nullrel,'懸空關聯',len(dang))
for x in dang[:10]: print('  懸空',x)
# 兩側俱經 promotions 正規化
_w2b={}
for b,ws in w2b.items(): _w2b.setdefault(nz(b),set()).update(nz(x) for x in ws)
_b2w={nz(b):nz(w) for b,w in b2w.items()}
ow=[(b,w) for b,w in _b2w.items() if w not in _w2b.get(b,set())]
ww=[(b,w) for b,ws in _w2b.items() for w in ws if _b2w.get(b)!=w]
print('Book→Work 單向',len(ow),' Work→Book 單向',len(ww))
for x in ow[:5]: print('  B→W',x)
for x in ww[:5]: print('  W→B',x)

# 人物 ↔ 作品之雙向：entity.works 指向作品，不代表作品回指該人物
ent={}
for p in glob.glob('Entity/*/*/*/*.json'):
    try: e=json.load(open(p)); ent[e['id']]=e
    except Exception: pass
w2e={}
for p in glob.glob('Work/*/*/*/*.json'):
    try: d=json.load(open(p))
    except Exception: continue
    w2e[d.get('id')]={a.get('entity_id') for a in (d.get('authors') or []) if a.get('entity_id')}
e_only=sum(1 for i,e in ent.items() for x in (e.get('works') or [])
           if x.get('work_id') in w2e and i not in w2e[x['work_id']])
w_only=sum(1 for w,es in w2e.items() for i in es
           if i in ent and not any(x.get('work_id')==w for x in (ent[i].get('works') or [])))
print('人物→作品 單向',e_only,' 作品→人物 單向',w_only)

# 整理本 section 之 work_ids ↔ work 之 emendated_by
import ast
desync=0
for f in glob.glob('Work/*/*/*/*/collated_edition/*.json'):
    if 'index' in f: continue
    try: cd=json.load(open(f))
    except Exception: continue
    if not isinstance(cd,dict): continue
    src=f.split('/')[4]
    for sec in cd.get('sections',[]):
        if not isinstance(sec,dict): continue
        v=sec.get('work_ids'); ids=ast.literal_eval(v) if isinstance(v,str) else (v or [])
        for i in ids:
            e=IW.get(i)
            if not e: continue
            try: dd=json.load(open(e['path']))
            except Exception: continue
            if not any(y.get('source_bid')==src for y in (dd.get('emendated_by') or [])
                       +(dd.get('indexed_by') or [])): desync+=1
print('整理本繫連而 work 側無記錄',desync)

# 輯佚檔 fragments/*.json
fbad=[]
for f in glob.glob('Work/*/*/*/*/fragments/*.json'):
    wid=f.split('/')[4]
    try: fd=json.load(open(f))
    except Exception as e: fbad.append((f,'解析失敗')); continue
    if fd.get('work_id')!=wid: fbad.append((f,'work_id 與路徑不符'))
    if wid not in IW: fbad.append((f,'work 不存在')); continue
    cov=fd.get('coverage') or {}
    rec=sum(1 for x in (fd.get('fragments') or []) if (x.get('text') or '').strip())
    if cov.get('fragments_recorded')!=rec:
        fbad.append((f,f"fragments_recorded {cov.get('fragments_recorded')} ≠ 實錄 {rec}"))
    if cov.get('level')=='著錄層' and rec and cov.get('level')!='文本層' and rec>0 and not cov.get('note'):
        fbad.append((f,'著錄層而有錄文，未說明'))
    if not (fd.get('collectors') or fd.get('fragments')):
        fbad.append((f,'既無輯家亦無佚文'))
    try: wd=json.load(open(IW[wid]['path']))
    except Exception: wd={}
    if 'fragments/' not in (wd.get('ai_note') or ''):
        fbad.append((f,'work 側未記本檔'))
print('輯佚檔',len(glob.glob('Work/*/*/*/*/fragments/*.json')),'不合',len(fbad))
for x in fbad[:12]: print('  ',x)
