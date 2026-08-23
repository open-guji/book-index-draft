#!/usr/bin/env python3
"""甲3 待覈 323 條之再裁

前輪三閘所擋者，其實非一色，今再分：

**一、多對一而諸條俱無撰人（如《連山》二條同指庫中一《連山》）**
   同題、俱不著撰人，是一書兩見於《經義考》之跡，非二書——朱彝尊於古易、
   竹書諸處屢有互見。依前輪 1,428 條「一書兩見者並記」之例，二條並掛於庫中
   之一條。

**二、多對一而諸條撰人各異**
   同題異撰是二書（SCHEMA〈同題二條〉）。庫中之一條至多當其一，餘皆庫中所
   無，當建。既不能定其孰是，則一律建之，而於 ai_note 明著此疑——寧可多一
   條可考之記錄，不可將甲之書繫乙之名。

**三、多候選（庫中同題二條以上）而本條無撰人**
   庫有數《春秋傳》而本條不著撰人，掛之必誤其一，建之則又添一無名之重出。
   仍留待覈——此非資料之不足，是《經義考》此條本身無以自別。

**四、同志而卷數異**
   SCHEMA〈同題二條〉第一則：同志則卷數之異疑二書。有撰人者建，無撰人者留。
"""
import json, os, re, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import nz, load_index
from jyk_attach_source import SRC, SRC_BID, STATUS, NOTE
from jyk_create_works import shard, mkid, CIT

DATA = '.claude/known-issues/經義考待裁.json'
LUN = '.claude/known-issues/經義考論斷.json'
HOLD = '.claude/known-issues/經義考甲3待覈.json'
LIMIT = 500
TAIL = '……（下略。全文見《經義考》整理本 collated_edition/{lei}.json，頁 {page}）'
NOTE_MULTI = ('本條與《經義考》另 {n} 條同題而撰人各異，同指庫中《{t}》一條'
              '（{wid}，撰人不著）。同題異撰是二書，庫中之一條至多當其一，'
              '故本條別建。孰是孰非，非逐條覈志不能定，姑存此疑。')
AI = ('本 work 據《經義考》（朱彝尊撰，欽定四庫全書文淵閣本，kanripo KR2n0011）'
      '新建——該書{lei}類著錄「{head}」。庫中雖有同題之《{t}》，然彼不著撰人而'
      '本條著「{a}」，同題異撰是二書，故別建。\n\n'
      '`period`／`loss_status`／`role`／`entity_id` 不繫，其由與本輪所建諸條同'
      '（見《經義考待裁分流方案》）。')


def main():
    apply = '--apply' in sys.argv
    works = load_index('works')
    taken = set(works)
    by_title = collections.defaultdict(list)
    for v in works.values():
        by_title[nz(v.get('title'))].append(v)
    lun = {(x['page'], x['head']): x for x in json.load(open(LUN))}
    D = json.load(open(DATA))
    J = [d for d in D if d['tier'] == '甲3'
         and not (d.get('attached_to') or d.get('created_work'))]

    # 依所指之庫條分組
    grp = collections.defaultdict(list)
    solo = []
    for d in J:
        cs = by_title[nz(re.sub(r'（[^）]*）', '', d['title'] or ''))]
        (grp[cs[0]['id']].append(d) if len(cs) == 1 else solo.append(d))

    attach, create, hold = [], [], []
    for wid, ds in grp.items():
        w = works[wid]
        auth = [d for d in ds if d.get('author')]
        anon = [d for d in ds if not d.get('author')]
        if not auth:
            for d in ds:
                attach.append((d, wid, '同題而俱不著撰人，是一書兩見於《經義考》，'
                                       '依「一書兩見者並記」之例並掛於此'))
        else:
            for d in auth:
                create.append((d, w, len(ds) - 1))
            for d in anon:
                attach.append((d, wid, '同組諸條之中，本條獨不著撰人，庫方亦不著，'
                                       '故繫於此；同組著撰人者別建'))
    for d in solo:
        hold.append({'head': d['head'], 'why': '庫中同題二條以上而本條不著撰人，'
                                               '掛之必誤其一，建之則添一無名之重出',
                     **{k: d[k] for k in ('lei', 'juan', 'page', 'status',
                                          'author', 'title', 'attest')}})
    print(f'甲3 待覈 {len(J)}：掛 {len(attach)}，建 {len(create)}，仍留 {len(hold)}')
    if not apply:
        print('（乾跑。加 --apply 方寫檔）')
        return

    def ib(x, t, a, extra=None):
        k = lun.get((x['page'], x['head']))
        zhu = (k['zhu'] if k else '') or '；'.join(x['attest'] or [])
        lu = k['lun'] if k else ''
        if len(lu) > LIMIT:
            lu = lu[:LIMIT] + TAIL.format(lei=(k['lei'] if k else x['lei']), page=x['page'])
        r = {'source': SRC, 'source_bid': SRC_BID,
             'title_info': f"《{t}》" + (f"（{a}）" if a else ''),
             'summary': ((zhu + '\n' + lu) if zhu else lu).strip(),
             'section': x['lei'], 'juan': x['juan'], 'page': x['page'],
             'attested_status': STATUS[x['status']],
             'attested_status_raw': x['status'], 'attested_status_note': NOTE}
        if extra:
            r['note'] = extra
        return r

    for d, wid, why in attach:
        p = works[wid]['path']
        rec = json.load(open(p))
        idx = rec.setdefault('indexed_by', [])
        if not any(e.get('source') == SRC and e.get('page') == d['page'] for e in idx):
            idx.append(ib(d, d['title'], d.get('author'), why))
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(rec, f, ensure_ascii=False, indent=2)
                f.write('\n')
        d['attached_to'] = wid

    shards = {s: json.load(open(f'index/works/{s}.json')) for s in '0123456789abcdef'}
    for d, w, nsib in create:
        t = re.sub(r'（[^）]*）', '', d['title'] or '').strip()
        a = d['author']
        wid = mkid(f"{d['juan']}|{d['page']}|{d['head']}", taken)
        path = f'Work/{wid[0]}/{wid[1]}/{wid[2]}/{wid}-{t}.json'
        rec = {'schema_version': 1, 'type': 'work', 'title': t, 'id': wid,
               'authors': [{'name': a, 'role': None}],
               'ai_note': AI.format(lei=d['lei'], head=d['head'], t=w['title'], a=a),
               'indexed_by': [ib(d, t, a, NOTE_MULTI.format(n=nsib, t=w['title'], wid=w['id'])
                                 if nsib else None)]}
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
            f.write('\n')
        shards[shard(wid)][wid] = {'id': wid, 'title': t, 'type': 'Work',
                                   'path': path, 'author': a}
        d['created_work'] = wid
    for s, obj in shards.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8') as f:
            json.dump(dict(sorted(obj.items())), f, ensure_ascii=False, indent=2)
            f.write('\n')
    json.dump(D, open(DATA, 'w'), ensure_ascii=False, indent=1)
    json.dump(hold, open(HOLD, 'w'), ensure_ascii=False, indent=1)
    print(f'掛 {len(attach)}，建 {len(create)}，留 {len(hold)}')


if __name__ == '__main__':
    main()
