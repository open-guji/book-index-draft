#!/usr/bin/env python3
"""為《經義考》所建之 work 補 `period_upper`——據其著錄語所引之前代志

D1 一輪建 work 4,826 條，`period` 一概不繫（其由見各條 ai_note：論斷所引之年
號屢是引者之年非撰人之年，準確率只 0.81，不足以充一欄之據）。然**上限與定代
是兩回事**——SCHEMA〈period_upper〉之第一源即「catalog_bound：一書見於某志，
其時代不得晚於該志」，而朱彝尊之著錄語正逐條記其所引之志（「隋志五卷」「宋志
二十四卷」「七錄十卷」）。此上限有據可驗，不涉定代之推。

**取著錄語，不取論斷**。二者本庫皆存於 `indexed_by[].summary`（著錄語一行，
換行後乃論斷），然論斷屢引諸志以論他事（「宋史袁甫字廣微……」是《宋史》本傳
非《宋史·藝文志》之著錄），故不可於 summary 全文搜志名。此處逕取
`經義考論斷.json` 之 `zhu` 欄——解析時即與論斷分立者。

**三閘防誤**：
  一、志名須在句首（著錄語之式是「{志}{卷數}」）；
  二、該段須短於二十六字（真著錄語皆極簡，長者是論斷混入）；
  三、「通志」須在句首方取——「江西通志」「福建通志」是地方志，非鄭樵《通志》；
      「宋史」一概不取，只取「宋志」——前者多是本傳。

**只標於 `period` 與 `period_upper` 俱空者**（SCHEMA：period 已定而無疑者標之
徒增冗餘）。`period_upper` 非索引欄，故不動 `index/works`。
"""
import json, glob, os, re, sys, collections

CIT = [('漢志', 'qin-han'), ('七略', 'qin-han'), ('七畧', 'qin-han'),
       ('别録', 'qin-han'), ('別錄', 'qin-han'),
       ('七録', 'nanbeichao'), ('七錄', 'nanbeichao'),
       ('隋志', 'sui-tang'), ('唐志', 'sui-tang'),
       ('崇文總目', 'song'), ('中興書目', 'song'), ('讀書志', 'song'),
       ('書録解題', 'song'), ('書錄解題', 'song'), ('館閣書目', 'song'),
       ('宋志', 'song'), ('通志', 'song'),
       ('通考', 'liao-jin-yuan'), ('國史志', 'ming')]
ORD = ['pre-qin', 'qin-han', 'three-kingdoms', 'jin', 'nanbeichao', 'sui-tang',
       'five-dynasties', 'song', 'liao-jin-yuan', 'ming', 'qing', 'modern']
I = {p: i for i, p in enumerate(ORD)}
ZHI_NAME = {'漢志': '《漢書·藝文志》', '七略': '劉歆《七略》', '七畧': '劉歆《七略》',
            '别録': '劉向《別錄》', '別錄': '劉向《別錄》',
            '七録': '阮孝緒《七錄》', '七錄': '阮孝緒《七錄》',
            '隋志': '《隋書·經籍志》', '唐志': '唐志', '崇文總目': '《崇文總目》',
            '中興書目': '《中興館閣書目》', '讀書志': '《郡齋讀書志》',
            '書録解題': '《直齋書錄解題》', '書錄解題': '《直齋書錄解題》',
            '館閣書目': '《館閣書目》', '宋志': '《宋史·藝文志》',
            '通志': '鄭樵《通志·藝文略》', '通考': '《文獻通考·經籍考》',
            '國史志': '焦竑《國史經籍志》'}
BASIS = ('catalog_bound：《經義考》之著錄語作「{zhu}」，是朱彝尊記{name}著錄本書。'
         '一書見於某志，其時代不得晚於該志（SCHEMA〈period_upper〉上限之六源第一），'
         '故上限 {p}。**只是上限，不得當下限用**——早期志書亡佚極多，'
         '一部漢代之書可能遲至《宋史·藝文志》方首見著錄。'
         '此是轉引：所據非該志原文，是朱彝尊之引，覆按時當回原志。')


def main():
    apply = '--apply' in sys.argv
    K = {(x['page'], x['head']): x
         for x in json.load(open('.claude/known-issues/經義考論斷.json'))}
    D = json.load(open('.claude/known-issues/經義考待裁.json'))
    W = {}
    for s in '0123456789abcdef':
        W.update(json.load(open(f'index/works/{s}.json')))
    plan = {}
    for d in D:
        w = d.get('created_work')
        if not w or w not in W:
            continue
        x = K.get((d['page'], d['head']))
        zhu = (x['zhu'] if x else '') or '；'.join(d.get('attest') or [])
        best = which = seg_hit = None
        for seg in re.split(r'[；;]', zhu):
            seg = seg.strip()
            if len(seg) > 26:
                continue
            for k, v in CIT:
                if seg.startswith(k) and (best is None or I[v] < I[best]):
                    best, which, seg_hit = v, k, seg
        if best:
            plan.setdefault(w, (best, which, seg_hit))
    print('可得上限者', len(plan), collections.Counter(v[0] for v in plan.values()))
    n = skip = 0
    for w, (p, k, seg) in plan.items():
        path = W[w]['path']
        d = json.load(open(path))
        if d.get('period') or d.get('period_upper'):
            skip += 1
            continue
        n += 1
        if not apply:
            continue
        d['period_upper'] = p
        d['period_upper_basis'] = BASIS.format(zhu=seg, name=ZHI_NAME.get(k, k), p=p)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write('\n')
    print(f'{"已補" if apply else "可補"} {n}；已有 period 或 period_upper 而跳過 {skip}')
    if not apply:
        print('（乾跑。加 --apply 方寫檔）')


if __name__ == '__main__':
    main()
