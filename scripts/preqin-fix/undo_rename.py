#!/usr/bin/env python3
"""save_item 载入时会剥离 title 的量词尾，导致 1evkphsnshs74 被改名。
《六韜六卷附逸文一卷》的「一卷」修饰的是「逸文」，剥掉会失义，改回。"""
import json, os, glob
os.chdir('/workspace/book-index-draft')
new = 'Work/1/e/v/1evkphsnshs74-六韜六卷附逸文.json'
old = 'Work/1/e/v/1evkphsnshs74-六韜六卷附逸文一卷.json'
if not os.path.exists(new):
    print('  无需处理'); raise SystemExit
d = json.load(open(new, encoding='utf-8'))
d['title'] = '六韜六卷附逸文一卷'
json.dump(d, open(old, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
os.remove(new)
for f in glob.glob('index/works/*.json'):
    idx = json.load(open(f, encoding='utf-8'))
    e = idx.get('1evkphsnshs74')
    if e:
        e['title'] = '六韜六卷附逸文一卷'; e['path'] = old
        json.dump(idx, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'  改回 {old}')
        break
