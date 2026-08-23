# -*- coding: utf-8 -*-
"""A 車道開工普查：時代逾限錯掛 ＋ section→work 反向著錄缺口 ＋ 真落空。

用法：在庫根目錄執行
    python3 .claude/skills/hanzhi-curation/scripts/lane_audit.py            # 全部
    python3 .claude/skills/hanzhi-curation/scripts/lane_audit.py A8         # 只跑一條車道
    python3 .claude/skills/hanzhi-curation/scripts/lane_audit.py A8 --list  # 並列出每一條

何以要有這二檢查、次序何以不可顛倒，見
`.claude/known-issues/A各車道-時代逾限與反向缺口普查.md`。要點三句：

1. `chk.py` 的磁鐵只查「同檔內異題共指一 work」，**一節獨自錯掛查不出來**。
2. 逾限查跨代同名，反向缺口查同代同名，二者各查得對方查不到的。
3. **補反向著錄之前必先過逾限這一關**——否則就把錯繫寫死成 `indexed_by`。
"""
import json,glob,os,sys,collections

ROOT='.'
def _idx(kind):
    d={}
    for s in '0123456789abcdef':
        d.update(json.load(open(f'{ROOT}/index/{kind}/{s}.json',encoding='utf-8')))
    return d
IW=_idx('works')
_PR=json.load(open(f'{ROOT}/promotions.json',encoding='utf-8'))['promotions']
PROD={v['production_id'] for v in _PR.values()}
D2P={k:v['production_id'] for k,v in _PR.items()}

ORDER=['pre-qin','qin-han','three-kingdoms','jin','nanbeichao','sui-tang',
       'five-dynasties','song','liao-jin-yuan','ming','qing','modern']
def _late(after):
    """該志所著錄之書不得晚於 after 代；回傳「逾限」之 period 集合。"""
    return set(ORDER[ORDER.index(after)+1:])

# 車道 → [(整理本 id, 名, 時代下限)]
LANES={
 'A1' :[('1ev3bb4qxubr4','國史經籍志',      'ming')],
 'A2' :[('1eujf2fs4v280','欽定四庫全書總目','qing'),
        ('1evjxczyavy80','四庫全書存目叢書','qing')],
 'A3' :[('1evcsw4kt579c','宋史藝文志',      'song')],
 'A4' :[('1evdiulq07rwg','清史稿藝文志',    'qing')],
 'A5' :[('1evjk1whvmznk','續修四庫全書',    'modern')],
 'A6' :[('1evcs059gkvls','新唐書藝文志',    'five-dynasties'),
        ('1evcpbhmiqdj4','舊唐書經籍志',    'five-dynasties')],
 'A7' :[('1ev88ee9jw6ps','明史藝文志',      'ming')],
 'A8' :[('1ev3bb403quio','直齋書錄解題',    'song'),
        ('1ev3bb3xyygw0','崇文總目',        'song')],
 'A9' :[('1ev85yncs9ibk','隋書經籍志',      'sui-tang'),
        ('1evfu57n5n37k','補晉書藝文志',    'sui-tang')],
 'A10':[('1eve1ek8wcnb4','元史藝文志',      'liao-jin-yuan'),
        ('1eve1ek5qq9kw','補遼金元藝文志',  'liao-jin-yuan'),
        ('1evgeo1zzls74','中國通俗小說書目','qing')],
}

# 選本與輯佚叢書：其 section 是「篇章」而非「著錄」，本就不該回寫 indexed_by。
# 反向缺口一律不計。判準是「該整理本之節全數皆缺」，下列為 2026-08-23 實測所得。
ANTHOLOGY={'1evjr68pzxog0','1evhnqciqrwu8','1evi5uod20l4w',
           '1evha3f4fpqf4','1evhmcmmhp2bk','1evi6d00q8zr4'}

_cache={}
def _work(p):
    if p not in _cache:
        try: _cache[p]=json.load(open(p,encoding='utf-8'))
        except Exception: _cache[p]={}
    return _cache[p]

def audit(src,late_after):
    LATE=_late(late_after); SB={src,D2P.get(src)}
    r={'tot':0,'gap':[],'late':[],'dang':[],'promo':0}
    for f in sorted(glob.glob(f'{ROOT}/Work/*/*/*/{src}/collated_edition/*.json')):
        if f.endswith('collated_edition_index.json'): continue
        try: cd=json.load(open(f,encoding='utf-8'))
        except Exception: continue
        if not isinstance(cd,dict): continue
        cat=os.path.basename(f)[:-5]
        for i,sec in enumerate(cd.get('sections',[])):
            if not isinstance(sec,dict): continue
            w=sec.get('work_id')
            if not isinstance(w,str): continue
            if w not in IW:
                if w in PROD: r['promo']+=1
                else: r['dang'].append((cat,i,sec.get('title'),w))
                continue
            r['tot']+=1
            d=_work(IW[w]['path'])
            if src not in ANTHOLOGY and not any(
                    y.get('source_bid') in SB
                    for y in (d.get('emendated_by') or [])+(d.get('indexed_by') or [])):
                r['gap'].append((cat,i,sec.get('title'),w,IW[w].get('title'),IW[w].get('author')))
            if d.get('period') in LATE:
                r['late'].append((cat,i,sec.get('title'),(sec.get('content') or '')[:60],
                                  w,IW[w].get('title'),IW[w].get('author'),d.get('period')))
    return r

if __name__=='__main__':
    args=[a for a in sys.argv[1:] if not a.startswith('--')]
    show='--list' in sys.argv
    lanes=args or sorted(LANES,key=lambda x:(len(x),x))
    print(f"{'車道':<5}{'志':<18}{'節':>7}{'反向缺口':>9}{'逾限':>7}{'真落空':>8}{'production':>12}")
    for lane in lanes:
        for src,name,after in LANES[lane]:
            r=audit(src,after)
            mark=' （選本，反向缺口不計）' if src in ANTHOLOGY else ''
            print(f"{lane:<5}{name:<18}{r['tot']:>7}{len(r['gap']):>9}{len(r['late']):>7}"
                  f"{len(r['dang']):>8}{r['promo']:>12}{mark}")
            if show:
                for x in r['late']:
                    print(f"    [逾限] ({x[0]}#{x[1]}) {x[2]} ‖ {x[3]}")
                    print(f"           → 《{x[5]}》{x[6]} period={x[7]}  {x[4]}")
                for x in r['gap']:
                    print(f"    [缺口] ({x[0]}#{x[1]}) {x[2]} → 《{x[4]}》{x[5]}  {x[3]}")
                for x in r['dang']:
                    print(f"    [落空] ({x[0]}#{x[1]}) {x[2]}  {x[3]}")
