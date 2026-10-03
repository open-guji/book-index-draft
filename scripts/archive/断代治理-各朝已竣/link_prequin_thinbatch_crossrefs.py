#!/usr/bin/env python3
"""補齊先秦組「85條漢志單條著錄亡佚書」批次（實際 61 條 thin_record+no_related_works）
逐條核讀後發現之缺漏 related_works 關聯（analysis 報告最後一項，「继续查」核查結果）。

方法：對 61 條批次逐條掃描 description.text 是否含本庫其他 268 條之題名字串，得 58
個候選，逐條人工核讀原文語境後，僅 6 對屬真實關聯（其餘 52 個皆為子串巧合或單純
史料引用，如「黃帝XXX」託名黃帝而非指本庫「黃帝」條、「呂氏春秋」含「春秋」子串、
《孟子》《荀子》《左傳》等僅作引文出處而非同書關係），予以排除：

  1. 公孫尼／公孫尼子——description 明言「此人可能與儒家的公孫尼子...是同一個人，
     但儒家的《公孫尼子》與此雜家《公孫尼》為兩部不同的書」。
  2. 大夫種／范蠡——兩條 description 互稱「同為越兵書」。
  3. 黃帝外經／黃帝內經——「與《黃帝內經》十八卷相配，同屬醫經七家之首黃帝一系」。
  4. 道家孫子／孫子——「與兵權謀類吳孫子兵法（孫武）非同一書」，明確曾生混淆之異書。
  5. 周史六弢／六韜——「顏師古以為即《六韜》，沈濤...梁啟超...考證『六』乃『大』之
     誤...非兵書《六韜》」，明確曾生混淆之異書。
  6. 田子／慎子——錢穆《國學概論》「《漢志》田子在道家、慎子在法家，則道家與法家
     相通」，田駢、慎到學派相通之軟性關聯。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def build_index():
    idx = {}
    for s in SHARDS:
        d = load(ROOT / "index" / "works" / f"{s}.json")
        for wid, entry in d.items():
            idx[wid] = ROOT / entry["path"]
    return idx


PAIRS = [
    ("1ev7xkhfcqdxc", "公孫尼", "1ev7xkhdmxedc", "公孫尼子",
     "此人可能與儒家的公孫尼子是同一個人，但儒家的《公孫尼子》與此雜家《公孫尼》為兩部不同的書"),
    ("1ev7xm2vhjf9c", "大夫種", "1ev7xm2zwf7r4", "范蠡",
     "《大夫種》與《范蠡》同為越兵書，句踐臣屬"),
    ("1evdiel8hiscg", "黃帝外經", "1ev7vo5guna4g", "黃帝內經",
     "與《黃帝內經》十八卷相配，同屬醫經七家之首黃帝一系"),
    ("1ev7xrlgashbv", "道家孫子", "1ev3bbesj0oow", "孫子",
     "《漢志》道家類孫子十六篇，與兵權謀類吳孫子兵法（孫武）非同一書，然題名易生混淆，特為互連"),
    ("1ev7xkiiv6tc0", "周史六弢", "1ev3bberznz0g", "六韜",
     "顏師古以為即《六韜》，沈濤、梁啟超考證「六」乃「大」之誤，實為周史大弢所著，非兵書《六韜》，然舊說易生混淆，特為互連"),
    ("1ev7xki359khs", "田子", "1ev3bbv1a8yrk", "慎子",
     "錢穆《國學概論》：「《漢志》田子在道家、慎子在法家，則道家與法家相通」；田駢、慎到學派相通"),
]


def add_related(data, target_id, target_title, note):
    rw = data.setdefault("related_works", [])
    if rw is None:
        rw = []
        data["related_works"] = rw
    if any(e["id"] == target_id for e in rw):
        return False
    rw.append({"id": target_id, "title": target_title, "relation": "related", "note": note})
    return True


def main():
    idx = build_index()
    added = 0
    for wid1, t1, wid2, t2, note in PAIRS:
        p1 = idx[wid1]
        d1 = load(p1)
        if add_related(d1, wid2, t2, note):
            save(p1, d1)
            added += 1
        p2 = idx[wid2]
        d2 = load(p2)
        if add_related(d2, wid1, t1, note):
            save(p2, d2)
            added += 1
    print("related_works entries added:", added)


if __name__ == "__main__":
    main()
