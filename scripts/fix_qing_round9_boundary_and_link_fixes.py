#!/usr/bin/env python3
"""清朝探勘 Round 9：33個剩餘「明」組混合Entity獨立立項之深查（第二批）。

  A. 錢士馨《甲申傳信錄》：WebSearch確證此書撰於順治十年（1653），
     記甲申之變（1644）始末，為明末清初親歷者之見證實錄。真正
     明末清初跨代人物，Work.period=qing（成書於清）與Entity既有
     dynasty=明並不矛盾，比照李中梓/費經虞先例，訂正Entity.dynasty
     為「明末清初」，period留null，不動Work。
  B. 華廷獻《閩事紀略》：WebSearch確認此書記鄭成功時期閩地事，為
     明末清初見證者記錄。同上處理。
  C. 劉若金《本草述》：WebSearch確證劉若金（1585-1665），明天啟
     進士、崇禎末刑部尚書，明亡後隱退行醫，《本草述》成書並刊行
     於清（約1700年前後其後人整理刊行），為典型明末清初醫家。
     補全生卒年，訂正dynasty為「明末清初」。
  D. 續指月錄／尊宿集·聶光→聶先：WebSearch確證《續指月錄》為清
     康熙十八年（1679）聶先所編，非「聶光」——查明本庫「聶光」
     為OCR/著錄原文「聶先」之「先」誤讀為「光」（形近致誤），
     實際應為聶先（清，已有正確Entity 1j96gx6h0eqdc，另編有其他
     3種）。訂正author.name並改連正確entity。
"""
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


def sync_work_index_fields(wid, fields):
    s = shard_of(wid)
    p = ROOT / "index" / "works" / f"{s:x}.json"
    idx = load(p)
    if wid in idx:
        idx[wid].update(fields)
        save(p, idx, get_indent(p))


def mark_boundary_entity(eid, work_wid, note):
    ep = find_entity(eid)
    e = load(ep)
    e["dynasty"] = "明末清初"
    e["period"] = None
    e["period_basis"] = "跨 ming/qing，逐條判"
    e["ai_note"] = e.get("ai_note", "") + f" 2026-08-17 清朝探勘round9：{note}"
    save(ep, e, get_indent(ep))
    sync_entity_index_fields(eid, {"dynasty": "明末清初", "period": None})

    wp = find_work(work_wid)
    w = load(wp)
    w["ai_note"] = w.get("ai_note", "") + f" 2026-08-17 清朝探勘round9：WebSearch確證：{note} period=qing（成書於清）維持不變。"
    save(wp, w, get_indent(wp))


def main():
    # A. 錢士馨
    mark_boundary_entity(
        "1j96hjwlx1gy3", "1evr5e3m8qyli",
        "《甲申傳信錄》確撰於順治十年（1653年），記甲申之變（1644）始末，"
        "為明末清初親歷者見證實錄，屬真正跨代人物（部分史料另作「錢甹只」，"
        "字稚農/稚拙，平湖貢生，姓名寫法或有異文，然明末清初之身分確鑿）。"
    )

    # B. 華廷獻
    mark_boundary_entity(
        "1j96hjwlx1gy5", "1evr5e3m8qyls",
        "《閩事紀略》確為華廷獻所撰、記鄭成功時期閩地事之明末清初見證記錄。"
    )

    # C. 劉若金
    ep = find_entity("1j96hjwlxcphd")
    e = load(ep)
    e["dynasty"] = "明末清初"
    e["birth_year"] = 1585
    e["death_year"] = 1665
    e["period"] = None
    e["period_basis"] = "跨 ming/qing，逐條判"
    e["ai_note"] = e.get("ai_note", "") + (
        " 2026-08-17 清朝探勘round9：WebSearch確證劉若金（1585-1665），字用汝，號雲密，"
        "湖廣承天府潛江縣人，明天啟進士，崇禎末官至刑部尚書，明亡後隱退行醫，"
        "《本草述》成書並流傳於清，為典型明末清初醫家。"
    )
    save(ep, e, get_indent(ep))
    sync_entity_index_fields("1j96hjwlxcphd", {"dynasty": "明末清初", "period": None, "birth_year": 1585, "death_year": 1665})
    wp = find_work("1evr5e3maxmc0")
    w = load(wp)
    w["ai_note"] = w.get("ai_note", "") + " 2026-08-17 清朝探勘round9：WebSearch確證劉若金1585-1665，明末清初醫家，period=qing維持不變。"
    save(wp, w, get_indent(wp))

    # D. 聶光 -> 聶先
    nieguang_eid = "1j96hhvcr8mxd"
    niexian_eid = "1j96gx6h0eqdc"
    for wid, role in [("1evr5e3mc6kkk", "撰"), ("1evr5e3mc6kkl", "撰")]:
        wp = find_work(wid)
        w = load(wp)
        w["authors"][0]["name"] = "聶先"
        w["authors"][0]["dynasty"] = "清"
        w["authors"][0]["entity_id"] = niexian_eid
        w["ai_note"] = w.get("ai_note", "") + (
            " 2026-08-17 清朝探勘round9：WebSearch確證《續指月錄》為清康熙十八年（1679）"
            "聶先所編，本條原author.name「聶光」為著錄原文「聶先」之「先」誤讀「光」（形近致誤），"
            "訂正author.name並改連正確之聶先Entity（1j96gx6h0eqdc）。"
        )
        w["dynasty"] = "清"
        w["dynasty_basis"] = "2026-08-17 清朝探勘round9：WebSearch確證撰人實為聶先（清康熙十八年編）"
        save(wp, w, get_indent(wp))
        sync_work_index_fields(wid, {"author": "聶先", "dynasty": "清"})

    ep = find_entity(nieguang_eid)
    e = load(ep)
    e["works"] = []
    save(ep, e, get_indent(ep))

    ep2 = find_entity(niexian_eid)
    e2 = load(ep2)
    e2.setdefault("works", [])
    for wid in ["1evr5e3mc6kkk", "1evr5e3mc6kkl"]:
        if not any(w.get("work_id") == wid for w in e2["works"]):
            e2["works"].append({"work_id": wid, "role": "撰"})
    save(ep2, e2, get_indent(ep2))

    print("done")


if __name__ == "__main__":
    main()
