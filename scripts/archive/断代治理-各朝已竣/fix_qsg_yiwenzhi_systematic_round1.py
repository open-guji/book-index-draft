#!/usr/bin/env python3
"""清史稿藝文志系統性排查 Round 1：以「清史稿藝文志」為著錄來源、
period因「撰人朝代闕，而所著錄之志唯一且為斷代志...故據之」啟發式
誤填為qing之全庫record系統性排查與訂正。

延續隋唐/五代十國/遼金元/清朝（Round 8-10）四輪個別發現之同一bug
模式，本輪改以「清史稿藝文志」此一著錄來源為統一排查單位，一次性
全庫掃描（見 `.claude/known-issues/清史稿藝文志系統性排查_*.json`
三檔：safe/collision/ambiguous，由獨立掃描腳本產生，未納入本repo）。
核心方法：解析citation開頭之朝代字首（依SCHEMA.md規範朝代名枚舉），
並用「姓名撞庫」檢驗防止朝代字（吳/唐/秦/金/元/梁/宋/魏/周等，皆
兼常見姓氏）與真實人物姓氏碰撞誤判。

本批（Round 1）處理 safe 桶（88條）扣除：
  - 1條假陽性排除：金石圖（1ev3bb55x8ef4）——citation「金石圖二卷。
    褚峻摹圖，牛運震補說」，「金」乃書名「金石圖」（金石學）之首字，
    非朝代；褚峻/牛運震皆確為清代人，本條非bug。
  - 8條entity本身dynasty與citation朝代衝突者：其中6條citation本身
    unambiguous且為著名歷史人物（劉瓛/王逡之/劉巘/張融→齊、張養浩→
    元、劉廞→吳），逕訂正entity本身之dynasty；另3條為「後周」（樊
    文深/沈重×2）——史源「後周」於經部小學/禮類古代經學家語境下
    實指宇文氏北周（承西魏而後，舊籍偶稱「後周」以別於郭威之後周），
    非五代政權，訂正為北周/nanbeichao而非DYNASTY_TABLE預設之
    five-dynasties。

餘79條（無entity衝突、citation朝代字首unambiguous）直接訂正
Work.period/dynasty。

「姓名撞庫」偵測出之5組真collision（吳則禮/吳皋/吳泳/吳芾/吳可）
與collision中之false alarm（梁元帝纂要/元魯明善/唐元行沖/周易分野/
周卜氏易傳）、以及34條真歧義（宋/魏/周/梁/後漢）待逐條判者，性質
更複雜，另見Round 2腳本處理。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

CONFLICT_IDS = {
    "1evr5e3mezpii", "1evr5e3m76rxd", "1evr5e3m6vjcl", "1evr5e3mchszp",
    "1evr5e3mdqr7e", "1evr5e3mezpda", "1evc5pcnov5ds", "1evc5pcu03wu8",
}
EXCLUDE_FALSE_POSITIVE = {"1ev3bb55x8ef4"}  # 金石圖
HOUZHOU_OVERRIDE = {"1evr5e3m84hew", "1evc5pcnov5ds", "1evc5pcu03wu8"}  # -> nanbeichao


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


def sync_work_index_fields(wid, fields):
    s = shard_of(wid)
    p = ROOT / "index" / "works" / f"{s:x}.json"
    idx = load(p)
    if wid in idx:
        idx[wid].update(fields)
        save(p, idx, get_indent(p))


def sync_entity_index_fields(eid, fields):
    s = shard_of(eid)
    p = ROOT / "index" / "entities" / f"{s:x}.json"
    idx = load(p)
    if eid in idx:
        idx[eid].update(fields)
        save(p, idx, get_indent(p))


def fix_work_period(wid, dynasty, period, note):
    p = find_work(wid)
    j = load(p)
    a = j.get("authors")
    if a and isinstance(a, list) and isinstance(a[0], dict):
        a[0]["dynasty"] = dynasty
        a[0].pop("dynasty_basis", None)
    if j.get("dynasty") is not None or not a:
        j["dynasty"] = dynasty
    j["period"] = period
    j["period_basis"] = (
        f"據 清史稿藝文志citation朝代字首「{dynasty}」"
        f"（2026-08-18 清史稿藝文志系統性排查Round1：{note}）"
    )
    save(p, j, get_indent(p))
    sync_work_index_fields(wid, {"dynasty": dynasty, "period": period})


# B. entity本身dynasty錯誤，需一併訂正
BATCH_B = [
    ("1evr5e3mezpii", "1j96hl6pen9c0", "劉瓛", "齊", "nanbeichao",
     "劉瓛（南齊經學家，字子珪，通五經），citation「齊劉瓛孝經說」明載，原entity誤配為清"),
    ("1evr5e3m76rxd", "1j96ha49jj0n4", "王逡之", "齊", "nanbeichao",
     "王逡之（南齊禮學家），citation「齊王逡之喪服世行要記」明載，原entity誤配為梁"),
    ("1evr5e3m6vjcl", "1j96h8rw6xrsw", "劉巘", "齊", "nanbeichao",
     "劉巘（南齊禮學家），citation「齊劉巘乾坤義」明載，原entity誤配為宋"),
    ("1evr5e3mchszp", "1j96hl5m5v6rk", "張融", "齊", "nanbeichao",
     "張融（南齊文學家），citation「齊張融少子」明載，原entity誤配為三國吳"),
    ("1evr5e3mdqr7e", "1j96h8rw6xruh", "張養浩", "元", "liao-jin-yuan",
     "張養浩（元代著名散曲家/政治家），citation「元張養浩歸田類稿」明載，原entity誤配為清"),
    ("1evr5e3mezpda", "1j96h28x1o7i9", "劉廞", "吳", "three-kingdoms",
     "劉廞（三國吳人），citation「吳劉廞新義」明載，原entity誤配為明（原於清朝探勘輪已記錄為存疑未決，本輪系統性排查解決）"),
]


def main():
    safe = load(ROOT / ".claude/known-issues/清史稿藝文志系統性排查_safe.json")

    fixed_a = fixed_b = 0
    skip_ids = CONFLICT_IDS | EXCLUDE_FALSE_POSITIVE

    for rec in safe:
        wid = rec["work_id"]
        if wid in skip_ids:
            continue
        dyn = rec["detected_dynasty"]
        period = rec["detected_period"]
        note = f"citation朝代字首「{dyn}」，無entity衝突，直接訂正"
        if wid in HOUZHOU_OVERRIDE:
            dyn, period = "北周", "nanbeichao"
            note = "史源「後周」於此語境指宇文氏北周，非五代政權，訂正為北周/nanbeichao"
        try:
            fix_work_period(wid, dyn, period, note)
            fixed_a += 1
        except StopIteration:
            print("MISSING WORK FILE (skip)", wid)

    eidx_cache = {}
    for wid, eid, name, dyn, period, note in BATCH_B:
        ep = find_entity(eid)
        e = load(ep)
        e["dynasty"] = dyn
        e["period"] = period
        e["external_ids"] = {}
        e.pop("birth_year", None)
        e.pop("death_year", None)
        e["period_basis"] = f"據 dynasty「{dyn}」（2026-08-18 清史稿藝文志系統性排查Round1：{note}）"
        e["ai_note"] = e.get("ai_note", "") + f" 2026-08-18：{note}"
        save(ep, e, get_indent(ep))
        sync_entity_index_fields(eid, {"dynasty": dyn, "period": period})

        wp = find_work(wid)
        w = load(wp)
        a = w.get("authors")
        if a and isinstance(a, list) and isinstance(a[0], dict):
            a[0]["dynasty"] = dyn
            a[0].pop("dynasty_basis", None)
        if w.get("dynasty") is not None:
            w["dynasty"] = dyn
        w["period"] = period
        w["period_basis"] = f"據 authors[0].dynasty「{dyn}」（2026-08-18 清史稿藝文志系統性排查Round1：{note}）"
        save(wp, w, get_indent(wp))
        sync_work_index_fields(wid, {"dynasty": dyn, "period": period})
        fixed_b += 1

    print(f"fixed_a={fixed_a}, fixed_b={fixed_b}")


if __name__ == "__main__":
    main()
