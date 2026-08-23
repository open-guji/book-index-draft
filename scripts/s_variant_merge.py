# -*- coding: utf-8 -*-
"""S 車道（同題同撰異體字重出）併池：按裁決計畫合併 Work，並同步五處。

本檔以 scripts/b1/merge.py 為底本，補其所無而本車道必須者：
  · resources 併入（以 id+url 去重）、description 承接（keeper 空則取之，
    否則把被刪條之說明記入 ai_note，不覆蓋）；
  · fragments/ 隨遷之後，補 keeper 之 ai_note 使其含「fragments/」
    （chk.py 之輯佚檔驗以此為據）；
  · Entity.works 之取捨改以 entity_id 為準——被刪條之撰人若別繫一 entity，
    該 entity 不得因改繫而 claim keeper（否則 chk 之「人物→作品 單向」上升）；
  · index/books 之 work_id 同步；
  · 派生欄位 _has_text／_has_image／_has_collated 重算；
  · index/works 之 path／title／author／role／dynasty／original_title 全欄重寫。

計畫檔格式（JSON list）：
  [{"loser":"<id>","keeper":"<id>","note":"<入 indexed_by[].note>",
    "ai_note":"<入 keeper ai_note 之案語>",
    "keeper_fix":{"juan_count":12,"measure_info":"十二卷"},   # 選填
    "keeper_author_alt":{"name":"張鳯翼","add":"張鳳翼"}}]     # 選填，補 alt_names

用法：python3 scripts/s_variant_merge.py <plan.json> [--apply]
"""
import json, sys, glob, os, shutil, datetime

SH = '0123456789abcdef'

def load(p):
    with open(p, encoding='utf-8') as f: return json.load(f)

def save(p, d):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2); f.write('\n')

def shard(i):
    h = 0
    for c in i: h = ((h*31)+ord(c)) & 0xFFFFFFFF
    return SH[h % 16]

def idx_all(k='works'):
    d = {}
    for s in SH: d.update(load(f'index/{k}/{s}.json'))
    return d

def key_of(e):
    return (e.get('source'), e.get('source_bid'), e.get('title_info'), (e.get('summary') or '')[:80])

def merge_lists(dst, src, tag, note):
    seen = {key_of(e) for e in dst}
    added = 0
    for e in src:
        if key_of(e) in seen: continue
        e = dict(e); e['merged_from'] = tag
        if note: e['note'] = note
        dst.append(e); seen.add(key_of(e)); added += 1
    return added

# 只承接「作品身分」之欄。period／period_upper／dynasty／loss_status 屬 C／D 車道，
# 一律不搬（見 b1/merge.py 之案）；被刪條若有而 keeper 無，記入 ai_note 以待其道。
SCALARS = ['juan_count', 'measures', 'measure_info', 'subtype', 'fragments']

def main():
    plan = load(sys.argv[1])
    apply = '--apply' in sys.argv
    IW = idx_all('works')
    today = datetime.date.today().isoformat()

    remap = {}
    keeper_ents = {}
    for job in plan:
        L, K = job['loser'], job['keeper']
        if L not in IW or K not in IW:
            print('！缺記錄，跳過', L, K); continue
        lp, kp = IW[L]['path'], IW[K]['path']
        ld, kd = load(lp), load(kp)
        n1 = merge_lists(kd.setdefault('indexed_by', []), ld.get('indexed_by') or [], L, job.get('note'))
        n2 = merge_lists(kd.setdefault('emendated_by', []), ld.get('emendated_by') or [], L, job.get('note'))
        if not kd['emendated_by']: del kd['emendated_by']
        filled = []
        for f in SCALARS:
            if kd.get(f) in (None, '', [], {}) and ld.get(f) not in (None, '', [], {}):
                kd[f] = ld[f]; filled.append(f)
        if ld.get('title') and ld['title'] != kd.get('title'):
            at = kd.setdefault('additional_titles', [])
            if ld['title'] not in at: at.append(ld['title'])
        for f in ('books',):
            if ld.get(f):
                cur = kd.setdefault(f, [])
                for x in ld[f]:
                    if x not in cur: cur.append(x)
        # resources：以 (id, url) 去重併入
        if ld.get('resources'):
            cur = kd.setdefault('resources', [])
            have = {(r.get('id'), r.get('url')) for r in cur if isinstance(r, dict)}
            for r in ld['resources']:
                if not isinstance(r, dict): continue
                if (r.get('id'), r.get('url')) in have: continue
                cur.append(r); have.add((r.get('id'), r.get('url'))); filled.append('resources')
        # description：keeper 空則承之，否則不覆蓋，其文記入案語
        carry = []
        if ld.get('description'):
            if not kd.get('description'):
                kd['description'] = ld['description']; filled.append('description')
            elif json.dumps(ld['description'], ensure_ascii=False) != json.dumps(kd['description'], ensure_ascii=False):
                carry.append('被刪條之 description：' + (ld['description'].get('text') or '')[:200]
                             + '（源：' + '、'.join(ld['description'].get('sources') or []) + '）')
        for f in ('period', 'period_upper', 'dynasty', 'loss_status'):
            if not kd.get(f) and ld.get(f):
                carry.append(f'被刪條之 {f}={ld[f]}，本條從缺，不越 C／D 車道而搬，俟其道補')
        # authors：補 entity_id／dynasty 等空欄
        for ka in kd.get('authors') or []:
            for la in ld.get('authors') or []:
                if ka.get('name') == la.get('name'):
                    for f in ('entity_id', 'dynasty', 'dynasty_basis', 'role', 'note'):
                        if not ka.get(f) and la.get(f): ka[f] = la[f]
        if not kd.get('authors') and ld.get('authors'):
            kd['authors'] = ld['authors']; filled.append('authors')
        alt = job.get('keeper_author_alt')
        if alt:
            for a in kd.get('authors') or []:
                if a.get('name') == alt['name']:
                    an = a.setdefault('alt_names', [])
                    if alt['add'] not in an: an.append(alt['add'])
        for f, v in (job.get('keeper_fix') or {}).items():
            kd[f] = v; filled.append('fix:' + f)
        rw = kd.setdefault('related_works', [])
        have = {r.get('id') for r in rw}
        for r in ld.get('related_works') or []:
            if r.get('id') in (K, L) or r.get('id') in have: continue
            if r.get('relation') == 'same_title_source': continue
            rw.append(r); have.add(r.get('id'))
        kd['related_works'] = [r for r in rw if r.get('id') not in (K, L)]
        if not kd['related_works']: del kd['related_works']
        msg = job.get('ai_note') or ''
        note = f'{today} S 同題同撰重出併池（異體字）：併入 `{L}`（{ld.get("title")}）。{msg}'
        if carry: note += '　' + '；'.join(carry) + '。'
        kd['ai_note'] = ((kd.get('ai_note') or '') + ('\n\n' if kd.get('ai_note') else '')) + note
        kd['updated_at'] = today + 'T00:00:00+00:00'
        print(f'{"寫" if apply else "擬"} {L} → {K}  著錄+{n1} 考證+{n2} 補欄{filled}')
        if apply:
            save(kp, kd)
            os.remove(lp)
            ldir = os.path.join(os.path.dirname(lp), L)
            if os.path.isdir(ldir):
                kdir = os.path.join(os.path.dirname(kp), K)
                os.makedirs(kdir, exist_ok=True)
                for item in os.listdir(ldir):
                    s, t = os.path.join(ldir, item), os.path.join(kdir, item)
                    if os.path.exists(t):
                        for sub in os.listdir(s):
                            s2, t2 = os.path.join(s, sub), os.path.join(t, sub)
                            if os.path.exists(t2): print('  ！檔名衝突，未遷', s2)
                            else: shutil.move(s2, t2)
                        if not os.listdir(s): os.rmdir(s)
                    else: shutil.move(s, t)
                if not os.listdir(ldir): os.rmdir(ldir)
                else: print('  ！殘留目錄', ldir)
        remap[L] = K
        kd2 = load(kp) if apply else kd
        keeper_ents[K] = {a.get('entity_id') for a in (kd2.get('authors') or []) if a.get('entity_id')}

    if not remap: return

    def walk(o):
        ch = False
        if isinstance(o, dict):
            for k, v in list(o.items()):
                if isinstance(v, str) and v in remap: o[k] = remap[v]; ch = True
                elif isinstance(v, list):
                    nv = [remap.get(x, x) if isinstance(x, str) else x for x in v]
                    if nv != v:
                        ch = True
                        if all(isinstance(x, str) for x in nv):
                            seen, dedup = set(), []
                            for x in nv:
                                if x not in seen: seen.add(x); dedup.append(x)
                            nv = dedup
                        o[k] = nv
                    for x in nv:
                        if isinstance(x, (dict, list)) and walk(x): ch = True
                elif isinstance(v, dict):
                    if walk(v): ch = True
        elif isinstance(o, list):
            for x in o:
                if isinstance(x, (dict, list)) and walk(x): ch = True
        return ch

    touched = 0
    pats = ['Work/*/*/*/*.json', 'Work/*/*/*/*/**/*.json', 'Book/*/*/*/*.json',
            'Collection/*/*/*/*.json', 'Collection/*/*/*/*/**/*.json', 'Entity/*/*/*/*.json']
    files = set()
    for p in pats: files.update(glob.glob(p, recursive=True))
    for p in sorted(files):
        try: d = load(p)
        except Exception: continue
        if walk(d):
            if p.startswith('Entity/'):
                eid = d.get('id'); keep, dropped, seen = [], [], set()
                for w in d.get('works') or []:
                    wid = w.get('work_id') if isinstance(w, dict) else None
                    if wid in keeper_ents and eid not in keeper_ents[wid]:
                        dropped.append(wid); continue
                    if wid and wid in seen: continue
                    if wid: seen.add(wid)
                    keep.append(w)
                if keep != (d.get('works') or []):
                    d['works'] = keep
                    if dropped:
                        print(('寫' if apply else '擬') + f" 人物「{d.get('primary_name')}」({eid}) 解連 {dropped}")
            if isinstance(d, dict) and isinstance(d.get('related_works'), list):
                seen, out = set(), []
                for r in d['related_works']:
                    i = r.get('id') if isinstance(r, dict) else None
                    if i and (i, r.get('relation')) in seen: continue
                    if i: seen.add((i, r.get('relation')))
                    if i and i == d.get('id'): continue
                    out.append(r)
                d['related_works'] = out
            if apply: save(p, d)
            else: print('   改繫', p)
            touched += 1
    print(('寫' if apply else '擬') + f'改繫檔 {touched}')

    if not apply: return

    # ---- fragments 之 work_id 與 keeper 之 ai_note ----
    for K in set(remap.values()):
        kp = idx_all('works')[K]['path'] if K in idx_all('works') else None
    IW2 = idx_all('works')
    for K in set(remap.values()):
        kp = IW2[K]['path']
        frs = glob.glob(os.path.join(os.path.dirname(kp), K, 'fragments', '*.json'))
        if not frs: continue
        kd = load(kp); ch = False
        for f in frs:
            fd = load(f)
            if fd.get('work_id') != K: fd['work_id'] = K; save(f, fd); print('  輯佚檔改繫', f)
        if 'fragments/' not in (kd.get('ai_note') or ''):
            kd['ai_note'] = (kd.get('ai_note') or '') + '　輯佚檔：' + '、'.join(
                'fragments/' + os.path.basename(f) for f in frs) + '（隨併池遷入本條）。'
            ch = True
        if ch: save(kp, kd)

    # ---- 派生欄位重算 ----
    for K in set(remap.values()):
        kp = IW2[K]['path']; kd = load(kp); ch = False
        ts = set()
        for r in kd.get('resources') or []:
            if isinstance(r, dict): ts.update(r.get('types') or ([r['type']] if r.get('type') else []))
        want = {'_has_text': 'text' in ts, '_has_image': 'image' in ts,
                '_has_collated': os.path.isdir(os.path.join(os.path.dirname(kp), K, 'collated_edition'))}
        for k, v in want.items():
            if (kd.get(k) or False) != v:
                if v: kd[k] = True
                else: kd.pop(k, None)
                ch = True
        if ch: save(kp, kd); print('  派生欄位重算', K, want)

    # ---- index/works ----
    for L in remap:
        sp = f'index/works/{shard(L)}.json'
        d = load(sp)
        if L in d:
            del d[L]
            save(sp, {k: d[k] for k in sorted(d)})
    for K in set(remap.values()):
        sp = f'index/works/{shard(K)}.json'
        d = load(sp); kd = load(IW2[K]['path']); e = d[K]
        a0 = (kd.get('authors') or [{}])[0]
        a0 = a0 if isinstance(a0, dict) else {}
        vals = {'path': IW2[K]['path'], 'title': kd.get('title'),
                'author': a0.get('name'), 'role': a0.get('role'),
                'dynasty': a0.get('dynasty') or kd.get('dynasty'),
                'original_title': kd.get('original_title'),
                'period': kd.get('period'), 'loss_status': kd.get('loss_status'),
                'juan_count': (kd.get('juan_count') or {}).get('number') if isinstance(kd.get('juan_count'), dict) else kd.get('juan_count'),
                'measure_info': kd.get('measure_info'),
                'additional_titles': kd.get('additional_titles')}
        for k, v in vals.items():
            if v in (None, '', [], {}): e.pop(k, None)
            else: e[k] = v
        save(sp, {k: d[k] for k in sorted(d)})
    print('index/works 已同步（摘除 %d、重寫 %d）' % (len(remap), len(set(remap.values()))))

    # ---- related_works[].title 隨題改繫（keeper 之題可與被刪條之題不同）----
    _T = {k: v.get('title') for k, v in idx_all('works').items()}
    import json as _j
    _T.update({k: v.get('title') for k, v in _j.load(open('index/collections.json')).items()})
    nt = 0
    for p2 in glob.glob('Work/*/*/*/*.json'):
        d = load(p2); ch = False
        for r in d.get('related_works') or []:
            t = _T.get(r.get('id'))
            if t and r.get('title') and r['title'] != t: r['title'] = t; ch = True
        if ch: save(p2, d); nt += 1
    print('related_works 題名同步', nt)

    # ---- index/books 之 work_id ----
    nb = 0
    for s in SH:
        sp = f'index/books/{s}.json'; d = load(sp); ch = False
        for k, v in d.items():
            if v.get('work_id') in remap:
                v['work_id'] = remap[v['work_id']]; ch = True; nb += 1
        if ch: save(sp, {k: d[k] for k in sorted(d)})
    print('index/books work_id 改繫', nb)

main()
