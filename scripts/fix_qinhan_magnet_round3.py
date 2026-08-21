#!/usr/bin/env python3
"""秦漢段磁鐵第三批：同題異書之節各歸其主。

用法：python scripts/fix_qinhan_magnet_round3.py [--apply]
"""
import json, glob, sys

APPLY = '--apply' in sys.argv

MOVES = [
    # 《喪服變除》一題三書：戴德、鄭玄、葛洪各一，庫中三主俱在
    ('1evcpcteyf85c', 6, '1evc5pcygjw1s',
     '補晉志「喪服變除一卷 葛洪。謹按見《隋志》」——葛洪本自是一書'),
    ('1evcpcteyf85c', 5, '1evc5pcygjw1s',
     '隋志「《喪服變除》一卷晉散騎常侍葛洪撰」——葛洪本自是一書'),
    ('1evcpcteyf85c', 0, '1evfa6oyt2scg',
     '舊唐志「《喪服變除》一卷鄭玄撰」——鄭玄本自是一書。'
     '本條餘節（清史稿、國史、經義考）皆明繫戴德，是戴德本'),
    # 王肅《毛詩注》之節誤繫毛公《毛詩》
    ('1evr5e3mjo9nk', 2, '1evr5e3m76run',
     '舊唐志「《毛詩》二十卷王肅注」——王肅注本自是一書'),
    ('1evr5e3mjo9nk', 1, '1evr5e3m76run',
     '隋志「《毛詩》二十卷王肅注」——同上。其下「梁有…鄭玄王肅合注、謝沈注、'
     '江熙注，亡」是隋志附記亡書之語，不隨本節移'),
]

MISATTACH = [
    ('1evfhd1qceqdc', 1,
     '舊唐志「《春秋外傳國語章句》二十二卷王肅注」——本條是鄭眾（鄭大司農）之章句'
     '（後漢志引韋昭《國語解序》「鄭大司農爲之訓注」為證），王肅另有其書，'
     '庫中無主，標記俟考定後別立'),
    ('1evcpjzo1035s', 0,
     '隋志「《易林》三卷魯洪度撰」——本條是舊題焦贛、清人考定為崔篆之《易林》'
     '（書目答問「舊題漢焦贛，依徐養原、牟廷相，定為漢崔篆」），'
     '魯洪度《易林》自是別書，庫中無主'),
    ('1evcpcuhe6874', 0,
     '舊唐志「《古文孝經》一卷劉邵注」——本條是孔安國傳本之敦煌殘卷，'
     '劉邵注本自是別書，庫中無主。按：本條題《古文孝經敦煌殘卷》而所繫'
     '隋志、崇文、四庫諸節皆論《古文孝經》通行本，題與節不相稱，待整體重排'),
]

FIX_AUTHOR = [
    ('1evcpcuy2fksg', '趙岐', '江灌', '注', '東晉', 'jin',
     '本條二節：舊唐志「《爾雅圖贊》二卷江灌注」、國史經籍志「（江瓘）」，'
     '皆作江灌（瓘）；「漢趙岐撰」出《國立故宮博物院善本舊籍》目錄，'
     '別無所據。從志不從目錄。按：《爾雅圖贊》本郭璞之作，'
     '二志所著錄者是江灌注本，原撰郭璞未見於本條諸節，未逕補'),
]

ADD_AUTHOR = [
    ('1ev7vo5sypszk', '鄭玄', '箋', '東漢',
     '本條五節有三節明書鄭箋：隋志「毛萇傳，鄭氏箋」、新唐志「鄭玄箋毛詩詁訓」、'
     '宋志「毛萇為詁訓傳，鄭玄箋」。本條所指正是毛傳鄭箋二十卷之合本'
     '（所掛十五部 Book 亦皆此本），而 authors 只列毛亨、毛萇，漏箋者'),
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
                    + '2026-08-21 秦漢段磁鐵覆核（三）：' + txt)


def main():
    W = load()
    touched = set()
    for src, i, dst, why in MOVES:
        sd, dd = W[src][0], W[dst][0]
        node = sd['indexed_by'][i]
        print(f"移《{sd['title']}》[{i}] {node.get('source')}｜{node.get('title_info')} →《{dd['title']}》")
        sd['indexed_by'] = [r for j, r in enumerate(sd['indexed_by']) if j != i]
        dd.setdefault('indexed_by', []).append(node)
        note(sd, f'「{node.get("title_info") or node.get("summary","")[:20]}」一節移繫'
                 f'《{dd["title"]}》{dst}——{why}。')
        note(dd, f'自《{sd["title"]}》{src} 移入一節——{why}。')
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
                a.pop('entity_id', None)
                a.pop('cbdb_id', None)
        if period:
            d['period'] = period
            d['period_basis'] = f'撰人訂正為{new}（{dyn}）後隨之改'
        print(f"正《{d['title']}》撰人：{old} → {new}（{dyn}），period → {period}")
        note(d, f'撰人由「{old}」正作「{new}」——{why}。')
        touched.add(wid)

    for wid, name, role, dyn, why in ADD_AUTHOR:
        d = W[wid][0]
        if any(a.get('name') == name for a in d.get('authors') or []):
            continue
        d.setdefault('authors', []).append({'name': name, 'role': role, 'dynasty': dyn})
        print(f"補《{d['title']}》撰人：{name}（{role}）")
        note(d, f'補「{name}」（{role}）於 authors——{why}。')
        touched.add(wid)

    if APPLY:
        for wid in touched:
            d, f = W[wid]
            with open(f, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(json.dumps(d, ensure_ascii=False, indent=2))
    print(f'\n涉 {len(touched)} 條' + ('' if APPLY else '　(dry-run)'))


if __name__ == '__main__':
    main()
