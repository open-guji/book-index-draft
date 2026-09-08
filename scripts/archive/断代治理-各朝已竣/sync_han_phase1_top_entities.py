#!/usr/bin/env python3
"""西漢探勘分期第一階段：382條「entity 存在但 dynasty 仍籠統」中，
按出現頻次處理前 20 位歷史人物（涵蓋約 200 條，佔該批過半）。

逐位以生卒年／仕歷核校後定案（見下表 CLASSIFICATIONS），先訂正各人
物 Entity 之 dynasty，再同步覆寫其名下 Work.authors[0].dynasty 仍作
籠統「漢」者。

順帶處理一個斷代邊界誤植：孔鮒（孔子八世孫，仕陳勝為博士，卒於秦
二世元年前209，未及見漢，dynasty「漢」有誤，訂正為「秦」）。
"""
import json
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

# name -> (correct dynasty, brief historical basis)
CLASSIFICATIONS = {
    "鄭玄": ("東漢", "127-200，東漢經學家"),
    "司馬遷": ("西漢", "前145-前86，西漢太史令，《史記》作者"),
    "揚雄": ("西漢", "前53-18，西漢末年學者（歷仕成哀平新四朝，習慣歸西漢）"),
    "劉向": ("西漢", "前77-前6，西漢經學家"),
    "賈誼": ("西漢", "前200-前168，西漢文帝時人"),
    "王粲": ("東漢", "177-217，東漢末建安七子之一"),
    "趙岐": ("東漢", "108-201，東漢經學家，注《孟子》"),
    "晁錯": ("西漢", "前200-前154，西漢景帝時人"),
    "毛亨": ("西漢", "西漢初傳《詩》學者"),
    "劉德": ("西漢", "?-前130，河間獻王，西漢景帝子"),
    "趙充國": ("西漢", "前137-前52，西漢宣帝時名將"),
    "陳琳": ("東漢", "?-217，東漢末建安七子之一"),
    "荀爽": ("東漢", "128-190，東漢經學家"),
    "孟喜": ("西漢", "西漢宣帝時易學孟氏學創始人"),
    "王褒": ("西漢", "?-前61，西漢宣帝時辭賦家"),
    "劉楨": ("東漢", "186-217，東漢末建安七子之一"),
    "匡衡": ("西漢", "西漢元帝時丞相"),
    "夏侯勝": ("西漢", "西漢宣帝時經學家"),
    "孔融": ("東漢", "153-208，東漢末建安七子之一"),
}

KONGFU_DYNASTY_FIX = "秦"  # 孔鮒，卒於秦二世元年（前209），未及見漢


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, data, indent=2):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
        f.write("\n")


def build_work_index():
    idx = {}
    for s in SHARDS:
        d = load(ROOT / "index" / "works" / f"{s}.json")
        for wid, entry in d.items():
            idx[wid] = ROOT / entry["path"]
    return idx


def shard_of(id_str, n=16):
    h = 0
    for c in id_str:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return h % n


def main():
    widx = build_work_index()

    ent_by_id = {}
    for f in glob.glob(str(ROOT / "Entity" / "**" / "*.json"), recursive=True):
        try:
            j = load(Path(f))
        except Exception:
            continue
        eid = j.get("id")
        if eid:
            ent_by_id[eid] = Path(f)

    fixed_entities = set()
    fixed_works = 0

    for wid, path in widx.items():
        try:
            j = load(path)
        except Exception:
            continue
        if j.get("period") != "qin-han":
            continue
        a = j.get("authors")
        if not a or a[0].get("dynasty") != "漢":
            continue
        name = a[0].get("name")
        eid = a[0].get("entity_id")
        if not eid:
            continue

        if name == "孔鮒":
            a[0]["dynasty"] = KONGFU_DYNASTY_FIX
            j["period_basis"] = "據 authors[0].dynasty「秦」（原誤標「漢」，2026-08-11 訂正：孔鮒卒於秦二世元年前209，未及見漢）"
            save(path, j)
            fixed_works += 1
            if eid in ent_by_id and eid not in fixed_entities:
                ent = load(ent_by_id[eid])
                ent["dynasty"] = KONGFU_DYNASTY_FIX
                ent["period_basis"] = "據 dynasty「秦」（原CBDB/匯入誤作「漢」，2026-08-11訂正：孔鮒卒於秦二世元年前209）"
                ent["ai_note"] = ent.get("ai_note", "") + " 2026-08-11：孔鮒卒於秦二世元年（前209），未及見漢，dynasty「漢」有誤，訂正為「秦」。"
                save(ent_by_id[eid], ent)
                fixed_entities.add(eid)
            continue

        if name not in CLASSIFICATIONS:
            continue
        target_dyn, basis = CLASSIFICATIONS[name]

        a[0]["dynasty"] = target_dyn
        j["period_basis"] = f"據 authors[0].dynasty「{target_dyn}」（原作籠統「漢」，2026-08-11 西漢探勘分期第一階段訂正：{basis}）"
        save(path, j)
        fixed_works += 1

        if eid in ent_by_id and eid not in fixed_entities:
            ent = load(ent_by_id[eid])
            if ent.get("dynasty") in (None, "漢", "秦漢"):
                ent["dynasty"] = target_dyn
                ent["period"] = "qin-han"
                ent["period_basis"] = f"據 dynasty「{target_dyn}」（原作籠統，2026-08-11 西漢探勘分期第一階段訂正：{basis}）"
                save(ent_by_id[eid], ent)
                fixed_entities.add(eid)

    print(f"fixed works: {fixed_works}, fixed entities: {len(fixed_entities)}")


if __name__ == "__main__":
    main()
