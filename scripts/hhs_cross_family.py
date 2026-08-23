#!/usr/bin/env python3
"""《後漢書》諸家輯本：跨家之同文二事

D2 五批對齊 750 條，皆在**同一家之內**（姚本某家之條配周本同家之條）。今補試
**跨家**——姚本繫甲家而周本繫乙家者，前此未驗。以第四批之度量（字集包含度
≥0.85 且 ratio ≥0.5）掃姚獨 392 × 非姚 761，得二事：

  一、「三君者，一時之所貴也，竇武、劉淑、陳蕃……」
     姚本繫**謝承**（《謝承後漢書》「三君」條），周本繫**謝沈**（《謝沈後漢書》
     「鍾離意傳」條）。二本之繫不同家。按《後漢書·黨錮傳》李賢注引此文明作
     「謝承《後漢書》曰」，姚繫是。然此是二輯家之異見，非本庫可代決——
     **只記其異，不改其繫**。

  二、「張溫以司空拜加車騎將軍，徵韓遂……」
     姚本繫《後漢紀》「張溫」條，周本繫《謝承後漢書》「竇武傳胡騰」條。周本
     一側之標目與其文不相應（文言張溫而標目言竇武、胡騰），疑其標目有誤，
     或此條本不當在彼。同上，只記其異。

**跨家之數如此之少（二事），本身即一結論**：二本於「此文屬何家」之判幾乎全
同，D2 之未對齊 318／175 不是繫家之異所致，仍是「二本收錄範圍之別」。
"""
import json, glob, os, sys

PAIRS = [
    (('謝承後漢書', 409), ('謝沈後漢書', 29),
     '本條之文與《謝沈後漢書》第 29 條（標目「鍾離意傳」）幾乎全同——'
     '姚之駰繫之謝承，汪文臺（周天游校注本）繫之謝沈，二輯家於此文屬何家所見不同。'
     '《後漢書·黨錮傳》李賢注引此文作「謝承《後漢書》曰」。'
     '此是二本之異見，本庫只記不裁，二處俱存原繫。'),
    (('後漢紀', 16), ('謝承後漢書', 807),
     '本條之文與《謝承後漢書》第 807 條（標目「竇武傳胡騰」）幾乎全同——'
     '姚之駰繫之《後漢紀》，汪文臺繫之謝承。且彼條標目言竇武、胡騰而其文言張溫，'
     '標目與文不相應，疑其標目有誤或此條本不當在彼。'
     '此是二本之異見，本庫只記不裁，二處俱存原繫。'),
]


def main():
    apply = '--apply' in sys.argv
    files = {}
    for f in glob.glob('Work/*/*/*/*/fragments/*.json'):
        d = json.load(open(f))
        if d.get('title'):
            files.setdefault(d['title'], []).append((f, d))
    n = 0
    for (ta, sa), (tb, sb), why in PAIRS:
        for (t, s), other in (((ta, sa), (tb, sb)), ((tb, sb), (ta, sa))):
            for f, d in files.get(t, []):
                for fr in (d.get('fragments') or []):
                    if fr.get('seq') != s:
                        continue
                    txt = why if (t, s) == (ta, sa) else why.replace(
                        f'《{tb}》第 {sb} 條', f'《{ta}》第 {sa} 條')
                    add = ('\n\n2026-08-23 D2 跨家覆勘：' + txt) if fr.get('note') else \
                          ('2026-08-23 D2 跨家覆勘：' + txt)
                    if 'D2 跨家覆勘' in (fr.get('note') or ''):
                        continue
                    fr['note'] = (fr.get('note') or '').rstrip() + add
                    n += 1
                    if apply:
                        with open(f, 'w', encoding='utf-8') as fh:
                            json.dump(d, fh, ensure_ascii=False, indent=2)
                            fh.write('\n')
    print('記其異者', n, '條')
    if not apply:
        print('（乾跑。加 --apply 方寫檔）')


if __name__ == '__main__':
    main()
