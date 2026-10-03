#!/usr/bin/env python3
"""合并两个 Work（source → target），改写全仓引用后删除 source。

基于 overview/scripts/merge_works.py，改动：
  - 路径参数化（原脚本硬编码 D:\workspace）
  - 增加 emendated_by 合并（原脚本漏了，商君書 的考證会丢）
  - 增加 books 合并 + 去重（红楼梦教训：Work.books 会重复）
"""
import json, os, sys
from book_index_manager import BookIndexManager
from book_index_manager.id_generator import BookIndexType

DRAFT = os.environ.get('DRAFT_ROOT', '/workspace/book-index-draft')
ROOT = os.environ.get('STORAGE_ROOT', '/workspace')


def find_all_jsons(root):
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if fn.endswith('.json'):
                yield os.path.join(dp, fn)


def _dedup_append(tgt, src, field, keyfn):
    cur = list(tgt.get(field) or [])
    keys = {keyfn(x) for x in cur if isinstance(x, dict)}
    n = 0
    for x in (src.get(field) or []):
        if not isinstance(x, dict):
            continue
        k = keyfn(x)
        if k not in keys:
            cur.append(x); keys.add(k); n += 1
    if n:
        tgt[field] = cur
    return n


def merge(source_wid, target_wid, mgr):
    src = mgr.get_item(source_wid)
    tgt = mgr.get_item(target_wid)
    if not src or not tgt:
        return {'error': f'not found: src={src is not None} tgt={tgt is not None}'}

    stat = {}
    stat['indexed_by'] = _dedup_append(tgt, src, 'indexed_by',
                                       lambda x: (x.get('source_bid', ''), x.get('volume', ''), x.get('title_info', '')))
    stat['emendated_by'] = _dedup_append(tgt, src, 'emendated_by',
                                         lambda x: (x.get('source_bid', ''), x.get('title_info', '')))
    stat['resources'] = _dedup_append(tgt, src, 'resources', lambda x: x.get('url', ''))
    stat['authors'] = _dedup_append(tgt, src, 'authors',
                                    lambda x: (x.get('name', ''), x.get('role', ''), x.get('dynasty', '')))
    stat['measures'] = _dedup_append(tgt, src, 'measures', lambda x: (x.get('unit', ''), x.get('number')))
    stat['related_works'] = _dedup_append(tgt, src, 'related_works',
                                          lambda x: (x.get('relation', ''), x.get('id', ''), x.get('title', '')))

    # books：合并 + 去重 + 去掉自指
    books = list(tgt.get('books') or []) + list(src.get('books') or [])
    seen, merged_books = set(), []
    for b in books:
        if b and b not in seen:
            seen.add(b); merged_books.append(b)
    stat['books'] = len(merged_books) - len(tgt.get('books') or [])
    if merged_books:
        tgt['books'] = merged_books

    # description：target 缺才补
    sd = src.get('description') or {}
    if isinstance(sd, dict) and sd.get('text'):
        td = tgt.get('description') or {}
        if not isinstance(td, dict) or not td.get('text'):
            tgt['description'] = sd
            stat['description'] = 'from-source'

    # juan_count / measure_info
    def _n(j):
        return j.get('number') if isinstance(j, dict) else (j if isinstance(j, int) else None)
    sn, tn = _n(src.get('juan_count')), _n(tgt.get('juan_count'))
    jc_conflict = None
    if sn is not None and tn is None:
        tgt['juan_count'] = src['juan_count']
    elif sn is not None and tn is not None and sn != tn:
        jc_conflict = f'juan_count 衝突: src={sn} tgt={tn}（保留 target 值 {tn}）'
    if not tgt.get('measure_info') and src.get('measure_info'):
        tgt['measure_info'] = src['measure_info']

    notes = [f'從 {source_wid}《{src.get("title")}》合併。' + (f'原註：{src.get("ai_note")}' if src.get('ai_note') else '')]
    if jc_conflict:
        notes.append(jc_conflict)
    note = tgt.get('ai_note', '') or ''
    for n in notes:
        if n not in note:
            note = (note + ' | ' + n).strip(' |') if note else n
    tgt['ai_note'] = note

    mgr.save_item(tgt, type_val=BookIndexType.Work)

    # 全仓改写引用
    rew = {'files': 0, 'book_work_id': 0, 'indexed_by': 0, 'related': 0, 'ce_section': 0, 'work_books': 0}
    for sub in ('Work', 'Book', 'Collection', 'Entity'):
        base = os.path.join(DRAFT, sub)
        if not os.path.isdir(base):
            continue
        for fp in find_all_jsons(base):
            if source_wid in os.path.basename(fp):
                continue
            try:
                content = open(fp, encoding='utf-8').read()
            except Exception:
                continue
            if source_wid not in content:
                continue
            try:
                d = json.loads(content)
            except Exception:
                continue
            if not isinstance(d, dict):
                continue
            mod = False
            if d.get('type') == 'book' and d.get('work_id') == source_wid:
                d['work_id'] = target_wid; rew['book_work_id'] += 1; mod = True
            for ib in (d.get('indexed_by') or []):
                if isinstance(ib, dict) and ib.get('source_bid') == source_wid:
                    ib['source_bid'] = target_wid; rew['indexed_by'] += 1; mod = True
            for e in (d.get('emendated_by') or []):
                if isinstance(e, dict) and e.get('source_bid') == source_wid:
                    e['source_bid'] = target_wid; rew['indexed_by'] += 1; mod = True
            for rw in (d.get('related_works') or []):
                if isinstance(rw, dict) and rw.get('id') == source_wid:
                    rw['id'] = target_wid; rew['related'] += 1; mod = True
            if isinstance(d.get('books'), list) and source_wid in d['books']:
                d['books'] = [b for b in d['books'] if b != source_wid]; rew['work_books'] += 1; mod = True
            if mod:
                json.dump(d, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
                rew['files'] += 1

    # collated_edition sections
    for dp, _, fns in os.walk(os.path.join(DRAFT, 'Work')):
        if 'collated_edition' not in dp:
            continue
        for fn in fns:
            if not fn.endswith('.json'):
                continue
            fp = os.path.join(dp, fn)
            try:
                content = open(fp, encoding='utf-8').read()
            except Exception:
                continue
            if source_wid not in content:
                continue
            try:
                d = json.loads(content)
            except Exception:
                continue
            mod = False
            for s in (d.get('sections') or []):
                if isinstance(s, dict) and s.get('work_id') == source_wid:
                    s['work_id'] = target_wid; rew['ce_section'] += 1; mod = True
            if mod:
                json.dump(d, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    deleted = mgr.delete_item(source_wid)
    return {'merged': stat, 'rewritten': rew, 'source_deleted': bool(deleted)}


if __name__ == '__main__':
    mgr = BookIndexManager(storage_root=ROOT)
    src, tgt = sys.argv[1], sys.argv[2]
    print(json.dumps(merge(src, tgt, mgr), ensure_ascii=False, indent=2))
