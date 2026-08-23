#!/usr/bin/env python3
"""合并后山海經 related_works 出现两条自指（原本是互指的「同書之重出」），移除。"""
from book_index_manager import BookIndexManager
from book_index_manager.id_generator import BookIndexType
m = BookIndexManager(storage_root='/workspace')
WID = '1ev3bck7g5wjk'
d = m.get_item(WID)
before = len(d.get('related_works') or [])
d['related_works'] = [r for r in (d.get('related_works') or []) if r.get('id') != WID]
add = '去重完成：原「同書之重出」兩條自指 related 已於合併 1evr5e3miqk1o 後移除。'
note = d.get('ai_note', '') or ''
if add not in note:
    d['ai_note'] = (note + ' | ' + add).strip(' |') if note else add
m.save_item(d, type_val=BookIndexType.Work)
print(f'  山海經 related_works {before} -> {len(d["related_works"])}')
