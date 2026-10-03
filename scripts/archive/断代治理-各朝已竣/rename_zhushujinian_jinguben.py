#!/usr/bin/env python3
"""比照《尚書》今古文重整原則處理《竹書紀年》命名消歧。

問題：今本（1ev3babc1g5c0）與抽象原典/古本一系（1evqpdnrz483k）目前共用完全
相同的字面標題「竹書紀年」，僅能靠內部 note 分辨，容易誤讀誤鏈。仿《尚書》
（今文尚書／偽古文尚書用不同主標題區分）之例，將今本改題「今本竹書紀年」，
抽象原典加註別名「古本竹書紀年」以資對照；並修正抽象原典 description 與
今本考證結論不一致之處（今本考證明確指向明范欽輯合，非「宋元間流傳本」）。

不新建 Work（王國維《古本竹書紀年輯校》《今本竹書紀年疏證》兩種本庫缺載的
關鍵著作，留待使用者確認後另行處理）。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

JINBEN = "1ev3babc1g5c0"
GUBEN_ABSTRACT = "1evqpdnrz483k"
NEW_JINBEN_TITLE = "今本竹書紀年"
OLD_TITLE = "竹書紀年"

REFERRING_FILES = [
    "Work/1/e/v/1evr5e3m8fq3y-竹書紀年校正.json",
    "Work/1/e/v/1evr5e3m8fq3z-校正竹書紀年.json",
    "Work/1/e/v/1evr5e3m8fq40-竹書紀年集注.json",
    "Work/1/e/v/1evr5e3m8fq41-竹書紀年校補.json",
    "Work/1/e/v/1evr5e3m8fq42-考訂竹書紀年.json",
    "Work/1/e/v/1evr5e3m8fq43-竹書紀年義證.json",
    "Work/1/e/v/1evr5e3m8fq44-竹書紀年補證.json",
    "Work/1/e/v/1evr5e3m8fq3x-竹書紀年集證集說敘略.json",
    "Work/1/e/v/1ev3babcek45c-竹書統箋.json",
    "Work/1/e/v/1evqpdnrz483k-竹書紀年.json",
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    jinben_path = ROOT / "Work/1/e/v/1ev3babc1g5c0-竹書紀年.json"
    jinben = load(jinben_path)
    jinben["title"] = NEW_JINBEN_TITLE
    jinben["additional_titles"] = [OLD_TITLE]
    jinben["ai_note"] = jinben.get("ai_note", "") + (
        " | 2026-08-10：應使用者要求比照《尚書》今古文重整原則處理——本條與抽象原典"
        "（1evqpdnrz483k）此前共用完全相同的字面標題「竹書紀年」，僅能靠 related_works"
        "之 note 分辨，容易誤讀誤鏈。今改題「今本竹書紀年」以醒目區分，原題「竹書紀年」"
        "移入 additional_titles 供檢索。所有指向本條的 related_works.title 已同步更新。"
    )
    save(jinben_path, jinben)

    guben_path = ROOT / "Work/1/e/v/1evqpdnrz483k-竹書紀年.json"
    guben = load(guben_path)
    guben["additional_titles"] = ["古本竹書紀年"]
    guben["description"] = {
        "text": "戰國時魏國史官編年體史書，記黃帝至魏襄王二十年（公元前 299 年）事。西晉太康二年（281）汲縣戰國魏襄王墓出土，原簡本至遲南宋已佚。今分兩系並行：「古本」為佚文輯本，據唐宋類書、注疏所引《竹書紀年》原文輯出，以清朱右曾《汲冢紀年存真》、王國維《古本竹書紀年輯校》最稱精審；「今本」十三卷（見「今本竹書紀年」條）則是明范欽等纂輯諸書湊合而成之偽本，非「宋元間流傳本」——詳見該條考證所引《四庫全書總目》《養新錄》之辨。",
        "sources": ["学界共识", "王國維《今本竹書紀年疏證》", "王國維《古本竹書紀年輯校》"]
    }
    for e in guben["related_works"]:
        if e["id"] == JINBEN:
            e["title"] = NEW_JINBEN_TITLE
    guben["ai_note"] = (
        "2026-08-10：應使用者要求比照《尚書》今古文重整原則處理——加註別名「古本竹書"
        "紀年」以與「今本竹書紀年」（1ev3babc1g5c0）對照；description 原稱今本為"
        "「宋元間流傳本（一說宋人偽輯）」，與今本條自身考證（引《四庫全書總目》《養新"
        "錄》，明確指向明范欽輯合）不一致，已修正對齊。王國維《古本竹書紀年輯校》《今"
        "本竹書紀年疏證》兩種關鍵著作本庫尚無獨立 Work 條目，僅見於本條 description."
        "sources 之書目線索，留待使用者確認後建檔。"
    )
    save(guben_path, guben)

    for rel_path in REFERRING_FILES:
        p = ROOT / rel_path
        data = load(p)
        changed = False
        for e in data.get("related_works", []):
            if e.get("id") == JINBEN and e.get("title") == OLD_TITLE:
                e["title"] = NEW_JINBEN_TITLE
                changed = True
        if changed:
            save(p, data)
            print("updated title ref in", rel_path)
        else:
            print("no matching ref found in", rel_path)


if __name__ == "__main__":
    main()
