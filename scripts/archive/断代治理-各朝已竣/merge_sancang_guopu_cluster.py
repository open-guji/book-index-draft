#!/usr/bin/env python3
"""解決「三蒼」（秦李斯等原編，東晉郭璞注）五方重出（秦朝文獻報告第五節
留供日後處理之發現第2項）。

五條記錄皆指同一部書——《三蒼》三卷，秦李斯（暨趙高、胡母敬）原編，
東晉郭璞注／解：

  1. 1evc5pequvegw「三蒼郭璞注」（隋書經籍志著錄，附詳實隋志考證引
     唐書經籍志／唐書藝文志／謝啟昆《小學考》／馬國翰輯本序／孫祠
     書目等，內容最豐，已建輯佚檔，定為主條）。
  2. 1evcpcv0ridq8「三蒼」（舊唐書經籍志：「李斯等撰，郭璞解」）。
  3. 1evgora3dg740「三蒼」（國史經籍志：「郭璞撰」——郭璞列為撰人
     實誤，當作解／注）。
  4. 1evcs0ac57shs「李斯等三蒼」（新唐書藝文志）。
  5. 1evfubynprmrk「三蒼注」（補晉書藝文志，其自身著錄語已言「兩
     《唐志》俱作『郭璞解』」，明確自陳與舊、新兩唐志同指一書；具
     完整郭璞／東晉／period=jin 結構化資料）。

今以 1 為主條，2-5 之 indexed_by 併入，並自 5 補入主條缺漏之作者角色
（注）、朝代（東晉）、period 等結構化欄位；改繫 4 處 collated_edition
引用；Entity 郭璞之 works[] 原有三筆分別指 1、3、5，今併為一筆指主條。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

BASE = "1evc5pequvegw"
DONORS = ["1evcpcv0ridq8", "1evgora3dg740", "1evcs0ac57shs", "1evfubynprmrk"]


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, data, indent=2):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
        f.write("\n")


def save_index(p, data):
    save(p, data, indent=1)


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


def delete_work(idx, wid):
    path = idx[wid]
    path.unlink()
    s = shard_of(wid)
    p = ROOT / "index" / "works" / f"{s:x}.json"
    d = load(p)
    if wid in d:
        del d[wid]
        save_index(p, d)


def retarget_collated(path, old_id, new_id, note):
    data = load(path)
    changed = False
    for sec in data.get("sections", []):
        if sec.get("work_id") == old_id:
            sec["work_id"] = new_id
            sec["link_basis"] = note
            changed = True
        wids = sec.get("work_ids")
        if wids and old_id in wids:
            sec["work_ids"] = [new_id if w == old_id else w for w in wids]
            sec["link_basis"] = note
            changed = True
    if changed:
        save(path, data, indent=1)
    return changed


COLLATED_RETARGETS = [
    ("1evcpcv0ridq8", "Work/1/e/v/1evcpbhmiqdj4/collated_edition/詁訓小學類.json"),
    ("1evgora3dg740", "Work/1/e/v/1ev3bb4qxubr4/collated_edition/經類.json"),
    ("1evcs0ac57shs", "Work/1/e/v/1evcs059gkvls/collated_edition/小學類.json"),
    ("1evfubynprmrk", "Work/1/e/v/1evfu57n5n37k/collated_edition/甲部經錄·小學類.json"),
]


def main():
    idx = build_index()
    base = load(idx[BASE])

    base["authors"] = [
        {
            "name": "郭璞",
            "role": "注",
            "dynasty": "東晉",
            "entity_id": "1j968k0jdrlz4",
            "dynasty_basis": "manual:historical_figure(郭璞(276-324)，字景純，東晉文學家訓詁學家)",
        }
    ]
    base["period"] = "jin"
    base["period_basis"] = "據 authors[0].dynasty「東晉」"

    for did in DONORS:
        donor = load(idx[did])
        base["indexed_by"] = base.get("indexed_by", []) + donor.get("indexed_by", [])

    base["ai_note"] = base.get("ai_note", "") + (
        " 2026-08-11：秦朝文獻逐條核查衍生發現——本條與 1evcpcv0ridq8"
        "「三蒼」（舊唐書經籍志）、1evgora3dg740「三蒼」（國史經籍志，"
        "誤題郭璞為撰人）、1evcs0ac57shs「李斯等三蒼」（新唐書藝文志）、"
        "1evfubynprmrk「三蒼注」（補晉書藝文志，其著錄語自陳「兩《唐志》"
        "俱作『郭璞解』」，明確自證與前二者同書）五方重出，皆指同一部"
        "《三蒼》三卷（秦李斯等原編，東晉郭璞注）。今以本條（隋書經籍志"
        "著錄，內容最豐）為主條，四條之 indexed_by 併入；並自 1evfubynprmrk"
        "補入本條原缺之作者角色（注）、朝代（東晉）、period 等結構化"
        "欄位。"
    )
    save(idx[BASE], base)

    for did, path in COLLATED_RETARGETS:
        retarget_collated(
            ROOT / path, did, BASE,
            f"原繫 {did}（三蒼異志著錄殘條，已併入 {BASE}，2026-08-11），今改繫。",
        )

    for did in DONORS:
        delete_work(idx, did)

    # Entity 郭璞：三筆併一
    ent_p = ROOT / "Entity/1/j/9/1j968k0jdrlz4-郭璞.json"
    ent = load(ent_p)
    works = ent.get("works", [])
    new_works = []
    seen_base = False
    for w in works:
        wid = w.get("work_id")
        if wid == BASE:
            if not seen_base:
                w["role"] = "注"
                new_works.append(w)
                seen_base = True
            continue
        if wid in DONORS:
            continue
        new_works.append(w)
    if not seen_base:
        new_works.append({"work_id": BASE, "role": "注"})
    ent["works"] = new_works
    save(ent_p, ent)

    print("done")


if __name__ == "__main__":
    main()
