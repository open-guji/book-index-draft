#!/usr/bin/env python3
"""新建王國維《古本竹書紀年輯校》《今本竹書紀年疏證》兩條 Work。

上一輪《竹書紀年》今古文重整發現：王國維這兩種現代權威著作——前者是古本
竹書紀年最精審的輯本（勝於朱右曾《汲冢紀年存真》），後者系統考辨今本之
偽（性質近於閻若璩《尚書古文疏證》之於尚書）——本庫僅見於抽象原典
description.sources 的書目線索，未建 Work。應使用者確認後建檔。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

GUBEN_ABSTRACT = "1evqpdnrz483k"   # 竹書紀年（古本一系抽象總綱）
JINBEN = "1ev3babc1g5c0"           # 今本竹書紀年
WGW_ENTITY = "1j98p5amz8glc"       # 王國維

GUBEN_JIXIAO = "1ewzymlopifqy"     # 新建：古本竹書紀年輯校
JINBEN_SHUZHENG = "1ew78f5m0nxyn"  # 新建：今本竹書紀年疏證


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def save_index(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")


def shard_of(id_str, n=16):
    h = 0
    for c in id_str:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return h % n


def main():
    jixiao = {
        "schema_version": 1,
        "id": GUBEN_JIXIAO,
        "type": "work",
        "title": "古本竹書紀年輯校",
        "authors": [
            {"name": "王國維", "role": "輯校", "dynasty": "清", "entity_id": WGW_ENTITY}
        ],
        "dynasty": "清",
        "description": {
            "text": "王國維據唐宋類書、史注（《水經注》《史記正義》《太平御覽》等）所引《竹書紀年》原文重新輯錄考校，較朱右曾《汲冢紀年存真》更為精審全面，糾正朱本誤收誤斷之處，為近世公認最重要的古本竹書紀年輯本，後世研究古本竹書紀年皆以此為基礎（1925年范祥雍、1957年方詩銘等續有校補，然體例悉本王氏）。與《今本竹書紀年疏證》同時撰成、互為姊妹篇，一輯古本佚文，一辨今本之偽。",
            "sources": ["王國維《古本竹書紀年輯校》（收入《海寧王靜安先生遺書》）"]
        },
        "related_works": [
            {"id": GUBEN_ABSTRACT, "title": "竹書紀年", "relation": "contains_text_of",
             "note": "所輯即古本竹書紀年之佚文，屬古本一系"},
            {"id": JINBEN_SHUZHENG, "title": "今本竹書紀年疏證", "relation": "related",
             "note": "與本書同時撰成之姊妹篇，一輯古本、一辨今本"}
        ],
        "ai_note": "2026-08-10：應使用者要求建檔——上一輪《竹書紀年》今古文重整時發現本書僅見於「竹書紀年」（古本一系，1evqpdnrz483k）description.sources 之書目線索，未建獨立 Work，今補立。",
        "updated_at": "2026-08-10T00:00:00+00:00",
        "period": "qing",
        "period_basis": "據 authors[0].dynasty「清」"
    }

    shuzheng = {
        "schema_version": 1,
        "id": JINBEN_SHUZHENG,
        "type": "work",
        "title": "今本竹書紀年疏證",
        "authors": [
            {"name": "王國維", "role": "撰", "dynasty": "清", "entity_id": WGW_ENTITY}
        ],
        "dynasty": "清",
        "description": {
            "text": "王國維系統考辨今本《竹書紀年》（明范欽輯合本）之偽，逐條列舉今本與《水經注》《史記正義》《太平御覽》等所引古本佚文之歧異，並考其割裂拼湊之跡，證成《四庫全書總目》《養新錄》「此書必明人所葺」之說，為今本辨偽最系統精審之作，性質近於閻若璩《尚書古文疏證》之於偽古文尚書。與《古本竹書紀年輯校》同時撰成、互為姊妹篇。",
            "sources": ["王國維《今本竹書紀年疏證》（收入《海寧王靜安先生遺書》）"]
        },
        "related_works": [
            {"id": JINBEN, "title": "今本竹書紀年", "relation": "studies",
             "note": "系統辨今本之偽，性質近閻若璩《尚書古文疏證》之於尚書"},
            {"id": GUBEN_JIXIAO, "title": "古本竹書紀年輯校", "relation": "related",
             "note": "與本書同時撰成之姊妹篇，一輯古本、一辨今本"}
        ],
        "ai_note": "2026-08-10：應使用者要求建檔——上一輪《竹書紀年》今古文重整時發現本書僅見於「竹書紀年」（古本一系，1evqpdnrz483k）description.sources 之書目線索，未建獨立 Work，今補立。",
        "updated_at": "2026-08-10T00:00:00+00:00",
        "period": "qing",
        "period_basis": "據 authors[0].dynasty「清」"
    }

    save(ROOT / "Work/1/e/w" / f"{GUBEN_JIXIAO}-古本竹書紀年輯校.json", jixiao)
    save(ROOT / "Work/1/e/w" / f"{JINBEN_SHUZHENG}-今本竹書紀年疏證.json", shuzheng)

    # 反向關聯
    guben_path = ROOT / "Work/1/e/v/1evqpdnrz483k-竹書紀年.json"
    guben = load(guben_path)
    guben["related_works"].append(
        {"id": GUBEN_JIXIAO, "title": "古本竹書紀年輯校", "relation": "text_carried_by"}
    )
    save(guben_path, guben)

    jinben_path = ROOT / "Work/1/e/v/1ev3babc1g5c0-今本竹書紀年.json"
    jinben = load(jinben_path)
    jinben["related_works"].append(
        {"id": JINBEN_SHUZHENG, "title": "今本竹書紀年疏證", "relation": "studied_by"}
    )
    save(jinben_path, jinben)

    # entity 王國維
    ent_path = ROOT / "Entity/1/j/9/1j98p5amz8glc-王國維.json"
    ent = load(ent_path)
    ent["works"].append({"work_id": GUBEN_JIXIAO, "role": "輯校"})
    ent["works"].append({"work_id": JINBEN_SHUZHENG, "role": "撰"})
    save(ent_path, ent)

    # index/works 補入
    for new_id, title, path in [
        (GUBEN_JIXIAO, "古本竹書紀年輯校", f"Work/1/e/w/{GUBEN_JIXIAO}-古本竹書紀年輯校.json"),
        (JINBEN_SHUZHENG, "今本竹書紀年疏證", f"Work/1/e/w/{JINBEN_SHUZHENG}-今本竹書紀年疏證.json"),
    ]:
        s = shard_of(new_id)
        shard_path = ROOT / "index" / "works" / f"{s:x}.json"
        shard_data = load(shard_path)
        shard_data[new_id] = {
            "id": new_id, "title": title, "type": "Work", "path": path,
            "author": "王國維", "dynasty": "清", "role": "撰" if "疏證" in title else "輯校",
            "period": "qing"
        }
        save_index(shard_path, shard_data)
        print(f"indexed {new_id} -> shard {s:x}.json")


if __name__ == "__main__":
    main()
