#!/usr/bin/env python3
"""補正乙1 之重出：庫題夾撰人於中，前次比對不中而重建

**此是本輪之失，記其由**：庫中頗有以「經名＋撰人＋役」立題者——《周易董遇
注》《周易何胤注》《尚書范寧注》——皆自《隋志》《舊唐志》之著錄語裁出。而
《經義考》之標目作「董氏（遇）周易註」，題只是《周易註》。二題既非全等
（「周易注」≠「周易董遇注」），亦不互為子串（撰人之名嵌在中間，非在首尾），
故甲1、甲2 兩閘俱不中，遂當作庫中無此書而新建，是造重出。

覺之之由：入乙1 之「稱篇不稱卷」閘時，見《漢志》諸條之撰人在庫中另有其書
（王同對《周易王氏》、丁寬對《周易丁氏》），乃知庫中另有一路題式，回頭覆
按已建之六百條，得同撰人者 230，剔名後相似者 35。

裁法：逐條看，不批量。35 條之中——

  併 31：剔撰人之名後兩題相合，或只差異體（統／綂、辯／辨、默／嘿、序／
         敘），或《經義考》自注其異（韓滉《春秋通例》注「唐志無例字」，
         劉炫《古文孝經義疏》注「隋唐志作述義」），皆一書。
  不併 4：
    公羊高《春秋傳》     庫之《春秋公羊傳注疏》是何休解詁、徐彥疏，非
                        公羊高之本傳。SCHEMA〈同題二條〉第六則：一方是
                        注疏，對方疑即原典，絕不可併。
    劉叔嗣《尚書注》     庫之《尚書亡篇序劉叔嗣注》，隋志本文自云「梁有
                        《尚書》二十一卷，劉叔嗣注」——是隋志自己把二書
                        分著。《經義考》七錄二十一卷正是後者。
    蕭子顯《孝經義疏》   庫之《孝經敬愛義》出隋志，題全異而俱一卷。七錄
                        與隋志各著一題，未可遽定其為一書。
    毛萇《詩傳》         庫之《毛詩詁訓傳》其 indexed_by 所繫宋志作「呂祖
                        謙」，是庫方此條自身有疑，不可據以併。另記。

併法：刪本輪所建之 work（連索引），改掛源於庫中原有之條。
"""
import json, os, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import load_index
from jyk_attach_source import SRC, SRC_BID, STATUS, NOTE
from jyk_create_works import shard

DATA = '.claude/known-issues/經義考待裁.json'
HOLD = '.claude/known-issues/經義考乙1重出待覈.json'

# 經義考標目 → 庫中原有之 work id。逐條裁定，見檔首。
MERGE = {
    '馬氏（融）周易注（或作傳）': '1evgop25dr1fk',
    '董氏（遇）周易註（釋文序録作章句）': '1evdmdheneeps',
    '何氏（𦙍）周易注': '1evc5p8kwipds',
    '王氏（又𤣥）周易注': '1evcubrzqxf5s',
    '王氏（𤣥度）周易注': '1evcubrzdi7sw',
    '范氏（寗）尚書注（經典序録作集解）': '1evfubez44u0w',
    '鄭氏（𤣥）喪服譜注': '1evc5pcy0bjsw',
    '陶氏（𢎞景）論語集注': '1evetxcydz6kg',
    '韓氏（滉）春秋通例（唐志無例字）': '1evdxnpuaqy2o',
    '尹氏（毅）論語注釋': '1evetxcy6hhj4',
    '段氏（肅）春秋榖梁傳注': '1evc5pdzm3rpc',
    '唐氏（固）春秋榖梁傳注': '1evc5pdzg69ds',
    '韋氏（表微）春秋三傳緫例': '1evdxnpri8j5s',
    '劉氏（炫）古文孝經義疏（隋唐志作述義）': '1evc5pe5emakg',
    '后氏（蒼）齊故': '1evgopsmji7eo',
    '孫氏（畧）周官禮駮難': '1evc5pctgfym8',
    '孔氏（衍）春秋榖梁傳（唐志作訓注）': '1evc5pdzqsbuo',
    '顧氏（歡）毛詩集解序義': '1evc5pcmbjnk0',
    '徐氏（乾）春秋榖梁傳注': '1ewsa4a57jclw',
    '鄒氏（湛）周易綂畧': '1evc5p8o74vsw',
    '韓氏（康伯）繫辭注': '1evdmdm6uc6bk',
    '王氏（肅）尚書駮議（唐志作釋駮）': '1evc5pccni1vk',
    '嚴氏（彭祖）春秋左氏圖': '1evdxnpesbe9s',
    '劉氏（兆）春秋公羊榖梁傳解詁': '1evc5pdyhix34',
    '張氏（靖）榖梁傳注': '1evc5pe0s8t1c',
    '沈氏（宏）春秋五辨': '1evc5pdrwx1c0',
    '虞氏（喜）論語讚鄭氏注': '1ewsa4afakcfi',
    '范氏（甯）春秋榖梁傳集解': '1evc5pdz6hwjk',
    '徐氏（整）孝經嘿注': '1evc5pe3jtibk',
    '王氏（元感）注孝經': '1evgoqsd72ubk',
    '田氏（僧紹）集解喪服經傳': '1evc5pcw72y9s',
}
KEEP = {
    '公羊髙春秋傳': '庫之《春秋公羊傳注疏》是何休解詁徐彥疏，非公羊高之本傳',
    '劉氏（叔嗣）尚書注': '隋志本文自云「梁有《尚書》二十一卷，劉叔嗣注」，與《尚書亡篇序》分著',
    '蕭氏（子顯）孝經義疏': '庫之《孝經敬愛義》出隋志，題全異而俱一卷，未可遽定為一書',
    '毛氏（萇）詩傳': '庫之《毛詩詁訓傳》其宋志一源作「呂祖謙」，庫方此條自身有疑',
}


def main():
    apply = '--apply' in sys.argv
    works = load_index('works')
    D = json.load(open(DATA))
    by_head = {d['head']: d for d in D}

    todo = []
    for head, tgt in MERGE.items():
        d = by_head.get(head)
        if d is None or not d.get('created_work'):
            print('！找不到或未建：', head)
            continue
        if tgt not in works:
            print('！標的不在庫：', head, tgt)
            continue
        todo.append((d, tgt))
    print(f'待併 {len(todo)}／{len(MERGE)}；留 {len(KEEP)}')
    if not apply:
        print('（乾跑。加 --apply 方寫檔）')
        return

    shards = {s: json.load(open(f'index/works/{s}.json')) for s in '0123456789abcdef'}
    for d, tgt in todo:
        wid = d['created_work']
        # 一、刪本輪所建之 work
        p = works[wid]['path']
        if os.path.exists(p):
            os.remove(p)
        shards[shard(wid)].pop(wid, None)
        # 二、改掛源於庫中原有之條
        tp = works[tgt]['path']
        w = json.load(open(tp))
        idx = w.setdefault('indexed_by', [])
        if not any(e.get('source') == SRC and e.get('page') == d['page'] for e in idx):
            idx.append({
                'source': SRC, 'source_bid': SRC_BID,
                'title_info': f"《{d['title']}》" + (f"（{d['author']}）" if d.get('author') else ''),
                'summary': '；'.join(d['attest']) if d['attest'] else '',
                'section': d['lei'], 'juan': d['juan'], 'page': d['page'],
                'attested_status': STATUS[d['status']],
                'attested_status_raw': d['status'],
                'attested_status_note': NOTE,
                'note': f'本條前次誤判為庫中所無而新建（{wid}），旋覺庫題《{w["title"]}》'
                        f'是「經名＋撰人＋役」之式，撰人之名嵌於題中，故兩閘俱不中。'
                        f'今刪所建，改掛此處。'})
        with open(tp, 'w', encoding='utf-8') as f:
            json.dump(w, f, ensure_ascii=False, indent=2)
            f.write('\n')
        d.pop('created_work', None)
        d['attached_to'] = tgt

    for s, obj in shards.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8') as f:
            json.dump(dict(sorted(obj.items())), f, ensure_ascii=False, indent=2)
            f.write('\n')
    json.dump(D, open(DATA, 'w'), ensure_ascii=False, indent=1)
    json.dump([{'head': k, 'why': v, 'created_work': by_head[k].get('created_work')}
               for k, v in KEEP.items() if k in by_head],
              open(HOLD, 'w'), ensure_ascii=False, indent=1)
    print('已併', len(todo))


if __name__ == '__main__':
    main()
