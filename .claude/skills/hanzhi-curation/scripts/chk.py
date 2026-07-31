"""校驗電池：每批整理之後必跑，比對基線數字。
用法：在庫根目錄執行 python3 .claude/skills/hanzhi-curation/scripts/chk.py"""
import json,os,glob
def li(k):
    d={}
    for s in '0123456789abcdef': d.update(json.load(open(f'index/{k}s/{s}.json')))
    return d
IW,IB=li('work'),li('book'); IC=json.load(open('index/collections.json'))
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
ow=[(b,w) for b,w in b2w.items() if w not in w2b.get(b,set())]
ww=[(b,s) for b,s in w2b.items() if b not in b2w]
print('Book→Work 單向',len(ow),' Work→Book 對方無 work_id',len(ww))
