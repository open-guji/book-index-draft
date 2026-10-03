#!/usr/bin/env python3
"""補齊「性有善有惡」四家群組（先秦組 transmission_complexity 75 條逐條核查發現）。

《論衡·本性》：「宓子賤、漆雕開、公孫尼子之徒，亦論情性，與世子相出入，
皆言性有善有惡。」四家並舉，同論人性有善有惡，然本庫僅 宓子／景子
（因景子之書「說宓子語」而相繫）已建 related，世子、漆雕子、公孫尼子
三條彼此及與宓子皆未建關聯。今據王充原文明文並舉之四家，建立五條
（四家兩兩相繫，扣除已存在之 宓子—景子，故僅需新增四家間之關聯）
雙向 related。
"""
import json
from pathlib import Path
from itertools import combinations

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


MEMBERS = [
    ("1ev7xkhywxreo", "世子"),
    ("1ev7xkht2v1ts", "宓子"),
    ("1ev7xkhvwmeww", "漆雕子"),
    ("1ev7xkhdmxedc", "公孫尼子"),
]
NOTE = "《論衡·本性》：「宓子賤、漆雕開、公孫尼子之徒，亦論情性，與世子相出入，皆言性有善有惡」，四家並舉論性之學派"


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
    for wid, title in MEMBERS:
        p = idx[wid]
        d = load(p)
        changed = False
        for owid, otitle in MEMBERS:
            if owid == wid:
                continue
            if add_related(d, owid, otitle, NOTE):
                changed = True
                added += 1
        if changed:
            save(p, d)
    print("related_works entries added:", added)


if __name__ == "__main__":
    main()
