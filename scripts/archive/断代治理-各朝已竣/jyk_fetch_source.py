#!/usr/bin/env python3
"""重取《經義考》原文，並補回前次解析所棄之「論斷」

**立此之由**：`經義考待裁.json` 之 `first_note` 只存二三十字，是截斷之餘。
覆按 kanripo 原文乃知，朱彝尊於每條之下所輯諸家論斷（劉歆曰、荀勗曰、崇文
總目、國史志、中興書目、唐會要……）動輒數百字，最長者一萬五千餘字，前次
一概棄去。此輩正是「庫中無此書、志亦不著」之條僅有的憑據——

  《學易說約》本無撰人，而論斷引《閩書》曰「丘富國字行可建安人……著周易
  輯解十卷、易學說約五篇」——撰人、里貫、時代俱在其中。
  《九經發題》本無撰人，而論斷引《先民錄》曰「唐仲友字與政金華人……紹興
  辛未進士」——同上。

故重取原文，全存其論斷，另出 `經義考論斷.json`（以頁次＋標目為鍵）。

**原文之體例**：縮排即層——0 條目首行／2 著錄／3 存佚／1 論斷／4 按語。
卷首另有一行縮排三格者，是本卷之**類**（「易(四/)」「鏤板」「著録」），在首條
之前，非某條之存佚；前次解析誤入存佚而棄，今別出為 `lei`。
行末之 `¶` 是原文換行符，一條論斷屢跨數行（並跨半葉），故同層之連行當並為
一段。標目中之 `(名/)` 是夾注之式，歸一為 `（名）` 方與 `經義考待裁.json`
之標目相合。
"""
import os, re, glob, json, subprocess, sys

RAW = os.environ.get('JYK_RAW', 'build/kr2n0011')
BASE = 'https://raw.githubusercontent.com/kanripo/KR2n0011/master'
OUT = '.claude/known-issues/經義考論斷.json'


def fetch():
    os.makedirs(RAW, exist_ok=True)
    got = miss = 0
    for i in range(1, 301):
        f = f'{RAW}/KR2n0011_{i:03d}.txt'
        if os.path.exists(f) and os.path.getsize(f):
            got += 1
            continue
        r = subprocess.run(['curl', '-sS', '-m', '60', '-o', f, '-w', '%{http_code}',
                            f'{BASE}/KR2n0011_{i:03d}.txt'], capture_output=True, text=True)
        if r.stdout.strip() == '200':
            got += 1
        else:
            os.path.exists(f) and os.remove(f)
            miss += 1
    print(f'原文 {got} 卷，缺 {miss}')


def norm_text(h):
    """原文歸一：kanripo 以 `(前半/後半)` 記雙行夾注，`/` 是分欄之號非文字，
    去之而括號歸全形——`公孫氏(叚/)` → `公孫氏（叚）`，
    `(七録二十四卷/目録一卷)` → `（七録二十四卷目録一卷）`。"""
    h = re.sub(r'\(([^)]*?)/\)', lambda m: '（' + m.group(1) + '）', h)
    return h.replace('(', '（').replace(')', '）').replace('/', '')


norm_head = norm_text   # 舊名


# 卷一之版式與餘卷不同：「御注」在頂格而非縮排三格，故類目取不到。
# 三百卷只此一卷如是，逕定之，並去其「御注」一條——那是類目不是書。
LEI_FIX = {'卷一': '御注'}


def parse():
    out = []
    prev_lei = None
    for f in sorted(glob.glob(f'{RAW}/*.txt')):
        juan = page = lei = None
        cur = None
        orphan = []
        first_page = None
        for ln in open(f, encoding='utf-8'):
            if ln.startswith('#+PROPERTY: JUAN'):
                juan = ln.split()[-1]
                lei = LEI_FIX.get(juan)
                continue
            if ln.startswith('#'):
                continue
            m = re.match(r'<pb:(\S+?)>', ln)
            if m:
                page = m.group(1)
                first_page = first_page or page
                ln = ln[m.end():]
            t = ln.rstrip('\n').rstrip('¶')
            if not t.strip():
                continue
            n = len(t) - len(t.lstrip('　'))
            body = t.strip('　')
            if n == 0:
                if body == '欽定四庫全書' or body.startswith('經義考卷') \
                        or body == LEI_FIX.get(juan):
                    continue
                if lei is None:
                    lei = prev_lei          # 卷首無類目者承前卷
                prev_lei = lei
                cur = {'juan': juan, 'lei': lei, 'page': page,
                       'head': norm_head(body), 'zhu': [], 'cun': [], 'lun': []}
                out.append(cur)
                continue
            if cur is None:
                # 卷首之版心：書名、卷次、撰人銜名，不入
                if body == '欽定四庫全書' or body.startswith('經義考卷') \
                        or body.endswith('朱彝尊撰') or body.endswith('朱彞尊撰'):
                    continue
                # 卷首之類目：「　　　易(四/)」「　　　鏤板」——縮排三格而在
                # 首條之前，是本卷之類，非某條之存佚。前次解析誤入存佚而棄。
                if n == 3 and lei is None:
                    c = re.sub(r'\(.*?\)|（.*?）|　.*$', '', body).strip()
                    # 「詩五」「論語一」是類名帶本類之卷次，去其數
                    lei = (re.sub(r'[一二三四五六七八九十]+$', '', c) or c) \
                        .translate(str.maketrans({'説': '說', '録': '錄'}))
                    continue
                # 卷中無頂格之條目者（鏤板、著録、通説、家學、自述諸卷），其
                # 文皆是論述而非書目。前次連同棄之，今別立一條以存其文。
                orphan.append(body)
                continue
            cur['zhu' if n == 2 else 'cun' if n == 3 else 'lun'].append(body)
        if orphan and cur is None:
            out.append({'juan': juan, 'lei': lei, 'page': first_page,
                        'head': lei or juan, 'zhu': [], 'cun': [],
                        'lun': orphan})
    for x in out:
        x['zhu'] = norm_text('；'.join(x['zhu']))
        x['cun'] = norm_text('；'.join(x['cun']))
        x['lun'] = norm_text(''.join(x['lun']))
    return out


def main():
    if '--no-fetch' not in sys.argv:
        fetch()
    out = parse()
    print('解析得', len(out), '條；有論斷者',
          sum(1 for x in out if x['lun']), '，論斷總字數',
          sum(len(x['lun']) for x in out))
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write('\n')


if __name__ == '__main__':
    main()
