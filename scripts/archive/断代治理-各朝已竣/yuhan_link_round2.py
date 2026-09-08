#!/usr/bin/env python3
"""《玉函山房輯佚書》未繫節第二輪：補繫六節

前輪（scripts/yuhan_link.py）之閘是 `if s.get('work_id') or not s.get('author')`
——**輯本不著撰人之節一概跳過**，故餘 42 節中三十餘節根本未經比對。
前記謂「庫中同題二至六條而各不著撰人，無可比之欄」，實測不然：**庫中諸條
多有撰人**，無撰人的是輯本那一側。

據此改二法，得六節：

一、**諸候選之撰人實同一人者，其分立本身是庫中重出**，可繫其備者。
   《魏略》二條皆魚豢（一條撰人欄空而《舊唐志》著錄語明書「魚豢撰」）、
   《趙書》二條皆田融。此類繫其著錄較備之條，而以重出交 S 車道。

二、**候選唯一而輯本亦不著撰人者可繫**。前輪立「候選唯一即繫不可」之戒，
   是因五節候選雖唯一而**撰人相牴**；輯本無撰人則無所牴，其戒不適用。
   《宋紀》（王智深）、《逸士傳》（皇甫謐）、《相貝經》（嚴助）皆此類。

三、《周官禮義疏》一節另有其由：輯本撰人「沉重」，而庫題《周官禮義疏沈重撰》
   夾撰人於題中，剝之即合，且《隋志》禮類正著「《周官禮義疏》四十卷沈重撰」
   ——前輪以題名相等為比，故漏之。此即《經義考》一路所立之「甲4 夾撰人」。

用法：python3 scripts/yuhan_link_round2.py [--apply]
"""
import json, glob, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import load_index

YH = '1evjr68pzxog0'
DIR = f'Work/1/e/v/{YH}/collated_edition'

# book_title → (work_id, 何以繫之)
LINK = {
 '周官禮義疏': ('1evc5pcu03wu8',
   '輯本撰人「沉重」，庫題《周官禮義疏沈重撰》四十卷夾撰人於題中，剝之即本節之題；'
   '《隋書經籍志》禮類正著「《周官禮義疏》四十卷沈重撰」，撰人卷數俱合。'
   '庫中另三條（十九卷、十卷、九卷）皆《隋志》同題而不著撰人之別本，非此。'),
 '魏略': ('1evftej5cn9q8',
   '庫中《魏略》二條**同是魚豢之書**——本條五十卷（《新唐志》《國史經籍志》'
   '皆繫魚豢），另一條三十八卷雖撰人欄空而《舊唐書經籍志》著錄語明書「魚豢撰」。'
   '繫其著錄較備者。二條之分（五十／三十八）交 S 車道。'),
 '趙書': ('1evcml41xe77k',
   '庫中《趙書》二條**同是田融之書**——本條十卷，《隋志》著「偽燕太傅長史田融撰」，'
   '《補晉書藝文志》復引之；另一條二十卷出《國史經籍志》亦繫田融。'
   '繫其著錄較備者。二條之分（十／二十）交 S 車道。'),
 '宋紀': ('1evgpgy0trl6o',
   '庫中同題唯此一條，王智深撰三十卷，《舊唐志》《新唐志》《國史經籍志》三志皆合；'
   '輯本不著撰人，故無所牴。'),
 '逸士傳': ('1evcml30rubk0',
   '庫中同題唯此一條，皇甫謐撰一卷，《隋志》著「《逸士傳》一卷皇甫謐撰」，'
   '四志皆合；輯本不著撰人，故無所牴。'),
 '相貝經': ('1evgpi1dbfq4g',
   '庫中同題唯此一條，一卷，《國史經籍志》繫嚴助（《直齋書錄解題》云「不知作者」）；'
   '輯本不著撰人，故無所牴。'),
}


def main():
    apply = '--apply' in sys.argv
    works = load_index('works')
    bad = [w for w, _ in LINK.values() if w not in works]
    if bad:
        print('！id 不在庫：', bad); return

    files, hits = {}, []
    for f in sorted(glob.glob(DIR + '/*.json')):
        if 'index' in f:
            continue
        cd = json.load(open(f, encoding='utf-8'))
        files[f] = cd
        for i, s in enumerate(cd['sections']):
            if s.get('work_id'):
                continue
            bt = s.get('book_title')
            if bt in LINK:
                hits.append((f, i, s, *LINK[bt]))
    print(f'表列 {len(LINK)} 題，命中未繫之節 {len(hits)}')
    for f, i, s, wid, why in hits:
        print(f"  繫 《{s.get('book_title')}》{s.get('author')} → {wid} "
              f"《{works[wid]['title']}》{works[wid].get('author')}")
    miss = set(LINK) - {s.get('book_title') for _, _, s, _, _ in hits}
    if miss:
        print('！表有而節無（或已繫）：', miss)
    if not apply:
        print('（乾跑。加 --apply 方寫檔）')
        return
    for f, i, s, wid, why in hits:
        s['work_id'] = wid
        s['link_basis'] = '2026-08-24 第二輪：' + why
        s.pop('unlinked_reason', None)
    for f, cd in files.items():
        with open(f, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(json.dumps(cd, ensure_ascii=False, indent=2) + '\n')
    print('已寫檔。次當跑 scripts/yuhan_fragments.py --apply 補其輯佚檔')


if __name__ == '__main__':
    main()
