"""校驗電池：每批整理之後必跑，比對基線數字。
用法：在庫根目錄執行 python3 .claude/skills/hanzhi-curation/scripts/chk.py"""
import json,os,glob
def li(k):
    d={}
    for s in '0123456789abcdef': d.update(json.load(open(f'index/{k}s/{s}.json')))
    return d
IW,IB=li('work'),li('book'); IC=json.load(open('index/collections.json'))
IE=li('entitie')
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
print('索引指向不存在檔案',sum(1 for v in list(IW.values())+list(IB.values())+list(IC.values())+list(IE.values()) if not os.path.exists(v['path'])),'　基線 0（含 entities；人物併池退役後索引殘留即現於此）')
prod={v['production_id'] for v in json.load(open('promotions.json'))['promotions'].values()}
ents=set()
for p in glob.glob('Entity/*/*/*/*.json'):
    try: ents.add(json.load(open(p))['id'])
    except Exception: pass
allids=set(IW)|set(IB)|set(IC)|prod|ents
selfref=nullrel=0; dang=[]; notidx=[]; mism=[]; parse=[]; derived=[]; rwdrift=[]
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
        # 索引其餘可機械推出之欄，規則照抄 book-index-manager 的 build_index_entry：
        # 空值不入索引，故一律以「或 None」比對。2026-08-22 實測：只比 path/title/
        # author 時，全庫尚有 2,666 條索引與記錄檔不符而無人知——dynasty 1,882、
        # original_title 680、work_id 45 皆在盲區。凡改記錄檔而未重建索引即生此漂移，
        # 修法：以本工具重建（見 .claude/plans/並行作業總表.md S2 條）。
        _a0=(d.get('authors') or [{}])[0]
        _a0=_a0 if isinstance(_a0,dict) else {}
        _want2={'dynasty':_a0.get('dynasty') or d.get('dynasty') or None,
                'role':_a0.get('role') or None,
                'original_title':d.get('original_title') or None}
        if kind=='B': _want2['work_id']=d.get('work_id') or None
        for _k,_v in _want2.items():
            if (e.get(_k) or None)!=_v: mism.append((_k,i,e.get(_k),_v))
        # 派生欄位（底線起首）：重新生成後比對，不一致以生成值為準（issue #10）。
        # has_text 曾是「有的對、有的錯、大半沒有」——欄名與手寫欄無別，遂無人知其該不該在。
        _ts=set()
        for _r in d.get('resources') or []:
            if isinstance(_r,dict): _ts.update(_r.get('types') or ([_r['type']] if _r.get('type') else []))
        _want={'_has_text':'text' in _ts,'_has_image':'image' in _ts,
               '_has_collated':bool(i) and os.path.isdir(os.path.join(os.path.dirname(p),i,'collated_edition'))}
        for _k,_v in _want.items():
            if (d.get(_k) or False)!=_v: derived.append((p,_k,d.get(_k),_v))
        if kind=='W':
            for r in d.get('related_works') or []:
                if not r or not r.get('id') or not r.get('relation'): nullrel+=1; continue
                if r['id']==i: selfref+=1
                if r['id'] not in allids: dang.append((p,r['id'],r.get('title')))
                # related_works[].title 靠人工同步，必然漂移；不改結構，只報其數
                elif r.get('title') and r['id'] in IW and r['title']!=IW[r['id']].get('title'):
                    rwdrift.append((p,r['id'],r['title'],IW[r['id']].get('title')))
            for b in d.get('books') or []: w2b.setdefault(b,set()).add(i)
        else:
            if d.get('work_id'): b2w[i]=d['work_id']
print('解析失敗',len(parse),'檔案未入索引',len(notidx),'索引欄位不符',len(mism))
print('派生欄位與重算不符',len(derived),'　基線 0（不符即以重算值為準）')
for x in derived[:8]: print('  派生',x)
print('related_works[].title 漂移',len(rwdrift),'　基線 0')
for x in rwdrift[:8]: print('  漂移',x)
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
    # 受控詞彙一律英文（2026-08 遷移）。輯佚檔本作中文三層而整理本作 toc/text，
    # 同一概念兩套詞，今並歸英文；專名與散文說明仍中文。
    _LV={'catalog','titles','text','text_partial'}
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
    # collection_attested：確有輯本而未詳其輯家者。此亦是據，不得作空檔論。
    if not (fd.get('collectors') or fd.get('fragments') or fd.get('collection_attested')):
        fbad.append((f,'既無輯家亦無佚文'))
    # 受控詞彙殘留中文者，是遷移未盡或新寫者未依例
    for _k,_ok in (('text_status',{'recorded','not_recorded'}),('confidence',{'certain','uncertain'})):
        for _fr in (fd.get('fragments') or []):
            if _fr.get(_k) and _fr[_k] not in _ok:
                fbad.append((f,f'{_k}「{_fr[_k]}」不在枚舉內（受控詞彙須英文）')); break
    if fd.get('provenance') and fd['provenance'] not in {'secondary','primary'}:
        fbad.append((f,f"provenance「{fd['provenance']}」不在枚舉內"))
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

# 題名互為子串而撰人相容之 work 對——「同一部書兩種題名」之重出。
# 立此驗之由：曾據《玉函山房輯佚書》目錄新建 work，以「題名精確相等」比對，
# 而庫中題名不規範（《六藝論》庫作「鄭玄六藝論」「六藝論鄭玄撰」），
# 精確比對必落空，遂誤建三十條。八輪之後方因他事偶然撞見。
# 判準取其準者，不取其備者——只認「長題恰為 撰人+短題 / 短題+撰人(+役)」一式：
#   兩側俱須有撰人且相容。一方無撰人則不取——《歸藏》(無撰人) 與《歸藏薛貞注》(薛貞)
#   是原典與注本之別，本為二物（注家有其創作），非重出。
#   短題為庫中多見者（《算經》《詩集》《兵法》之屬）不取，通名撞而不實。
from opencc import OpenCC as _OCC
_t2s=_OCC('t2s'); _N=lambda x:_t2s.convert((x or '').strip())
_byt={}
for _i,_e in IW.items():
    _t=_N(_e.get('title'))
    if _t: _byt.setdefault(_t,[]).append(_i)
_ROLE=('撰','注','傳','疏','集解','注疏','述','說','解','章句','集注','集註')
_dupt=set()
for _i,_e in IW.items():
    _t=_N(_e.get('title')); _au=_N(_e.get('author'))
    if not _t or len(_t)<3 or not _au or len(_au)<2: continue
    _cd=set()
    if _t.startswith(_au) and len(_t)>len(_au): _cd.add(_t[len(_au):])
    if _t.endswith(_au) and len(_t)>len(_au): _cd.add(_t[:-len(_au)])
    for _r in _ROLE:
        if _t.endswith(_au+_r) and len(_t)>len(_au)+len(_r): _cd.add(_t[:-(len(_au)+len(_r))])
    for _s in _cd:
        if len(_s)<2: continue
        _js=_byt.get(_s,())
        if len(_js)>2: continue
        for _j in _js:
            if _j==_i: continue
            _a2=_N(IW[_j].get('author'))
            if not _a2: continue
            if _a2!=_au and _a2 not in _au and _au not in _a2: continue
            _dupt.add((min(_i,_j),max(_i,_j)))
print('題名重出（長題＝撰人＋短題，撰人相容）',len(_dupt),'　基線 70（2026-08-08 batch16 連書省撰人合併消解其中 2 組）')
for _a,_b in sorted(_dupt)[:6]:
    print(f"   《{IW[_a].get('title')}》({IW[_a].get('author')}) ←→ 《{IW[_b].get('title')}》({IW[_b].get('author')})")

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
secmag=_c.Counter(); secmag_ex=[]; secpart=_c.Counter()
for f in glob.glob('Work/*/*/*/*/collated_edition/*.json'):
    if f.endswith('collated_edition_index.json'): continue
    try: cd=json.load(open(f))
    except Exception: continue
    if not isinstance(cd,dict): continue
    own=f.split('/')[4]; m=_c.defaultdict(set)
    for sec in cd.get('sections',[]):
        if not isinstance(sec,dict): continue
        # 版本附屬部帙（外集、附錄之屬）依 SCHEMA 不別立 Work，本就與母條共繫，非磁鐵
        if sec.get('section_kind')=='附屬部帙': secpart[own]+=1; continue
        w=sec.get('work_id')
        if isinstance(w,str) and w in IW and sec.get('title'): m[w].add(_nz(sec['title']))
    for w,ts in m.items():
        if len(ts)>1:
            secmag[own]+=len(ts)
            if len(secmag_ex)<6: secmag_ex.append((own,w,IW[w]['title'],sorted(ts)[:4]))
print('整理本 section 級磁鐵（異題共指一 work 之題數）',sum(secmag.values()),
      '　附屬部帙節（依 SCHEMA 與母條共繫，不計）',sum(secpart.values()))
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

# 簡轉繁之過度轉換（over-conversion）
# 立此驗之由：析隋志注中亡書時撰人析出「幹寶」「硃育」「釧會」，覆按乃知某幾批匯入
# 之文本是由簡體回轉而來，一簡對多繁未擇而誤。此類欄位有值、非空、不觸發任何校驗，
# 而比對時永不相合，於是同書被判成「本庫沒有」而重建一遍——與「殘名撰人」同族之靜默缺陷。
# 只驗確係誤者。多數用例是對的，不可一律回轉：
#   洪範／師範大學／範圍／軌範——當作範；　徐幹／黃幹／張元幹——當作幹；
#   硃批（四庫之硃批）——本字；　毫髮／鬚髮／晞髮集——當作髮；
#   瞭若指掌／明瞭、纔、薝蔔——皆本字。故此處列詞不列字。
# 幹：徐幹、公幹、黃幹、張元幹、幹辦、才幹、幹羽皆本字，只此數詞誤
_OVER = ('幹寶', '幹子', '幹祿', '幹鑿', '十幹', '餘幹', '釧會', '鬆', '錶',
         '捲髮明', '髮微', '麵部訣', '馬麵法式', '氣色麵圖')
# 範／范：不列詞而立位置之判——範居姓位者誤，居名位者不誤。
# 姓位之判準：其前一字是界（引號、書名號、頓逗句號、括弧、空白、「案」）。
# 如此則「案范書」「《范泰集》」「"范德機"」皆得，而洪範、師範大學、桓範集、
# 陳祖範撰、帝範、家範、軌範、懿範皆不動——前一字非界故也。
_BOUND = set('"《「『、，。；：（）〔〕[]{}〈〉!?\n\t \u3000\'') | set('】》案')
# 官爵之後亦是姓位（「安北將軍范汪」「臨淮太守范作」），界判收不到，故並驗
_OFF2 = ('將軍', '太守', '刺史', '尚書', '侍郎', '議郎', '中郎', '參軍', '司馬',
         '長史', '郎中', '縣令', '太尉', '司徒', '司空', '僕射', '祭酒', '博士',
         '別駕', '從事', '校尉', '主簿', '舍人', '內史', '大夫', '常侍', '侍中',
         '中書', '學士', '給事', '功曹', '太常', '光祿', '諮議')
_KEEP2 = {'範圍', '範式', '範例', '範疇', '範金', '範土', '範銅', '範模'}
_ovc = _c.Counter()
_FILES = (glob.glob('Work/*/*/*/*.json') + glob.glob('Book/*/*/*/*.json')
          + glob.glob('Entity/*/*/*/*.json') + glob.glob('Collection/*/*/*/*.json')
          + glob.glob('Work/*/*/*/*/fragments/*.json')
          + glob.glob('Work/*/*/*/*/collated_edition/*.json')
          + glob.glob('index/*.json') + glob.glob('index/*/*.json'))
for _f in _FILES:
    try:
        _raw = open(_f).read()
    except Exception:
        continue
    for _w in _OVER:
        _n = _raw.count(_w)
        if _n:
            _ovc[_w] += _n
    # 硃須去其本字之用例（硃批之屬）而後計
    if '硃' in _raw:
        _t = _raw
        for _k in ('硃批', '硃墨', '硃筆', '硃砂', '硃卷', '硃絲', '硃書', '硃印', '硃點', '硃提'):
            _t = _t.replace(_k, '')
        if _t.count('硃'):
            _ovc['硃'] += _t.count('硃')
    for _i, _ch in enumerate(_raw):
        if _ch == '範' and _raw[_i:_i + 2] not in _KEEP2 \
                and ((_raw[_i - 1] if _i else '\n') in _BOUND
                     or _raw[max(0, _i - 2):_i] in _OFF2):
            _ovc['範（居姓位）'] += 1
print('簡轉繁過度轉換', sum(_ovc.values()), '　基線 0')
for _k, _v in _ovc.most_common(8):
    print('  ', _k, _v)

# period 之枚舉，並與索引對查
_PER = ('pre-qin', 'qin-han', 'three-kingdoms', 'jin', 'nanbeichao', 'sui-tang',
        'five-dynasties', 'song', 'liao-jin-yuan', 'ming', 'qing', 'modern')
_pbad = []
_pc = _c.Counter()
for _p in glob.glob('Work/*/*/*/*.json'):
    try:
        _d = json.load(open(_p))
    except Exception:
        continue
    _v = _d.get('period')
    if _v is None:
        _pc[None] += 1
        continue
    _pc[_v] += 1
    if _v not in _PER:
        _pbad.append((_d.get('id'), 'period 不合枚舉', _v))
    # 有 period 必有 period_basis——此軸是本庫之判，無據則不可用
    if not _d.get('period_basis'):
        _pbad.append((_d.get('id'), 'period 無 period_basis', _v))
    _e = IW.get(_d.get('id'))
    if _e is not None and _e.get('period') != _v:
        _pbad.append((_d.get('id'), '索引 period 不符', f"{_e.get('period')}≠{_v}"))
print('period', dict(_pc), '不合', len(_pbad), '　基線 0')
for _x in _pbad[:8]:
    print('  ', _x)

# JSON 書寫格式護欄（見 SCHEMA.md〈JSON 書寫格式〉、.claude/plans/升格並行方案.md §六）
# 格式不一致是並行時最大的機械衝突源：任一工具以自己的縮排整檔重寫，
# 就把「可自動合併的行級改動」變成「整檔衝突」。約定：indent=2、檔尾一換行、
# 鍵序不重排（索引檔另須按 id 有序）。修法：scripts/normalize_json_format.py
_JIND, _JNL, _JORD = [], [], []
for _p in glob.glob('**/*.json', recursive=True):
    if _p.startswith(('node_modules', 'book-index/', '.claude/', '.git/')):
        continue
    try:
        _raw = open(_p, encoding='utf-8').read()
    except Exception:
        continue
    if not _raw.strip():
        continue
    for _ln in _raw.split('\n')[1:]:
        _m = _re.match(r'^( +)\S', _ln)
        if _m:
            if len(_m.group(1)) != 2:
                _JIND.append((_p, len(_m.group(1))))
            break
    if not _raw.endswith('\n'):
        _JNL.append(_p)
    if _p.startswith('index/'):
        try:
            _k = list(json.loads(_raw).keys())
            if _k != sorted(_k):
                _JORD.append((_p, len(_k)))
        except Exception:
            pass
print('JSON 縮排非 2', len(_JIND), '　基線 0（2026-08-21 全庫歸一化竣工；'
      '不為零即有工具用了別的縮排，修法：scripts/normalize_json_format.py）')
for _x in _JIND[:5]:
    print('  ', _x)
print('JSON 缺檔尾換行', len(_JNL), '　基線 0（同上）')
print('索引檔鍵未按 id 排序', len(_JORD), '　基線 0')
for _x in _JORD[:5]:
    print('  ', _x)
