#!/usr/bin/env python3
"""秦漢段磁鐵第二批：注本之節歸位、故宮目錄所補之誤撰人訂正。

《國立故宮博物院善本舊籍》目錄所補之撰人有誤者三條——本條所繫諸志之著錄語
無一作鄭玄，而目錄作「漢鄭玄撰」，從志不從目錄。

用法：python scripts/fix_qinhan_magnet_round2.py [--apply]
"""
import json, glob, sys

APPLY = '--apply' in sys.argv

MOVES = [
    ('1evcpjohisutc', 0, '1ev3barfo76dc',
     '舊唐志「又四十卷酈道元注」——「又」承前條而言，其書無撰人而唯有注者，'
     '正是酈道元四十卷注本，非桑欽《水經》本身'),
    ('1evcpcuq62dxc', 1, '1evcs09y7lfk0',
     '崇文總目「易緯九卷。宋均註」——宋均注本自是一書，本條隋志、後漢志所繫者是鄭玄注本'),
    ('1evcpcuq62dxc', 0, '1evcs09y7lfk0',
     '舊唐志「《易緯》九卷宋均注」——同上'),
]

MISATTACH = [
    ('1evcpctp2dxj4', 0,
     '舊唐志「《禮議》一卷傅伯祚撰」——本條之《禮議》是鄭玄二十卷本'
     '（後漢志「鄭玄禮議二十卷」、新唐志「又禮議二十卷」），'
     '傅伯祚一卷本自是別書，庫中無主，標記俟考定後別立'),
]

FIX_AUTHOR = [
    ('1evcpctqlbp4w', '鄭玄', '崔靈恩', '撰', '南朝梁', 'nanbeichao',
     '《三禮義宗》是崔靈恩之書。本條所繫三節：舊唐志「崔靈恩撰」、'
     '宋志「成伯璵」、新唐志「又三禮義宗」，無一作鄭玄；'
     '「漢鄭玄撰」出《國立故宮博物院善本舊籍》目錄，誤。從志不從目錄。'
     '按：庫中別有《三禮義宗》1evr5e3meogul（崔靈恩，五節）與'
     '《三禮義宗崔靈恩撰》1evc5pdamhu68，本條正之後與之重出，待併'),
    ('1evcpct6ltp1c', '鄭玄', '侯苞', '傳', '漢', 'qin-han',
     '隋志「《韓詩翼要》十卷漢侯苞傳」、國史經籍志「（侯苞）」；'
     '舊唐志作「卜商撰」是託名子夏之說。三節無一作鄭玄，'
     '「漢鄭玄撰」出故宮目錄，誤'),
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


def note(d, txt):
    d['ai_note'] = ((d.get('ai_note') or '') + ('\n\n' if d.get('ai_note') else '')
                    + '2026-08-21 秦漢段磁鐵覆核（二）：' + txt)


def main():
    W = load()
    touched = set()

    for src, i, dst, why in MOVES:
        sd, dd = W[src][0], W[dst][0]
        node = sd['indexed_by'][i]
        print(f"移《{sd['title']}》[{i}] {node.get('source')}｜{node.get('title_info')} →《{dd['title']}》")
        sd['indexed_by'] = [r for j, r in enumerate(sd['indexed_by']) if j != i]
        dd.setdefault('indexed_by', []).append(node)
        note(sd, f'「{node.get("title_info")}」一節移繫《{dd["title"]}》{dst}——{why}。')
        note(dd, f'自《{sd["title"]}》{src} 移入「{node.get("title_info")}」一節——{why}。')
        touched |= {src, dst}

    for wid, i, why in MISATTACH:
        d = W[wid][0]
        r = d['indexed_by'][i]
        r['misattached'] = True
        r['misattached_note'] = why
        print(f"標《{d['title']}》[{i}] {r.get('source')}｜{r.get('title_info')} 為錯掛")
        note(d, f'「{r.get("title_info")}」一節標 misattached——{why}。')
        touched.add(wid)

    for wid, old, new, role, dyn, period, why in FIX_AUTHOR:
        d = W[wid][0]
        for a in d.get('authors') or []:
            if a.get('name') == old:
                a.update({'name': new, 'role': role, 'dynasty': dyn})
                a.pop('entity_id', None)      # 人既易，舊之繫人不可留
                a.pop('cbdb_id', None)
        if period and d.get('period') != period:
            d['period'] = period
            d['period_basis'] = f'撰人訂正為{new}（{dyn}）後隨之改'
        print(f"正《{d['title']}》撰人：{old} → {new}（{dyn}），period → {period}")
        note(d, f'撰人由「{old}」正作「{new}」——{why}。')
        touched.add(wid)

    if APPLY:
        for wid in touched:
            d, f = W[wid]
            with open(f, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(json.dumps(d, ensure_ascii=False, indent=2))
    print(f'\n涉 {len(touched)} 條' + ('' if APPLY else '　(dry-run)'))


if __name__ == '__main__':
    main()
