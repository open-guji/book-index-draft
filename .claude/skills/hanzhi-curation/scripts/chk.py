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
    _LV={'著錄層','篇目層','文本層','文本層（部分）'}
    if (fd.get('coverage') or {}).get('level') not in _LV:
        fbad.append((f,"coverage.level「%s」不在三層之內"%(fd.get('coverage') or {}).get('level')))
    for _fr in (fd.get('fragments') or []):
        # 篇目層之條：有 piece_title 而 text 為 null，須明記 text_status
        if _fr.get('text') is None and _fr.get('piece_title') and not _fr.get('text_status'):
            fbad.append((f,'fragments 有篇題而無 text_status，未錄與無文無從分辨'))
    _LS={'lost','partially_extant','extant','undetermined'}
    if 'loss_status' in fd and fd['loss_status'] not in _LS:
        fbad.append((f,f"loss_status「{fd['loss_status']}」不在枚舉內"))
    cov=fd.get('coverage') or {}
    rec=sum(1 for x in (fd.get('fragments') or []) if (x.get('text') or '').strip())
    if cov.get('fragments_recorded')!=rec:
        fbad.append((f,f"fragments_recorded {cov.get('fragments_recorded')} ≠ 實錄 {rec}"))
    if cov.get('level')=='著錄層' and rec and cov.get('level')!='文本層' and rec>0 and not cov.get('note'):
        fbad.append((f,'著錄層而有錄文，未說明'))
    if not (fd.get('collectors') or fd.get('fragments')):
        fbad.append((f,'既無輯家亦無佚文'))
    for _x in (fd.get('collectors') or []):
        # collectors 之一條即斷言「某人輯過此書」；無其人則此斷言落空
        if not (_x.get('collector') or '').strip():
            fbad.append((f,'collectors 有條而輯家為空'))
        _wk=_x.get('work'); _wi=_x.get('work_id')
        if _wi and _wi not in IW: fbad.append((f,f'輯本 work_id {_wi} 不存在'))
    try: wd=json.load(open(IW[wid]['path']))
    except Exception: wd={}
    if 'fragments/' not in (wd.get('ai_note') or ''):
        fbad.append((f,'work 側未記本檔'))
print('輯佚檔',len(glob.glob('Work/*/*/*/*/fragments/*.json')),'不合',len(fbad))
for x in fbad[:12]: print('  ',x)

# 整理本 section 之 work_id / target_bid 是否落空
# （匯入時每條都鑄了 id，而 Work 檔只生成了一部分，故有懸空；索引側查不到這一類）
try: IB
except NameError:
    IB={}
    for _s in '0123456789abcdef':
        try: IB.update(json.load(open(f'index/books/{_s}.json')))
        except Exception: pass
import collections as _c
dang=_c.Counter(); dang_is_book=0; dang_ids=set()
for f in glob.glob('Work/*/*/*/*/collated_edition/*.json'):
    if f.endswith('collated_edition_index.json'): continue
    try: cd=json.load(open(f))
    except Exception: continue
    if not isinstance(cd,dict): continue
    for sec in cd.get('sections',[]):
        if not isinstance(sec,dict): continue
        ws=[sec['work_id']] if isinstance(sec.get('work_id'),str) else []
        v=sec.get('work_ids')
        if isinstance(v,list): ws+=[x for x in v if isinstance(x,str)]
        for w in ws:
            if w in IW: continue
            dang[f.split('/')[4]]+=1; dang_ids.add(w)
            if w in IB: dang_is_book+=1
        b=sec.get('book_id')
        if isinstance(b,str) and b not in IB:
            dang[f.split('/')[4]]+=1; dang_ids.add(b)
        b=sec.get('target_bid')
        if isinstance(b,str) and b not in IB and b not in IW:
            dang[f.split('/')[4]]+=1; dang_ids.add(b)
print('整理本繫連落空 section',sum(dang.values()),'相異 id',len(dang_ids),'其中實為 Book',dang_is_book)
for k,v in dang.most_common(6): print('  ',k,v)

# 整理本 section 級磁鐵：同一檔內，數個異題 section 共指一 work
# （匯入時同名條目未分，如隋志四種卷數各異之《後漢書》皆繫一 id）
import re as _re
_VAR=str.maketrans({'説':'說','録':'錄','歴':'歷','爲':'為','畧':'略','别':'別','吴':'吳'})
def _nz(t): return _re.sub(r'[《》\s]','',(t or '').translate(_VAR))
secmag=_c.Counter(); secmag_ex=[]
for f in glob.glob('Work/*/*/*/*/collated_edition/*.json'):
    if f.endswith('collated_edition_index.json'): continue
    try: cd=json.load(open(f))
    except Exception: continue
    if not isinstance(cd,dict): continue
    own=f.split('/')[4]; m=_c.defaultdict(set)
    for sec in cd.get('sections',[]):
        if not isinstance(sec,dict): continue
        w=sec.get('work_id')
        if isinstance(w,str) and w in IW and sec.get('title'): m[w].add(_nz(sec['title']))
    for w,ts in m.items():
        if len(ts)>1:
            secmag[own]+=len(ts)
            if len(secmag_ex)<6: secmag_ex.append((own,w,IW[w]['title'],sorted(ts)[:4]))
print('整理本 section 級磁鐵（異題共指一 work 之題數）',sum(secmag.values()))
for k,v in secmag.most_common(6): print('  ',k,v)
for x in secmag_ex: print('   例',x)

# Work 之 loss_status 須在枚舉內（SCHEMA「loss_status 枚舉」）
_LSW={'lost','partially_extant','extant','undetermined'}
lsbad=[]; lsc=_c.Counter()
for w,e in IW.items():
    try: d=json.load(open(e['path']))
    except Exception: continue
    if not isinstance(d,dict) or 'loss_status' not in d: continue
    v=d['loss_status']; lsc[v]+=1
    if v not in _LSW: lsbad.append((w,v))
print('Work loss_status',dict(lsc),'不合枚舉',len(lsbad))
for x in lsbad[:8]: print('  ',x)

# 輯佚叢書整理本（type: fragment_collection）之雙向對查
fc=[]; todo=0
for f in glob.glob('Work/*/*/*/*/collated_edition/collated_edition_index.json'):
    try: ci=json.load(open(f))
    except Exception: continue
    if ci.get('type')!='fragment_collection': continue
    base=f.rsplit('/',1)[0]; owner=f.split('/')[4]
    fwd={}
    for g in glob.glob(base+'/*.json'):
        if g.endswith('collated_edition_index.json'): continue
        for i,sec in enumerate(json.load(open(g)).get('sections') or []):
            w=sec.get('work_id')
            if isinstance(w,str): fwd.setdefault(w,[]).append((g.split('/')[-1],i))
            if 'fragments' in sec and (sec.get('coverage') or {}).get('level') is None:
                fc.append((g,i,'section 有 fragments 而無 coverage.level——空陣列之歧義未消'))
    for w,locs in fwd.items():
        if w not in IW: fc.append((f,w,'section 所繫 work 不存在')); continue
        fr=glob.glob('Work/*/*/*/%s/fragments/*.json'%w)
        if not fr: todo+=1; continue      # 非損壞，是待辦：目錄既言馬氏輯之，該 work 當有輯佚檔
        cs=json.load(open(fr[0])).get('collectors') or []
        mine=[x for x in cs if x.get('work_id')==owner]
        if not mine: todo+=1; continue          # 輯佚檔尚無此輯家之條，目錄為新知，待補
        if not any(x.get('sections') or x.get('section_file') for x in mine):
            fc.append((f,w,'整理本繫之而輯佚檔未記其 section_file'))
print('輯佚叢書整理本 不合',len(fc),'　待辦（已繫而無輯佚檔）',todo)
for x in fc[:8]: print('  ',x)
