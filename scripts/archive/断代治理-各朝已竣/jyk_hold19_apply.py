#!/usr/bin/env python3
"""經義考待覈「庫中二條以上」19 條之裁決。

此 19 條之閘是「一條對庫中二書以上者一律不掛」。逐條翻庫而覈之，
**十六條實可決**——庫中二條之中，恆有一條與《經義考》所引之志的卷數
或題名嚴合，另一條是庫中重出或別書。餘三條真不可決。

判之所憑，依次：
  一、卷數與《經義考》所引之志相合者取之（隋志二十卷→《禮記鄭玄注》二十卷）
  二、題名夾撰人而剝之即得者取之（《禮記鄭玄注》剝「鄭玄」即「禮記注」）
  三、撰人異體（陸德明／陸元朗、袁曄／袁暐）不足以為異人
  四、《經義考》一題而庫分數條者（歐陽修《春秋論》三篇、倪元璐《兒易》
      內外儀），諸條並掛，各記其由——不擇一而掛

用法：python3 scripts/jyk_hold19_apply.py [--apply]
"""
import json, os, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import nz, load_index

DATA = '.claude/known-issues/經義考待覈.json'
SRC, SRC_BID = '經義考', '1ev3bb43bv4lc'
STATUS = {'佚': 'lost', '存': 'extant', '未見': 'not_seen', '闕': 'partial'}
NOTE = ('此是朱彝尊所判，非本庫之判，故不改本記錄之 loss_status。'
        '四庫御製題論此書曰「所注闕佚未見者，今四庫所録往往其書尚存」'
        '——其判是十七世紀一人之見聞。「未見」尤非亡佚，是朱氏未見其書。')

# head → (掛之對象 id 列, 何以取之)
ATTACH = {
 '朱氏（升）周易旁注前圖': (['1evdibhqb9am8'],
   '庫題《周易旁注前圖周易旁注》二卷，與本條著錄「二卷」合；另一條《旁注》十二卷非此書。'),
 '桓氏（𤣥）繫辭注': (['1evfubb80ka9s'],
   '庫題《周易繫辭注》二卷（東晉），與本條著錄「隋志二卷」合。'
   '另有《晉桓玄周易繫辭注》一卷，卷數不合，疑是輯本或庫中重出，交 S 車道。'),
 '謝氏（沉）尚書': (['1evd3dbargem8'],
   '庫題《尚書謝沈注》十五卷，與本條著錄「隋志十五巻」合。沉／沈異體。'),
 '王氏（安石）洪範傳': (['1evgopo65ef40'],
   '庫題《王安石洪範傳》一卷，與本條著錄「宋志一卷」合。'),
 '賀氏（循）喪服要紀': (['1evcpctf41hxc'],
   '庫中賀循《喪服要紀》二條，十卷者與本條著錄「隋志舊唐志十卷」合，取之；'
   '五卷者卷數不合，別是一本。'),
 '鄭氏（𤣥）禮記注': (['1ev7vo5ehfhts'],
   '庫題《禮記鄭玄注》二十卷，剝其所夾之撰人即「禮記注」，'
   '且卷數與本條著錄「隋志二十卷」合。庫中他條皆《注疏》《正義》，'
   '是鄭注孔疏合刻之本，非鄭玄注之單行，不可掛。'),
 '何氏（始眞）春秋左氏區别': (['1evc5pdr054ao'],
   '庫題《春秋左氏區別何始真撰》三十卷，與本條著錄「隋志三十巻」合。'
   '另有《何始真春秋左氏區別》十二卷，卷數不合，疑庫中重出，交 S 車道。'),
 '顧氏（啓期）大夫譜': (['1evfteolexcsg'],
   '庫題《春秋大夫譜》十一卷，與本條著錄「唐志十一巻」合。'
   '另有《顧啟期大夫譜》無卷數，疑庫中重出，交 S 車道。'),
 '陸氏（徳明）經典釋文': (['1ev3ba4k93wg0'],
   '庫題《經典釋文》三十卷，撰人作「陸元朗」——元朗是名，德明是字，一人也；'
   '卷數與本條著錄「唐志三十卷」合。另有《陸德明經典釋文》無卷數，'
   '疑庫中重出，交 S 車道。'),
 '吕氏（柟）涇野經説': (['1evkphuvsd7uo'],
   '庫題《呂涇野經說》二十一卷，與本條著錄「十卷（或作二十一卷）」之後說合。'),
 '蔡氏（仁）皇極經世衍數': (['1evga634m6wow'],
   '掛其正集《皇極經世衍數》五十卷。本條著錄「一百五十四卷」是全帙之數——'
   '庫中別有後集五十二卷、續集十六卷、別集十五卷、支集十五卷，'
   '諸集之數相加與之相近。正集為其本，故掛於此。'),
 '袁氏（曄）獻帝春秋': (['1evftejbw07b4'],
   '庫題《獻帝春秋》，撰人作「袁暐」——曄／暐一名之異寫，'
   '《隋志》《三國志》注所引互見。題名全同，取之。'),
 '虞氏（卿）春秋': (['1ev7xkie5dpts'],
   '庫題《虞氏春秋》十五篇，與本條著錄「漢志十五篇」篇數全合。'),
 '喬氏（萊）易俟': (['1ev0r91v7bu2o'],
   '庫題《喬氏易俟》，即喬萊《易俟》。另一條《易俟圖》是其圖，別為一書。'
   '按：庫作十八卷（四庫本之數）而本條著錄「六卷」，'
   '喬萊卒於康熙三十三年，朱彝尊所見或是早出之本，卷數之異記此存查，不改庫值。'),
 '歐陽氏（修）春秋論': (['1evi66meh0npc', '1evi66mkccbgg', '1evi66mq6q9kw'],
   '本條著錄「三篇」，而庫分《春秋論上》《春秋論中》《春秋論下》三條——'
   '《經義考》所著即此三篇之總。**三條並掛，不擇一**：擇一則其餘二篇失其著錄，'
   '而三篇本是一文之分。'),
 '倪氏（元璐）兒易': (['1evdibk04239c', '1evkabyzryqdc'],
   '本條著錄「内儀六卷外儀十五卷」，而庫分《兒易內儀以》六卷、《兒易外儀》二條——'
   '《經義考》所著即內外二儀之總。**二條並掛，不擇一**。'),
}

# head → 何以仍不可決
HOLD = {
 '張氏（特立）周易集說':
   '庫中張特立二條——《易集說》《集說》——皆無卷數，皆金人，'
   '而本條亦無著錄之數可比。二者疑即一書之兩截題（《周易集說》之省），'
   '是庫中重出而非二書；當先併而後掛，不可擇一。交 S 車道。',
 '薛氏（漢）韓詩章句':
   '庫中薛漢二條——《薛君韓詩章句》《漢薛漢韓詩章句》——皆二卷、皆東漢，'
   '**是庫中重出無疑**（二題皆「薛漢韓詩章句」之異寫，卷數復同）。'
   '本條著錄「隋志二十二卷」是原書之數，庫之二卷是輯本。'
   '當先併而後掛。交 S 車道。',
 '方氏（孔炤）周易時論':
   '本條著錄「十五卷」，而庫中方孔炤二條為《周易時論合編》二十二卷、'
   '《周易時論合編圖象幾表》八卷（其 measure_info 又記「周易時論合編十五卷」）。'
   '十五卷之數見於後者之附記而不見於前者之題，二條之分合本身即未清；'
   '強掛必誤其一。俟《周易時論合編》之卷帙釐清而後掛。',
}


def main():
    apply = '--apply' in sys.argv
    works = load_index('works')
    D = json.load(open(DATA, encoding='utf-8'))
    sub = [d for d in D if d['why'] == '庫中二條以上']

    # ── 先驗：所有 id 須在庫，且 head 須對得上 ──
    bad = [i for ids, _ in ATTACH.values() for i in ids if i not in works]
    if bad:
        print('！id 不在庫：', bad); return
    heads = {d['head'] for d in sub}
    miss = (set(ATTACH) | set(HOLD)) - heads
    extra = heads - (set(ATTACH) | set(HOLD))
    if miss or extra:
        print('！表與待覈之目不符  表有而目無:', miss, ' 目有而表無:', extra); return
    print(f'驗過：待覈 {len(sub)} 條，掛 {len(ATTACH)}、仍扣 {len(HOLD)}，'
          f'涉 work {sum(len(v[0]) for v in ATTACH.values())} 個')

    plan = collections.defaultdict(list)
    for d in sub:
        if d['head'] in ATTACH:
            ids, why = ATTACH[d['head']]
            for i in ids:
                plan[i].append((d, why, len(ids)))

    n_add = n_skip = 0
    for wid, items in plan.items():
        path = works[wid]['path']
        w = json.load(open(path, encoding='utf-8'))
        idx = w.setdefault('indexed_by', [])
        seen = {(e.get('source'), e.get('page')) for e in idx}
        for d, why, k in items:
            if (SRC, d['page']) in seen:
                n_skip += 1; continue
            ti = f"《{d['title']}》" + (f"（{d['author']}）" if d.get('author') else '')
            rec = {'source': SRC, 'source_bid': SRC_BID, 'title_info': ti,
                   'summary': '；'.join(d['attest']) if d['attest'] else '',
                   'section': d['lei'], 'juan': d['juan'], 'page': d['page'],
                   'attested_status': STATUS[d['status']],
                   'attested_status_raw': d['status'],
                   'attested_status_note': NOTE,
                   'link_basis': '2026-08-24 待覈「庫中二條以上」逐條裁：' + why
                                 + ('　（本條著錄一題而庫分數條，諸條並掛）' if k > 1 else '')}
            idx.append(rec); seen.add((SRC, d['page'])); n_add += 1
        if apply:
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(json.dumps(w, ensure_ascii=False, indent=2) + '\n')

    # 待覈之目：掛者移去，扣者改記其由
    rest = []
    for d in D:
        if d['why'] != '庫中二條以上':
            rest.append(d); continue
        if d['head'] in ATTACH:
            continue
        d['why'] = '庫中二條以上（2026-08-24 覆裁仍扣）'
        d['hold_basis'] = HOLD[d['head']]
        rest.append(d)

    print(f'掛源 {n_add} 條，涉 work {len(plan)} 個；已有而跳過 {n_skip}；'
          f'待覈 {len(D)} → {len(rest)}')
    if apply:
        with open(DATA, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(rest, ensure_ascii=False, indent=1) + '\n')
        print('已寫檔')
    else:
        print('（乾跑。加 --apply 方寫檔）')


if __name__ == '__main__':
    main()
