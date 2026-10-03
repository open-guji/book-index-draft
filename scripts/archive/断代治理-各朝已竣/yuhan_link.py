#!/usr/bin/env python3
"""《玉函山房輯佚書》整理本 48 未繫節之逐條裁

`D3-玉函山房未繫節複測.json`（2026-08-22）留 48 節未繫，其判是「三十餘條輯本
亦不著撰人，庫中同題二至六條而各不著撰人，無可比之欄……非本輪可決」。

今再試三法，二法無所得，據實記之：

  **候選唯一即繫**——不可。五節之候選雖唯一而撰人相牴（輯本作羅含而庫作張
  謂、輯本作顧夷而庫作蕭子良），繫之即以甲書繫乙名。
  **以類收窄**——不可。四十一節之多候選，以輯本之類（易類、五經總類）比對
  候選之 `indexed_by[].section`，只二節收至唯一，而二者撰人皆不合（輯本作
  「武帝」而所收者時少章、輯本作許慎而所收者張遐），是偶合非真解。

**可決者只在輯本自著撰人之十五節**，逐條讀之：

  繫一：《周易大義》輯本作「武帝」，庫有《周易大義》蕭衍（南朝梁）——梁武帝
        即蕭衍，是一人。
  建五：《渾儀》張衡、《孝子傳》劉向、《高士傳》嵇康、《纂要》元帝（梁元帝
        蕭繹）、《神農本草》吳普等。此五書皆別有明徵，而庫中同題諸條之撰人
        無一相符，依 SCHEMA〈同題二條〉「同題異撰是二書」別建。
  留九：或輯本之繫本可疑（《典論》繫荀悅而《典論》是曹丕之書、《五經通義》
        繫許慎而許慎所撰是《五經異義》、《周易王氏義》一繫王充一繫王嗣宗而
        隋志作晉王宏）、或題名過泛（《補遺》《義記》）、或是注非撰（《禽經》
        舊題師曠撰、張華注，庫中師曠一條即其書，依「注本與原典絕不可併」不
        繫）、或前輪已裁不繫（《湘中記》）。

**餘三十三節輯本亦不著撰人者一概不動**——庫中同題二至六條而各不著撰人，無
可比之欄；非得輯本正文或他志之著錄語補出撰人，不能決。
"""
import json, glob, os, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import nz, load_index
from jyk_create_works import shard, mkid

YH = '1evjr68pzxog0'
DIR = f'Work/1/e/v/{YH}/collated_edition'

LINK = {('周易大義', '武帝'): ('1evcpcsue0bnk', '輯本作「武帝」，庫作蕭衍（南朝梁）——梁武帝即蕭衍')}
CREATE = {
    ('渾儀', '張衡'): '張衡撰《渾儀》別有明徵（《後漢書》本傳、《隋志》天文類），'
                      '而庫中同題二條一無撰人、一繫歐陽發（北宋），無一相符',
    ('孝子傳', '劉向'): '劉向《孝子傳》歷代著錄不絕，而庫中同題七條分繫蕭衍、宋躬、'
                        '虞槃佐、徐廣、蕭廣濟、師覺授、鄭緝之，無一相符',
    ('高士傳', '嵇康'): '嵇康撰《聖賢高士傳贊》，馬氏題作《高士傳》；庫中同題三條'
                        '分繫皇甫謐（二條）、虞盤佐，無一相符',
    ('纂要', '元帝'): '梁元帝蕭繹撰《纂要》別有明徵；庫中同題三條一無撰人、'
                      '餘繫戴安道、顏延之，無一相符',
    ('神農本草', '吳普等'): '吳普《本草》（世稱《吳普本草》）別有明徵；庫中同題二條'
                            '繫陶隱居、雷公，無一相符',
}
HOLD = {
    ('周易王氏義', '王嗣宗'): '隋志作「晉驃騎將軍王宏撰」，庫中二條繫王宏、王濟；'
                              '嗣宗之名於此書無徵，輯本之繫可疑',
    ('周易王氏義', '王充'): '同上。王充所撰是《論衡》，於《周易王氏義》無徵',
    ('典論', '荀悅'): '《典論》是魏文帝曹丕之書，庫中一條正繫文帝；荀悅所撰是'
                      '《申鑒》。輯本置之道家類而繫荀悅，其繫可疑',
    ('五經通義', '許慎'): '許慎所撰是《五經異義》；庫中同題五條繫劉炫、宋翔鳳、'
                          '曹褎、劉向、張遐，無一相符而輯本之繫亦可疑',
    ('周官禮義疏', '沉重'): '沈重（北周）撰《周禮義疏》有徵，然庫中同題三條俱不著'
                            '撰人，不能定其為三者之一抑三者之外，繫之必誤其二',
    ('禽經', '張華'): '《禽經》舊題師曠撰、張華注，庫中師曠一條即其書。'
                      'SCHEMA〈同題二條〉第六則：注本與原典絕不可併',
    ('湘中記', '羅含'): '2026-08-22 已裁不繫——輯本繫羅含（東晉）而庫中此條繫張謂，'
                        '三家著錄俱作一卷而歸張謂；羅含《湘中記》隋志作三卷，'
                        '疑本庫尚無其條。此屬著錄歸屬之疑',
    ('補遺', '劉熙'): '題名過泛，庫中無同題；且「補遺」疑是輯本之附錄非獨立之書',
    ('義記', '顧夷'): '題名過泛。庫中同題一條繫蕭子良，與顧夷不相涉',
}


def main():
    apply = '--apply' in sys.argv
    works = load_index('works')
    taken = set(works)
    files = {f: json.load(open(f)) for f in glob.glob(DIR + '/*.json') if 'index' not in f}
    todo_link, todo_new = [], []
    for f, cd in files.items():
        for i, s in enumerate(cd['sections']):
            if s.get('work_id') or not s.get('author'):
                continue
            k = (s.get('book_title'), s['author'])
            if k in LINK:
                todo_link.append((f, i, s, *LINK[k]))
            elif k in CREATE:
                todo_new.append((f, i, s, CREATE[k]))
    print(f'繫既有 {len(todo_link)}；新建 {len(todo_new)}；留 {len(HOLD)}')
    for f, i, s, wid, why in todo_link:
        print(f"  繫 《{s['book_title']}》{s['author']} → {wid}（{why}）")
    for f, i, s, why in todo_new:
        print(f"  建 《{s['book_title']}》{s['author']}")
    if not apply:
        print('（乾跑。加 --apply 方寫檔）')
        return

    shards = {x: json.load(open(f'index/works/{x}.json')) for x in '0123456789abcdef'}
    for f, i, s, wid, why in todo_link:
        s['work_id'] = wid
        s['link_basis'] = why
        s.pop('unlinked_reason', None)
    for f, i, s, why in todo_new:
        t = s['book_title']
        a = s['author']
        wid = mkid(f"yuhan|{s.get('lei')}|{t}|{a}", taken)
        path = f'Work/{wid[0]}/{wid[1]}/{wid[2]}/{wid}-{t}.json'
        rec = {'schema_version': 1, 'type': 'work', 'title': t, 'id': wid,
               'authors': [{'name': a, 'role': None}],
               'ai_note': f'本 work 據《玉函山房輯佚書》目錄（光緒九年長沙嫏嬛館補校刊本）'
                          f'新建——該叢書{s.get("lei")}著錄「{t}{s.get("measure") or ""}卷」'
                          f'而繫「{a}」，本庫先前雖有同題之 work，撰人無一相符。'
                          f'{why}。依 SCHEMA〈同題二條〉「同題異撰是二書」別建。\n\n'
                          f'所記止於目錄所有。`period`／`loss_status`／`role`／'
                          f'`entity_id` 不繫——目錄只給題、卷數、人名，繫人定代'
                          f'須另考。本書之輯佚著錄見同目錄下 fragments/。'}
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
        shards[shard(wid)][wid] = {'id': wid, 'title': t, 'type': 'Work',
                                   'path': path, 'author': a}
        s['work_id'] = wid
        s['link_basis'] = '本輪據目錄所繫之撰人新建（' + why + '）'
        s.pop('unlinked_reason', None)
    for f, cd in files.items():
        with open(f, 'w', encoding='utf-8') as fh:
            json.dump(cd, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
    for x, obj in shards.items():
        with open(f'index/works/{x}.json', 'w', encoding='utf-8') as fh:
            json.dump(dict(sorted(obj.items())), fh, ensure_ascii=False, indent=2)
            fh.write('\n')
    print('繫', len(todo_link), '建', len(todo_new))


if __name__ == '__main__':
    main()
