# -*- coding: utf-8 -*-
# HBCC 對比之一：逐目比對（見 .claude/plans/HBCC對比-20260826.md）
# 用法：SP=<輸出目錄> python3 scripts/hbcc_cmp.py <本庫之來源書目名>
# 需 open-guji/pku-hbcc-data clone 於 /home/user/pku-hbcc-data
# -*- coding: utf-8 -*-
"""逐目比對：HBCC 之著錄 vs 本庫之 indexed_by。以書名（正規化後）為鍵。"""
import json,glob,re,sys,collections,os
sys.path.insert(0,'/home/user/pku-hbcc-data/scripts/hbcc')
import parse as hp
H='/home/user/pku-hbcc-data/data/hbcc/harvest_export/records/'

# 本庫之名 → (HBCC 之名, entryId 前綴群)
MAP={
 '漢書藝文志':('漢書 • 藝文志',['10006016']),
 '隋書經籍志':('隋書 • 經籍志',['10008018']),
 '舊唐書經籍志':('舊唐書 • 經籍志',['10010020']),
 '新唐書藝文志':('新唐書·藝文志',['10012021']),
 '宋史藝文志':('宋史·藝文志',['10014022']),
 '明史藝文志':('明史 • 藝文志',['10016023']),
 '清史稿藝文志':('清史稿 • 藝文志',['10018024']),
 '元史藝文志':('元史藝文志',['10068073']),
 '補晋書藝文志':('補晉書藝文志',['10066071']),
 '三國藝文志':('三國藝文志',['10062067']),
 '後漢藝文志':('補後漢書藝文志并考',['10064069']),
 '崇文總目':('崇文總目',['10056061']),
 '直齋書錄解題':('直齋書錄解題',['10050055']),
 '欽定四庫全書總目':('四庫總目提要',['10004014']),
}

CN='〇一二三四五六七八九十百千零壹貳參叁肆伍陸柒捌玖拾佰仟兩两'
DEL=re.compile(r'[《》〈〉「」『』（）()\[\]【】·・•‧∙・．.,，、。：:；;？?！!\s　“”"\'’‘\-—－_～~*#〔〕]')
# 常見異體歸一（只取確鑿無疑者）
VAR=str.maketrans({
 '硏':'研','畧':'略','菉':'錄','録':'錄','刋':'刊','敍':'敘','敕':'勅','鬬':'鬥','鬭':'鬥',
 '踈':'疏','䟽':'疏','疎':'疏','羣':'群','徧':'遍','冊':'册','卻':'却','裏':'裡','牀':'床',
 '衞':'衛','靑':'青','眞':'真','幷':'并','並':'并','爲':'為','虛':'虚','戶':'户','戸':'户',
 '槪':'概','敎':'教','說':'説','溫':'温','俱':'俱','琁':'璇','璿':'璇','鈔':'抄','曆':'歷',
 '厤':'歷','歴':'歷','経':'經','蹟':'跡','迹':'跡','菴':'庵','峯':'峰','讚':'贊','絃':'弦',
 '筭':'算','喦':'岩','巖':'岩','嵓':'岩','緫':'總','総':'總','攷':'考','敝':'弊','冑':'胄',
})
JUAN=re.compile(r'[一二三四五六七八九十百千零〇兩两0-9]+[卷篇帙冊册部通首章]$')

def norm(t):
    if not t: return ''
    t=t.translate(VAR)
    t=DEL.sub('',t)
    # 去尾之卷數
    for _ in range(3):
        m=JUAN.search(t)
        if m and m.start()>0: t=t[:m.start()]
        else: break
    return t

def hbcc(prefixes):
    out=collections.Counter(); rows=[]
    for pre in prefixes:
        for f in sorted(glob.glob(H+pre+'-*.tsv')):
            with open(f,encoding='utf-8') as fh:
                next(fh)
                for line in fh:
                    a=line.rstrip('\n').split('\t')
                    if len(a)<4: continue
                    r=hp.parse(a[3])
                    n=norm(r['書名'])
                    if n: out[n]+=1; rows.append((a[0],a[1],r['書名'],r['卷數'],a[3]))
    return out,rows

def ours(src):
    out=collections.Counter(); rows=[]
    for root in ['.','../book-index']:
        for p in glob.glob(root+'/Work/*/*/*/*.json'):
            d=json.load(open(p))
            if d.get('_promoted_to'): continue
            for s in (d.get('indexed_by') or []):
                if s.get('source')!=src: continue
                # 以 title_info 為主，闕則用 work 之 title
                # 一節可有數鑰：work 之 title（本庫所考定之正題）與著錄原文之 title_info。
                # 本庫之 title_info 各志體例不一——明志、後漢志、三國志把撰人前置，
                # 三國志更把按語一併收入——故不可專恃其一。
                keys=set()
                for t in (d.get('title'), s.get('title_info')):
                    if not t: continue
                    n=norm(t)
                    if n: keys.add(n)
                    # 撰人前置之式：去首段（至《》之前，或首個空格之前）再取一鑰
                    m=re.match(r'^[^《》]{1,8}《([^》]+)》', t or '')
                    if m: keys.add(norm(m.group(1)))
                    if ' ' in (t or ''):
                        keys.add(norm(t.split(' ',1)[1]))
                if keys: out[frozenset(keys)]+=1; rows.append((d['id'],d.get('title'),s.get('title_info'),keys))
    return out,rows

if __name__=='__main__':
    src=sys.argv[1]
    hn,hpre=MAP[src]
    HC,HR=hbcc(hpre); OC,OR=ours(src)
    okeys=set()
    for ks in OC: okeys |= set(ks)
    only_h={k:v for k,v in HC.items() if k not in okeys}
    only_o=collections.Counter()
    for ks,v in OC.items():
        if not (ks & set(HC)): only_o[sorted(ks)[0]]+=v
    both=set(HC)&okeys
    print(f'== {src} ↔ {hn} ==')
    print(f'  HBCC 條 {sum(HC.values())}（相異名 {len(HC)}）　本庫節 {sum(OC.values())}（相異鑰組 {len(OC)}）')
    print(f'  名相合 {len(both)}　HBCC 獨有 {len(only_h)} 名 / {sum(only_h.values())} 條　'
          f'本庫獨有 {len(only_o)} 名 / {sum(only_o.values())} 節')
    json.dump({'only_hbcc':sorted(only_h.items(),key=lambda x:-x[1]),
               'only_ours':sorted(only_o.items(),key=lambda x:-x[1])},
              open(os.environ['SP']+'/diff-%s.json'%src,'w'),ensure_ascii=False,indent=1)
    print('  HBCC 獨有（前 25）：',[k for k,_ in sorted(only_h.items(),key=lambda x:-x[1])][:25])
    print('  本庫獨有（前 25）：',[k for k,_ in sorted(only_o.items(),key=lambda x:-x[1])][:25])
