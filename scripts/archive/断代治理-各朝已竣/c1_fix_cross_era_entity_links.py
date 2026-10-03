#!/usr/bin/env python3
"""訂正「撰人 Entity 之代晚於該書著錄志上限」之誤繫。

偵測：Work 之 authors[].entity_id 所指 Entity，其 period 之起年晚於該書
period_upper 之終年——即「明清之人被繫成隋唐以前之書的撰人」。全庫實測 166 條，
其中 entity 標明者 68、標清者 62，是同名異代誤繫之典型。

處置三分：
  改繫 —— 庫中有同名而合代者，且其代**早於**現繫者（是在糾正繫得太晚）。
          多為同一人被拆成兩個 Entity 而其一朝代錯（許慎清/東漢、范寧清/東晉）。
  脫繫 —— 庫中無同名合代者，或候選反而更晚。去其 entity_id，存其 name。
          錯的連結比沒有連結更壞：它會把錯朝代傳播出去（顏延之一條掛 28 部書）。
  存疑 —— 該書自身之 period 與上限相斥者，錯的多半是**上限**而非人物，不動。
          《涉史隨筆》南宋葛洪撰而被《補晉書藝文志》繫上，遂壓出 upper=jin。

Entity 側之 works[] 同步增刪，否則 chk 之「人物→作品／作品→人物 單向」立漲。

用法：python3 scripts/c1_fix_cross_era_entity_links.py [--apply]
"""
import json, glob, os, sys, datetime
from collections import defaultdict
sys.path.insert(0, 'scripts')
from period_bounds import PERIOD_YEARS

TODAY = '2026-08-22'


def main():
    apply_ = '--apply' in sys.argv
    IE, epath = {}, {}
    for s in '0123456789abcdef':
        IE.update(json.load(open(f'index/entities/{s}.json')))
    for p in glob.glob('Entity/*/*/*/*.json'):
        epath[os.path.basename(p).split('-')[0]] = p
    byname = defaultdict(list)
    for eid, e in IE.items():
        if e.get('primary_name'):
            byname[e['primary_name']].append(eid)

    relink, detach, suspect = [], [], []
    for p in glob.glob('Work/*/*/*/*.json'):
        d = json.load(open(p, encoding='utf-8'))
        if d.get('_promoted_to'):
            continue
        ub = d.get('period_upper')
        if not ub or ub not in PERIOD_YEARS:
            continue
        ube = PERIOD_YEARS[ub][1]
        per = d.get('period')
        conflict_self = bool(per and PERIOD_YEARS.get(per) and PERIOD_YEARS[per][0] > ube)
        for a in (d.get('authors') or []):
            if not isinstance(a, dict):
                continue
            eid = a.get('entity_id')
            e = IE.get(eid) if eid else None
            if not e:
                continue
            ep = e.get('period')
            if not (ep and PERIOD_YEARS.get(ep) and PERIOD_YEARS[ep][0] > ube):
                continue
            rec = {'wid': d['id'], 'title': d.get('title'), 'path': p,
                   'name': a.get('name'), 'eid': eid, 'edy': e.get('dynasty'),
                   'ep': ep, 'ub': ub, 'period': per}
            if conflict_self:
                rec['故'] = '書之 period 與上限相斥——疑上限誤繫，人物不動'
                suspect.append(rec)
                continue
            cands = [x for x in byname.get(e.get('primary_name'), []) if x != eid
                     and IE[x].get('period') and PERIOD_YEARS.get(IE[x]['period'])
                     # 須整個落在上限之內（比終年），非只起年早於上限——
                     # 只比起年會踩 song×liao-jin-yuan 全重疊之坑：遼起 907
                     # 早於北宋 960，遂把《宋東宮儀記》（隋志著錄，其「宋」是劉宋）
                     # 由北宋張鑑「改繫」成元張鑑，愈改愈遠。
                     and PERIOD_YEARS[IE[x]['period']][1] <= ube
                     and PERIOD_YEARS[IE[x]['period']][0] < PERIOD_YEARS[ep][0]]
            if len(cands) == 1:
                rec['to'] = cands[0]
                rec['to_dy'] = IE[cands[0]].get('dynasty')
                relink.append(rec)
            else:
                detach.append(rec)

    print(f'改繫 {len(relink)}　脫繫 {len(detach)}　存疑不動 {len(suspect)}')
    if not apply_:
        for r in relink[:6]:
            print(f'   改繫《{r["title"]}》{r["name"]}：{r["edy"]} → {r["to_dy"]}')
        for r in detach[:6]:
            print(f'   脫繫《{r["title"]}》{r["name"]}（{r["edy"]}，上限 {r["ub"]}）')
        for r in suspect[:4]:
            print(f'   存疑《{r["title"]}》period {r["period"]} vs 上限 {r["ub"]}')
        print('（dry-run，加 --apply 方寫入）')
        return

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ent_del, ent_add = defaultdict(set), defaultdict(set)
    touched = {}
    for r in relink + detach:
        d = touched.get(r['path']) or json.load(open(r['path'], encoding='utf-8'))
        for a in (d.get('authors') or []):
            if not isinstance(a, dict) or a.get('entity_id') != r['eid']:
                continue
            if 'to' in r:
                a['entity_id'] = r['to']
                if not a.get('dynasty') or a.get('dynasty') == r['edy']:
                    a['dynasty'] = r['to_dy']
                a['name_basis'] = ((a.get('name_basis') or '') +
                    f'\n{TODAY} C1：原繫 {r["eid"]}（{r["edy"]}），其代晚於本書上限 '
                    f'{r["ub"]}，是同名異代之誤繫；改繫 {r["to"]}（{r["to_dy"]}）。').strip()
                ent_del[r['eid']].add(r['wid'])
                ent_add[r['to']].add((r['wid'], a.get('role') or '撰'))
            else:
                a.pop('entity_id', None)
                if a.get('dynasty') == r['edy']:
                    a.pop('dynasty', None)
                a['name_basis'] = ((a.get('name_basis') or '') +
                    f'\n{TODAY} C1：原繫 {r["eid"]}（{r["edy"]}），其代晚於本書上限 '
                    f'{r["ub"]}，是同名異代之誤繫；庫中無同名而合代者，故去其 entity_id，'
                    f'存其名待考。').strip()
                ent_del[r['eid']].add(r['wid'])
        d['updated_at'] = now
        touched[r['path']] = d
    for p, d in touched.items():
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write('\n')

    for eid, wids in list(ent_del.items()) :
        ep = epath.get(eid)
        if not ep:
            continue
        e = json.load(open(ep, encoding='utf-8'))
        e['works'] = [w for w in (e.get('works') or [])
                      if not (isinstance(w, dict) and w.get('work_id') in wids)]
        e['updated_at'] = now
        with open(ep, 'w', encoding='utf-8') as f:
            json.dump(e, f, ensure_ascii=False, indent=2)
            f.write('\n')
    for eid, pairs in ent_add.items():
        ep = epath.get(eid)
        if not ep:
            continue
        e = json.load(open(ep, encoding='utf-8'))
        have = {w.get('work_id') for w in (e.get('works') or []) if isinstance(w, dict)}
        e.setdefault('works', [])
        for wid, role in pairs:
            if wid not in have:
                e['works'].append({'work_id': wid, 'role': role})
        e['updated_at'] = now
        with open(ep, 'w', encoding='utf-8') as f:
            json.dump(e, f, ensure_ascii=False, indent=2)
            f.write('\n')

    with open('.claude/known-issues/C1-撰人跨代誤繫.json', 'w', encoding='utf-8') as f:
        json.dump({'_說明': f'{TODAY} C1 據「撰人 Entity 之代晚於該書著錄志上限」查出之誤繫。'
                            '改繫者已改，脫繫者已去 entity_id 存其名，'
                            '存疑者疑上限誤繫而非人物誤繫，未動，交 A 車道查其著錄。',
                   '改繫': relink, '脫繫': detach, '存疑_疑上限誤': suspect},
                  f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'訖：改繫 {len(relink)}　脫繫 {len(detach)}　存疑 {len(suspect)}')


if __name__ == '__main__':
    main()
