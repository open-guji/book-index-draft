#!/usr/bin/env python3
"""三國魏晉探勘第一輪：period=three-kingdoms 範圍內同名人物之 Entity
分裂與朝代誤植，比照西漢探勘之賈逵案例方法逐一核實後修正。

高信度朝代誤植（有內證可斷，逕行修正）：
  - 蘇林（陳留耆舊傳）：三國蜀→三國魏。本條自身 indexed_by 引《隋書
    經籍志》「魏散騎常侍蘇林撰」，同一引文並提及「周斐汝南先賢傳」
    亦作「魏周斐撰」——一併訂正周斐。
  - 高堂隆（魏臺雜訪議）：三國蜀→三國魏。題名「魏臺」即指曹魏朝廷，
    与蜀漢無涉。
  - 何晏（魏明帝詮議）：三國吳→三國魏。題名「魏明帝」即指曹魏明帝，
    与孫吳無涉。

Entity 分裂合併（核對書目後確認同屬一人）：
  - 諸葛亮：1j96keo5xmjgg（蜀漢，2作品）併入 1j96ad6j691c0（三國蜀，
    18作品），標準化為「三國蜀」。
  - 虞翻：1j967cp1zdr29（秦漢，4作品，誤植）、1j96keepyy1a8（三國魏，
    1作品，誤植）併入 1j96kee06m9s0（三國吳，3作品，正確）。
  - 高堂隆：1j96hf9hvppmo（1作品）併入 1j96gyqur0ydc（三國魏，4作品）。
  - 何晏：1j96hf9ifowe8（1作品）併入 1j96ad6aoyy2o（三國魏，13作品）。
  - 薛綜、王象、王朗、孟康、李譔、張晏：各兩個同朝代 Entity，核對
    書目後確認同屬一人，合併（保留作品數較多或建立較早者為主條）。

周氏「雜字解站」／「雜字解詀」：同引三國藝文志同一段文字（僅題名
OCR之異體字差），為同書異錄，且其中一條 Entity 誤植朝代「明」，
逕予合併並訂正。
"""
import json
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, data, indent=2):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
        f.write("\n")


def shard_of(id_str, n=16):
    h = 0
    for c in id_str:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return h % n


def build_work_index():
    idx = {}
    for s in SHARDS:
        d = load(ROOT / "index" / "works" / f"{s}.json")
        for wid, entry in d.items():
            idx[wid] = ROOT / entry["path"]
    return idx


def build_entity_index():
    idx = {}
    for f in glob.glob(str(ROOT / "Entity" / "**" / "*.json"), recursive=True):
        try:
            j = load(Path(f))
        except Exception:
            continue
        eid = j.get("id")
        if eid:
            idx[eid] = Path(f)
    return idx


def delete_entity(eid, ent_path):
    ent_path.unlink()
    s = shard_of(eid)
    p = ROOT / "index" / "entities" / f"{s:x}.json"
    d = load(p)
    if eid in d:
        del d[eid]
        save(p, d, indent=1)


def fix_work_dynasty(widx, wid, new_dyn, note):
    p = widx[wid]
    j = load(p)
    j["authors"][0]["dynasty"] = new_dyn
    if j.get("dynasty"):
        j["dynasty"] = new_dyn
    j["period_basis"] = f"據 authors[0].dynasty「{new_dyn}」（原誤植，2026-08-11 三國魏晉探勘訂正：{note}）"
    j["ai_note"] = j.get("ai_note", "") + f" 2026-08-11：三國魏晉探勘查出朝代誤植——{note}，已訂正。"
    save(p, j)


def merge_entities(widx, eidx, base_eid, donor_eids, target_dyn, note):
    base_p = eidx[base_eid]
    base = load(base_p)
    base_works = {w["work_id"]: w for w in base.get("works", [])}
    base["dynasty"] = target_dyn

    for did in donor_eids:
        donor_p = eidx[did]
        donor = load(donor_p)
        for w in donor.get("works", []):
            base_works.setdefault(w["work_id"], w)
        delete_entity(did, donor_p)

    base["works"] = list(base_works.values())
    base["ai_note"] = base.get("ai_note", "") + f" 2026-08-11：三國魏晉探勘查出同名分裂——{note}，已合併。"
    save(base_p, base)

    for wid in base_works:
        p = widx.get(wid)
        if not p:
            continue
        j = load(p)
        for a in j.get("authors", []):
            if a.get("entity_id") in donor_eids:
                a["entity_id"] = base_eid
                a["dynasty"] = target_dyn
                if j.get("dynasty"):
                    j["dynasty"] = target_dyn
        save(p, j)


def main():
    widx = build_work_index()
    eidx = build_entity_index()

    # 高信度朝代誤植
    fix_work_dynasty(widx, "1evfteli62neo", "三國魏",
                      "蘇林本人自身著錄語（隋書經籍志）明言「魏散騎常侍蘇林撰」")
    fix_work_dynasty(widx, "1evcml2wy6o00", "三國魏",
                      "周斐同見於蘇林條下三國藝文志引文，明言「魏周斐撰」")
    fix_work_dynasty(widx, "1evftek8psnwg", "三國魏",
                      "題名「魏臺雜訪議」，魏臺即曹魏朝廷，与蜀漢無涉")
    fix_work_dynasty(widx, "1evftekuaf3eo", "三國魏",
                      "題名「魏明帝詮議」，魏明帝即曹魏明帝，与孫吳無涉")

    # Entity 分裂合併
    merge_entities(widx, eidx, "1j96ad6j691c0", ["1j96keo5xmjgg"], "三國蜀",
                    "諸葛亮：原分繫「蜀漢」與「三國蜀」二Entity，標準化為「三國蜀」")
    merge_entities(widx, eidx, "1j96kee06m9s0", ["1j967cp1zdr29", "1j96keepyy1a8"], "三國吳",
                    "虞翻：三方分裂（其一朝代誤作「秦漢」，其一誤作「三國魏」），核對書目（周易注/春秋外傳國語注/論語注/太玄注/京氏易律曆注等）確係同一東吳學者")
    merge_entities(widx, eidx, "1j96gyqur0ydc", ["1j96hf9hvppmo"], "三國魏",
                    "高堂隆：原一Entity朝代誤作「三國蜀」")
    merge_entities(widx, eidx, "1j96ad6aoyy2o", ["1j96hf9ifowe8"], "三國魏",
                    "何晏：原一Entity朝代誤作「三國吳」")
    merge_entities(widx, eidx, "1j96hhvcrjvi1", ["1j96kef653mdc"], "三國吳",
                    "薛綜：核對書目（薛綜集/二京賦解）確係同一東吳學者，逕予合併")
    merge_entities(widx, eidx, "1j96kedjpjdog", ["1j96hjwlxz6nb"], "三國魏",
                    "王象：核對書目（皇覽/王象集）確係同一曹魏學者，逕予合併")
    merge_entities(widx, eidx, "1j96kee2c14hs", ["1j96hhvcrjvi0"], "三國魏",
                    "王朗：核對書目（易傳/周官傳/孝經傳/春秋傳/王朗集）確係同一曹魏學者，逕予合併")
    merge_entities(widx, eidx, "1j96hjwlxz6mk", ["1j96hf9mali4g"], "三國魏",
                    "孟康：核對書目（漢書音義/老子注）確係同一曹魏學者，逕予合併")
    merge_entities(widx, eidx, "1j96kee9muxvk", ["1j96hjwlxz6mu"], "三國蜀",
                    "李譔：核對書目（尚書注/三禮注/古文易注解）確係同一蜀漢學者，逕予合併")
    merge_entities(widx, eidx, "1j96hjwlxz6n6", ["1j96keczv169s"], "三國魏",
                    "張晏：地理記與漢書注二條分述同一人生平（子博，中山人），確係同一曹魏學者，逕予合併")

    # 周氏「雜字解站」／「雜字解詀」：同書異題，其一Entity誤植朝代「明」
    merge_entities(widx, eidx, "1j96keemx2i2o", ["1j96hjwlxcpif"], "三國魏",
                    "周氏：其一Entity誤植朝代「明」，二條實引同一三國藝文志引文（隋志「魏掖庭右丞周氏撰」），為同書異錄")

    print("done")


if __name__ == "__main__":
    main()
