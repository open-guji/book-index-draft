#!/usr/bin/env python3
"""經義考待覈「不著撰人」161 條：以論斷與標目之姓決其十六

此 161 條之閘是「庫中同題二條以上而本條不著撰人，掛之必誤其一」。
然「不著撰人」只就**標目解析所得之 author 欄**而言，其人未必真不可知——
本輪不從撰人欄下手，改從二處：

**一、論斷**。《經義考》一條之論斷，其首所引每即該書之著錄或其撰人之傳：
  《周易林》論斷首句「隋書魏少府丞管輅撰」即隋志之著錄語；
  《周禮集説》論斷「陳友仁序曰」是撰人**自序**；
  《孟子音義》論斷「奭撰進序曰」是孫奭**自序**；
  《春秋集傳》論斷「周必大作墓志曰葆字彦光」是撰人**墓志**。
  以歸一後之候選撰人名比對論斷，**再逐條讀論斷全文而後定**——不以命中為準。

**二、標目之姓**。標目作「X氏（失名）題」者，X 是姓而非缺文；
  庫中同題諸條若恰有一條姓 X，即其人（趙氏《讀易記》、周氏《論語章句》、
  姜氏《孝經説》，庫中之撰人欄正作「趙氏」「周氏」「姜氏」）。

**只命中而不讀論斷者必誤，有實例**：《孟子音義》以名相比命中「張鎰」，
而論斷實是孫奭之進序，其中「為之音者則有張鎰丁公著……張氏則徒分章句漏略頗多」
——張鎰是孫奭所訂正之前人，非本書撰人。**若逕從命中，恰好掛反。**
故本表逐條讀論斷全文而定，命中只用來縮小範圍。

又：條之鍵用 `page` 不用 `head`——同題之條多有數見（《周易林》二、《毛詩音》四、
《爾雅圖讚》二），以 head 為鍵必張冠李戴。

用法：python3 scripts/jyk_lun_attach.py [--apply]
"""
import json, os, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import load_index

HOLD = '.claude/known-issues/經義考待覈.json'
SRC, SRC_BID = '經義考', '1ev3bb43bv4lc'
STATUS = {'佚': 'lost', '存': 'extant', '未見': 'not_seen', '闕': 'partial'}
NOTE = ('此是朱彝尊所判，非本庫之判，故不改本記錄之 loss_status。'
        '四庫御製題論此書曰「所注闕佚未見者，今四庫所録往往其書尚存」'
        '——其判是十七世紀一人之見聞。「未見」尤非亡佚，是朱氏未見其書。')

# page → (work_id, 何以定之)
ATTACH = {
 'KR2n0011_WYG_010-4a|周易林': ('1evftespybqio',
   '論斷首句「隋書魏少府丞管輅撰」即《隋志》之著錄語，是朱氏逕錄其撰人；'
   '其下趙汝楳、胡一桂、郝敬三家所論亦皆論管輅之占。庫條四卷，'
   '合本條著錄「唐志五行家四卷」。'),
 'KR2n0011_WYG_011-8b|易八卦命錄斗内圖': ('1evfuv0yermkg',
   '論斷全文是《晉書》郭璞本傳（字景純、河東聞喜人、受青囊書、撰《洞林》）。'
   '庫條一卷，合本條著錄「隋志五行家一卷」；另一候選不著撰人。'),
 'KR2n0011_WYG_012-11a|周易集林': ('1evcpjod0sow0',
   '論斷全文是《南史》伏曼容本傳，末言其「為周易毛詩喪服集解老莊論語義」。'
   '庫條十二卷，合本條著錄「唐志十二卷」。按：庫中別有《周易集林》繫「伏氏」'
   '（一卷）、「伏萬壽」二條，與本條之屬同姓，其分合交 S 車道。'),
 'KR2n0011_WYG_054-7b|易辨': ('1ev0r92frqqkg',
   '論斷全文是陳子龍、陸元輔論豐坊（字存禮、鄞縣人、嘉靖二年進士、'
   '好偽撰古本）。庫條一卷，合本條著錄「一卷」。'),
 'KR2n0011_WYG_125-17b|周禮集説': ('1evgbrxbsygow',
   '論斷首句「陳友仁序曰」是撰人**自序**。庫條十二卷，合本條著錄「十二卷」；'
   '另一候選繫俞庭椿。'),
 'KR2n0011_WYG_173-4a|春秋公羊傳注': ('1evfhb6r9usjk',
   '論斷「吳錄固字子正吳志丹陽唐固修身積學稱為儒者**著國語公羊榖梁傳注**」'
   '——明言唐固著《公羊傳注》。另一候選繫高龍。'),
 'KR2n0011_WYG_184-17b|春秋集傳': ('1evr5e3mjzi1y',
   '論斷首句「周必大作墓志曰葆字彦光呉郡崑山人……尤邃於春秋」是撰人**墓志**。'
   '庫條十五卷，合本條著錄「宋志十五卷」。庫中同題十五條，撰人各異，'
   '唯王葆一條與論斷相值。'),
 'KR2n0011_WYG_233-3b|孟子音義': ('1ev3ba58cke0w',
   '**此條最須逐條讀**。以名相比則命中「張鎰」，然論斷實是孫奭之**進序**，'
   '其文曰「為之音者則有張鎰丁公著……張氏則徒分章句漏略頗多……'
   '若非刋正詎可通行」——張鎰是孫奭所訂正之前人，非本書撰人。'
   '本條當掛孫奭之二卷本，合著錄「宋志二卷」（張鎰本三卷）。'),
 'KR2n0011_WYG_237-11a|爾雅音': ('1evgor8i1j3eo',
   '論斷「顔之推曰孫叔然創爾雅音義是漢末人獨知反語」——叔然即孫炎之字，'
   '其下復引訪碑錄之孫炎碑。庫中同題五條（顧野王、施乾、江灌、謝嶠、孫炎），'
   '唯孫炎與論斷相值。按：庫條一卷而本條著錄「七録二卷（釋文序録一巻）」，'
   '一卷合《釋文·序錄》之數，二卷是《七錄》之數，卷數兩存不相礙。'),
 'KR2n0011_WYG_237-13a|爾雅圖讚': ('1evfubxke6fb4',
   '論斷「鄭樵曰爾雅圖蓋本郭注而為圖……有郭璞注則其圖可圖也」，是論郭璞。'
   '庫條二卷，合本條著錄「七録二卷」。'),
 'KR2n0011_WYG_237-14a|爾雅圖讚': ('1evcpcuy2fksg',
   '同卷之另一《爾雅圖讚》條。論斷「晉書灌字道羣陳留圉人……**著爾雅圖二巻'
   '音六卷讚二卷**」是江灌本傳，明言其著《爾雅圖讚》。'
   '本條著錄「唐志一卷」，與 13a 條之「七録二卷」異，二條本非一書。'),
 'KR2n0011_WYG_239-28a|鄭記': ('1evcpcut472m8',
   '論斷首句「隋書鄭𤣥弟子撰」即《隋志》之著錄語，庫條之撰人欄正作'
   '「鄭玄弟子」；六卷合本條著錄「隋志六卷」。'),
 'KR2n0011_WYG_265-12a|詩緯': ('1evcpcuqn8fsw',
   '論斷「張衡曰……**隋書魏博士宋均注**」，末句即《隋志》之著錄語。'
   '庫條十八卷，合本條著錄「隋志十八卷」。'),
 'KR2n0011_WYG_048-17a|趙氏（失名）讀易記': ('1evgb9490c9vk',
   '標目作「趙氏（失名）讀易記」——趙是姓，非缺文。庫中同題八條，'
   '唯一條之撰人欄正作「趙氏」，即其人。'),
 'KR2n0011_WYG_211-16a|周氏（失名）論語章句': ('1evr5e3mezpih',
   '標目作「周氏（失名）論語章句」，庫中同題三條（周氏、劉炫、包咸），'
   '唯周氏一條相值。論斷「陸徳明曰**不詳何人**邢昺曰包氏周氏就張侯論為之'
   '章句訓解」——「不詳何人」正解其標目之「失名」，是周氏一條無疑；'
   '包咸自有其條，不相混。'),
 'KR2n0011_WYG_227-14a|姜氏（失名）孝經説': ('1evga192gnny8',
   '標目作「姜氏（失名）孝經説」，庫中同題六條，唯一條之撰人欄正作「姜氏」；'
   '其一卷復合本條著錄「一卷」。'),
}

# page → 何以仍扣
HOLD_WHY = {
 'KR2n0011_WYG_101-10b|毛詩音':
   '論斷「陸德明曰**爲詩音者九人**鄭康成徐邈蔡氏孔氏阮侃王肅江惇于寳李軌」'
   '——一口氣列九人，正是不可指之證，非可指而未指。',
 'KR2n0011_WYG_101-13a|毛詩音':
   '論斷引陸德明、歐陽修論王肅之毛詩説，然**通篇不及「音」字**，'
   '是論王肅之毛詩學而非論其《毛詩音》。庫中同題八條，'
   '以此掛王肅是以論其學者當論其書，不足為據。',
 'KR2n0011_WYG_010-20a|易辨':
   '論斷「陳振孫曰……舘閣書目**王弼易辨一卷**」指本書為王弼作，'
   '而庫中同題五條無一繫王弼——依 SCHEMA〈同題異撰是二書〉當新建，非掛。'
   '惟其撰人出於論斷所引之書目而非標目，立書而繫撰人須另裁，本輪不建。',
 'KR2n0011_WYG_011-7b|周易林':
   '無論斷。著錄「七録五行家六卷」，而庫中同題六條無一為六卷，無可比之欄。',
 'KR2n0011_WYG_010-24b|周易集林':
   '無論斷。著錄「隋志五行家一卷」，庫中「伏氏」一條正一卷，然「伏氏」'
   '與「伏曼容」「伏萬壽」三條之分合本身未清（見 012-11a 條之按），'
   '先掛必牽動其判，俟 S 車道釐清而後掛。',
 'KR2n0011_WYG_277-3b|李氏（失名）春秋':
   '標目「李氏（失名）春秋」，庫中《春秋》五條唯一條撰人作「李氏」'
   '（`1ev7xkhqvkruo`，二篇，合著錄「漢志二篇」），本可掛；'
   '**惟該條屬先秦域，他會話所主，本輪一律不動**，故扣。'
   '所需之據已備，先秦域一路可逕掛。',
}


def main():
    apply = '--apply' in sys.argv
    works = load_index('works')
    bad = [w for w, _ in ATTACH.values() if w not in works]
    if bad:
        print('！id 不在庫：', bad); return
    D = json.load(open(HOLD, encoding='utf-8'))
    sub = [r for r in D if r['why'].startswith('庫中同題二條以上而本條不著撰人')]
    # 鍵用 page＋head：同一葉每有二條（102-6b 之蔡氏、孔氏《毛詩音》即是），
    # 單以 page 為鍵必張冠李戴
    bypage = {f"{r['page']}|{r['head']}": r for r in sub}
    dup = len(sub) - len(bypage)
    if dup: print(f'！同一 page＋head 有 {dup} 條相重，鍵不唯一'); return
    miss = (set(ATTACH) | set(HOLD_WHY)) - set(bypage)
    if miss: print('！表列之 page 不在待覈之目：', miss); return
    print(f'驗過：不著撰人 {len(sub)} 條，掛 {len(ATTACH)}、明記其扣 {len(HOLD_WHY)}')

    plan = collections.defaultdict(list)
    for pg, (wid, why) in ATTACH.items():
        plan[wid].append((bypage[pg], why))
    n_add = 0
    for wid, items in plan.items():
        path = works[wid]['path']
        w = json.load(open(path, encoding='utf-8'))
        idx = w.setdefault('indexed_by', [])
        seen = {(e.get('source'), e.get('page')) for e in idx}
        for r, why in items:
            if (SRC, r['page']) in seen: continue
            idx.append({
                'source': SRC, 'source_bid': SRC_BID,
                'title_info': f"《{r['title']}》",
                'summary': '；'.join(r['attest']) if r['attest'] else '',
                'section': r['lei'], 'juan': r['juan'], 'page': r['page'],
                'attested_status': STATUS[r['status']],
                'attested_status_raw': r['status'],
                'attested_status_note': NOTE,
                'link_basis': '2026-08-24 待覈「不著撰人」逐條裁（據論斷或標目之姓）：' + why})
            n_add += 1
            print(f"  掛 {wid} 《{works[wid]['title']}》{works[wid].get('author')} ← {r['head']} p{r['page']}")
        if apply:
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(json.dumps(w, ensure_ascii=False, indent=2) + '\n')

    rest = []
    for d in D:
        _k = f"{d['page']}|{d['head']}"
        if _k in ATTACH and d in sub: continue
        if _k in HOLD_WHY and d in sub:
            d = dict(d); d['hold_basis'] = HOLD_WHY[_k]
        rest.append(d)
    print(f'掛源 {n_add} 條，涉 work {len(plan)} 個；待覈 {len(D)} → {len(rest)}')
    if apply:
        with open(HOLD, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(rest, ensure_ascii=False, indent=1) + '\n')
        print('已寫檔')
    else:
        print('（乾跑。加 --apply 方寫檔）')


if __name__ == '__main__':
    main()
