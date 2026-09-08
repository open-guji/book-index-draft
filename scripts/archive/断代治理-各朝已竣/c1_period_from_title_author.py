#!/usr/bin/env python3
"""C1 續：題名自著撰人者，據其人定代。

本庫多有「撰人見於題名而 authors 欄闕」之條（《李悝法經》《張璠後漢記》之類），
前此三判準皆夠不著，遂長留 null。然其代實可由題名所冠之人定之——此即
SCHEMA〈period〉判準一（dynasty → period），只是撰人須自題名取。

取名之防（缺一不可，皆為實測誤判所迫）：
  1 人名須 ≥3 字。兩字前綴太貪：「朱文」截斷朱文公、「唐蒙」把朝代前綴當人名、
    「方廣」是經名之一截、「張昌」截斷張昌齡。
  2 人名不得同時是庫中書名。庫有「周易」而朝代標明之 Entity，
    不設此防則《周易某氏義》全遭帶歪。
  3 「某氏」二字通稱不取（戴氏、呂氏）。
  4 該人物須已繫有作品——未繫者多是錄入殘條。
  5 同名多人而朝代不一者不取。
  6 朝代須無歧義且在 DYNASTY_PERIOD 表中。
  7 所定之代不得晚於 period_upper。
  8 撰人卒年晚於所定 period 之終年者不取（跨代人物）。

只寫 period／period_basis（C 車道所有）。**不代補 authors 欄**——那是 B 車道之權，
故 basis 中記明所據何人何 Entity，俾 B 車道日後正式補入時可驗。

用法：python3 scripts/c1_period_from_title_author.py [--apply]
"""
import json, glob, sys, datetime
from collections import defaultdict, Counter
sys.path.insert(0, 'scripts')
from period_bounds import DYNASTY_PERIOD, AMBIGUOUS, PERIOD_YEARS

TODAY = '2026-08-22'


def main():
    apply_ = '--apply' in sys.argv
    IE, IW = {}, {}
    for s in '0123456789abcdef':
        IE.update(json.load(open(f'index/entities/{s}.json')))
        IW.update(json.load(open(f'index/works/{s}.json')))
    WT = {e.get('title') for e in IW.values() if e.get('title')}

    ework = Counter()
    works = []
    for p in glob.glob('Work/*/*/*/*.json'):
        d = json.load(open(p, encoding='utf-8'))
        works.append((p, d))
        for a in (d.get('authors') or []):
            if isinstance(a, dict) and a.get('entity_id'):
                ework[a['entity_id']] += 1

    byname = defaultdict(list)
    for eid, e in IE.items():
        n = e.get('primary_name')
        if n and len(n) >= 3 and n not in WT and not (len(n) == 2 and n.endswith('氏')):
            byname[n].append(eid)

    picks = []
    for p, d in works:
        if d.get('_promoted_to') or d.get('period') or d.get('authors'):
            continue
        t = d.get('title') or ''
        best = None
        for L in range(min(7, len(t) - 1), 2, -1):
            if t[:L] in byname:
                best = t[:L]
                break
        if not best:
            continue
        eids = byname[best]
        if not any(ework.get(e) for e in eids):
            continue
        dys = {IE[e].get('dynasty') for e in eids if IE[e].get('dynasty')}
        if len(dys) != 1:
            continue
        dy = dys.pop()
        if dy in AMBIGUOUS or dy not in DYNASTY_PERIOD:
            continue
        got = DYNASTY_PERIOD[dy]
        rng = PERIOD_YEARS.get(got)
        ub = d.get('period_upper')
        if ub and rng and PERIOD_YEARS.get(ub) and rng[0] >= PERIOD_YEARS[ub][1]:
            continue
        dyr = [IE[e].get('death_year') for e in eids if IE[e].get('death_year')]
        if dyr and rng and max(dyr) > rng[1]:
            continue
        picks.append((p, d, got, best, dy, eids[0]))

    print('可定', len(picks))
    print(' 分代：', dict(Counter(g for _, _, g, _, _, _ in picks).most_common()))
    if not apply_:
        print('（dry-run，加 --apply 方寫入）')
        return

    SH = {s: json.load(open(f'index/works/{s}.json')) for s in '0123456789abcdef'}

    def shard(i):
        h = 0
        for c in i:
            h = ((h * 31) + ord(c)) & 0xFFFFFFFF
        return '%x' % (h % 16)

    for p, d, got, nm, dy, eid in picks:
        d['period'] = got
        d['period_basis'] = (
            f'題名自著撰人「{nm}」，據其朝代「{dy}」定代（庫中 Entity {eid}）。'
            f'本條 authors 欄闕，撰人僅見於題名，故前此判準俱夠不著而留 null；'
            f'authors 之補屬併池車道，此處只定代。（{TODAY} C1）')
        d['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write('\n')
        e = SH[shard(d['id'])].get(d['id'])
        if e is not None:
            e['period'] = got
    for s, obj in SH.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write('\n')
    with open('.claude/known-issues/C1-題名自著撰人定代.json', 'w', encoding='utf-8') as f:
        json.dump({'_說明': f'{TODAY} C1 據題名所冠撰人定代者。authors 欄仍闕，'
                            '交併池車道正式補入（basis 已記所據 Entity id）。',
                   '條目': [{'id': d['id'], 'title': d.get('title'), '撰人': nm,
                             'dynasty': dy, 'period': g, 'entity_id': eid}
                            for _, d, g, nm, dy, eid in picks]},
                  f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('已寫入')


if __name__ == '__main__':
    main()
