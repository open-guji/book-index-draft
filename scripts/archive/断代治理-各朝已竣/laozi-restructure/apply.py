# -*- coding: utf-8 -*-
"""执行老子／道德經 原典—注疏体系重整。"""
import json, os, sys, glob

sys.path.insert(0, '/workspace/laozi')
sys.path.insert(0, '/workspace/book-index-manager')
import plan                                                    # noqa: E402
from book_index_manager import BookIndexManager                # noqa: E402
from book_index_manager.id_generator import BookIndexType      # noqa: E402

sys.path.insert(0, '/workspace/preqin-fix')
from merge_works_v2 import merge                               # noqa: E402

APPLY = '--apply' in sys.argv
DRAFT = '/workspace/book-index-draft'
mgr = BookIndexManager(storage_root='/workspace')
log = []


def save(d, why):
    log.append(why)
    if APPLY:
        mgr.save_item(d, type_val=BookIndexType.Work)


def note(d, text):
    n = d.get('ai_note', '') or ''
    if text not in n:
        d['ai_note'] = (n + ' | ' + text).strip(' |') if n else text


# ── P1 原典本体 ──────────────────────────────────────────────
c = mgr.get_item(plan.CANON)
at = list(c.get('additional_titles') or [])
if '老子' not in at:
    at.append('老子')
c['additional_titles'] = at
c['description'] = plan.CANON_DESC
c['period'] = 'pre-qin'
c['period_basis'] = '據 authors[0].dynasty「周」（規則1 粗粒度自消歧）'
for a in (c.get('authors') or []):
    if a.get('name') == '李耳':
        a['role'] = '撰（舊題）'
        a['note'] = '周柱下史，字聃。《史記》已載其人三說並存，成書年代學界未定'
note(c, '2026-08-20 老子體系重整：本條定為《老子》／《道德經》原典。'
        '題名用《道德經》，《老子》入 additional_titles——二者為同書異名，'
        '先秦兩漢多稱《老子》，唐以後尊《道德真經》。'
        'description 原僅述元趙孟頫寫本一個版本，今改寫為全書提要；'
        '該版本說明宜下沉至對應 Book。')
save(c, f'P1 原典 {plan.CANON}《道德經》：additional_titles +《老子》、重寫 description、period=pre-qin')

# ── P2 并入原典的志书著录 ─────────────────────────────────────
for src, why in plan.MERGE_INTO_CANON:
    if APPLY:
        r = merge(src, plan.CANON, mgr)
        log.append(f'P2 併入原典 {src} → {plan.CANON}：{why}｜{r.get("merged")}')
    else:
        log.append(f'P2 [dry] 併入原典 {src} → {plan.CANON}：{why}')

# ── P3 注本组内合并 ──────────────────────────────────────────
for keep, drops in plan.MERGE_GROUPS.items():
    for src in drops:
        if APPLY:
            r = merge(src, keep, mgr)
            log.append(f'P3 合併 {src} → {keep}｜{r.get("merged")}')
        else:
            log.append(f'P3 [dry] 合併 {src} → {keep}')

# ── P4 正条题名／撰者订正 ────────────────────────────────────
for wid, spec in plan.RETITLE.items():
    d = mgr.get_item(wid)
    if not d:
        log.append(f'P4 ⚠ {wid} 不存在'); continue
    old = d.get('title')
    d['title'] = spec['title']
    if spec.get('authors'):
        d['authors'] = spec['authors']
    d['original_title'] = '老子'
    note(d, f'2026-08-20 老子體系重整：題名 {old} → {spec["title"]}；'
            f'original_title 記原書書名《老子》。')
    save(d, f'P4 {wid} 題名 {old} → {spec["title"]}')

# ── P5 其余注本改名 + original_title ────────────────────────
for wid, newt in plan.RENAME.items():
    d = mgr.get_item(wid)
    if not d:
        log.append(f'P5 ⚠ {wid} 不存在'); continue
    old = d.get('title')
    changed = []
    if old != newt:
        d['title'] = newt; changed.append(f'題名 {old} → {newt}')
    if d.get('original_title') != '老子':
        prev = d.get('original_title')
        d['original_title'] = '老子'
        changed.append(f'original_title {prev!r} → 老子')
    if changed:
        note(d, '2026-08-20 老子體系重整：' + '；'.join(changed)
                + '。注本統一作「老子＋撰者＋體裁」，original_title 記原書書名。'
                + ('志書原題見 indexed_by[].title_info。' if prev else ''))
        save(d, f'P5 {wid} ' + '；'.join(changed))

# ── P6 给 A 名下其余注本补 original_title ──────────────────
a = mgr.get_item(plan.MAGNET)
kept, excluded = [], []
for r in (a.get('related_works') or []):
    if r.get('relation') != 'text_carried_by':
        continue
    (excluded if r['id'] in plan.NOT_LAOZI_COMMENTARY else kept).append(r)

for r in kept:
    d = mgr.get_item(r['id'])
    if not d or d.get('original_title') == '老子':
        continue
    prev = d.get('original_title')
    d['original_title'] = '老子'
    note(d, f'2026-08-20 老子體系重整：original_title {prev!r} → 老子（原書書名）。')
    save(d, f'P6 {r["id"]}《{d.get("title")}》 original_title → 老子')

print(('APPLY' if APPLY else 'DRY-RUN') + f'  共 {len(log)} 项')
for x in log:
    print('  ', x)
print(f'\nA 名下 text_carried_by：保留 {len(kept)}、剔出 {len(excluded)}')


# ── P7 拆解磁铁条目 A ────────────────────────────────────────
# A 的三条著录各归其主，考證归梁曠，剔出 6 条非老子注本，
# 清掉误标的撰人与已迁走的著录，最后整条併入原典——
# 併入时 merge 会把 47 条注本的 contains_text_of 回指从 A 改到原典。
RELOCATE_IB = {                      # source → 目标正条
    '隋書經籍志':     '1evcpd0xjm03k',   # 《老子》四卷梁曠撰 → 老子道德經品
    '舊唐書經籍志':   '1evqp46oh0sg0',   # 《老子》二卷河上公注 → 老子河上公章句
    '書目答問':       '1evftepodelfk',   # 《老子》王弼注二卷 → 老子王弼注
}

a = mgr.get_item(plan.MAGNET)
if a:
    for ib in list(a.get('indexed_by') or []):
        tgt = RELOCATE_IB.get(ib.get('source'))
        if not tgt:
            continue
        t = mgr.get_item(tgt)
        if not t:
            log.append(f'P7 ⚠ 目標 {tgt} 不存在'); continue
        cur = list(t.get('indexed_by') or [])
        key = {(x.get('source_bid'), x.get('title_info')) for x in cur if isinstance(x, dict)}
        if (ib.get('source_bid'), ib.get('title_info')) not in key:
            cur.append(ib); t['indexed_by'] = cur
            note(t, f'2026-08-20 老子體系重整：{ib.get("source")}「{ib.get("title_info")}」'
                    f'原繫於磁鐵條目 1evcmnccovx1c《老子》，今歸本條。')
            save(t, f'P7 著錄遷移 [{ib.get("source")}] → {tgt}')
        else:
            log.append(f'P7 著錄 [{ib.get("source")}] 目標已有，跳過')

    # 考證（姚振宗論梁曠）归梁曠正条
    if a.get('emendated_by'):
        t = mgr.get_item('1evcpd0xjm03k')
        cur = list(t.get('emendated_by') or [])
        keys = {(x.get('source_bid'), x.get('title_info')) for x in cur if isinstance(x, dict)}
        n = 0
        for e in (a.get('emendated_by') or []):
            if (e.get('source_bid'), e.get('title_info')) not in keys:
                cur.append(e); n += 1
        if n:
            t['emendated_by'] = cur
            note(t, '2026-08-20 老子體系重整：姚振宗《隋書經籍志考證》論梁曠一條，'
                    '原繫於磁鐵條目《老子》，今歸本條。')
            save(t, f'P7 考證遷移 {n} 條 → 1evcpd0xjm03k')

    # 剔出非老子注本 + 清空已迁走的字段与误标撰人
    a['related_works'] = [r for r in (a.get('related_works') or [])
                          if r.get('id') not in plan.NOT_LAOZI_COMMENTARY]
    a['indexed_by'] = []
    a['emendated_by'] = []
    a['authors'] = []          # 梁曠是隋志著錄之撰人，已隨著錄遷走
    a['juan_count'] = None     # 四卷是梁曠注本之卷數，非原典
    a['measure_info'] = ''
    save(a, f'P7 清理磁鐵條目：剔出 {len(plan.NOT_LAOZI_COMMENTARY)} 條非老子注本，'
            f'清空已遷走的著錄／考證／撰人')

    if APPLY:
        r = merge(plan.MAGNET, plan.CANON, mgr)
        log.append(f'P7 磁鐵條目併入原典 {plan.MAGNET} → {plan.CANON}｜'
                   f'rel+{r["merged"]["related_works"]} 改寫 {r["rewritten"]["files"]} 檔')
    else:
        log.append(f'P7 [dry] 磁鐵條目併入原典 {plan.MAGNET} → {plan.CANON}')

# ── P8 原典关系去重 ─────────────────────────────────────────
c = mgr.get_item(plan.CANON)
if c:
    seen, out = set(), []
    for r in (c.get('related_works') or []):
        k = (r.get('relation'), r.get('id'))
        if k in seen:
            continue
        seen.add(k); out.append(r)
    if len(out) != len(c.get('related_works') or []):
        n = len(c['related_works']) - len(out)
        c['related_works'] = out
        save(c, f'P8 原典 related_works 去重，移除 {n} 條')
    print(f'\n原典最終 related_works: {len(out)} 條')


# ── P9 清理合并带进来的杂质 ─────────────────────────────────
# 併入隋志原典著錄（1evcmncbkb2f4）时会一併带入该条目误标的撰人「鐘會」，
# 以及版本层／注本层的 measures（二冊＝故宮元寫本，四卷＝梁曠注本）。
c = mgr.get_item(plan.CANON)
if c:
    before = [x.get('name') for x in (c.get('authors') or [])]
    c['authors'] = [x for x in (c.get('authors') or []) if x.get('name') == '李耳']
    c['measures'] = [{'unit': '卷', 'number': 2}]
    c['measure_info'] = '二卷'
    note(c, '2026-08-20 老子體系重整（續）：併入隋志原典著錄時一併帶入該條目誤標之撰人'
            '「鐘會」，今移除——鐘會注別有專條 1evcua702ksu8《老子鐘會注》。'
            'measures 亦帶入「二冊」（故宮元寫本，版本層）與「四卷」（梁曠注本卷數），'
            '今統一為原典之二卷。')
    save(c, f'P9 原典撰人 {before} → [李耳]；measures 統一為二卷')
    rel = c.get('related_works') or []
    print(f'P9 後原典：撰人 {[x.get("name") for x in c["authors"]]}、關係 {len(rel)} 條')
