#!/usr/bin/env python3
"""
investigate_sui_tang.py — 隋唐未決項深度調查（只讀）

目的：
1. 從當前 main 數據中找出 period=sui-tang 的 Work，分類 dynasty 補全之置信度。
2. 區分「可機械補全」「需人工覆核」「疑似誤入隋唐」。
3. 清查 Entity 側 period=sui-tang 而無 dynasty 者，及 dynasty=隋/唐 而無 period 者。
4. 交叉比對 CBDB c_dy（6/13=唐, 12=隋），攔截同名異人（唐 vs 後唐）。
5. 輸出可人工覆核的候選清單，不直接修改 Work/Entity/index。

背景：五代十國 Round 2 顯式將「dynasty=唐/漢 大批殘留」移交隋唐/秦漢進程。
本輪聚焦隋唐：period=sui-tang 之 1,832 Work 全數 dynasty 為空，需補全。
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / ".claude" / "known-issues" / "cbdb_dy_cache.json"
OUT_PATH = ROOT / ".claude" / "known-issues" / "隋唐未決.json"

# Sui-Tang 規範 dynasty 值
ST_CANON = {"隋", "唐", "隋唐"}
# 歧義朝代（可能誤入隋唐者）
AMBIGUOUS = {"宋", "晉", "梁", "周", "齊", "魏", "吳", "蜀", "陳", "漢",
             "三國", "南北朝", "南朝", "北朝", "五代", "後唐", "後梁",
             "後晉", "後漢", "後周", "北宋", "南宋"}

# CBDB c_dy → 規範名（隋唐相關）
CDY_TO_CANON = {
    "12": "隋",
    "6": "唐",   # CBDB 之唐
    "13": "唐",   # SCHEMA 表列之唐
    "47": "後唐",  # 五代後唐，不應入隋唐
    "34": "後梁",  # 五代後梁
    "15": "北宋",
    "29": "西漢",
    "25": "東漢",
}
# CBDB c_dy 屬於隋唐者
ST_CDY = {"12", "6", "13"}
# CBDB c_dy 屬於五代者（若 entity 指此，則 period=sui-tang 為誤入）
FD_CDY = {"34", "47", "48", "52", "49", "7"}


def load_json(fp: Path):
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None


def iter_work_files():
    return sorted(ROOT.glob("Work/?/?/?/*.json"))


def iter_entity_files():
    return sorted(ROOT.glob("Entity/?/?/?/*.json"))


def sources_of(work: dict) -> list[str]:
    out = []
    for item in work.get("indexed_by", []) or []:
        if isinstance(item, dict) and item.get("source"):
            out.append(item["source"])
    return sorted(set(out))


def entity_cbdy(entity: dict, cbdb_cache: dict) -> tuple[str | None, str | None]:
    """回傳 (cbdb_id, c_dy)。"""
    ext = entity.get("external_ids", {})
    cbdb_id = ext.get("cbdb_id") if isinstance(ext, dict) else None
    if not cbdb_id:
        return None, None
    entry = cbdb_cache.get(str(cbdb_id))
    if not entry or "error" in entry:
        return str(cbdb_id), None
    return str(cbdb_id), str(entry.get("dynasty_id", ""))


def classify_work(work: dict, entity_map: dict, cbdb_cache: dict) -> tuple[str, str]:
    """回傳 (bucket, reason)。"""
    wd = work.get("dynasty")
    if wd:
        return "already_has_dynasty", f"Work.dynasty 已有「{wd}」"

    authors = [a for a in (work.get("authors", []) or []) if isinstance(a, dict)]
    if not authors:
        return "no_author", "Work 無 authors，無法據 author.dynasty 補全"

    # 單一作者
    if len(authors) == 1:
        a = authors[0]
        ad = a.get("dynasty")
        if ad in ST_CANON:
            return "high_confidence_fill", f"唯一 author.dynasty={ad}，可補 Work.dynasty={ad}"
        if ad is None:
            # 查 entity 之 CBDB
            eid = a.get("entity_id")
            ent = entity_map.get(eid) if eid else None
            if ent:
                cbdb_id, cdy = entity_cbdy(ent, cbdb_cache)
                if cdy in ST_CDY:
                    canon = CDY_TO_CANON[cdy]
                    return "high_confidence_fill_by_cbdb", f"author.dynasty 空但 entity CBDB c_dy={cdy}→{canon}"
                if cdy in FD_CDY:
                    return "misclassification_fd", f"author.dynasty 空但 entity CBDB c_dy={cdy}→{CDY_TO_CANON.get(cdy)}，疑五代誤入隋唐"
                if cbdb_id:
                    return "manual_no_cbdy_st", f"author.dynasty 空且 entity CBDB c_dy={cdy}，需人工判"
            # 查 entity 自身 dynasty
            if ent and ent.get("dynasty") in ST_CANON:
                return "high_confidence_fill_by_entity", f"author.dynasty 空但 entity.dynasty={ent.get('dynasty')}"
            return "manual_author_null", "唯一 author.dynasty 空，需人工判"
        if ad in AMBIGUOUS:
            # 北宋/南宋/後唐 等 — 需人工判
            return "manual_ambiguous", f"author.dynasty={ad}（歧義），需人工判"
        return "manual_other", f"author.dynasty={ad}（非隋唐規範值），需人工判"

    # 多作者：取 author.dynasty 之集合
    dyns = set()
    for a in authors:
        ad = a.get("dynasty")
        if ad:
            dyns.add(ad)
    if not dyns:
        return "manual_multi_null", "多作者但 author.dynasty 俱空，需人工判"
    if dyns <= ST_CANON:
        # 全是隋/唐/隋唐
        if len(dyns) == 1:
            d0 = next(iter(dyns))
            return "high_confidence_fill", f"多作者 author.dynasty 俱={d0}，可補 Work.dynasty={d0}"
        if dyns == {"隋", "唐"} or dyns == {"隋", "隋唐"} or dyns == {"唐", "隋唐"} or dyns == {"隋", "唐", "隋唐"}:
            return "high_confidence_fill", "多作者 author.dynasty 屬隋唐範圍，可補 Work.dynasty=隋唐"
        return "high_confidence_fill", f"多作者 author.dynasty={dyns} 屬隋唐範圍"
    # 混有歧義值
    if dyns & AMBIGUOUS:
        return "manual_mixed", f"多作者 author.dynasty={dyns} 含歧義值，需人工判"
    return "manual_mixed_other", f"多作者 author.dynasty={dyns}，需人工判"


def main():
    works = {}
    entities = {}
    cbdb_cache = load_json(CACHE_PATH) or {}

    for fp in iter_work_files():
        d = load_json(fp)
        if d:
            works[d.get("id", fp.stem)] = d
    for fp in iter_entity_files():
        d = load_json(fp)
        if d:
            entities[d.get("id", fp.stem)] = d

    st_works = [w for w in works.values() if w.get("period") == "sui-tang"]

    # Work 側普查
    work_buckets = defaultdict(list)
    authdyn_dist = Counter()
    for w in st_works:
        for a in (w.get("authors", []) or []):
            if isinstance(a, dict):
                authdyn_dist[a.get("dynasty") or "null"] += 1
        bucket, reason = classify_work(w, entities, cbdb_cache)
        rec = {
            "work_id": w.get("id"),
            "title": w.get("title"),
            "dynasty": w.get("dynasty"),
            "authors": [{"name": a.get("name"), "dynasty": a.get("dynasty"),
                        "entity_id": a.get("entity_id")}
                       for a in (w.get("authors", []) or []) if isinstance(a, dict)],
            "sources": sources_of(w),
            "bucket": bucket,
            "reason": reason,
        }
        # 補 entity 資訊
        for a in rec["authors"]:
            eid = a.get("entity_id")
            if eid and eid in entities:
                e = entities[eid]
                cbdb_id, cdy = entity_cbdy(e, cbdb_cache)
                a["entity_dynasty"] = e.get("dynasty")
                a["entity_period"] = e.get("period")
                a["entity_birth_year"] = e.get("birth_year")
                a["entity_death_year"] = e.get("death_year")
                a["cbdb_c_dy"] = cdy
        work_buckets[bucket].append(rec)

    # Entity 側普查
    st_entities = [e for e in entities.values() if e.get("period") == "sui-tang"]
    ent_no_dyn = []
    ent_dyn_dist = Counter()
    for e in st_entities:
        ent_dyn_dist[e.get("dynasty") or "null"] += 1
        if not e.get("dynasty"):
            cbdb_id, cdy = entity_cbdy(e, cbdb_cache)
            ent_no_dyn.append({
                "entity_id": e.get("id"),
                "name": e.get("name"),
                "dynasty": e.get("dynasty"),
                "period": e.get("period"),
                "birth_year": e.get("birth_year"),
                "death_year": e.get("death_year"),
                "cbdb_c_dy": cdy,
            })

    # dynasty=隋/唐 但 period 為非 sui-tang 之 Work（疑似漏標 period）
    tang_other_period = []
    sui_other_period = []
    for w in works.values():
        if w.get("dynasty") == "唐" and w.get("period") != "sui-tang":
            tang_other_period.append({
                "work_id": w.get("id"), "title": w.get("title"),
                "period": w.get("period"), "dynasty": w.get("dynasty"),
                "sources": sources_of(w),
            })
        if w.get("dynasty") == "隋" and w.get("period") != "sui-tang":
            sui_other_period.append({
                "work_id": w.get("id"), "title": w.get("title"),
                "period": w.get("period"), "dynasty": w.get("dynasty"),
                "sources": sources_of(w),
            })

    # dynasty=唐/隋 但 period 空（應補 sui-tang）之 Entity
    ent_tang_no_period = []
    ent_sui_no_period = []
    for e in entities.values():
        if e.get("dynasty") == "唐" and not e.get("period"):
            ent_tang_no_period.append({"entity_id": e.get("id"), "name": e.get("name")})
        if e.get("dynasty") == "隋" and not e.get("period"):
            ent_sui_no_period.append({"entity_id": e.get("id"), "name": e.get("name")})

    out = {
        "description": "隋唐未決項深度調查（只讀輸出）",
        "summary": {
            "work_total": len(works),
            "entity_total": len(entities),
            "sui_tang_work_total": len(st_works),
            "sui_tang_work_without_dynasty": sum(1 for w in st_works if not w.get("dynasty")),
            "sui_tang_author_dynasty_distribution": dict(authdyn_dist.most_common()),
            "sui_tang_entity_total": len(st_entities),
            "sui_tang_entity_dynasty_distribution": dict(ent_dyn_dist.most_common()),
            "sui_tang_entity_without_dynasty": len(ent_no_dyn),
            "work_bucket_counts": {k: len(v) for k, v in sorted(work_buckets.items())},
            "work_dynasty_tang_other_period": len(tang_other_period),
            "work_dynasty_sui_other_period": len(sui_other_period),
            "entity_dynasty_tang_no_period": len(ent_tang_no_period),
            "entity_dynasty_sui_no_period": len(ent_sui_no_period),
        },
        "work_buckets": {k: v for k, v in sorted(work_buckets.items())},
        "entity_without_dynasty": ent_no_dyn,
        "work_dynasty_tang_other_period": tang_other_period,
        "work_dynasty_sui_other_period": sui_other_period,
        "entity_dynasty_tang_no_period": ent_tang_no_period,
        "entity_dynasty_sui_no_period": ent_sui_no_period,
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("=== 隋唐未決深查 ===")
    print(f"Work 總數: {len(works)}")
    print(f"Entity 總數: {len(entities)}")
    print(f"period=sui-tang Work: {len(st_works)}")
    print(f"  其中 dynasty 空: {sum(1 for w in st_works if not w.get('dynasty'))}")
    print("\nperiod=sui-tang 之 author.dynasty 分布:")
    for k, v in authdyn_dist.most_common(20):
        print(f"  {str(k):12s} {v:>5}")
    print("\nWork 補全分組:")
    for k, v in sorted(work_buckets.items()):
        print(f"  {k:36s} {len(v):>5}")
    print(f"\nperiod=sui-tang Entity: {len(st_entities)} (dynasty 空 {len(ent_no_dyn)})")
    print(f"dynasty=唐 但 period 非 sui-tang 之 Work: {len(tang_other_period)}")
    print(f"dynasty=隋 但 period 非 sui-tang 之 Work: {len(sui_other_period)}")
    print(f"dynasty=唐 但 period 空 之 Entity: {len(ent_tang_no_period)}")
    print(f"dynasty=隋 但 period 空 之 Entity: {len(ent_sui_no_period)}")
    print(f"\n輸出: {OUT_PATH}")


if __name__ == "__main__":
    main()
