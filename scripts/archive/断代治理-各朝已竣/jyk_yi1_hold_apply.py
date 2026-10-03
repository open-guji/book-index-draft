#!/usr/bin/env python3
"""行乙1 待覈 91 條之裁定（表見 jyk_yi1_hold_tables.py）"""
import json, os, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import load_index
from jyk_attach_source import SRC, SRC_BID, STATUS, NOTE
from jyk_create_works import shard, mkid, clean_title, AI_NOTE, CIT
import jyk_yi1_hold_tables as T

DATA = '.claude/known-issues/經義考待裁.json'
HOLD = '.claude/known-issues/經義考乙1待覈.json'


def ib_rec(d, title=None, author=None, note=None):
    t = title if title is not None else d['title']
    a = author if author is not None else d.get('author')
    r = {'source': SRC, 'source_bid': SRC_BID,
         'title_info': f"《{t}》" + (f"（{a}）" if a else ''),
         'summary': '；'.join(d['attest']) if d['attest'] else '',
         'section': d['lei'], 'juan': d['juan'], 'page': d['page'],
         'attested_status': STATUS[d['status']],
         'attested_status_raw': d['status'],
         'attested_status_note': NOTE}
    if note:
        r['note'] = note
    return r


def main():
    apply = '--apply' in sys.argv
    works = load_index('works')
    D = json.load(open(DATA))
    by_head = {d['head']: d for d in D}
    taken = set(works)

    for h in list(T.ATTACH) + list(T.CREATE) + list(T.GAIJI) + list(T.HOLD):
        if h not in by_head:
            print('！標目不見於待裁：', h)
    print(f'掛源 {len(T.ATTACH)}　新建 {len(T.CREATE) + len(T.GAIJI)}　留覈 {len(T.HOLD)}')
    if not apply:
        print('（乾跑。加 --apply 方寫檔）')
        return

    shards = {s: json.load(open(f'index/works/{s}.json')) for s in '0123456789abcdef'}

    # 一、掛源
    n_at = 0
    for head, tgt in T.ATTACH.items():
        d = by_head[head]
        p = works[tgt]['path']
        w = json.load(open(p))
        idx = w.setdefault('indexed_by', [])
        if not any(e.get('source') == SRC and e.get('page') == d['page'] for e in idx):
            idx.append(ib_rec(d, note=f'《經義考》標目「{head}」與庫題《{w["title"]}》'
                                      f'題式不同而是一書，見 jyk_yi1_hold_tables.py 之裁'))
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(w, f, ensure_ascii=False, indent=2)
                f.write('\n')
            n_at += 1
        d['attached_to'] = tgt

    # 二、新建
    n_cr = 0
    plan = [(h, a, t, why, None) for h, (a, t, why) in T.CREATE.items()]
    plan += [(h, a, t, None, why) for h, (a, t, why) in T.GAIJI.items()]
    for head, author, title, why, gaiji in plan:
        d = by_head[head]
        wid = mkid(f"{d['juan']}|{d['page']}|{d['head']}", taken)
        path = f'Work/{wid[0]}/{wid[1]}/{wid[2]}/{wid}-{title}.json'
        cit = '、'.join(c for c in CIT if c in ''.join(d['attest'] or [])) or '無前代志'
        note = AI_NOTE.format(lei=d['lei'], head=head, cit=cit, status=d['status'])
        if why:
            note += '\n\n標目之正：' + why + '。'
        if gaiji:
            note += '\n\n缺字碼之還原：' + gaiji
        rec = {'schema_version': 1, 'type': 'work', 'title': title, 'id': wid,
               'authors': [{'name': author, 'role': None}], 'ai_note': note,
               'indexed_by': [ib_rec(d, title=title, author=author)]}
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
            f.write('\n')
        shards[shard(wid)][wid] = {'id': wid, 'title': title, 'type': 'Work',
                                   'path': path, 'author': author}
        d['created_work'] = wid
        n_cr += 1

    for s, obj in shards.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8') as f:
            json.dump(dict(sorted(obj.items())), f, ensure_ascii=False, indent=2)
            f.write('\n')
    json.dump(D, open(DATA, 'w'), ensure_ascii=False, indent=1)
    json.dump([{'head': h, 'why': w, **{k: by_head[h][k] for k in
                ('lei', 'juan', 'page', 'status', 'author', 'title', 'attest')}}
               for h, w in T.HOLD.items()],
              open(HOLD, 'w'), ensure_ascii=False, indent=1)
    print(f'掛源 {n_at}　新建 {n_cr}　留覈 {len(T.HOLD)}')


if __name__ == '__main__':
    main()
