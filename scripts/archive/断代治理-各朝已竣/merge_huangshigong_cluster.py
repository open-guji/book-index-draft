#!/usr/bin/env python3
"""解決黃石公術數兵陰陽類文獻叢集中四對確鑿重出（秦朝文獻報告第五節
留供日後處理之發現第1項，本輪先處理其中題名／卷數完全吻合之高信度
部分，其餘因書名歧異較大或卷數不合，暫不合併，留待日後）。

四對重出（皆隋書經籍志一卷本 vs 國史經籍志一卷本，題名全同或僅為
異體字之別，卷數相合）：
  1. 黃石公內記敵法：1evcmndc4y1og（隋志）／1evgq11uuyk8w（國史經籍志）
  2. 黃石公五壘圖：  1evcmndcq66m8（隋志）／1evgq16adum80（國史經籍志）
  3. 黃石公三奇法：  1evcmndcl6dxc（隋志，"奇"）／1evgq181569z4（國史經籍志，"竒"異體）
  4. 黃石公陰謀行軍秘法：1evcmndcuuqrk（隋志，"陰"）／1evgq183vi134（國史經籍志，"隂"異體）

以隋書經籍志所錄者（時代較早）為主條，國史經籍志之著錄併入。

另建立二條低信度軟連結（僅 related，不合併，皆存疑待覈）：
  - 黃石公陰謀行軍秘法（1evcmndcuuqrk）↔ 黃石公秘經（1evgq11s5vrb4）
    ——前者隋志著錄語本身即言「梁有《黃石公秘經》二卷」，卷數與後者合。
  - 黃石公陰謀乘鬥魁剛行軍秘（1evcpd2s57shs，舊唐志）↔ 黃石公隂陽乗
    斗魁是行軍秘法（1evgq19rkmx34，國史經籍志）——題名近似惟差三字，
    卷數不全合（前者無卷數記載），存疑不合併。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

MERGE_PAIRS = [
    ("1evcmndc4y1og", "1evgq11uuyk8w", "黃石公內記敵法"),
    ("1evcmndcq66m8", "1evgq16adum80", "黃石公五壘圖"),
    ("1evcmndcl6dxc", "1evgq181569z4", "黃石公三奇法"),
    ("1evcmndcuuqrk", "1evgq183vi134", "黃石公陰謀行軍秘法"),
]

COLLATED_FILE = "Work/1/e/v/1ev3bb4qxubr4/collated_edition/子類下.json"

SOFT_LINKS = [
    ("1evcmndcuuqrk", "黃石公陰謀行軍秘法", "1evgq11s5vrb4", "黃石公秘經",
     "本條隋志著錄語自言「梁有《黃石公秘經》二卷」，與彼條卷數相合，存疑待覈"),
    ("1evcpd2s57shs", "黃石公陰謀乘鬥魁剛行軍秘", "1evgq19rkmx34", "黃石公隂陽乗斗魁是行軍秘法",
     "題名近似（舊唐志／國史經籍志分錄），然差三字且卷數未全合，存疑待覈，暫不合併"),
]


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, data, indent):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
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


def delete_work(idx, wid):
    path = idx[wid]
    path.unlink()
    s = shard_of(wid)
    p = ROOT / "index" / "works" / f"{s:x}.json"
    d = load(p)
    if wid in d:
        del d[wid]
        save(p, d, indent=1)


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

    # 偵測 collated_edition 原始 indent
    raw = (ROOT / COLLATED_FILE).read_text(encoding="utf-8")
    coll_indent = 2 if raw.startswith('{\n  "') else 1
    coll = load(ROOT / COLLATED_FILE)

    for base_id, donor_id, canon_title in MERGE_PAIRS:
        base_p = idx[base_id]
        donor_p = idx[donor_id]
        base = load(base_p)
        donor = load(donor_p)
        base["indexed_by"] = base.get("indexed_by", []) + donor.get("indexed_by", [])
        base["ai_note"] = base.get("ai_note", "") + (
            f" 2026-08-11：秦朝文獻逐條核查衍生發現——併入 {donor_id}"
            f"「{donor['title']}」（國史經籍志著錄，與本條隋書經籍志著錄"
            "題名全同或僅異體字之別，卷數相合，同書異志重出）。"
        )
        save(base_p, base, indent=2)

        changed = False
        for sec in coll.get("sections", []):
            if sec.get("work_id") == donor_id:
                sec["work_id"] = base_id
                sec["link_basis"] = f"原繫 {donor_id}（{donor['title']}，已併入 {base_id}，2026-08-11），今改繫。"
                changed = True
            wids = sec.get("work_ids")
            if wids and donor_id in wids:
                sec["work_ids"] = [base_id if w == donor_id else w for w in wids]
                sec["link_basis"] = f"原繫 {donor_id}（{donor['title']}，已併入 {base_id}，2026-08-11），今改繫。"
                changed = True

        delete_work(idx, donor_id)

    save(ROOT / COLLATED_FILE, coll, indent=coll_indent)

    for wid1, t1, wid2, t2, note in SOFT_LINKS:
        p1 = idx[wid1]
        d1 = load(p1)
        if add_related(d1, wid2, t2, note):
            save(p1, d1, indent=2)
        p2 = idx[wid2]
        d2 = load(p2)
        if add_related(d2, wid1, t1, note):
            save(p2, d2, indent=2)

    print("done")


if __name__ == "__main__":
    main()
