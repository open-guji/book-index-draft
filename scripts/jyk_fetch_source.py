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


def norm_head(h):
    """標目歸一：`公孫氏(叚/)` → `公孫氏（叚）`"""
    h = re.sub(r'\(([^)]*?)/\)', lambda m: '（' + m.group(1) + '）', h)
    return h.replace('(', '（').replace(')', '）').replace('/', '')


def parse():
    out = []
    for f in sorted(glob.glob(f'{RAW}/*.txt')):
        juan = page = None
        cur = None
        for ln in open(f, encoding='utf-8'):
            if ln.startswith('#+PROPERTY: JUAN'):
                juan = ln.split()[-1]
                continue
            if ln.startswith('#'):
                continue
            m = re.match(r'<pb:(\S+?)>', ln)
            if m:
                page = m.group(1)
                ln = ln[m.end():]
            t = ln.rstrip('\n').rstrip('¶')
            if not t.strip():
                continue
            n = len(t) - len(t.lstrip('　'))
            body = t.strip('　')
            if n == 0:
                if body == '欽定四庫全書' or body.startswith('經義考卷'):
                    continue
                cur = {'juan': juan, 'page': page, 'head': norm_head(body),
                       'zhu': [], 'cun': [], 'lun': []}
                out.append(cur)
                continue
            if cur is None:
                continue
            cur['zhu' if n == 2 else 'cun' if n == 3 else 'lun'].append(body)
    for x in out:
        x['zhu'] = '；'.join(x['zhu'])
        x['cun'] = '；'.join(x['cun'])
        x['lun'] = ''.join(x['lun'])
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
