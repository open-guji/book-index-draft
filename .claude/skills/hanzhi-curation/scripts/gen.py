import json,time,os
A="0123456789abcdefghijklmnopqrstuvwxyz"
def enc(v):
    o=""
    while v: o=A[v%36]+o; v//=36
    return o
def shard(i):
    h=0
    for c in i: h=((h*31)+ord(c))&0xFFFFFFFF
    return '%x'%(h%16)
TYPE={'book':0,'collection':2,'work':3,'entity':4}
# 索引目錄名不是一律加 s：entity 的目錄是 index/entities（曾因此寫成 index/entitys 而 FileNotFoundError）
DIR={'book':'books','collection':'collections','work':'works','entity':'entities'}
# 索引分片之縮排：全庫一律 2（2026-08-21 歸一化竣工，`chk.py`「JSON 縮排非 2」基線 0）。
# 此處原寫 works:1，與實庫不符——用之則整片重排，基線立破且生萬行假 diff。
# 2026-08-23 A9 實測 index/works/*.json 為 indent=2 而訂正。
IND={'books':2,'collections':2,'works':2,'entities':2}
_seq={'n':0}
def newid(kind):
    ts=int(time.time()*1000)&((1<<40)-1)
    _seq['n']+=1
    return enc((1<<62)|(TYPE[kind]<<59)|(ts<<19)|(1<<8)|(_seq['n']%256))
def load_idx(kind):
    if kind=='collection': return json.load(open('index/collections.json'))
    d={}
    for s in '0123456789abcdef': d.update(json.load(open(f'index/{DIR[kind]}/{s}.json')))
    return d
def put_idx(kind,entry):
    # 鍵序須按 id（`chk.py`「索引檔鍵未按 id 排序」基線 0）——dict 是插入序，
    # 新 id 直接附在尾端多半就不合序，故寫入前一律重排。
    i=entry['id']
    if kind=='collection':
        p='index/collections.json'; x=json.load(open(p)); x[i]=entry
        with open(p,'w') as f:
            json.dump({k:x[k] for k in sorted(x)},f,ensure_ascii=False,indent=2); f.write('\n')
        return
    d=DIR[kind]
    p=f'index/{d}/{shard(i)}.json'; x=json.load(open(p)); x[i]=entry
    with open(p,'w') as f:
        json.dump({k:x[k] for k in sorted(x)},f,ensure_ascii=False,indent=IND[d]); f.write('\n')
def wpath(i,t): return f'Work/{i[0]}/{i[1]}/{i[2]}/{i}-{t}.json'
def bpath(i,t): return f'Book/{i[0]}/{i[1]}/{i[2]}/{i}-{t}.json'
def cpath(i,t): return f'Collection/{i[0]}/{i[1]}/{i[2]}/{i}-{t}.json'
def epath(i,t): return f'Entity/{i[0]}/{i[1]}/{i[2]}/{i}-{t}.json'
def save(p,d):
    # 檔尾一換行是硬約定（`chk.py`「JSON 缺檔尾換行」基線 0）；原本漏寫。
    os.makedirs(os.path.dirname(p),exist_ok=True)
    with open(p,'w') as f:
        json.dump(d,f,ensure_ascii=False,indent=2); f.write('\n')
