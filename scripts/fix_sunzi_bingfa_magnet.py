#!/usr/bin/env python3
"""解決 1evcmnd8q9s74「孫子兵法」磁鐵（先秦組「transmission_complexity」75條逐條核查時發現）。

本條原掛三類不相干內容：
  1. 隋書經籍志「孫子兵法二卷……魏武帝注」——真實著錄，然本庫已有專門的
     「孫子魏武帝注」(1evcs0sj05qf4) 承接魏武帝注本諸志著錄，本條應併入。
  2. 舊唐書經籍志「孫子兵法十三卷……魏武帝注」——與「孫子兵法魏武帝注」
     (1evcua6tdllhc) 既有著錄逐字重複，逕行捨棄。
  3. 新唐書藝文志「又續孫子兵法二卷」——與「續孫子兵法」(1evcmnd9kjsw0)
     既有著錄逐字重複，逕行捨棄。
  4. has_part 五條銀雀山漢簡孫子佚篇（吳問、四變、黃帝伐赤帝、地形二、
     見吳王）——這些是漢志八十二篇本之佚文，應屬《孫子》原典
     (1ev3bbesj0oow) 之子篇，非魏武帝注本之子篇，移正。
  5. Book 11rot1ajkr7yc（銀雀山漢墓竹簡整理本）——其自身 ai_note 已明言
     「屬版本層，故不另立作品」，應為《孫子》原典之版本，非魏武帝注本，
     一併移正。

移正後刪除本條。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

DOOMED = "1evcmnd8q9s74"
BASE = "1ev3bbesj0oow"          # 孫子（原典）
WEIWUDI = "1evcs0sj05qf4"       # 孫子魏武帝注

HAS_PART_CHAPTERS = [
    "1ewozvrrlfjex", "1ewozvrt845jf", "1ewozvrut8ky5", "1ewozvrwflyj3", "1ewozvry6z4sx"
]


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


def build_index():
    idx = {}
    for s in SHARDS:
        d = load(ROOT / "index" / "works" / f"{s}.json")
        for wid, entry in d.items():
            idx[wid] = ROOT / entry["path"]
    return idx


def retarget_collated(path, old_id, new_id, note):
    data = load(path)
    changed = False
    for sec in data.get("sections", []):
        if sec.get("work_id") == old_id:
            sec["work_id"] = new_id
            sec["link_basis"] = note
            changed = True
    if changed:
        save(path, data)
    return changed


def main():
    idx = build_index()
    doomed_p = idx[DOOMED]
    doomed = load(doomed_p)

    # 1. 隋書經籍志條目 -> 孫子魏武帝注
    weiwudi_p = idx[WEIWUDI]
    weiwudi = load(weiwudi_p)
    for e in doomed["indexed_by"]:
        if e["source"] == "隋書經籍志":
            weiwudi["indexed_by"].append(e)
    for e in doomed.get("emendated_by", []):
        if e["source"] in ("隋書經籍志考證",):
            weiwudi.setdefault("emendated_by", []).append(e)
    weiwudi["ai_note"] = weiwudi.get("ai_note", "") + (
        " | 2026-08-11：併入 1evcmnd8q9s74（原題「孫子兵法」磁鐵）中屬本條之隋書經籍志"
        "著錄及其考證；該條其餘內容（舊唐志/新唐志條目與既有記錄重複、has_part銀雀山漢簡"
        "佚篇、整理本Book）分別捨棄或移正至孫子原典 1ev3bbesj0oow，詳見該條 ai_note。"
    )
    save(weiwudi_p, weiwudi)

    # 2. has_part 五篇 -> 孫子原典
    base_p = idx[BASE]
    base = load(base_p)
    base_rw = base.setdefault("related_works", [])
    for wid in HAS_PART_CHAPTERS:
        p = idx[wid]
        d = load(p)
        crw = d.get("related_works", [])
        for e in crw:
            if e.get("id") == DOOMED:
                e["id"] = BASE
                e["title"] = "孫子"
        d["related_works"] = crw
        save(p, d)
        title = d["title"]
        if not any(e["id"] == wid for e in base_rw):
            base_rw.append({"id": wid, "title": title, "relation": "has_part"})

    # 3. Book 改繫
    book_p = ROOT / "Book/1/1/r/11rot1ajkr7yc-孫子兵法.json"
    bdata = load(book_p)
    bdata["work_id"] = BASE
    save(book_p, bdata)
    base.setdefault("books", []).append("11rot1ajkr7yc")

    # 4. 移除 base 對 doomed 的 related 自指
    base["related_works"] = [e for e in base_rw if e["id"] != DOOMED]
    base["ai_note"] = base.get("ai_note", "") + (
        " | 2026-08-11：解消 1evcmnd8q9s74「孫子兵法」磁鐵——該條原混雜隋志魏武帝注本著錄"
        "（已併入「孫子魏武帝注」1evcs0sj05qf4）、與既有記錄重複之舊唐志/新唐志著錄（已捨棄）、"
        "銀雀山漢簡孫子佚篇 has_part（吳問/四變/黃帝伐赤帝/地形二/見吳王，正確歸屬本條）、"
        "及銀雀山漢墓竹簡整理本 Book（11rot1ajkr7yc，其自身 ai_note 已明言「屬版本層」，"
        "正確歸屬本條，非魏武帝注本）。"
    )
    save(base_p, base)

    # 5. entity 孫武
    ent_p = ROOT / "Entity/1/j/9/1j96hl9t5ahog-孫武.json"
    ent = load(ent_p)
    ent["works"] = [w for w in ent["works"] if w["work_id"] != DOOMED]
    save(ent_p, ent)

    # 6. collated_edition 改繫（隋志相關兩處指向 doomed 者改繫至孫子魏武帝注）
    retarget_collated(ROOT / "Work/1/e/v/1ev85yncs9ibk/collated_edition/兵家類.json",
                       DOOMED, WEIWUDI,
                       "原繫 1evcmnd8q9s74（磁鐵，已解消），該條隋書經籍志著錄已併入 1evcs0sj05qf4（2026-08-11），今改繫。")
    retarget_collated(ROOT / "Work/1/e/v/1evdlszdhf5z4/collated_edition/子部十·兵家類.json",
                       DOOMED, WEIWUDI,
                       "原繫 1evcmnd8q9s74（磁鐵，已解消），該條隋書經籍志考證已併入 1evcs0sj05qf4（2026-08-11），今改繫。")

    # 7. 刪除 doomed
    doomed_p.unlink()
    s = shard_of(DOOMED)
    p = ROOT / "index" / "works" / f"{s:x}.json"
    d = load(p)
    if DOOMED in d:
        del d[DOOMED]
        save_index(p, d)

    print("done")


if __name__ == "__main__":
    main()
