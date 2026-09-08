#!/usr/bin/env python3
"""
investigate_liao_jin_yuan.py — 遼金元未決項深度調查（只讀）

目的：
1. 掃描 period=liao-jin-yuan 之 Work，分類 dynasty 補全置信度。
2. 區分「可機械補全」「需人工覆核」「疑似誤入遼金元」（如南宋王厚之）。
3. 清查 Entity 側 period=liao-jin-yuan 而無 dynasty 者，及 dynasty=遼/金/元/蒙古/西夏 而 period 空者。
4. 交叉 CBDB c_dy（16=遼, 17=西夏, 18=金, 19=蒙古/元），攔截同名異人。
5. 輸出可人工覆核候選清單，不直接修改記錄。

背景：period=liao-jin-yuan 之 4,227 Work 全數 dynasty 為空。
依據 author.dynasty 分布：元 3501 / 金 369 / 遼 31 / null 5 / 三國魏 1。
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / ".claude" / "known-issues" / "cbdb_dy_cache.json"
OUT_PATH = ROOT / ".claude" / "known-issues" / "遼金元未決.json"

LJY_CANON = {"遼", "金", "元", "金元", "蒙古", "西夏", "遼金元", "偽齊"}
AMBIGUOUS = {
    "宋", "北宋", "南宋", "明", "清", "唐", "隋", "漢", "秦", "先秦",
    "三國", "三國魏", "南北朝", "五代", "隋唐", "明清", "漢魏", "春秋", "戰國"
}

# CBDB c_dy → 規範名
CDY_TO_CANON = {
    "16": "遼", "17": "西夏", "18": "金", "19": "元",
    "15": "北宋",
    "20": "明", "21": "清",
}
# CBDB c_dy 屬 liao-jin-yuan
LJY_CDY = {"16", "17", "18", "19"}
# CBDB c_dy 屬 song（若 entity 指此，period=liao-jin-yuan 疑誤入）
SONG_CDY = {"15"}


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
    ext = entity.get("external_ids", {})
    cbdb_id = ext.get("cbdb_id") if isinstance(ext, dict) else None
    if not cbdb_id:
        return None, None
    entry = cbdb_cache.get(str(cbdb_id))
    if not entry or "error" in entry:
        return str(cbdb_id), None
    return str(cbdb_id), str(entry.get("dynasty_id", ""))


def classify_work(work: dict, entity_map: dict, cbdb_cache: dict) -> tuple[str, str]:
    wd = work.get("dynasty")
    if wd:
        return "already_has_dynasty", f"Work.dynasty 已有「{wd}」"

    authors = [a for a in (work.get("authors", []) or []) if isinstance(a, dict)]
    if not authors:
        return "no_author", "Work 無 authors，無從據 author.dynasty 補全"

    # 單作者
    if len(authors) == 1:
        a = authors[0]
        ad = a.get("dynasty")
        if ad in LJY_CANON:
            return "high_confidence_fill", f"唯一 author.dynasty={ad}，可補 Work.dynasty={ad}"
        if ad is None:
            eid = a.get("entity_id")
            ent = entity_map.get(eid) if eid else None
            if ent:
                cbdb_id, cdy = entity_cbdy(ent, cbdb_cache)
                if cdy in LJY_CDY:
                    canon = CDY_TO_CANON[cdy]
                    return "high_confidence_fill_by_cbdb", f"author.dynasty 空但 entity CBDB c_dy={cdy}→{canon}"
                if cdy in SONG_CDY:
                    canon = CDY_TO_CANON.get(cdy, cdy)
                    return "misclassification_song", f"author.dynasty 空但 entity CBDB c_dy={cdy}→{canon}，疑南宋北宋誤入遼金元"
                # 用 Entity.dynasty/period 自身
                ed = ent.get("dynasty")
                if ed in LJY_CANON:
                    return "high_confidence_fill_by_entity", f"author.dynasty 空但 entity.dynasty={ed}"
                if ed in AMBIGUOUS:
                    return "manual_ambiguous_by_entity", f"author.dynasty 空且 entity.dynasty={ed}（歧義）"
            return "manual_author_null", "唯一 author.dynasty 空且 entity/CBDB 無結論"
        if ad in AMBIGUOUS:
            # 再核 Entity 實際值：author.dynasty 有時是髒值（Entity 已正確）
            eid = a.get("entity_id")
            ent = entity_map.get(eid) if eid else None
            if ent and ent.get("dynasty") in LJY_CANON:
                return "high_confidence_fill_override_authdyn", \
                    f"author.dynasty={ad}(髒) 但 entity.dynasty={ent.get('dynasty')}，以 Entity 為準可補"
            return "manual_ambiguous", f"author.dynasty={ad}（歧義），需人工判"
        return "manual_other", f"author.dynasty={ad}（非遼金元規範值），需人工判"

    # 多作者
    dyns = set()
    for a in authors:
        ad = a.get("dynasty")
        if ad:
            dyns.add(ad)
    if not dyns:
        return "manual_multi_null", "多作者但 author.dynasty 俱空，需人工判"
    if dyns <= LJY_CANON:
        if len(dyns) == 1:
            d0 = next(iter(dyns))
            return "high_confidence_fill", f"多作者 author.dynasty 俱={d0}"
        if dyns == {"金", "元"}:
            return "high_confidence_fill", f"多作者 author.dynasty={dyns} → 金元"
        return "high_confidence_fill", f"多作者 author.dynasty={dyns} 俱屬遼金元範圍 → 遼金元"
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

    ljy_works = [w for w in works.values() if w.get("period") == "liao-jin-yuan"]
    work_buckets = defaultdict(list)
    authdyn_dist = Counter()
    for w in ljy_works:
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

    # Entity 側
    ljy_entities = [e for e in entities.values() if e.get("period") == "liao-jin-yuan"]
    ent_no_dyn = []
    ent_dyn_dist = Counter()
    for e in ljy_entities:
        ent_dyn_dist[e.get("dynasty") or "null"] += 1
        if not e.get("dynasty"):
            cbdb_id, cdy = entity_cbdy(e, cbdb_cache)
            ent_no_dyn.append({
                "entity_id": e.get("id"),
                "name": e.get("name"),
                "dynasty": None,
                "period": e.get("period"),
                "birth_year": e.get("birth_year"),
                "death_year": e.get("death_year"),
                "cbdb_c_dy": cdy,
            })

    # Entity.dynasty 為 遼/金/元/蒙古/西夏 但 period 空
    ent_ljy_no_period = []
    for e in entities.values():
        dyn = e.get("dynasty")
        if dyn in LJY_CANON and not e.get("period"):
            ent_ljy_no_period.append({
                "entity_id": e.get("id"),
                "name": e.get("name"),
                "dynasty": dyn,
            })

    out = {
        "description": "遼金元未決項深度調查（只讀輸出）",
        "summary": {
            "work_total": len(works),
            "entity_total": len(entities),
            "liao_jin_yuan_work_total": len(ljy_works),
            "liao_jin_yuan_work_without_dynasty": sum(1 for w in ljy_works if not w.get("dynasty")),
            "liao_jin_yuan_author_dynasty_distribution": dict(authdyn_dist.most_common()),
            "liao_jin_yuan_entity_total": len(ljy_entities),
            "liao_jin_yuan_entity_dynasty_distribution": dict(ent_dyn_dist.most_common()),
            "liao_jin_yuan_entity_without_dynasty": len(ent_no_dyn),
            "entity_dynasty_ljy_no_period": len(ent_ljy_no_period),
            "work_bucket_counts": {k: len(v) for k, v in sorted(work_buckets.items())},
        },
        "work_buckets": {k: v for k, v in sorted(work_buckets.items())},
        "entity_without_dynasty": ent_no_dyn,
        "entity_dynasty_ljy_no_period": ent_ljy_no_period,
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("=== 遼金元未決深查 ===")
    print(f"Work 總數: {len(works)}")
    print(f"Entity 總數: {len(entities)}")
    print(f"period=liao-jin-yuan Work: {len(ljy_works)}")
    print(f"  其中 dynasty 空: {sum(1 for w in ljy_works if not w.get('dynasty'))}")
    print("\nperiod=liao-jin-yuan 之 author.dynasty 分布:")
    for k, v in authdyn_dist.most_common(20):
        print(f"  {str(k):12s} {v:>5}")
    print("\nWork 補全分組:")
    for k, v in sorted(work_buckets.items()):
        print(f"  {k:42s} {len(v):>5}")
    print(f"\nperiod=liao-jin-yuan Entity: {len(ljy_entities)} (dynasty 空 {len(ent_no_dyn)})")
    print(f"dynasty=遼金元規範 但 period 空 Entity: {len(ent_ljy_no_period)}")
    print(f"\n輸出: {OUT_PATH}")


if __name__ == "__main__":
    main()
