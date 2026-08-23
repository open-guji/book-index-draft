#!/usr/bin/env python3
"""甲3：題合而一方闕撰人者，逐條裁

甲3 是《經義考》之題與庫中某書全等，而撰人一方有、一方無——或朱彝尊未著
其人而庫中有之，或反是，或兩皆不著。題既全合，其為一書之疑甚大，然「疑」
不是「是」，故立三閘：

**閘一．庫中同題須只一條**。庫有二條以上，則《經義考》此條究指其一，非
逐條覈《志》不能定，批量掛之必誤。

**閘二．一標的不得為二條所指**。庫中一條無撰人之《尚書解》，而《經義考》
著《尚書解》者十九家——袁默、文彥博、范純仁、蔡卞……——十九之中至多一
家是它，其餘皆是庫中所無之別書。此輩一律不掛。

**閘三．同志而卷數異者不掛**。SCHEMA〈同題二條〉第一則：同志則卷數之異
疑二書。《周易講義》庫方繫宋志三卷，而《經義考》之夏休作九卷、商飛卿作一
卷——宋志本自著數家同題之書，庫方所存只是其一。此閘擋下者出待覈之目。

過三閘者掛源，`indexed_by[]` 記《經義考》之題、撰人、所引之志、卷、頁。
**不補 `authors[]`**：朱彝尊之著撰人是一源之言，繫人須另考（B 車道），此
處只令其言可查。
"""
import json, os, sys, collections, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import nz, load_index
from jyk_attach_source import SRC, SRC_BID, STATUS, NOTE

DATA = '.claude/known-issues/經義考待裁.json'
HOLD = '.claude/known-issues/經義考甲3待覈.json'

# 《經義考》之志簡稱 → 庫中 indexed_by[].source 之名
ZHI = {'漢志': ['漢書藝文志'], '隋志': ['隋書經籍志'],
       '唐志': ['新唐書藝文志', '舊唐書經籍志'], '宋志': ['宋史藝文志'],
       '通志': ['通志藝文略'], '崇文總目': ['崇文總目'], '國史志': ['國史經籍志'],
       '文獻通考': ['文獻通考經籍考'], '書録解題': ['直齋書錄解題'],
       '讀書志': ['郡齋讀書志']}
CN = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8,
      '九': 9, '十': 10, '百': 100}


def juan(s):
    """自著錄語取卷（篇）數。「二十四卷」→24，無則 None"""
    m = re.search(r'([一二三四五六七八九十百]+)[卷巻篇]', s or '')
    if not m:
        return None
    n = cur = 0
    for ch in m.group(1):
        v = CN[ch]
        if v >= 10:
            cur = (cur or 1) * v
            n += cur
            cur = 0
        else:
            cur = v
    return n + cur


def main():
    apply = '--apply' in sys.argv
    works = load_index('works')
    by_title = collections.defaultdict(list)
    for v in works.values():
        by_title[nz(v.get('title'))].append(v)

    D = json.load(open(DATA))
    J = [d for d in D if d['tier'] == '甲3'
         and not (d.get('attached_to') or d.get('created_work'))]

    # 閘一
    single, multi = [], []
    for d in J:
        cs = by_title[nz(re.sub(r'（[^）]*）', '', d['title'] or ''))]
        (single if len(cs) == 1 else multi).append((d, cs))

    # 閘二
    tgt = collections.defaultdict(list)
    for d, cs in single:
        tgt[cs[0]['id']].append(d)

    ok, hold = [], []
    for d, cs in single:
        w = cs[0]
        if len(tgt[w['id']]) > 1:
            hold.append((d, w, f'庫中此條為《經義考》{len(tgt[w["id"]])} 條所同指，'
                               f'至多一條是它，餘皆庫中所無之別書'))
            continue
        # 閘三
        rec = json.load(open(w['path']))
        lib = collections.defaultdict(list)
        for e in (rec.get('indexed_by') or []):
            lib[e.get('source')].append(juan(e.get('summary') or e.get('title_info') or ''))
        bad = None
        for zh, names in ZHI.items():
            at = [a for a in (d['attest'] or []) if a.startswith(zh)]
            if not at:
                continue
            jn = juan(at[0])
            if jn is None:
                continue
            for nm in names:
                if nm in lib and any(x is not None for x in lib[nm]) and jn not in lib[nm]:
                    bad = f'同引{zh}而卷數異——《經義考》作{jn}，庫方作' \
                          f'{"、".join(str(x) for x in lib[nm] if x is not None)}'
                break
            if bad:
                break
        (hold.append((d, w, bad)) if bad else ok.append((d, w)))

    for d, cs in multi:
        hold.append((d, None, f'庫中同題者 {len(cs)} 條，非逐條覈志不能定其所指'))

    print(f'甲3 未辦 {len(J)}：掛源 {len(ok)}，待覈 {len(hold)}')
    print(collections.Counter(h[2].split('——')[0][:14] for h in hold))
    if not apply:
        print('（乾跑。加 --apply 方寫檔）')
        return

    n = 0
    for d, w in ok:
        p = w['path']
        rec = json.load(open(p))
        idx = rec.setdefault('indexed_by', [])
        if any(e.get('source') == SRC and e.get('page') == d['page'] for e in idx):
            continue
        idx.append({
            'source': SRC, 'source_bid': SRC_BID,
            'title_info': f"《{d['title']}》" + (f"（{d['author']}）" if d.get('author') else ''),
            'summary': '；'.join(d['attest']) if d['attest'] else '',
            'section': d['lei'], 'juan': d['juan'], 'page': d['page'],
            'attested_status': STATUS[d['status']],
            'attested_status_raw': d['status'],
            'attested_status_note': NOTE,
            'note': '題與庫題全等而撰人一方闕。庫中同題只此一條，亦無他條同指，'
                    '所引之志與卷數與庫方不相牴，故繫於此。'
                    + (f'朱彝尊著其撰人為「{d["author"]}」，是一源之言，'
                       '未據以補 authors[]——繫人須另考。' if d.get('author')
                       and not w.get('author') else '')})
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
            f.write('\n')
        d['attached_to'] = w['id']
        n += 1
    json.dump(D, open(DATA, 'w'), ensure_ascii=False, indent=1)
    json.dump([{'head': d['head'], 'why': why,
                'lib': (w['id'], w['title'], w.get('author')) if w else None,
                **{k: d[k] for k in ('lei', 'juan', 'page', 'status', 'author', 'title', 'attest')}}
               for d, w, why in hold], open(HOLD, 'w'), ensure_ascii=False, indent=1)
    print('已掛', n)


if __name__ == '__main__':
    main()
