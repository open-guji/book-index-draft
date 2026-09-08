#!/usr/bin/env python3
"""《隋書經籍志》主條自「亡」者之逐條裁

`隋志注中亡書.md` 末節留一事未辦：主條之 summary 以「亡」結而其前無《》者，
判準不準，須逐條讀，否則「一律加 loss_status: lost，則《荀子》《陸機集》
《傅玄集》皆成亡書——大錯」。

今以本日之資料重掃，得 19 條（非舊記之 34——庫中記錄已易）。逐條讀畢，**無
一條之「亡」指主條**，故 `loss_status` 一概不動。所異者只在「亡」之所指：

  甲　亡指注中所列之他書（十二條）。「《三禮目錄》一卷鄭玄撰。梁有陶弘景注
      一卷，亡」——亡者陶弘景之注，非鄭玄之《目錄》。
  丙　亡指梁本或原本之全帙（七條）。「《雜傳》三十六卷任昉撰。本一百四十七
      卷，亡」——今存三十六卷，亡者是那一百四十七卷之本。

所補止於一句 `note`，記其「亡」之所指，使後之覈者不復以此判主條之存亡。
"""
import json, glob, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SUI = '1ev85yncs9ibk'
JIA = '此行末之「亡」指注中所列之他書（{what}），非本條之書。隋志之例：正文著隋時' \
      '見存之書，而以注記梁時尚存、隋時已亡者。**不可據此判本書已亡。**'
BING = '此行末之「亡」指{what}，非今存之本。今存者即本條所著之卷數。' \
       '**不可據此判本書全亡。**'
FIX = {
    '周載': ('丙', '「本三十卷」之全帙'),
    '王絢集': ('丙', '梁本十卷及錄一卷'),
    '潛夫論': ('甲', '王逸《正部論》、應奉《後序》、周生烈《周生子要論》、裴啟《語林》'),
    '風角雜占五音圖': ('丙', '梁本十三卷'),
    '春秋公羊謚例何休撰': ('甲', '《春秋公羊傳條例》《春秋公羊傳問答》《春秋公羊論》諸書'),
    '三禮目錄鄭玄撰': ('甲', '陶弘景注一卷'),
    '禮記默房宋均注': ('甲', '鄭玄注三卷'),
    '儀禮王肅注': ('甲', '李軌、劉昌宗、鄭玄諸家之音'),
    '雜傳': ('丙', '「本一百四十七卷」之全帙'),
    '春秋左氏傳音嵇康撰': ('甲', '服虔、杜預、高貴鄉公、曹軀、荀訥諸家之音'),
    '禮記音徐爰撰': ('甲', '鄭玄、王肅、射慈、蔡謨、曹耽、尹毅、李軌、范宣諸家之音'),
    '尚書駁議王肅撰': ('甲', '《尚書義問》《尚書釋問》《尚書王氏傳問》《尚書義》諸書'),
    '漏刻經': ('甲', '霍融、何承天、楊偉等所撰三卷'),
    '周易論': ('丙', '梁本三十卷'),
    '殷仲堪集': ('丙', '梁本十卷及錄一卷'),
    '周易論周顯撰': ('丙', '梁本三十卷'),
    '禮論要鈔': ('甲', '荀萬秋《鈔略》、丘季彬論議統諸書'),
    '春秋穀梁傳唐固注': ('甲', '尹更始所撰《春秋穀梁傳》十五卷'),
    '書集': ('丙', '梁本八十卷'),
}


def main():
    apply = '--apply' in sys.argv
    n = miss = 0
    seen = set()
    for p in glob.glob('Work/*/*/*/*.json'):
        d = json.load(open(p))
        if d['title'] not in FIX:
            continue
        hit = False
        for e in (d.get('indexed_by') or []):
            if e.get('source_bid') != SUI or e.get('in_note_of'):
                continue
            s = e.get('summary') or ''
            if not re.search(r'亡[。．]?$', s):
                continue
            k, what = FIX[d['title']]
            txt = (JIA if k == '甲' else BING).format(what=what)
            if e.get('note') == txt:
                continue
            e['note'] = txt
            hit = True
        if hit:
            seen.add(d['title'])
            n += 1
            if apply:
                with open(p, 'w', encoding='utf-8') as f:
                    json.dump(d, f, ensure_ascii=False, indent=2)
                    f.write('\n')
    print(f'主條自「亡」19 條：記其所指 {n}；表中未見於庫者 {sorted(set(FIX) - seen)}')
    if not apply:
        print('（乾跑。加 --apply 方寫檔）')


if __name__ == '__main__':
    main()
