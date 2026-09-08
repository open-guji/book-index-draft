#!/usr/bin/env python3
"""重整《尚書》has_part 篇章歸屬（上一輪尚書今古文重整的遺留待辦）。

原掛在「尚書」（今文尚書，1evl7fct2ezgg）下的 71 個 has_part 子篇，混雜三種
性質不同的材料：

  GENUINE（33 篇）：今文28篇析分後的33篇，內容確為伏生一系真今文，同時亦是
    通行58篇本（偽古文尚書）的組成部分——採雙重歸屬：今文尚書、偽古文尚書
    兩處皆記 has_part（各篇自身之 part_of 亦雙記）。
  FAKE（25 篇）：東晉梅賾偽造之25篇，今文從未有過此內容，只能是偽古文尚書
    的子篇，自今文尚書移除。
  QHJ（13 篇）：清華大學藏戰國竹簡出土文獻（保訓、厚父、耆夜、尹至、尹誥、
    傅說之命上中下、攝命、封許之命、四告、成后、昭后），各篇自身描述皆明載
    其為戰國竹簡實物、與今本《尚書》不同源（部分甚至明言與偽古文對應篇「全
    異」），本非「尚書」任何傳本之子篇，過去因篇題偶合被磁鐵式掛上——移除
    has_part 關聯，不轉掛他處，作獨立 Work 保留。

分類依三份 Work 自身 description 已有的「今文／偽古文／竹簡」字樣核實
（71 篇零誤判，見執行紀錄）。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

JINWEN = "1evl7fct2ezgg"
WEIGUWEN = "1evd3dbcb0nb4"

GENUINE = [
    ("1evrerq5g8xs0", "堯典"), ("1evrerqbuxb7k", "舜典"), ("1evrerqotwbuo", "皋陶謨"),
    ("1evrerqvp4a2o", "益稷"), ("1evrerr27uqkg", "禹貢"), ("1evrerr8eexvk", "甘誓"),
    ("1evrerrrnp0cg", "湯誓"), ("1evrert5vca2o", "盤庚上"), ("1evrertc2iygw", "盤庚中"),
    ("1evrertidghds", "盤庚下"), ("1evreru76ifi8", "高宗肜日"), ("1evrerudgi8sg", "西伯戡黎"),
    ("1evrerujxzr40", "微子"), ("1evrerv995gqo", "牧誓"), ("1evrervlxtngg", "洪範"),
    ("1evrervyjopa8", "金縢"), ("1evrerw4w6eww", "大誥"), ("1evrerwhi1gqo", "康誥"),
    ("1evrerwnscikg", "酒誥"), ("1evrerwtzufi8", "梓材"), ("1evrerx07ccg0", "召誥"),
    ("1evrerx6iwcg0", "洛誥"), ("1evrerxcve22o", "多士"), ("1evrerxj5p3wg", "無逸"),
    ("1evrerxpadvy8", "君奭"), ("1evrery364tmo", "多方"), ("1evrery9phr7k", "立政"),
    ("1evreryum2ww0", "顧命"), ("1evrerz14tdds", "康王之誥"), ("1evrerzqfclxc", "呂刑"),
    ("1evrerzwvwem8", "文侯之命"), ("1evres0325dds", "費誓"), ("1evres0975dz4", "秦誓"),
]

FAKE = [
    ("1evrerqiea8sg", "大禹謨"), ("1evrerrf2gfls", "五子之歌"), ("1evrerrle0fls", "胤征"),
    ("1evrerrxt09hc", "仲虺之誥"), ("1evrers3ymr5s", "湯誥"), ("1evrersa8mkg0", "伊訓"),
    ("1evrersgojw1s", "太甲上"), ("1evrersn11log", "太甲中"), ("1evrerstgcg74", "太甲下"),
    ("1evrerszqc9hc", "咸有一德"), ("1evrertoj2z28", "說命上"), ("1evrertuopgqo", "說命中"),
    ("1evreru0vw54w", "說命下"), ("1evreruq7d3b4", "泰誓上"), ("1evreruwnaeww", "泰誓中"),
    ("1evrerv2wyznk", "泰誓下"), ("1evrervfq0hz4", "武成"), ("1evrervs6vr40", "旅獒"),
    ("1evrerwb6spa8", "微子之命"), ("1evrerxvkoxs0", "蔡仲之命"), ("1evrerygtgcn4", "周官"),
    ("1evreryo2eqrk", "君陳"), ("1evrerz7ffnr4", "畢命"), ("1evrerzdnk1s0", "君牙"),
    ("1evrerzk93n5s", "冏命"),
]

QHJ = [
    ("1evres0fj0mio", "保訓"), ("1evres0s0tla8", "厚父"), ("1evres0ya6xhc", "耆夜"),
    ("1evrfbwje7ev4", "尹至"), ("1ewozi5r1muip", "尹誥"), ("1ewozi5tl3doi", "傅說之命上"),
    ("1ewozi5w4v5dv", "傅說之命中"), ("1ewozi5yoy5ms", "傅說之命下"), ("1ewozi61c5jb9", "攝命"),
    ("1ewozi6jvu591", "封許之命"), ("1ewozjltmomcy", "四告"), ("1ewozjm2y8qbu", "成后"),
    ("1ewozjm3qc37w", "昭后"),
]

assert len(GENUINE) == 33 and len(FAKE) == 25 and len(QHJ) == 13


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


def main():
    idx = build_index()
    jinwen = load(idx[JINWEN])
    weiguwen = load(idx[WEIGUWEN])

    jinwen_rw = jinwen["related_works"]
    weiguwen_rw = weiguwen.setdefault("related_works", [])
    weiguwen_existing_ids = {e["id"] for e in weiguwen_rw}

    report = {"genuine": [], "fake": [], "qhj": []}

    # GENUINE: keep on jinwen, add to weiguwen, add part_of on each chapter file
    for wid, title in GENUINE:
        if wid not in weiguwen_existing_ids:
            weiguwen_rw.append({"id": wid, "title": title, "relation": "has_part"})
            weiguwen_existing_ids.add(wid)
        cpath = idx[wid]
        cdata = load(cpath)
        crw = cdata.setdefault("related_works", [])
        if not any(e["id"] == WEIGUWEN for e in crw):
            crw.append({"id": WEIGUWEN, "title": "偽古文尚書", "relation": "part_of"})
        save(cpath, cdata)
        report["genuine"].append([wid, title])

    # FAKE: remove from jinwen, add to weiguwen, retarget part_of on each chapter file
    fake_ids = {wid for wid, _ in FAKE}
    jinwen_rw = [e for e in jinwen_rw if e["id"] not in fake_ids]
    for wid, title in FAKE:
        if wid not in weiguwen_existing_ids:
            weiguwen_rw.append({"id": wid, "title": title, "relation": "has_part"})
            weiguwen_existing_ids.add(wid)
        cpath = idx[wid]
        cdata = load(cpath)
        crw = cdata.get("related_works", [])
        retargeted = False
        for e in crw:
            if e.get("id") == JINWEN:
                e["id"] = WEIGUWEN
                e["title"] = "偽古文尚書"
                retargeted = True
        if not retargeted and not any(e["id"] == WEIGUWEN for e in crw):
            crw.append({"id": WEIGUWEN, "title": "偽古文尚書", "relation": "part_of"})
        cdata["related_works"] = crw
        save(cpath, cdata)
        report["fake"].append([wid, title])

    # QHJ: remove from jinwen entirely, strip part_of->jinwen on each chapter file
    qhj_ids = {wid for wid, _ in QHJ}
    jinwen_rw = [e for e in jinwen_rw if e["id"] not in qhj_ids]
    for wid, title in QHJ:
        cpath = idx[wid]
        cdata = load(cpath)
        crw = cdata.get("related_works", [])
        new_crw = [e for e in crw if not (e.get("id") == JINWEN and e.get("relation") == "part_of")]
        cdata["related_works"] = new_crw
        save(cpath, cdata)
        report["qhj"].append([wid, title])

    jinwen["related_works"] = jinwen_rw
    weiguwen["related_works"] = weiguwen_rw

    jinwen["ai_note"] = jinwen.get("ai_note", "") + (
        " | 2026-08-10（續）：處理上一輪遺留之 has_part 篇章歸屬待辦。原 71 個子篇中，"
        "33 篇今文析出篇（堯典……秦誓）留本條 has_part，並雙重歸屬新增於偽古文尚書"
        "（因二者皆含此33篇之內容）；25 篇偽古文獨有篇（大禹謨……冏命）自本條移除，"
        "改為偽古文尚書專屬 has_part；13 篇清華簡出土文獻（保訓、厚父、耆夜、尹至、"
        "尹誥、傅說之命上中下、攝命、封許之命、四告、成后、昭后）自本條移除且不轉掛"
        "他處——各篇自身描述已明載其為戰國竹簡實物、與今本《尚書》不同源，過去因篇題"
        "偶合被磁鐵式掛於本抽象總綱下，今並非本條或偽古文尚書之子篇，仍作獨立 Work。"
    )
    weiguwen["ai_note"] = weiguwen.get("ai_note", "") + (
        " | 2026-08-10（續）：接收上一輪遺留之 has_part 篇章歸屬——33 篇今文析出篇"
        "（與今文尚書雙重歸屬）與25 篇偽古文獨有篇，共58篇，皆記為本條 has_part，"
        "完整反映通行58篇本之篇目結構。"
    )

    save(idx[JINWEN], jinwen)
    save(idx[WEIGUWEN], weiguwen)

    out = ROOT / ".claude" / "known-issues" / "尚書has_part重整_round1.json"
    save(out, report)
    print(json.dumps({k: len(v) for k, v in report.items()}, ensure_ascii=False, indent=2))
    print("jinwen related_works count now:", len(jinwen_rw))
    print("weiguwen related_works count now:", len(weiguwen_rw))
    print("report ->", out.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
