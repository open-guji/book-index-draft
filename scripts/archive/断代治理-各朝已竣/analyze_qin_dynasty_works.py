#!/usr/bin/env python3
"""秦朝文獻（dynasty="秦"）逐條深入處理，比照先秦組方法論。

發現與處理：
  1. 嶧山碑（1evgorjm3e60w）——秦始皇七刻石之一，原記錄無作者／朝代／
     period，完全遊離於系統之外。補作者（嬴政）、朝代、period。
  2. 七刻石（琅邪臺、東觀、碣石門、之罘、會稽、泰山、嶧山）原僅各自單向
     繫於《正續古文辭類纂》，彼此之間全無關聯，今建立七方全連通之
     related 關聯，並在說明性 description 中標明「秦始皇刻石」通稱系列。
  3. 秦皇東巡會稽刻石文（1evc5pf5687b4，隋書經籍志著錄之會稽刻石搨本）
     與 三十七年會稽立石刻文（1evhnsc0fnmkg，維基文庫／正續古文辭類纂
     本）為同一篇刻石文之不同志書著錄，未曾繫連，今併入後者（後者保留
     嬴政作者與 period 等結構化欄位，前者之隋志／隋志考證著錄併入）。
  4. 秦帝刻石文（1ewsovuzr2s3m，劉宋褚淡所輯七刻石合編本，已佚）與七
     刻石之間亦未建關聯；其本志原考語已言「不知是否即是此書」存疑，
     故僅建單向存疑 related，不作merge。
  5. 諫逐客書（1evhmgj3cy77k）與 上書秦始皇（1evi5wyrwah34）為李斯同
     一篇文章（「諫逐客書」乃通稱），前者無作者結構化資料，後者結構
     完整，今以後者為主併入前者之著錄與 collected_in 關聯，並以「諫
     逐客書」為正題、「上書秦始皇」入 additional_titles。
  6. 黃石公《素書》一書原有三條 Work 疊床架屋：素書（1ev3bbevqtq80，
     一般書目彙纂之正條）、黃石公素書（1evkappbarw1s，故宮善本目錄
     匯入之版本層孤條，四冊）、繙譯黃石公素書（1evkpo0oqa800，故宮
     滿漢合璧本孤條，一冊）——後二者實為《素書》之具體印本，比照本庫
     既有體例（版本層併入原作品之 books[]，不另立 Work），今併入正條。
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
            idx[wid] = (ROOT / entry["path"], entry)
    return idx


def delete_work(idx, wid):
    path, _ = idx[wid]
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
        save(path, data)
    return changed


def add_related(data, target_id, target_title, relation, note=None):
    rw = data.setdefault("related_works", [])
    if rw is None:
        rw = []
        data["related_works"] = rw
    if any(e["id"] == target_id for e in rw):
        return False
    entry = {"id": target_id, "title": target_title, "relation": relation}
    if note:
        entry["note"] = note
    rw.append(entry)
    return True


QISHI_STONES = [
    ("1evhnsbbfqghs", "二十八年泰山刻石文"),
    ("1evhnsbgi11q8", "琅邪臺立石刻文"),
    ("1evhnsblig7pc", "二十九年之罘刻石文"),
    ("1evhnsbqjt3b4", "東觀刻石文"),
    ("1evhnsbvjajnk", "三十二年刻碣石門"),
    ("1evhnsc0fnmkg", "三十七年會稽立石刻文"),
    ("1evgorjm3e60w", "嶧山碑"),
]
STONE_NOTE = "秦始皇統一天下後歷次東巡所立刻石，通稱「秦始皇刻石」系列"


def fix_yishan_stele(idx):
    p, _ = idx["1evgorjm3e60w"]
    d = load(p)
    d["authors"] = [
        {"name": "嬴政", "dynasty": "秦", "role": "作", "entity_id": "1j968iupu11ql"}
    ]
    d["period"] = "qin-han"
    d["period_basis"] = "據 authors[0].dynasty「秦」"
    d["ai_note"] = d.get("ai_note", "") + (
        " 2026-08-11：秦朝文獻逐條核查補入——本條原無作者／朝代／period，"
        "完全遊離於系統之外。嶧山碑為秦始皇二十八年（前219）東巡所立七刻石"
        "之一（原石早佚，今傳本為宋鄭文寶據南唐徐鉉摹本所刻），今補作者"
        "（嬴政）、朝代、period，並與其餘六刻石建立 related 關聯。"
    )
    save(p, d)


def link_qishi_stones_group(idx):
    added = 0
    for wid, title in QISHI_STONES:
        p, _ = idx[wid]
        d = load(p)
        changed = False
        for owid, otitle in QISHI_STONES:
            if owid == wid:
                continue
            if add_related(d, owid, otitle, "related", STONE_NOTE):
                changed = True
                added += 1
        if changed:
            save(p, d)
    return added


def merge_kuaiji_stone(idx):
    """秦皇東巡會稽刻石文 -> 三十七年會稽立石刻文"""
    donor_p, _ = idx["1evc5pf5687b4"]
    base_p, _ = idx["1evhnsc0fnmkg"]
    donor = load(donor_p)
    base = load(base_p)
    base["indexed_by"] = base.get("indexed_by", []) + donor.get("indexed_by", [])
    base["emendated_by"] = base.get("emendated_by", []) + donor.get("emendated_by", [])
    base["ai_note"] = base.get("ai_note", "") + (
        " 2026-08-11：併入 1evc5pf5687b4「秦皇東巡會稽刻石文」（隋書經籍志"
        "著錄之會稽刻石搨本一卷）——與本條同為秦始皇三十七年會稽刻石文，"
        "僅志書著錄之著錄脈絡不同（一由隋志經部史部小學／集部著錄，一由"
        "維基文庫暨《正續古文辭類纂》所收原文轉錄），今併其 indexed_by／"
        "emendated_by 入本條。"
    )
    save(base_p, base)
    retarget_collated(
        ROOT / "Work/1/e/v/1ev85yncs9ibk/collated_edition/小學類.json",
        "1evc5pf5687b4", "1evhnsc0fnmkg",
        "原繫 1evc5pf5687b4（秦皇東巡會稽刻石文，已併入 1evhnsc0fnmkg，2026-08-11），今改繫。",
    )
    retarget_collated(
        ROOT / "Work/1/e/v/1evdlszdhf5z4/collated_edition/經部十·小學類.json",
        "1evc5pf5687b4", "1evhnsc0fnmkg",
        "原繫 1evc5pf5687b4（秦皇東巡會稽刻石文，已併入 1evhnsc0fnmkg，2026-08-11），今改繫。",
    )
    delete_work(idx, "1evc5pf5687b4")


def link_qindi_keshiwen(idx):
    """秦帝刻石文（劉宋褚淡輯，已佚）-> 七刻石群組，存疑軟連結"""
    p, _ = idx["1ewsovuzr2s3m"]
    d = load(p)
    note = "劉宋褚淡所輯七刻石合編本，已佚；其隋志原著錄語即言「不知是否即是此書」，存疑"
    changed = False
    for wid, title in QISHI_STONES:
        if add_related(d, wid, title, "related", note):
            changed = True
    if changed:
        save(p, d)


def merge_jianzhukeshu(idx):
    """諫逐客書 -> 上書秦始皇（保留為主條，改題為「諫逐客書」）"""
    donor_p, _ = idx["1evhmgj3cy77k"]
    base_p, _ = idx["1evi5wyrwah34"]
    donor = load(donor_p)
    base = load(base_p)

    base["additional_titles"] = base.get("additional_titles", []) + ["上書秦始皇"]
    base["title"] = "諫逐客書"

    existing_urls = {r.get("url") for r in base.get("resources", [])}
    for r in donor.get("resources", []):
        if r.get("url") not in existing_urls:
            base.setdefault("resources", []).append(r)
            existing_urls.add(r.get("url"))

    existing_rel_ids = {e["id"] for e in base.get("related_works", [])}
    for e in donor.get("related_works", []):
        if e["id"] not in existing_rel_ids:
            base.setdefault("related_works", []).append(e)
            existing_rel_ids.add(e["id"])

    base["ai_note"] = base.get("ai_note", "") + (
        " 2026-08-11：本條原題「上書秦始皇」，與 1evhmgj3cy77k「諫逐客書」"
        "為李斯同一篇文章（收入《昭明文選》《古文觀止》《正續古文辭類纂》），"
        "「諫逐客書」為通稱正題，今改題並將「上書秦始皇」移入 additional_"
        "titles；併入該條之 collected_in 關聯（古文觀止、正續古文辭類纂）"
        "及 Wikisource 資源連結。"
    )
    save(base_p, base)
    retarget_collated(
        ROOT / "Work/1/e/v/1evhmcmmhp2bk/collated_edition/juan_04.json",
        "1evhmgj3cy77k", "1evi5wyrwah34",
        "原繫 1evhmgj3cy77k（諫逐客書，已併入 1evi5wyrwah34 並改該條主題為「諫逐客書」，2026-08-11），今改繫。",
    )
    retarget_collated(
        ROOT / "Work/1/e/v/1evhnqciqrwu8/collated_edition/juan_11.json",
        "1evhmgj3cy77k", "1evi5wyrwah34",
        "原繫 1evhmgj3cy77k（諫逐客書，已併入 1evi5wyrwah34 並改該條主題為「諫逐客書」，2026-08-11），今改繫。",
    )
    delete_work(idx, "1evhmgj3cy77k")


def merge_suishu_editions(idx):
    """黃石公素書、繙譯黃石公素書（故宮善本孤條，版本層）-> 素書（正條）"""
    base_p, _ = idx["1ev3bbevqtq80"]
    base = load(base_p)
    base_books = set(base.get("books", []))

    for donor_id in ("1evkappbarw1s", "1evkpo0oqa800"):
        donor_p, _ = idx[donor_id]
        donor = load(donor_p)
        for bid in donor.get("books", []):
            base_books.add(bid)
            # retarget Book.work_id
            shard = shard_of(bid)
            found = None
            for cand in (ROOT / "Book").rglob(f"{bid}-*.json"):
                found = cand
                break
            if found:
                bdata = load(found)
                bdata["work_id"] = "1ev3bbevqtq80"
                save(found, bdata)

    base["books"] = sorted(base_books)
    base["ai_note"] = base.get("ai_note", "") + (
        " 2026-08-11：併入 1evkappbarw1s「黃石公素書」（故宮善本目錄匯入之"
        "清康熙四十三年武英殿刊漢滿合璧本孤條，四冊）與 1evkpo0oqa800"
        "「繙譯黃石公素書」（故宮善本目錄匯入之清乾隆間武英殿刊漢滿合璧本"
        "孤條，一冊）——二者皆屬本書之具體印本（版本層），比照本庫既有"
        "體例（如「莊子」條故宮善本孤條之處理）併入本條 books[]，不另立"
        "Work。"
    )
    save(base_p, base)
    delete_work(idx, "1evkappbarw1s")
    delete_work(idx, "1evkpo0oqa800")


def main():
    idx = build_index()
    fix_yishan_stele(idx)
    added = link_qishi_stones_group(idx)
    print("七刻石 related_works added:", added)
    merge_kuaiji_stone(idx)
    link_qindi_keshiwen(idx)
    merge_jianzhukeshu(idx)
    merge_suishu_editions(idx)
    print("done")


if __name__ == "__main__":
    main()
