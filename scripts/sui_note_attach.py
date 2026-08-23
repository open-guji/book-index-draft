#!/usr/bin/env python3
"""《隋書經籍志》注中亡書 56 條：既判為庫中已有其書，補其一源

第二輪（2026-08-10）裁定：注中析出之 257 條，建 201，餘 56 判為與庫中既有記
錄同書而未建（`隋志注亡書待裁.json` 逐條備 `skip_reason` 及所指之 work id）。

**未建是對的，未掛則是漏**。此 56 條之隋志原文，如今只以字串形式活在**別條**
的 `summary` 裡——注中之書寄於某條之注，本無獨立條目。所指之 work 之中，54
條並無隋志一源，於是「隋志明言此書已亡」這一條志書自身之判，在該 work 上查
不到。今補。

所補止於一源：`indexed_by[]` 記題、卷數、撰人、隋志原文全行，`in_note_of` 指
其所寄之條（SCHEMA 2026-08-06 所設之欄），`attested_status` 記隋志之「亡」。

**不動 `loss_status`**——那是本庫之判，屬 D4；隋志之判入 `attested_status`，
與《經義考》之例同。
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import load_index

DATA = '.claude/known-issues/隋志注亡書待裁.json'
SUI = '1ev85yncs9ibk'
NOTE = ('本書於《隋志》無獨立條目，只見於《{head}》一條之注——隋志之例，正文'
        '著隋時見存之書，而以注記梁時尚存、隋時已亡者，故 `summary` 是那一整行'
        '（首書名是正文之書，非本 work），`in_note_of` 指其所寄。'
        '2026-08-10 裁定本條與庫中此記錄同書而未別建，其由：{why}')


def main():
    apply = '--apply' in sys.argv
    works = load_index('works')
    D = json.load(open(DATA))
    plan = []
    for d in D:
        m = re.search(r'([0-9a-z]{13})', d.get('skip_reason') or '')
        if not m or m.group(1) not in works:
            print('！無所指:', d['title'])
            continue
        w = works[m.group(1)]
        rec = json.load(open(w['path']))
        if any(e.get('source_bid') == SUI and e.get('title_info', '').startswith(f"《{d['title']}》")
               for e in (rec.get('indexed_by') or [])):
            continue
        plan.append((d, w))
    print(f'56 條：可補 {len(plan)}，已有而跳過 {len(D) - len(plan)}')
    if not apply:
        print('（乾跑。加 --apply 方寫檔）')
        return
    for d, w in plan:
        rec = json.load(open(w['path']))
        e = {'source': '隋書經籍志', 'source_bid': SUI,
             'title_info': f"《{d['title']}》" + (d.get('juan') or '')
                           + (f"（{d['author']}）" if d.get('author') else ''),
             'summary': d['summary'],
             'in_note_of': d['in_note_of'],
             'attested_status': 'lost', 'attested_status_raw': '亡',
             'note': NOTE.format(head=d.get('head_title') or '?',
                                 why=d.get('skip_reason') or '')}
        rec.setdefault('indexed_by', []).append(e)
        with open(w['path'], 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
            f.write('\n')
        d['attached_to'] = w['id']
    json.dump(D, open(DATA, 'w'), ensure_ascii=False, indent=1)
    print('已補', len(plan))


if __name__ == '__main__':
    main()
