# -*- coding: utf-8 -*-
"""B1 併池：按裁決計畫合併同名重出 Work。

計畫檔格式（JSON list）：
  [{"loser": "<id>", "keeper": "<id>", "note": "<入 indexed_by[].note 之語>",
    "ai_note": "<入雙方 ai_note 之語>"}]

作業：
  1. loser 之 indexed_by／emendated_by 併入 keeper，各條蓋 merged_from=loser 與 note；
  2. keeper 缺而 loser 有之欄位補之（juan_count/measures/period/dynasty/loss_status/
     description/original_title/additional_titles/books/related_works/authors[].entity_id）；
  3. loser 之題若異於 keeper，入 keeper.additional_titles；
  4. 全庫單次掃描，把一切指向 loser 之字串改指 keeper（整理本 work_id/work_ids、
     entity.works、Book.work_id、他 work 之 related_works……），並去重；
  5. 刪 loser 檔、遷其 Work/<id>/ 目錄之內容、自索引摘除；keeper 索引欄位重算。

用法：python3 scripts/b1/merge.py <plan.json> [--apply]
不帶 --apply 為乾跑，只印不寫。
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

def idx_all():
    d = {}
    for s in SH: d.update(load(f'index/works/{s}.json'))
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

# period_upper / period_upper_basis 不搬——那是 C 車道之欄，且 keeper 多已有硬 period，
# 搬過去只是噪音。其餘欄位僅在 keeper 空缺時補入，屬合併之必要承接。
# 只承接「作品身分」之欄。period／period_upper／dynasty 屬 C 車道、loss_status 與
# description 屬 D 車道，一律不搬——搬了不只越界，還會把 loser 的誤判蓋到 keeper 上：
# 《毛詩義疏》被併之條因清史稿「不著時代」被誤判成 period=qing，而 keeper 是隋志之書。
SCALARS = ['juan_count', 'measures', 'measure_info', 'subtype', 'fragments']

def main():
    plan = load(sys.argv[1])
    apply = '--apply' in sys.argv
    IW = idx_all()
    today = datetime.date.today().isoformat()

    remap = {}      # loser -> keeper
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
        # authors: 補 entity_id / dynasty
        for ka in kd.get('authors') or []:
            for la in ld.get('authors') or []:
                if ka.get('name') == la.get('name'):
                    for f in ('entity_id', 'dynasty', 'dynasty_basis', 'role', 'note'):
                        if not ka.get(f) and la.get(f): ka[f] = la[f]
        if not kd.get('authors') and ld.get('authors'):
            kd['authors'] = ld['authors']; filled.append('authors')
        # related_works：併入，去 self/loser
        rw = kd.setdefault('related_works', [])
        have = {r.get('id') for r in rw}
        for r in ld.get('related_works') or []:
            if r.get('id') in (K, L) or r.get('id') in have: continue
            if r.get('relation') == 'same_title_source': continue
            rw.append(r); have.add(r.get('id'))
        kd['related_works'] = [r for r in rw if r.get('id') not in (K, L)]
        if not kd['related_works']: del kd['related_works']
        fix = job.get('keeper_author_fix')
        if fix:
            for a in kd.get('authors') or []:
                if a.get('name') == fix['from']:
                    a['name'] = fix['to']
                    alt = a.setdefault('alt_names', [])
                    if fix['from'] not in alt: alt.append(fix['from'])
                    a['name_basis'] = fix['why']
                    print(f"  正名 {fix['from']} → {fix['to']}")
        msg = job.get('ai_note') or ''
        kd['ai_note'] = ((kd.get('ai_note') or '') + ('\n\n' if kd.get('ai_note') else '')
                         + f'{today} B1 同名異書併池：併入 `{L}`（{kd.get("title")}）。{msg}')
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
                    if os.path.exists(t): print('  ！目錄衝突，未遷', s)
                    else: shutil.move(s, t)
                if not os.listdir(ldir): os.rmdir(ldir)
                else: print('  ！殘留目錄', ldir)
        remap[L] = K

    if not remap: return
    # ---- 全庫單次掃描改繫 ----
    def walk(o):
        """只在真正改到 loser id 時才動；純字串列僅於被改動後去重，
        否則會把全庫無關的重複字串列一併重寫（乾跑時誤報 ctext 檔即此）。"""
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
    kauthors = {}
    for K in set(remap.values()):
        _kd = load(IW[K]['path'])
        kauthors[K] = {a.get('name') for a in (_kd.get('authors') or [])}
    pats = ['Work/*/*/*/*.json', 'Work/*/*/*/*/**/*.json', 'Book/*/*/*/*.json',
            'Collection/*/*/*/*.json', 'Collection/*/*/*/*/**/*.json', 'Entity/*/*/*/*.json']
    files = set()
    for p in pats: files.update(glob.glob(p, recursive=True))
    for p in sorted(files):
        try: d = load(p)
        except Exception: continue
        if walk(d):
            if p.startswith('Entity/'):
                # 異名之人物不隨併：keeper 之 authors 無此名者，解其連而非改繫
                name = d.get('primary_name'); keep, dropped = [], []
                for w in d.get('works') or []:
                    wid = w.get('work_id') if isinstance(w, dict) else None
                    if wid in kauthors and name not in kauthors[wid]: dropped.append(wid)
                    else: keep.append(w)
                else:
                    # 留連者：keeper 撰人欄之 entity_id 若空，補之，否則生「人物→作品 單向」
                    for w in keep:
                        wid = w.get('work_id') if isinstance(w, dict) else None
                        if wid in kauthors and name in kauthors[wid]:
                            wp = IW[wid]['path']
                            wd = load(wp); ch = False
                            for a in wd.get('authors') or []:
                                if a.get('name') == name and not a.get('entity_id'):
                                    a['entity_id'] = d.get('id'); ch = True
                            if ch:
                                print(('寫' if apply else '擬') + f" 補 {wid} 撰人「{name}」entity_id={d.get('id')}")
                                if apply: save(wp, wd)
                if dropped:
                    d['works'] = keep
                    print(('寫' if apply else '擬') + f" 人物「{name}」解連 {dropped}"
                          + ('，works 已空，刪檔' if not keep else ''))
                    if apply:
                        if keep: save(p, d)
                        else: os.remove(p)
                    touched += 1
                    continue
            # related_works 去重（同 id 只留一）
            if isinstance(d, dict) and isinstance(d.get('related_works'), list):
                seen, out = set(), []
                for r in d['related_works']:
                    i = r.get('id') if isinstance(r, dict) else None
                    if i and i in seen: continue
                    if i: seen.add(i)
                    out.append(r)
                d['related_works'] = out
            if apply: save(p, d)
            else: print('   改繫', p)
            touched += 1
    print(('寫' if apply else '擬') + f'改繫檔 {touched}')

    # ---- 索引 ----
    if apply:
        IW2 = idx_all()
        for L, K in remap.items():
            sp = f'index/works/{shard(L)}.json'
            d = load(sp)
            if L in d: del d[L]; save(sp, d)
        for K in set(remap.values()):
            sp = f'index/works/{shard(K)}.json'
            d = load(sp)
            kd = load(d[K]['path'])
            e = d[K]
            e['title'] = kd.get('title')
            if kd.get('authors'): e['author'] = kd['authors'][0].get('name')
            for f, g in (('dynasty', 'dynasty'), ('period', 'period'), ('loss_status', 'loss_status')):
                if kd.get(g) is not None: e[f] = kd[g]
            if kd.get('juan_count'): e['juan_count'] = kd['juan_count'].get('number')
            if kd.get('measure_info'): e['measure_info'] = kd['measure_info']
            save(sp, d)
        print('索引已同步（摘除 %d、更新 %d）' % (len(remap), len(set(remap.values()))))

main()
