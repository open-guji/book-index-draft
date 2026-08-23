#!/usr/bin/env python3
"""《經義考》未匯入之 6,523 條分流

輸入 `.claude/known-issues/經義考待裁.json`（解析所得之條目），
輸出同檔，逐條加 tier／era_bracket／era_lo／era_hi／same_author_sub 五欄。

── 分流之二軸 ──────────────────────────────────────────────
軸一．庫中已有其書否
  以題名歸一後比對 index/works。歸一之序須守：先剔校語括號（「周易注（或
  作傳）」之「或作傳」是朱氏校語非題名之部分），次異體歸一，**最後**才
  OpenCC t2s——次序倒置則異體表不發火（見 SCHEMA〈簡繁歸一之序〉）。
  只作全等比對，不作子串比對；子串另以「撰人相同」為閘（見下）。

軸二．時代
  《經義考》各類之內以撰人時代為序，然一類之中屢有分段（如易類卷七十一
  另起「太極圖」一系，自北宋周敦頤重排至明清）。故不可以整類作一序列，
  須先分段：以庫中已知朝代之撰人為錨，錨值較本段已達之最高值低四階以上
  者，判為新段之始。段內以錨之遞增包絡（running max）夾出每條之上下界。

  **此二界只作分流之用，不得寫入 period。** 留一驗證：錨 2,024，能判者
  1,808，準確率 0.9646（誤 64：≤元誤判明清 52，明清誤判≤元 12）。定代仍
  須逐條依《經義考》本文所引之志與撰人本傳，一如庫規「朝代不推，只取有
  據者」。

── 甲2 之閘 ────────────────────────────────────────────────
題名全等不中，而撰人相同且兩題互為子串者，判為同書（「易洞林」對「周易
洞林」、「周易注」對「漢宋衷周易注」）。單靠子串必濫（「五經」對「五經
要略」），故必以撰人相同為前提。
"""
import json, glob, collections, re, sys, bisect, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from magnet_lib import VARIANT
import opencc

T2S = opencc.OpenCC('t2s')
# 《經義考》文淵閣本用字，VARIANT 未收者。
# 下半是人名之異體——初版漏收，致焦延壽（夀）、施讎（讐）、陸德明（徳）、程頤
# （頥）、曾穜（曽）一輩明明在庫中之人被判成「庫中無此書」而幾乎重建一遍。
# 只收純字形之異；避諱之改（元／玄、正／貞、丘／邱）不入此表——那不是字形之
# 事，同人之疑雖大，仍當逐條裁。
EXTRA = str.maketrans({'叅': '參', '刋': '刊', '𤣥': '玄', '恱': '悅', '厯': '歷',
                       '歴': '歷', '録': '錄', '説': '說', '别': '別', '踈': '疏',
                       '亰': '京', '鳯': '鳳', '徴': '徵', '灾': '災', '𢎞': '弘',
                       '竒': '奇', '徳': '德', '呉': '吳', '曽': '曾', '夀': '壽',
                       '濓': '濂', '寳': '寶', '髙': '高', '澂': '澄', '𦙍': '胤',
                       '凖': '準', '頥': '頤', '䝉': '蒙', '彛': '彝', '彞': '彝',
                       '熈': '熙', '纉': '纘', '挍': '校', '寗': '寧', '廸': '迪',
                       '寛': '寬', '隂': '陰', '飬': '養', '祗': '祇', '讐': '讎',
                       '苖': '苗', '隚': '鏜', '蘓': '蘇', '沉': '沈', '禇': '褚',
                       '潁': '穎', '夣': '夢', '槩': '概'})

ORD = {'西漢': 1, '漢': 1, '東漢': 2, '三國魏': 3, '三國吳': 3, '三國蜀': 3,
       '西晉': 4, '晉': 4, '東晉': 5, '前涼': 5, '南朝宋': 6, '南朝齊': 6,
       '南朝梁': 6, '南朝陳': 6, '齊': 6, '北魏': 6, '北齊': 6, '北周': 6,
       '南北朝': 6, '隋': 7, '隋唐': 7, '唐': 8, '五代': 9, '北宋': 10, '宋': 10,
       '遼': 10, '南宋': 11, '金': 11, '宋末元初': 12, '元': 12,
       '元末明初': 13, '明': 14, '明末清初': 15, '清': 16}
ORDNAME = {0: '?', 1: '西漢', 2: '東漢', 3: '三國', 4: '晉', 5: '東晉', 6: '南北朝',
           7: '隋', 8: '唐', 9: '五代', 10: '北宋', 11: '南宋金', 12: '元',
           13: '元末明初', 14: '明', 15: '明末清初', 16: '清', 99: '?'}
CIT = ['漢志', '七略', '七畧', '别録', '別錄', '隋志', '唐志', '宋志', '七録',
       '七錄', '通志', '崇文總目', '中興書目', '書録解題', '讀書志', '文獻通考',
       '國史志', '館閣書目']
CUT = 12          # 元 及其前為「≤元」
RESET = 4         # 段之界：低於本段最高階四階以上

DATA = '.claude/known-issues/經義考待裁.json'


def nz(t):
    """題名／人名歸一：剔校語括號 → 剔標點 → 異體歸一 → t2s"""
    t = re.sub(r'（[^）]*）|\([^)]*\)', '', t or '')
    t = re.sub(r'[《》〈〉\s、，。]', '', t)
    return T2S.convert(t.translate(VARIANT).translate(EXTRA))


def load_index(sub):
    out = {}
    for f in glob.glob(f'index/{sub}/*.json'):
        out.update(json.load(open(f)))
    return out


def embedded_author(jt, ja, by_author):
    """庫題以「經名＋撰人＋役」立題者，撰人之名嵌於題中，既非全等亦不互為
    子串（《周易董遇注》對《周易注》）。剔去其名（或姓）後再比，容尾綴之
    「撰」「著」，並容字序之異（《周易朱異集注》對《集注周易》）。
    此閘是 2026-08-23 補立——初版無之，遂有三十一條重建為重出。"""
    if not ja or len(jt) < 2:
        return []
    out = []
    for w in by_author.get(ja, []):
        lt = nz(w.get('title'))
        for name in (ja, ja[:2], ja[:1]):
            if not name or name not in lt:
                continue
            r = re.sub(r'(撰|著)$', '', lt.replace(name, '', 1))
            if r == jt or sorted(r) == sorted(jt):
                out.append(w)
            break
    return out


def segment(seq):
    """依錨之驟降切段，回傳每段之 index 列"""
    out, cur, mx = [], [], 0
    for j, d in enumerate(seq):
        o = d['_o']
        if o is not None and mx - o >= RESET:
            out.append(cur); cur = []; mx = 0
        cur.append(j)
        if o is not None:
            mx = max(mx, o)
    out.append(cur)
    return out


def main():
    works = load_index('works')
    ents = load_index('entities')

    dyn_of = collections.defaultdict(set)
    for v in ents.values():
        if v.get('dynasty'):
            dyn_of[v['primary_name']].add(v['dynasty'])

    by_title = collections.defaultdict(list)
    by_author = collections.defaultdict(list)
    for v in works.values():
        by_title[nz(v.get('title'))].append(v)
        if v.get('author'):
            by_author[nz(v['author'])].append(v)

    D = json.load(open(DATA))

    # ── 時代：錨 ──
    for d in D:
        ds = dyn_of.get(d.get('author')) or set()
        d['_o'] = ORD[next(iter(ds))] if len(ds) == 1 and next(iter(ds)) in ORD else None

    for lei in sorted({d['lei'] for d in D}):
        seq = [d for d in D if d['lei'] == lei]
        for s in segment(seq):
            pts = [(j, seq[j]['_o']) for j in s if seq[j]['_o'] is not None]
            ai = [p[0] for p in pts]
            av = [p[1] for p in pts]
            for k in range(1, len(av)):
                av[k] = max(av[k], av[k - 1])      # 遞增包絡
            for j in s:
                k = bisect.bisect_left(ai, j)
                lo = av[k - 1] if k > 0 else 0
                hi = av[k] if k < len(av) else 99
                if k < len(av) and ai[k] == j:
                    lo = hi = av[k]
                seq[j]['_lo'], seq[j]['_hi'] = lo, hi

    # ── 分流 ──
    for d in D:
        era = '≤元' if d['_hi'] <= CUT else ('明清' if d['_lo'] > CUT else '跨界')
        ja, jt = nz(d.get('author')), nz(d.get('title'))
        cands = by_title.get(jt, [])
        cas = [nz(x.get('author')) for x in cands]
        sub = []
        if ja and len(jt) >= 2:
            sub = [x for x in by_author.get(ja, [])
                   if jt in nz(x['title']) or nz(x['title']) in jt]

        if cands and ja and ja in cas:
            tier = '甲1'                      # 題撰俱合
        elif cands and not (ja and any(cas)):
            tier = '甲3'                      # 題合而一方闕撰人——待逐條裁
        elif sub:
            tier = '甲2'                      # 撰人同、題互子串
        elif embedded_author(jt, ja, by_author):
            tier = '甲4'                      # 撰人同、其名嵌於庫題之中
            sub = embedded_author(jt, ja, by_author)
        else:
            # 題合而撰人俱有且不同者亦落此——依《SCHEMA》同題異撰是二書，當新建
            has_cit = any(c in ''.join(d['attest'] or []) for c in CIT)
            tier = ('乙' if era != '明清' else '丙') + ('1' if has_cit else '2')

        d['tier'] = tier
        d['era_bracket'] = era
        d['era_lo'] = ORDNAME.get(d['_lo'], '?')
        d['era_hi'] = ORDNAME.get(d['_hi'], '?')
        if sub:
            d['same_author_sub'] = [(x['id'], x['title'], x.get('dynasty')) for x in sub[:3]]
        for k in ('_o', '_lo', '_hi'):
            d.pop(k, None)

    json.dump(D, open(DATA, 'w'), ensure_ascii=False, indent=1)
    c = collections.Counter(d['tier'] for d in D)
    for t in ['甲1', '甲2', '甲3', '甲4', '乙1', '乙2', '丙1', '丙2']:
        print(f'{t} {c[t]:5d}')
    print('合計', len(D))


if __name__ == '__main__':
    main()
