#!/usr/bin/env python3
"""補齊出土文獻 138 條互相點名卻未建 related_works 的缺漏（先秦組分析報告第5項第一部分）。

方法：對 138 條逐條掃描 description.text，比對是否含另一條（同屬 138 條）之
題名字串，得 45 個候選，逐條人工核讀原文語境（區分「確指該書」與「泛詞／
巧合子串」）後，分三類建立雙向 related：

  A. 同卷／同一竹簡束之明確關聯（description 明言「與……同卷」「編連為一卷」
     「相附而行」之屬）：大夫食禮／大夫食禮記；廼命一／廼命二；邦家處位／
     邦家之政；馭馬之道／馭術／馴馬／胥馬／凡馬之疾（清華簡馬政文獻群）；
     祝辭／良臣；行稱／病方；鶹鷅／有皇將起；四時／司歲；仲尼曰／孔子曰
     （原始發現之例，安大簡與王家嘴楚簡互證）。
  B. 學界歸類為同一系統之篇章（description 明言「學界多以為出……一系」
     「義理相通」）：子思子／五行／性自命出／魯穆公問子思（子思學派）；
     語叢二／性自命出；亙先／太一生水；伊尹（漢志目錄條目）／湯在啻門／
     湯處於湯丘／赤鵠之集湯之屋／尹至／尹誥（伊尹故事群，主題性關聯，非
     文本傳承關係）。
  C. 與庫中既有大部頭原典之明確互證關係（description 明言「可與……互參／
     互證」）：晉文公入於晉、管仲、越公其事 → 國語；繫年 → 竹書紀年。

判為子串巧合、非真實關聯而排除者（供覆核追蹤）：伊尹→春秋、殷高宗問於
三壽→彭祖、競公瘧→春秋（皆指《左傳》非本庫「春秋」條）、舉治王天下→
天下之道（「王天下之道」子串巧合）、良臣→春秋（泛指「春秋時期」而非
本書）、語叢一→春秋（六經並列泛稱）、靈王遂申→春秋（泛指「春秋楚國」）、
八氣五味五祀五行之屬→五行、參不韋→五行（皆泛詞「五行」概念非本書）、
太一生水→四時（宇宙生成鏈中之「四時」為泛詞）、赤鵠之集湯之屋→伊尹
（原文指《伊尹說》非本庫「伊尹」條，兩者為漢志道家／小說家兩種不同
著錄，本庫暫無《伊尹說》獨立條目，留待覆核）。
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


# (id, title) pairs; each tuple in GROUPS is a fully-connected mesh with a shared note
GROUPS = [
    ([("1ewozjlz30w1s", "大夫食禮"), ("1ewozjlzu6jb6", "大夫食禮記")],
     "清華簡禮書，同卷書寫、編連相附"),
    ([("1ewozjlr45sto", "廼命一"), ("1ewozjlrxi3vy", "廼命二")],
     "清華簡訓誡之辭，同卷相承"),
    ([("1ewozjlksx1cs", "邦家處位"), ("1ewozjlk22mmy", "邦家之政")],
     "清華簡政論，同卷書寫，相為表裏"),
    ([("1ewozjm8fipnc", "馭馬之道"), ("1ewozjm7pm0k6", "馭術"),
      ("1ewozjm6xino4", "馴馬"), ("1ewozjm57efkg", "胥馬"),
      ("1ewozjm5zhsgi", "凡馬之疾")],
     "清華簡馬政文獻群，現存最早之馬政文獻"),
    ([("1ewozi6ih9p8x", "祝辭"), ("1ewozi6hpstfz", "良臣")],
     "清華簡，同卷書寫"),
    ([("1ewozjlw1gldk", "行稱"), ("1ewozjlwvqm2i", "病方")],
     "清華簡數術類，同卷相次"),
    ([("1ewozs6dlwfvr", "鶹鷅"), ("1ewozs6cu4bj9", "有皇將起")],
     "上博楚簡逸詩類，同卷書寫"),
    ([("1ewozjlug0xf8", "四時"), ("1ewozjlv8fiuu", "司歲")],
     "清華簡數術類，原編連同卷"),
    ([("1ewozxkq0ta92", "仲尼曰"), ("1ewozxl9pp7wg", "孔子曰")],
     "安大簡《仲尼曰》與荊州王家嘴楚簡《孔子曰》體裁近《論語》，可互證《論語》成書前孔子語錄之流傳形態"),
    ([("1evcpjzpcre9s", "子思子"), ("1ewozqtxm3tal", "五行"),
      ("1ewozqu1c0mc7", "性自命出"), ("1ewozqtw4ezux", "魯穆公問子思")],
     "郭店楚簡，學界多以為出子思一系"),
    ([("1ewozqu3mf9r1", "語叢二"), ("1ewozqu1c0mc7", "性自命出")],
     "郭店楚簡，義理相通"),
    ([("1ewozs5k8cffb", "亙先"), ("1ewozqtum3pc5", "太一生水")],
     "上博／郭店楚簡道家宇宙論佚篇，義理相通"),
    ([("1ev7xkic75bls", "伊尹"), ("1ewozi6m2t6or", "湯在啻門"),
      ("1ewozi6le5frt", "湯處於湯丘"), ("1ewozi6j6jx8z", "赤鵠之集湯之屋"),
      ("1evrfbwje7ev4", "尹至"), ("1ewozi5r1muip", "尹誥")],
     "皆以伊尹為主角之故事／學說，主題性關聯，非文本傳承關係"),
]

SOFT_LINKS = [
    ("1ewozjlhmzf2s", "晉文公入於晉", "1ev3bad2is7pc", "國語",
     "可與《左傳》《國語·晉語》互參"),
    ("1ewozjlfd78r2", "管仲", "1ev3bad2is7pc", "國語",
     "所論可與《管子》《國語·齊語》互證"),
    ("1ewozjlj9z9qw", "越公其事", "1ev3bad2is7pc", "國語",
     "與《國語·吳語》《越語》詳略互異"),
    ("1ewozi6fj50jt", "繫年", "1evqpdnrz483k", "竹書紀年",
     "體例近《竹書紀年》"),
]


def add_related(data, target_id, target_title, note):
    rw = data.setdefault("related_works", [])
    if any(e["id"] == target_id for e in rw):
        return False
    rw.append({"id": target_id, "title": target_title, "relation": "related", "note": note})
    return True


def main():
    idx = build_index()
    added = 0

    for members, note in GROUPS:
        for i, (wid, title) in enumerate(members):
            p = idx[wid]
            d = load(p)
            changed = False
            for j, (owid, otitle) in enumerate(members):
                if owid == wid:
                    continue
                if add_related(d, owid, otitle, note):
                    changed = True
                    added += 1
            if changed:
                save(p, d)

    for wid1, t1, wid2, t2, note in SOFT_LINKS:
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
