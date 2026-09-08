#!/usr/bin/env python3
"""把 C1「題名自著撰人」已判出的撰人正式補入 authors 欄。

前一步（c1_period_from_title_author.py）只定了 period，authors 仍闕，
理由是那屬併池車道之權。經使用者指示逕補——撰人既已查明，留著不補
徒使後人重做一遍。

role 取題名中人名之後一字：作注／疏／傳／箋／解／釋／校／輯／編／纂者用之，
餘作「撰」（《裴松之集》之「集」是別集之集，非役名，故不入此表）。

Entity 側之 works[] 同步補入——只補 Work 而不補 Entity，
chk.py 之「作品→人物 單向」立即上升。

用法：python3 scripts/c1_fill_authors_from_title.py [--apply]
"""
import json, glob, os, sys, datetime

ROLE_CH = {'注': '注', '疏': '疏', '傳': '傳', '箋': '箋', '解': '解',
           '釋': '釋', '校': '校', '輯': '輯', '編': '編', '纂': '纂'}
TODAY = '2026-08-22'


def shard(i):
    h = 0
    for c in i:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return '%x' % (h % 16)


def main():
    apply_ = '--apply' in sys.argv
    src = json.load(open('.claude/known-issues/C1-題名自著撰人定代.json', encoding='utf-8'))
    items = src['條目']
    wpath = {os.path.basename(p).split('-')[0]: p for p in glob.glob('Work/*/*/*/*.json')}
    epath = {os.path.basename(p).split('-')[0]: p for p in glob.glob('Entity/*/*/*/*.json')}

    plan, skip = [], []
    for it in items:
        p = wpath.get(it['id'])
        if not p:
            skip.append((it['id'], '檔已不在（併池刪去）'))
            continue
        d = json.load(open(p, encoding='utf-8'))
        if d.get('authors'):
            skip.append((it['id'], 'authors 已有值'))
            continue
        nm = it['撰人']
        rest = (d.get('title') or '')[len(nm):]
        role = ROLE_CH.get(rest[:1], '撰') if rest else '撰'
        if it['entity_id'] not in epath:
            skip.append((it['id'], 'Entity 檔不在'))
            continue
        plan.append((p, d, it, role))

    print(f'可補 {len(plan)}　略過 {len(skip)}')
    from collections import Counter
    print('  略過之由：', dict(Counter(r for _, r in skip)))
    print('  role 分佈：', dict(Counter(r for _, _, _, r in plan)))
    if not apply_:
        for p, d, it, role in plan[:8]:
            print(f'   《{d["title"]}》 ← {it["撰人"]}・{it["dynasty"]}・{role}')
        print('（dry-run，加 --apply 方寫入）')
        return

    SH = {s: json.load(open(f'index/works/{s}.json')) for s in '0123456789abcdef'}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ents = {}
    for p, d, it, role in plan:
        eid = it['entity_id']
        d['authors'] = [{'name': it['撰人'], 'dynasty': it['dynasty'], 'role': role,
                         'entity_id': eid,
                         'name_basis': f'撰人見於題名「{d.get("title")}」，'
                                       f'繫庫中同名人物 {eid}。（{TODAY} C1）'}]
        d['period_basis'] = (f'據撰人{it["撰人"]}之朝代「{it["dynasty"]}」。'
                             f'本條撰人原只見於題名而 authors 欄闕，'
                             f'{TODAY} C1 定代並補撰人。')
        d['updated_at'] = now
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write('\n')
        e = SH[shard(d['id'])].get(d['id'])
        if e is not None:
            e['author'] = it['撰人']
            e['dynasty'] = it['dynasty']
            e['role'] = role
        ents.setdefault(eid, []).append((d['id'], role))

    for s, obj in SH.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write('\n')

    for eid, lst in ents.items():
        ep = epath[eid]
        e = json.load(open(ep, encoding='utf-8'))
        have = {w.get('work_id') for w in (e.get('works') or []) if isinstance(w, dict)}
        e.setdefault('works', [])
        for wid, role in lst:
            if wid not in have:
                e['works'].append({'work_id': wid, 'role': role})
                have.add(wid)
        e['updated_at'] = now
        with open(ep, 'w', encoding='utf-8') as f:
            json.dump(e, f, ensure_ascii=False, indent=2)
            f.write('\n')
    print(f'已補 Work {len(plan)}　Entity {len(ents)}')


if __name__ == '__main__':
    main()
