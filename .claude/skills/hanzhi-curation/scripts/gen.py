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
_seq={'n':0}
def newid(kind):
    ts=int(time.time()*1000)&((1<<40)-1)
    _seq['n']+=1
    return enc((1<<62)|(TYPE[kind]<<59)|(ts<<19)|(1<<8)|(_seq['n']%256))
def load_idx(kind):
    if kind=='collection': return json.load(open('index/collections.json'))
    d={}
    for s in '0123456789abcdef': d.update(json.load(open(f'index/{kind}s/{s}.json')))
    return d
def put_idx(kind,entry):
    i=entry['id']
    if kind=='collection':
        p='index/collections.json'; x=json.load(open(p)); x[i]=entry
        json.dump(x,open(p,'w'),ensure_ascii=False,indent=2); return
    p=f'index/{kind}s/{shard(i)}.json'; x=json.load(open(p)); x[i]=entry
    json.dump(x,open(p,'w'),ensure_ascii=False,indent=2)
def wpath(i,t): return f'Work/{i[0]}/{i[1]}/{i[2]}/{i}-{t}.json'
def bpath(i,t): return f'Book/{i[0]}/{i[1]}/{i[2]}/{i}-{t}.json'
def cpath(i,t): return f'Collection/{i[0]}/{i[1]}/{i[2]}/{i}-{t}.json'
def save(p,d):
    os.makedirs(os.path.dirname(p),exist_ok=True)
    json.dump(d,open(p,'w'),ensure_ascii=False,indent=2)
