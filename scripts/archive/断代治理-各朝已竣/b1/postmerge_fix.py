#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B 車道：merge.py 收工後的索引補綴。

merge.py 有四處已知的收尾不全，每批合併後都要補：
  一、`index/books/*.json` 之 `work_id` 未隨 Book 改繫而改；
  二、`index/entities/*.json` 留下已刪 Entity 之鍵；
  三、`index/works/*.json` 之 `dynasty` 被改寫為 Work 的 `dynasty` 欄，
      而 `chk.py` 的正解是 `authors[0].dynasty or work.dynasty`——撰人之朝代優先，
      無之才退到書之朝代（《江南錄》書成於宋而撰人徐鉉為南唐舊臣，索引當作南唐；
      《文章流別集》撰人摯虞無朝代欄而書標晉，索引當作晉）；
  四、隨 loser 遷入 keeper 目錄之 `fragments/*.json`：檔內 `work_id`
      須隨路徑改，且 keeper 之 `ai_note` 須記其檔位（見 SCHEMA〈輯佚檔〉，
      `chk.py` 以 ai_note 含 `fragments/` 為據）。

用法：python3 scripts/b1/postmerge_fix.py <plan.json>  （只動索引與 ai_note，不動 Work 之實質欄）
"""
import json, glob, os, sys

def load(p): return json.load(open(p, encoding='utf-8'))
def save(p, d):
    json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    open(p, 'a').write('\n')

def wpath(wid, IW):
    p = (IW.get(wid) or {}).get('path')
    if p and os.path.exists(p): return p
    g = glob.glob('Work/%s/%s/%s/%s-*.json' % (wid[0], wid[1], wid[2], wid))
    return g[0] if g else None

def main(plan_path):
    plan = load(plan_path)
    keepers = {x['keeper'] for x in plan}
    IW = {}
    for f in glob.glob('index/works/*.json'): IW.update(load(f))
    n = {'book': 0, 'entity': 0, 'dynasty': 0, 'frag': 0}

    # 一、books work_id
    want = {}
    for k in keepers:
        p = wpath(k, IW)
        if not p: continue
        for b in (load(p).get('books') or []): want[b] = k
    for f in glob.glob('index/books/*.json'):
        d = load(f); ch = False
        for b, k in want.items():
            if b in d and d[b].get('work_id') != k:
                d[b]['work_id'] = k; ch = True; n['book'] += 1
        if ch: save(f, d)

    # 二、entities 孤兒鍵
    for f in glob.glob('index/entities/*.json'):
        d = load(f); rm = [k for k, v in d.items() if v.get('path') and not os.path.exists(v['path'])]
        if rm:
            for k in rm: del d[k]
            save(f, d); n['entity'] += len(rm)

    # 三、works dynasty 取 authors[0].dynasty
    for f in glob.glob('index/works/*.json'):
        d = load(f); ch = False
        for k in keepers & set(d):
            p = wpath(k, IW)
            if not p: continue
            w = load(p)
            a = (w.get('authors') or [None])[0]
            want_dy = ((a or {}).get('dynasty')) or w.get('dynasty') or None
            if d[k].get('dynasty') != want_dy:
                if want_dy is None: d[k].pop('dynasty', None)
                else: d[k]['dynasty'] = want_dy
                ch = True; n['dynasty'] += 1
        if ch: save(f, d)

    # 四、隨遷之 fragments
    for k in keepers:
        for fr in glob.glob('Work/%s/%s/%s/%s/fragments/*.json' % (k[0], k[1], k[2], k)):
            fd = load(fr)
            if fd.get('work_id') != k:
                fd['work_id'] = k; save(fr, fd); n['frag'] += 1
            p = wpath(k, IW)
            if not p: continue
            wd = load(p)
            rel = os.path.relpath(fr)
            if 'fragments/' not in (wd.get('ai_note') or ''):
                wd['ai_note'] = (wd.get('ai_note') or '') + (
                    '\n\n2026-08-23 B 車道併池：本條之輯佚檔隨所併入之條遷入本目錄，'
                    '檔位 `%s`，檔內 work_id 已隨路徑改繫。' % rel)
                save(p, wd); n['frag'] += 1
    print('補綴：books work_id %d、entities 孤兒鍵 %d、works dynasty %d、fragments %d'
          % (n['book'], n['entity'], n['dynasty'], n['frag']))

if __name__ == '__main__':
    main(sys.argv[1])
