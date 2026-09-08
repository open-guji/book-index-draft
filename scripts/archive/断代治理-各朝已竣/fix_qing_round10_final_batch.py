#!/usr/bin/env python3
"""清朝探勘 Round 10：33個剩餘「明」組混合Entity獨立立項之深查（第三批，收尾）。

  A. 黃之俊《堂集》《香屑集》：查明「堂集六十一卷」實為「𢈪堂集」
     （𢈪為罕用字，OCR/著錄脫落），真正撰人為黃之雋（1668-1748，
     清，庫中已有正確Entity與Work記錄：𢈪堂集1ev3begjoledc、
     香屑集1ev3bdfl66fwg），與明代同名人黃之俊（字君籲，b.1553）
     全然無關，本條為重出著錄，逕併入既有正確記錄。
  B. 劉昆《劉中丞奏稿》：查明實為晚清湖南巡撫劉崐（1808-1888，
     字玉崑，號韞齋，雲南景東人，道光二十一年進士，同治年間任
     湖南巡撫，清代官場俗稱巡撫為「中丞」，與書名合），與明代
     同名人劉昆全然無關，訂正author並拆分建立新Entity。
  C. 邱維屏／熊文舉／程正揆／鄧志謨：WebSearch確證四人皆為典型
     明末清初跨代人物（邱維屏為易堂九子之一、明遺民，1614-1679；
     熊文舉明末仕清至吏部左侍郎，1595-1668；程正揆前明崇禎進士、
     入清官工部侍郎，1606-1676；鄧志謨《蘭雪堂古事苑定本》書成於
     康熙丙寅〔1686〕，中國人民大學/中國科學院兩館著錄分別作
     「明」「清」，反映其人跨代身分本身即有歧見），比照李中梓/
     劉若金先例，訂正Entity.dynasty為「明末清初」，period留null，
     Work.period（皆已為qing，成書於清）維持不變。
"""
import hashlib
import json
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


def get_indent(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    lines = raw.split("\n")
    if len(lines) > 1:
        cand = len(lines[1]) - len(lines[1].lstrip(" "))
        if cand > 0:
            return cand
    return 2


def find_work(wid):
    return next(ROOT.glob(f"Work/?/?/?/{wid}-*.json"))


def find_entity(eid):
    return next(ROOT.glob(f"Entity/?/?/?/{eid}-*.json"))


def shard_of(id_str, n=16):
    h = 0
    for c in id_str:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return h % n


def sync_entity_index_fields(eid, fields):
    s = shard_of(eid)
    p = ROOT / "index" / "entities" / f"{s:x}.json"
    idx = load(p)
    if eid in idx:
        idx[eid].update(fields)
        save(p, idx, get_indent(p))


def remove_from_work_index(wid):
    s = shard_of(wid)
    p = ROOT / "index" / "works" / f"{s:x}.json"
    idx = load(p)
    if wid in idx:
        del idx[wid]
        save(p, idx, get_indent(p))


def detach_entity_work(eid, wid):
    p = find_entity(eid)
    e = load(p)
    e["works"] = [w for w in e.get("works", []) if w.get("work_id") != wid]
    save(p, e, get_indent(p))


def new_id_from(seed):
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    return "1j99" + h[:9]


def create_entity(eid, name, dyn, period, works, note, extra=None):
    ent = {
        "schema_version": 1,
        "id": eid,
        "type": "entity",
        "subtype": "people",
        "primary_name": name,
        "dynasty": dyn,
        "works": [{"work_id": w, "role": "撰"} for w in works],
        "external_ids": {},
        "ai_note": note,
        "period": period,
        "period_basis": f"據 dynasty「{dyn}」（2026-08-17 清朝探勘round10：{note}）",
    }
    if extra:
        ent.update(extra)
    c1, c2, c3 = eid[0], eid[1], eid[2]
    ent_dir = ROOT / "Entity" / c1 / c2 / c3
    ent_dir.mkdir(parents=True, exist_ok=True)
    ent_path = ent_dir / f"{eid}-{name}.json"
    save(ent_path, ent, indent=2)

    s = shard_of(eid)
    idx_path = ROOT / "index" / "entities" / f"{s:x}.json"
    idx = load(idx_path)
    idx[eid] = {
        "id": eid, "type": "entity", "subtype": "people",
        "primary_name": name, "path": str(ent_path.relative_to(ROOT)),
        "dynasty": dyn, "period": period,
    }
    save(idx_path, idx, get_indent(idx_path))


def mark_boundary_entity(eid, work_wids, note):
    ep = find_entity(eid)
    e = load(ep)
    e["dynasty"] = "明末清初"
    e["period"] = None
    e["period_basis"] = "跨 ming/qing，逐條判"
    e["ai_note"] = e.get("ai_note", "") + f" 2026-08-17 清朝探勘round10：{note}"
    save(ep, e, get_indent(ep))
    sync_entity_index_fields(eid, {"dynasty": "明末清初", "period": None})
    for wid in work_wids:
        wp = find_work(wid)
        w = load(wp)
        w["ai_note"] = w.get("ai_note", "") + f" 2026-08-17 清朝探勘round10：WebSearch確證：{note} period=qing（成書於清）維持不變。"
        save(wp, w, get_indent(wp))


def main():
    # A. 黃之俊《堂集》《香屑集》-> 併入既有黃之雋作品
    dup_wid = "1evr5e3mct1kz"
    huangzhijun_eid = "1j96hjwlxcpi7"
    dup_p = find_work(dup_wid)
    dup = load(dup_p)
    dup_ib = dup.get("indexed_by", []) or []

    tang_wid = "1ev3begjoledc"
    tp = find_work(tang_wid)
    tj = load(tp)
    tj.setdefault("indexed_by", [])
    tj["indexed_by"].append({
        "source": "清史稿藝文志", "source_bid": "1evdiulq07rwg",
        "title_info": "堂集", "summary": "堂集六十一卷，香屑集十六卷。黃之俊撰。",
    })
    tj["ai_note"] = tj.get("ai_note", "") + (
        " 2026-08-17 清朝探勘round10：併入 1evr5e3mct1kz（清史稿藝文志著錄「堂集六十一卷」，"
        "為本條「𢈪堂集」之著錄原文脫落罕用字「𢈪」；原誤連至明代同名人黃之俊，實為黃之雋本人著作）。"
    )
    save(tp, tj, get_indent(tp))

    xiangxie_wid = "1ev3bdfl66fwg"
    xp = find_work(xiangxie_wid)
    xj = load(xp)
    xj.setdefault("indexed_by", [])
    xj["indexed_by"].append({
        "source": "清史稿藝文志", "source_bid": "1evdiulq07rwg",
        "title_info": "香屑集", "summary": "堂集六十一卷，香屑集十六卷。黃之俊撰。",
    })
    xj["ai_note"] = xj.get("ai_note", "") + (
        " 2026-08-17 清朝探勘round10：併入 1evr5e3mct1kz 之香屑集部分（清史稿藝文志作十六卷，"
        "與本條十八卷略異，同書異本著錄，暫依既有先例視為同書）。"
    )
    save(xp, xj, get_indent(xp))

    detach_entity_work(huangzhijun_eid, dup_wid)
    dup_p.unlink()
    remove_from_work_index(dup_wid)
    print("A done")

    # B. 劉昆 -> 劉崐（新建Entity）
    liukun_wid = "1evr5e3m9270r"
    liuhun_old_eid = "1j96hjwlx1gy6"
    new_eid = new_id_from("劉崐清湖南巡撫韞齋景東")
    detach_entity_work(liuhun_old_eid, liukun_wid)
    wp = find_work(liukun_wid)
    w = load(wp)
    w["authors"][0]["name"] = "劉崐"
    w["authors"][0]["dynasty"] = "清"
    w["authors"][0]["entity_id"] = new_eid
    w["dynasty"] = "清"
    w["dynasty_basis"] = "2026-08-17 清朝探勘round10：WebSearch確證撰人實為晚清湖南巡撫劉崐"
    w["ai_note"] = w.get("ai_note", "") + (
        " 2026-08-17 清朝探勘round10：WebSearch確證《劉中丞奏稿》撰人為劉崐（1808-1888，字玉崑，"
        "號韞齋，雲南景東人，道光二十一年進士，同治年間任湖南巡撫，清代官場俗稱巡撫為「中丞」，"
        "與書名合），原entity_id所指劉昆為明代同名人（pending_accept低信度比對），拆分建立新Entity。"
    )
    save(wp, w, get_indent(wp))
    create_entity(
        new_eid, "劉崐", "清", "qing", [liukun_wid],
        "劉崐（1808-1888），字玉崑，號韞齋，雲南景東人，道光二十一年進士，同治年間任湖南巡撫。"
        "與明代同名人劉昆（1j96hjwlx1gy6）為姓名巧合之不同人物。",
        extra={"birth_year": 1808, "death_year": 1888, "alt_names": [{"name": "玉崑", "type": "字"}, {"name": "韞齋", "type": "號"}]},
    )
    print("B done")

    # C. 邱維屏／熊文舉／程正揆／鄧志謨：明末清初
    mark_boundary_entity(
        "1j96hjwlxcpi4", ["1evr5e3mcht35"],
        "邱維屏（1614-1679），江西寧都人，易堂九子之一，明遺民，隱居翠微峰講學，明末清初典型人物。"
    )
    mark_boundary_entity(
        "1j96hjwlxcpi5", ["1evr5e3mcht3q"],
        "熊文舉（1595-1668），字公遠，號雪堂，江西新建人，明崇禎四年進士，明亡後仕清至吏部左侍郎。"
    )
    mark_boundary_entity(
        "1j96h024mpyiq", ["1ev3bc66d9a0w", "1ev3be4kpm2o0"],
        "程正揆（1606-1676），前明崇禎辛未進士，入清官至工部侍郎，典型明末清初仕清文人。"
    )
    mark_boundary_entity(
        "1j967da978dfy", ["1ev3bci3exx4w"],
        "鄧志謨《蘭雪堂古事苑定本》書成於康熙丙寅（1686年），中國人民大學圖書館著錄作「明」、"
        "中國科學院圖書館著錄作「清」，兩館著錄本身即有歧見，反映其人跨代身分。"
    )
    print("C done")


if __name__ == "__main__":
    main()
