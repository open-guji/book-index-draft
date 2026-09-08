#!/usr/bin/env python3
"""秦漢段磁鐵：相牴之節改繫其應歸之注本，並正撰人異名。

判準見 SCHEMA〈磁鐵之判〉。逐條經人工覆核，非機讀所定。
用法：python scripts/reattach_qinhan_magnet.py [--apply]
"""
import json, glob, sys

APPLY = '--apply' in sys.argv

# (源 work, 節序, 承接 work, 案語)
MOVES = [
    ('1ev3baq2ibmdc', 4, '1evcpcwgo0xds',
     '隋志「《吳越春秋》十卷皇甫遵撰」，撰人為皇甫遵而非趙曄，本非趙曄之書之著錄'),
    ('1ev3baq2ibmdc', 5, '1evcpcwgo0xds',
     '宋志「趙曄《吳越春秋》十卷皇甫遵注」，《隋志考證》引此條正列於皇甫遵名下'),
    ('1ev3bbv4iohds', 3, '1evftx3j0zo5c',
     '書目答問「《淮南子》高誘注二十一卷」，所著錄者是高誘注本，無淮南王之名'),
    ('1ev7w0evl7400', 1, '1evgpkdb43oxs',
     '隋志「《世本》二卷劉向撰」，劉向本自是一書，庫中別有其條'),
    ('1ev3ba9imamtc', 1, '1evfubxn890xs',
     '舊唐志「《小爾雅》一卷李軌撰」，《補晉志》明謂「《舊唐志》誤作『李軌撰』」，'
     '所指即李軌《小爾雅略解》'),
]

# (work, 舊名, 新名, 案語)
RENAME = [
    ('1ev3baq2ibmdc', '趙煜', '趙曄',
     '《後漢書·儒林傳》《隋志》《兩唐志》《宋志》俱作趙曄，四庫提要作趙煜，'
     '同一人之異寫。從通行之趙曄，庫中所繫八節之著錄語遂皆相合'),
]

# (work, 補入之撰人, role, dynasty, 案語)
ADD_AUTHOR = [
    ('1ev7vo52r3ev4', '公羊高', '傳', '漢',
     '舊唐志「《春秋公羊傳》五卷公羊高傳，嚴彭祖述」，本條原只繫公羊壽；'
     '公羊壽是公羊高玄孫，書成於壽而傳自高，二名並存'),
]


def load():
    W = {}
    for root in ('/workspace/book-index-draft', '/workspace/book-index'):
        for f in glob.glob(f'{root}/Work/*/*/*/*.json'):
            try:
                d = json.load(open(f, encoding='utf-8'))
            except Exception:
                continue
            if not d.get('_promoted_to'):
                W[d['id']] = (d, f)
    return W


def save(W, wid):
    d, f = W[wid]
    if APPLY:
        with open(f, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(json.dumps(d, ensure_ascii=False, indent=2))


def note(d, txt):
    d['ai_note'] = ((d.get('ai_note') or '') + ('\n\n' if d.get('ai_note') else '')
                    + '2026-08-21 秦漢段磁鐵覆核：' + txt)


def main():
    W = load()
    touched = set()

    # 一、移節（自後向前刪，免序位錯亂）
    for src, i, dst, why in sorted(MOVES, key=lambda x: -x[1]):
        sd = W[src][0]
        dd = W[dst][0]
        node = sd['indexed_by'][i]
        print(f"移《{sd['title']}》[{i}] {node.get('source')}｜{node.get('title_info')}"
              f" →《{dd['title']}》")
        sd['indexed_by'] = [r for j, r in enumerate(sd['indexed_by']) if j != i]
        dd.setdefault('indexed_by', []).append(node)
        note(sd, f'「{node.get("title_info")}」一節移繫《{dd["title"]}》{dst}——{why}。')
        note(dd, f'自《{sd["title"]}》{src} 移入「{node.get("title_info")}」一節——{why}。')
        touched |= {src, dst}

    # 二、正撰人異名
    for wid, old, new, why in RENAME:
        d = W[wid][0]
        for a in d.get('authors') or []:
            if a.get('name') == old:
                a['name'] = new
                print(f"正《{d['title']}》撰人：{old} → {new}")
        note(d, f'撰人由「{old}」正作「{new}」——{why}。')
        touched.add(wid)

    # 三、補撰人
    for wid, name, role, dyn, why in ADD_AUTHOR:
        d = W[wid][0]
        if any(a.get('name') == name for a in d.get('authors') or []):
            continue
        d.setdefault('authors', []).insert(0, {'name': name, 'role': role,
                                               'dynasty': dyn})
        print(f"補《{d['title']}》撰人：{name}（{role}）")
        note(d, f'補撰人「{name}」（{role}）——{why}。')
        touched.add(wid)

    for wid in touched:
        save(W, wid)
    print(f'\n涉 {len(touched)} 條' + ('' if APPLY else '　(dry-run)'))


if __name__ == '__main__':
    main()
