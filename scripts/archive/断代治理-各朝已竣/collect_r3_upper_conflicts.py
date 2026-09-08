#!/usr/bin/env python3
"""R3 引文判讀中浮出之「上限與實證相斥」條目，匯總出清單。

判讀員逐條讀引文時，遇引文內證（刊本紀年、官修之年、撰人生平）明與本條
`period_upper` 相斥者，依規範置 confidence=low 並於 basis 註明，不擅改。
此類**多半不是斷代之誤，是同題異書誤併**——與
`period上限與現判相斥-20260824.md` 所記甲型同源：宋志所著錄之某書與清人
某書本是二事，繫於一 work 而已。

本腳本掃 result 檔中 basis 含相斥語者，出清單交 B 車道（同題異書拆併）。
不改任何 work。

用法：python3 scripts/collect_r3_upper_conflicts.py <batches_dir>
"""
import json, glob, os, sys, re

KEY = re.compile(r'(相斥|矛盾|與 ?upper|upper 為|上限.*(不合|有誤|矛盾|相斥)|'
                 r'超出上限|晚於上限)')


def main():
    bdir = sys.argv[1]
    inputs = {}
    for f in sorted(glob.glob(os.path.join(bdir, 'batch_*.json'))):
        if f.endswith('.result.json'):
            continue
        for e in json.load(open(f)):
            inputs[e['id']] = e

    hits = []
    for f in sorted(glob.glob(os.path.join(bdir, 'batch_*.result.json'))):
        for r in json.load(open(f)):
            basis = r.get('basis') or ''
            if not KEY.search(basis):
                continue
            src = inputs.get(r['id']) or {}
            hits.append({
                'id': r['id'],
                'title': src.get('title'),
                'authors': src.get('authors'),
                'period_upper_現值': src.get('upper'),
                '引文所示之代': r.get('period'),
                'confidence': r.get('confidence'),
                'basis': basis,
                'evidence': r.get('evidence'),
                '所繫之志': sorted({q.get('src') for q in (src.get('quotes') or [])}),
            })

    out = {
        '_說明': (
            'R3 引文判讀（2026-08-24）中浮出：引文內證（刊本紀年／官修之年／撰人生平）'
            '與本條 period_upper 相斥。**不是斷代之誤，多是同題異書誤併**——'
            '上限出於某早志所著錄之同題書，而引文所述乃另一晚出之書，二者繫於一 work。'
            '與 period上限與現判相斥-20260824.md 之甲型同源。'
            '\n\n當拆不當改：拆屬 B 車道（同題異書併池），須逐條裁，'
            '本輪只記不動（欄位級所有權；本庫定例不得批量合併）。'),
        '條目': hits,
    }
    p = '.claude/known-issues/R3-上限與引文相斥-20260824.json'
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'相斥條目 {len(hits)} 條，已出 {p}')
    for h in hits[:15]:
        print(f"  {h['id']} 《{h['title']}》 upper={h['period_upper_現值']}"
              f" 引文示 {h['引文所示之代']}")


if __name__ == '__main__':
    main()
