#!/usr/bin/env python3
"""宋志「頂真格」誤讀所致之七條錯掛：各歸其主

`period_upper` 補標時浮出十三條「已有 period 而所繫之志給出更早之上限」，
其中七條同型：**一清（或明）人之書，身上掛著一則《宋史藝文志》之著錄**。
清人之書不可能見於元脫脫所修之宋志，故其節必不屬本條。

**其真主可讀**——宋志匯入之節作「`[本條撰人]《本條題》N卷[下條撰人]`」
（頂真格，N2 道已立此準）。逐節連讀其前後二節，撰人即出：

| 節 | 原文 | 讀法 |
|---|---|---|
| 小學類 #91 | 《字說》二十四卷米芾 | 前節 #90 末綴「王安石」即本節撰人；「米芾」屬下節《書評》 |
| 故事類 #130 | 趙概《日記》一卷司馬光 | 趙概撰；「司馬光」屬下節《日錄》 |
| 儀注類 #153 | 王叡《雜錄》五卷 | 王叡撰 |
| 兵書類 #186 | 《兵鑒》五卷 | 前節無綴，本節無撰人；下節自注「並不知作者」 |
| 編年類 #141 | 一百篇李孟傳《讀史》十卷崔敦詩 | 「一百篇」是 #140 之卷數，李孟傳撰；「崔敦詩」屬下節 |
| 別集類 #340 | 《遺文》一卷 | 前節 #339「《韓愈集》五十卷**又**」——「又」字承下，本節是韓集之遺文 |
| 別集類 #971 | 張君房《野語》三卷 | 前節 #970 末綴「張君房」即本節撰人 |

**建之前先以夾撰人之法覆掃**（甲4），二節之主庫中實已有：
趙概《日記》即《趙康靖日記》`1evgpj75sgv0g`（康靖是其諡，一卷數合）；
《遺文》是韓愈集之附屬部帙，繫 `1evcs14zhd6v4` 並標 `section_kind`。
餘五節庫中確無，依 SCHEMA〈同題異撰是二書〉別建。

用法：python3 scripts/songzhi_dingzhen_fix.py [--apply]
"""
import json, os, sys, glob, hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import load_index

SZ = '1evcsw4kt579c'          # 宋史藝文志
CE = f'Work/1/e/v/{SZ}/collated_edition/'

# 舊主 → (整理本檔, 節序, 動作, 目標或新建之題撰卷, 何以)
PLAN = [
 ('1evr5e3meogvs', '小學類.json', 91, 'new',
  ('字說', '王安石', 24, '二十四卷'),
  '本節作「《字說》二十四卷米芾」，本身無撰人；而前節 #90「《續書斷》二卷王安石」'
  '末綴之「王安石」依頂真格即本節之撰人，「米芾」則屬下節 #92《書評》'
  '（米芾《書評》正合）。王安石《字說》二十四卷，宋人著錄屢見。'
  '舊主 `1evr5e3meogvs` 是清吳大澂《字說》一卷（清史稿著錄），與此無涉。'),
 ('1evr5e3meogzb', '故事類.json', 130, 'link', '1evgpj75sgv0g',
  '本節作「趙概《日記》一卷司馬光」——趙概撰，「司馬光」屬下節 #131《日錄》'
  '（司馬光《日錄》正合）。庫中已有《趙康靖日記》一卷 `1evgpj75sgv0g`'
  '（撰人作「趙槩」，概／槩異體；康靖是趙概之諡），一卷數合，即其主。'
  '舊主 `1evr5e3meogzb` 是清陸隴其《日記》十二卷（清史稿著錄），與此無涉。'),
 ('1evr5e3meogx8', '儀注類.json', 153, 'new',
  ('雜錄', '王叡', 5, '五卷'),
  '本節作「王叡《雜錄》五卷」，撰人在題前，無下綴。'
  '舊主 `1evr5e3meogx8` 是清蔡上翔《雜錄》二卷（清史稿著錄），與此無涉。'),
 ('1evr5e3mezpcl', '兵書類.json', 186, 'new',
  ('兵鑒', None, 5, '五卷'),
  '本節作「《兵鑒》五卷」，前節 #185「《武備圖》一卷」無下綴，故本節無撰人；'
  '下節 #187 自注「（並不知作者）」，正可為證。'
  '舊主 `1evr5e3mezpcl` 是清徐宗幹《兵鑑》五卷（清史稿著錄）——卷數雖同而代不相容。'),
 ('1evdic73ew2yo', '編年類.json', 141, 'new',
  ('讀史', '李孟傳', 10, '十卷'),
  '本節作「一百篇李孟傳《讀史》十卷崔敦詩」——「一百篇」是前節 #140'
  '《通鑒補遺》之卷數，「李孟傳」是本節撰人，「崔敦詩」屬下節 #142'
  '《通鑒要覽》（崔敦詩《通鑒要覽》正合）。'
  '舊主 `1evdic73ew2yo` 是明楊以任《讀史四集》四卷（明志著錄），與此無涉。'),
 ('1evr5e3mezpgt', '別集類.json', 340, 'part',
  ('1evcs14zhd6v4', '附屬部帙'),
  '本節作「《遺文》一卷」，其前節 #339 作「《韓愈集》五十卷**又**」——'
  '「又」字承下，本節即韓集之《遺文》一卷，是該本之附屬部帙，'
  '依 SCHEMA〈版本附屬部帙〉不別立 Work，與母條共繫並標 `section_kind`。'
  '舊主 `1evr5e3mezpgt` 是清莫友芝《遺文》八卷（清史稿著錄），與此無涉。'),
 ('1evjvw76rxclc', '別集類.json', 971, 'new',
  ('野語', '張君房', 3, '三卷'),
  '本節作「張君房《野語》三卷」；前節 #970「《章士廉集》二卷張君房」'
  '末綴之「張君房」正指本節，二處相印。'
  '舊主 `1evjvw76rxclc` 是清程岱葊《野語》九卷（續修四庫著錄），與此無涉。'),
]


def b36(n, w=13):
    d = '0123456789abcdefghijklmnopqrstuvwxyz'
    s = ''
    while n:
        s = d[n % 36] + s; n //= 36
    return s.rjust(w, '0')[-w:]


def shard(i):
    h = 0
    for c in i: h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return '0123456789abcdef'[h % 16]


def main():
    apply = '--apply' in sys.argv
    works = load_index('works')
    files = {}
    for _, fn, *_ in PLAN:
        if fn not in files:
            files[fn] = json.load(open(CE + fn, encoding='utf-8'))

    # ── 驗：節之內容與舊主須相符 ──
    for old, fn, i, act, arg, why in PLAN:
        s = files[fn]['sections'][i]
        if s.get('work_id') != old:
            print(f'！{fn}#{i} 之 work_id 作 {s.get("work_id")}，非 {old}'); return
        if act == 'link' and arg not in works:
            print('！目標不在庫', arg); return
        if act == 'part' and arg[0] not in works:
            print('！母條不在庫', arg[0]); return
    print(f'驗過：{len(PLAN)} 節，其 work_id 皆與表相符')

    taken = set(works); made = []
    for old, fn, i, act, arg, why in PLAN:
        s = files[fn]['sections'][i]
        node = {'source': '宋史藝文志', 'source_bid': SZ,
                'title_info': s.get('title'), 'summary': s.get('content'),
                'link_basis': '2026-08-24 宋志頂真格覆讀：' + why}
        if act == 'new':
            t, a, jn, mi = arg
            for salt in range(64):
                h = hashlib.sha1(f'songzhi:{fn}:{i}:{salt}'.encode()).hexdigest()
                wid = '1ex' + b36(int(h[:16], 16), 10)
                if wid not in taken: break
            taken.add(wid)
            rec = {'schema_version': 1, 'type': 'work', 'title': t, 'id': wid,
                   'indexed_by': [node],
                   'juan_count': {'number': jn},
                   'measures': [{'unit': '卷', 'number': jn}], 'measure_info': mi,
                   'period_upper': 'song',
                   'period_upper_basis':
                       'catalog_bound：所繫諸志中最緊者為《宋史藝文志》'
                       '（元脫脫等（1345），著錄宋代藏書），故不晚於 song',
                   'ai_note':
                       f'2026-08-24 自 `{old}` 拆出而立。{why}\n\n'
                       f'**建前已以夾撰人之法（甲4）覆掃庫中同題諸條**，'
                       f'確無此撰人之條，乃建。\n\n'
                       f'`period`／`loss_status` 不繫——宋志只給題、卷、撰人。'}
            if a:
                rec['authors'] = [{'name': a, 'role': None,
                                   'name_basis': '據《宋史藝文志》頂真格連讀所得，見 ai_note'}]
            made.append((wid, t, a, rec))
            s['work_id'] = wid
            s['link_basis'] = node['link_basis']
            print(f'  建 {wid} 《{t}》{a or "（不著撰人）"} {mi}  ← {fn}#{i}')
        elif act == 'link':
            s['work_id'] = arg
            s['link_basis'] = node['link_basis']
            print(f'  繫 {arg} 《{works[arg]["title"]}》  ← {fn}#{i}')
        else:
            mid, kind = arg
            s['work_id'] = mid
            s['section_kind'] = kind
            s['section_kind_basis'] = node['link_basis']
            s['link_basis'] = node['link_basis']
            print(f'  繫母條 {mid} 《{works[mid]["title"]}》並標「{kind}」 ← {fn}#{i}')
        # 舊主摘去該節之著錄
        p = works[old]['path']
        d = json.load(open(p, encoding='utf-8'))
        before = len(d.get('indexed_by') or [])
        d['indexed_by'] = [n for n in (d.get('indexed_by') or [])
                           if n.get('source') != '宋史藝文志']
        if len(d['indexed_by']) == before:
            print(f'！{old} 無宋志之節可摘'); return
        d['ai_note'] = (d.get('ai_note', '') + '\n\n' if d.get('ai_note') else '') + (
            f'2026-08-24 摘去所繫之《宋史藝文志》一節——本條是'
            f'{"清" if d.get("period") == "qing" else "明"}人之書，'
            f'不可能見於元脫脫所修之宋志。{why}')
        d['updated_at'] = '2026-08-24T00:00:00+00:00'
        if apply:
            with open(p, 'w', encoding='utf-8', newline='\n') as f:
                f.write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')

    if not apply:
        print('（乾跑。加 --apply 方寫檔）'); return

    shards = {x: json.load(open(f'index/works/{x}.json', encoding='utf-8'))
              for x in '0123456789abcdef'}
    for wid, t, a, rec in made:
        p = f'Work/{wid[0]}/{wid[1]}/{wid[2]}/{wid}-{t}.json'
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(rec, ensure_ascii=False, indent=2) + '\n')
        e = {'id': wid, 'title': t, 'type': 'Work', 'path': p,
             'juan_count': rec['juan_count']['number'],
             'measure_info': rec['measure_info']}
        if a: e['author'] = a
        shards[shard(wid)][wid] = e
    for x, obj in shards.items():
        with open(f'index/works/{x}.json', 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps({k: obj[k] for k in sorted(obj)},
                               ensure_ascii=False, indent=2) + '\n')
    for fn, cd in files.items():
        with open(CE + fn, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(cd, ensure_ascii=False, indent=2) + '\n')
    print(f'已寫檔：新建 {len(made)}、改繫 {len(PLAN)} 節')


if __name__ == '__main__':
    main()
