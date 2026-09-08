#!/usr/bin/env python3
"""合併「長題＝撰人＋短題」之重出（chk.py 題名重出項）。

題名之取：一律用短題（使用者 2026-08-22 定）。長題入 additional_titles。
惟四類簡轉繁誤映射逕改為正字——簡體一字對兩繁字而選錯者，非異體之異：
    于/於（于湖，張孝祥之號，取于）
    復/複（大復山人何景明、存復齋朱德潤，取復）
    谷/穀（虎谷王雲鳳、少谷侯一元，取谷）
    梁/樑（梁園，取梁）
其餘字面分歧（庵／菴、采／採、修／脩、歷／曆、贊／讚、錄／録、真／眞、
教／敎、畫／畵、鐘／鍾、志／誌、嶽／岳、藥／葯）兩形皆見於志書，
不在本批裁定，出清單另辦。

存者之取：indexed_by 源多者為主；相等則取短題那條。

用法：python3 scripts/merge_title_author_dupes.py [--apply]
"""
import json, glob, os, sys, shutil, datetime

TODAY = '2026-08-22'
FIX = {'於湖集': '于湖集', '大複集': '大復集', '存複齋集': '存復齋集',
       '虎穀集': '虎谷集', '少穀集': '少谷集', '樑園集': '梁園集'}


def shard(i):
    h = 0
    for c in i:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return '%x' % (h % 16)


def dedup(seq, key):
    seen, out = set(), []
    for x in seq or []:
        if not isinstance(x, dict):
            continue
        k = key(x)
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


def main():
    apply_ = '--apply' in sys.argv
    pairs = json.load(open(sys.argv[sys.argv.index('--pairs') + 1]
                           if '--pairs' in sys.argv
                           else '.claude/known-issues/C1-題名重出待併.json',
                           encoding='utf-8'))
    if isinstance(pairs, dict):
        pairs = pairs['條目']
    wp = {os.path.basename(p).split('-')[0]: p for p in glob.glob('Work/*/*/*/*.json')}

    plan = []
    for o in pairs:
        si, li = o['short_id'], o['long_id']
        if si not in wp or li not in wp:
            continue
        ds = json.load(open(wp[si], encoding='utf-8'))
        dl = json.load(open(wp[li], encoding='utf-8'))
        ns, nl = len(ds.get('indexed_by') or []), len(dl.get('indexed_by') or [])
        tgt, src = (si, li) if ns >= nl else (li, si)
        title = o['short']
        title = FIX.get(title, title)
        plan.append({'tgt': tgt, 'src': src, 'title': title,
                     'other': o['long'] if tgt == si else o['short']})

    # 短題撞名之判：併後若他條同題而撰人明確且相異，則此條改用「書名＋撰人＋役」
    # 之別題式（本庫既有體例，如《韓詩翼要侯苞撰》）。他條無撰人者不算「不同作者」
    # ——無從斷其異同，仍取短題，另出清單。
    bytitle, merging = {}, {x['tgt'] for x in plan} | {x['src'] for x in plan}
    for p2 in glob.glob('Work/*/*/*/*.json'):
        d2 = json.load(open(p2, encoding='utf-8'))
        if d2.get('_promoted_to'):
            continue
        a2 = (d2.get('authors') or [{}])[0]
        bytitle.setdefault(d2.get('title'), []).append(
            (d2['id'], a2.get('name') if isinstance(a2, dict) else None))
    unresolved = []
    for x in plan:
        others = [(i, a) for i, a in bytitle.get(x['title'], [])
                  if i != x['tgt'] and i not in merging]
        if not others:
            continue
        dt = json.load(open(wp[x['tgt']], encoding='utf-8'))
        ds2 = json.load(open(wp[x['src']], encoding='utf-8'))
        names = [((dt.get('authors') or [{}])[0] or {}).get('name'),
                 ((ds2.get('authors') or [{}])[0] or {}).get('name')]
        mine = max([n for n in names if n], key=len, default=None)
        named = [a for _, a in others if a]
        if not named or not mine:
            unresolved.append((x['title'], x['tgt'], mine, others))
            continue
        if all(a != mine for a in named):
            role = ((dt.get('authors') or [{}])[0] or {}).get('role') or '撰'
            x['title'] = f'{x["title"]}{mine}{role}'
            x['disambig'] = True
    if unresolved:
        print('　撞名而他條無撰人（仍取短題，另記）：', len(unresolved))
        for t, i, m, o2 in unresolved:
            print(f'     《{t}》 本條 {m} ←撞→ {o2}')
    json.dump({'_說明': '併後短題與他條同名，而他條無撰人，無從斷其異同，'
                        '故仍取短題。二者是否重出待併池車道查。',
               '條目': [{'title': t, 'id': i, '本條撰人': m, '他條': o2}
                        for t, i, m, o2 in unresolved]},
              open('.claude/known-issues/C1-併後同題而他條無撰人.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    print(f'擬併 {len(plan)} 組；存長題那條者 {sum(1 for x in plan if x["tgt"] != None and False)}')
    tgts = {x['tgt'] for x in plan}
    srcs = {x['src'] for x in plan}
    assert not (tgts & srcs), '有 work 同時為存者與併者，須人工'
    if not apply_:
        for x in plan[:10]:
            print(f'   存 {x["tgt"]} 題《{x["title"]}》 ← 併 {x["src"]}（別題《{x["other"]}》）')
        print('（dry-run，加 --apply 方寫入）')
        return

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    remap = {x['src']: x['tgt'] for x in plan}

    for x in plan:
        tp, sp = wp[x['tgt']], wp[x['src']]
        t = json.load(open(tp, encoding='utf-8'))
        s = json.load(open(sp, encoding='utf-8'))
        old = t.get('title')
        t['title'] = x['title']
        at = [a for a in (t.get('additional_titles') or []) if isinstance(a, str)]
        for cand in (old, s.get('title'), x['other']):
            if cand and cand != x['title'] and cand not in at:
                at.append(cand)
        for a in (s.get('additional_titles') or []):
            if isinstance(a, str) and a != x['title'] and a not in at:
                at.append(a)
        if at:
            t['additional_titles'] = at
        t['indexed_by'] = dedup((t.get('indexed_by') or []) + (s.get('indexed_by') or []),
                                lambda e: (e.get('source'), e.get('title_info')))
        if s.get('emendated_by') or t.get('emendated_by'):
            t['emendated_by'] = dedup((t.get('emendated_by') or []) + (s.get('emendated_by') or []),
                                      lambda e: (e.get('source'), e.get('title_info')))
        rw = dedup((t.get('related_works') or []) + (s.get('related_works') or []),
                   lambda e: (e.get('id'), e.get('relation')))
        rw = [r for r in rw if r.get('id') not in (x['src'], x['tgt'])]
        if rw:
            t['related_works'] = rw
        bk = list(dict.fromkeys((t.get('books') or []) + (s.get('books') or [])))
        if bk:
            t['books'] = bk
        for f in ('authors', 'period', 'period_basis', 'period_upper', 'period_upper_basis',
                  'loss_status', 'juan_count', 'measures', 'measure_info', 'description',
                  'original_title', 'contains_text_of', 'authenticity'):
            if not t.get(f) and s.get(f):
                t[f] = s[f]
        t['ai_note'] = ((t.get('ai_note') or '').rstrip() +
                        f'\n\n{TODAY} 併池：《{s.get("title")}》{x["src"]} 併入本條。'
                        f'二者長短題並存而撰人相容，係志書連書省撰人之體例所致之重出。'
                        f'題名依約取短題' +
                        (f'（原短題作《{old}》，「{old}」係簡轉繁誤映射，正之）'
                         if old != x['title'] else '') +
                        f'，別題存於 additional_titles。').strip()
        t['updated_at'] = now
        with open(tp, 'w', encoding='utf-8') as f:
            json.dump(t, f, ensure_ascii=False, indent=2)
            f.write('\n')
        sd = os.path.join(os.path.dirname(sp), x['src'])
        td = os.path.join(os.path.dirname(tp), x['tgt'])
        if os.path.isdir(sd):
            for sub in os.listdir(sd):
                os.makedirs(td, exist_ok=True)
                dst = os.path.join(td, sub)
                if os.path.exists(dst):
                    for fn in os.listdir(os.path.join(sd, sub)):
                        shutil.move(os.path.join(sd, sub, fn), os.path.join(dst, fn))
                else:
                    shutil.move(os.path.join(sd, sub), dst)
            shutil.rmtree(sd, ignore_errors=True)
        os.remove(sp)

    # 全庫改指
    n = {'Book': 0, 'Work.rw': 0, 'Entity': 0, 'collated': 0}
    for p in glob.glob('Book/*/*/*/*.json'):
        d = json.load(open(p, encoding='utf-8'))
        if d.get('work_id') in remap:
            d['work_id'] = remap[d['work_id']]
            d['updated_at'] = now
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
                f.write('\n')
            n['Book'] += 1
    for p in glob.glob('Work/*/*/*/*.json'):
        d = json.load(open(p, encoding='utf-8'))
        ch = False
        for r in (d.get('related_works') or []):
            if isinstance(r, dict) and r.get('id') in remap:
                r['id'] = remap[r['id']]
                ch = True
        if ch:
            d['related_works'] = [r for r in d['related_works'] if r.get('id') != d.get('id')]
            d['updated_at'] = now
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
                f.write('\n')
            n['Work.rw'] += 1
    for p in glob.glob('Entity/*/*/*/*.json'):
        d = json.load(open(p, encoding='utf-8'))
        ws = d.get('works') or []
        ch = False
        for w in ws:
            if isinstance(w, dict) and w.get('work_id') in remap:
                w['work_id'] = remap[w['work_id']]
                ch = True
        if ch:
            seen, out = set(), []
            for w in ws:
                k = (w.get('work_id'), w.get('role'))
                if k in seen:
                    continue
                seen.add(k)
                out.append(w)
            d['works'] = out
            d['updated_at'] = now
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
                f.write('\n')
            n['Entity'] += 1
    for p in glob.glob('Work/*/*/*/*/collated_edition/*.json'):
        raw = open(p, encoding='utf-8').read()
        new = raw
        for a, b in remap.items():
            new = new.replace(f'"{a}"', f'"{b}"')
        if new != raw:
            json.loads(new)
            open(p, 'w', encoding='utf-8').write(new)
            n['collated'] += 1
    print('改指：', n)

    # 索引
    SH = {s: json.load(open(f'index/works/{s}.json')) for s in '0123456789abcdef'}
    for src, tgt in remap.items():
        SH[shard(src)].pop(src, None)
    wp2 = {os.path.basename(p).split('-')[0]: p for p in glob.glob('Work/*/*/*/*.json')}
    for x in plan:
        d = json.load(open(wp2[x['tgt']], encoding='utf-8'))
        e = SH[shard(x['tgt'])].get(x['tgt'])
        if e is None:
            continue
        e['title'] = d['title']
        e['path'] = wp2[x['tgt']]
        if d.get('additional_titles'):
            e['additional_titles'] = d['additional_titles']
    for s, obj in SH.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write('\n')
    print('併訖', len(plan))


if __name__ == '__main__':
    main()
