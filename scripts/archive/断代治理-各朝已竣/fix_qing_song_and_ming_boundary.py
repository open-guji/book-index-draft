#!/usr/bin/env python3
"""清朝探勘：修復period=qing範圍內與宋代、明代之period不一致案例。

分兩類：

A. 「宋」組（72個Entity，144作品規模其中部分已為song）：Entity皆為
   `name_exact+dy_match`型高信度比對（非姓名巧合式pending_accept），
   死亡年份皆落於960-1300年間宋代範圍，與period=qing間隔三百年以
   上，不存在邊界過渡之可能性。逐一核對indexed_by引文，其Work.
   period_basis欄位皆載明同一套「撰人朝代闕，而所著錄之志唯一且
   為斷代志...故據之：清史稿藝文志」之啟發式代填錯誤——此bug模式
   已於隋唐/五代十國/遼金元/清朝（本輪古代組）四度出現，本次為
   第五度，且規模最大。逕依Entity既有正確分類同步Work.period。

B. 「明」組：與A類性質不同，經以Work自身indexed_by引文中之明代
   紀年（洪武~崇禎）／清代紀年（順治~宣統）關鍵字比對後，分為
   二子類：
   B1. 引文僅含明代紀年（11個Entity，Work.period=qing為誤，Entity
       已正確為ming）：金之俊、孫慎行、張恆、朱孔陽、王寵、季本、
       周嘉胄、提橋、易學實、劉芳、胡時忠——訂正Work.period為ming。
   B2. 引文僅含清代紀年（22個Entity，Entity.period=ming為誤，
       Work.period已正確為qing）：南懷仁（清初來華耶穌會士，欽天監
       監正）、汪昂（清代醫家，本草備要作者）、圖理琛（清代滿洲
       官員）、周拱辰/王堂/徐震/唐靖/趙振芳/崔維雅/朱瓚/宋士宗/
       汪基/譚文光/熊文登/吳廣成/朱崇道/賀裳/唐一麟/朱謹/武之望/
       秘丕笈——訂正Entity.dynasty/period為清/qing。

其餘47個Entity（引文中明清紀年關鍵字皆無或皆有）、5個明清之際
邊界人物、9個「entity其餘作品已支持其誤配朝代」之混合entity，本輪
不予處理，留待未來個案核實。
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


def build_work_index():
    idx = {}
    for s in SHARDS:
        d = load(ROOT / "index" / "works" / f"{s}.json")
        for wid, entry in d.items():
            idx[wid] = ROOT / entry["path"]
    return idx


def build_entity_index():
    idx = {}
    for f in Path(ROOT / "Entity").rglob("*.json"):
        try:
            j = load(f)
        except Exception:
            continue
        if isinstance(j, dict) and j.get("id"):
            idx[j["id"]] = f
    return idx


MING_ERAS = ["洪武", "建文", "永樂", "洪熙", "宣德", "正統", "景泰", "天順", "成化",
             "弘治", "正德", "嘉靖", "隆慶", "萬曆", "泰昌", "天啟", "崇禎"]
QING_ERAS = ["順治", "康熙", "雍正", "乾隆", "嘉慶", "道光", "咸豐", "同治", "光緒", "宣統"]

BOUNDARY_KEYWORDS = ["明末", "清初", "入清", "仕清", "降清", "晚清", "入民國", "清末"]


def sync_work(path, dyn, period, note):
    j = load(path)
    a0 = j["authors"][0]
    a0["dynasty"] = dyn
    a0.pop("dynasty_basis", None)
    if j.get("dynasty") is not None:
        j["dynasty"] = dyn
    j["period"] = period
    j["period_basis"] = f"據 authors[0].dynasty「{dyn}」（2026-08-13 清朝探勘：{note}）"
    save(path, j, get_indent(path))


def main():
    widx = build_work_index()
    eidx_paths = build_entity_index()
    eidx = {eid: load(p) for eid, p in eidx_paths.items()}

    fixed_a = fixed_b1 = fixed_b2 = 0

    # A. song cluster
    fwd_song = set()
    for wid, path in widx.items():
        j = load(path)
        if j.get("period") != "qing":
            continue
        a = j.get("authors")
        if not a or not isinstance(a, list) or not isinstance(a[0], dict):
            continue
        eid = a[0].get("entity_id")
        if eid in eidx and eidx[eid].get("period") == "song":
            fwd_song.add(eid)

    for eid in fwd_song:
        e = eidx[eid]
        dyn = e.get("dynasty")
        note = f"{e.get('primary_name')}：Entity為高信度宋代人物比對，Work.period因清史稿藝文志代填啟發式誤植為qing，訂正"
        for w in e.get("works", []):
            p = widx.get(w.get("work_id"))
            if not p:
                continue
            j = load(p)
            a = j.get("authors")
            if not a or not isinstance(a, list) or not isinstance(a[0], dict):
                continue
            if a[0].get("entity_id") != eid or j.get("period") != "qing":
                continue
            sync_work(p, dyn, "song", note)
            fixed_a += 1

    # B1: confirmed ming (fix specific qing-tagged works under ming entities)
    fwd_ming = set()
    for wid, path in widx.items():
        j = load(path)
        if j.get("period") != "qing":
            continue
        a = j.get("authors")
        if not a or not isinstance(a, list) or not isinstance(a[0], dict):
            continue
        eid = a[0].get("entity_id")
        if eid in eidx and eidx[eid].get("period") == "ming":
            fwd_ming.add(eid)

    for eid in fwd_ming:
        e = eidx[eid]
        works = e.get("works", [])
        text = ""
        for w in works:
            p = widx.get(w.get("work_id"))
            if not p:
                continue
            j = load(p)
            for ib in j.get("indexed_by", []) or []:
                text += (ib.get("summary") or "") + " "
        has_ming = any(era in text for era in MING_ERAS)
        has_qing = any(era in text for era in QING_ERAS)
        if not (has_ming and not has_qing):
            continue
        dyn = e.get("dynasty")
        note = f"{e.get('primary_name')}：Work引文含明代紀年而無清代紀年，Entity已正確為ming，Work.period因啟發式誤植為qing，訂正"
        for w in works:
            p = widx.get(w.get("work_id"))
            if not p:
                continue
            j = load(p)
            if j.get("period") != "qing":
                continue
            sync_work(p, dyn, "ming", note)
            fixed_b1 += 1

    # B2: confirmed qing (entity wrong, fix entity)
    for eid in fwd_ming:
        if eid not in eidx:
            continue
        e = eidx[eid]
        works = e.get("works", [])
        text = ""
        for w in works:
            p = widx.get(w.get("work_id"))
            if not p:
                continue
            j = load(p)
            for ib in j.get("indexed_by", []) or []:
                text += (ib.get("summary") or "") + " "
        has_ming = any(era in text for era in MING_ERAS)
        has_qing = any(era in text for era in QING_ERAS)
        if not (has_qing and not has_ming):
            continue
        src = (e.get("external_ids") or {}).get("cbdb_source", "") or ""
        if any(kw in src for kw in BOUNDARY_KEYWORDS):
            continue
        ent_p = eidx_paths[eid]
        ent = load(ent_p)
        note = f"{ent.get('primary_name')}：Work自身引文僅含清代紀年，Entity遭CBDB誤配至一位明代同名人物（原cbdb_source: {src}），訂正為清"
        ent["dynasty"] = "清"
        ent["period"] = "qing"
        ent["period_basis"] = f"據 dynasty「清」（2026-08-13 清朝探勘：{note}）"
        ent["ai_note"] = ent.get("ai_note", "") + f" 2026-08-13：{note}"
        ent["external_ids"] = {}
        ent.pop("dynasty_basis", None)
        ent.pop("birth_year", None)
        ent.pop("death_year", None)
        save(ent_p, ent, get_indent(ent_p))
        fixed_b2 += 1

    print(f"fixed_a(song)={fixed_a}, fixed_b1(ming-work)={fixed_b1}, fixed_b2(qing-entity)={fixed_b2}")


if __name__ == "__main__":
    main()
