#!/usr/bin/env python3
"""
investigate_ming.py — 明朝未決項深度調查（只讀）

目的：
1. 掃描 period=ming 之 10435 Work，原全數 dynasty 空。
2. 分類 Work.dynasty 補全置信度：
   · author.dynasty ∈ {明,明清,南明,明末清初} → high_confidence_fill
   · author.dynasty null 但 Entity.dynasty ∈ MING_CANON → high_confidence_fill_by_entity
   · author.dynasty null 且 Entity.cbdb c_dy 指向非明（19=元/21=清） → misclassification（應移出）
   · multi author → 作者集合一致則補，否則判
   · no_author → gazetteer 推斷留 Round 2
   · 其他 → manual
3. 清查 Entity 側 period=ming 無 dynasty、dynasty=明系 而 period 空。
4. 交叉 CBDB c_dy=20 明。
5. 輸出 known-issues/明朝未決.json，不直接修改檔案。
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / ".claude" / "known-issues" / "cbdb_dy_cache.json"
OUT_PATH = ROOT / ".claude" / "known-issues" / "明朝未決.json"

MING_CANON = {"明", "南明", "明末清初", "明清"}
AMBIGUOUS = {
    "宋", "北宋", "南宋", "唐", "隋", "元", "金", "遼", "清", "秦", "漢", "先秦",
    "三國", "三國魏", "南北朝", "五代", "隋唐", "遼金元", "秦漢", "晉", "魏",
    "南朝宋", "南朝齊", "南朝梁", "南朝陳", "北魏", "北齊", "北周", "前蜀", "後蜀",
    "漢魏", "春秋", "戰國", "周", "三國吳", "三國蜀", "朝鮮", "上古", "中華民國",
}
CDY_TO_CANON = {"20": "明", "21": "清", "19": "元", "18": "金", "15": "北宋"}
MING_CDY = {"20"}  # CBDB c_dy=20 明
SONG_CDY = {"15"}  # 宋
QING_CDY = {"21"}  # 清
LJY_CDY = {"16", "17", "18", "19"}  # 遼金元


def load_json(fp: Path):
    try: return json.loads(fp.read_text(encoding="utf-8"))
    except Exception: return None


def iter_work_files(): return sorted(ROOT.glob("Work/?/?/?/*.json"))
def iter_entity_files(): return sorted(ROOT.glob("Entity/?/?/?/*.json"))


def sources_of(w):
    return sorted(set(s["source"] for s in (w.get("indexed_by") or []) if isinstance(s, dict) and s.get("source")))


def entity_cbdy(e, cbdb_cache):
    ext = e.get("external_ids", {})
    cid = ext.get("cbdb_id") if isinstance(ext, dict) else None
    if not cid: return None, None
    entry = cbdb_cache.get(str(cid))
    if not entry or "error" in entry: return str(cid), None
    return str(cid), str(entry.get("dynasty_id", ""))


def classify(w, emap, cbdb_cache):
    if w.get("dynasty"):
        return "already_has_dynasty", f"已有「{w.get('dynasty')}」"
    authors = [a for a in (w.get("authors") or []) if isinstance(a, dict)]
    if not authors:
        return "no_author", "authors=[]，留 gazetteer 規則 Round 2"

    # 解決每個作者的朝代
    resolved = []  # (dyn, kind)
    for a in authors:
        ad = a.get("dynasty")
        if ad in MING_CANON:
            resolved.append((ad, "direct"))
            continue
        eid = a.get("entity_id")
        ent = emap.get(eid) if eid else None
        ed = ent.get("dynasty") if ent else None
        # Entity 自身已明確
        if ad is None and ed in MING_CANON:
            resolved.append((ed, "entity"))
            continue
        # Entity/CBDB 指非明，判定誤入
        if ent:
            cid, cdy = entity_cbdy(ent, cbdb_cache)
            if cdy in LJY_CDY:
                return "misclassification_ljy", \
                    f"author({a.get('name')}) Entity/CBDB c_dy={cdy}→{CDY_TO_CANON.get(cdy)}，應 period=liao-jin-yuan"
            if cdy in QING_CDY:
                return "misclassification_qing", \
                    f"author({a.get('name')}) Entity/CBDB c_dy={cdy}→清，應 period=qing"
            if cdy in SONG_CDY:
                return "misclassification_song", \
                    f"author({a.get('name')}) Entity/CBDB c_dy={cdy}→宋系，應 period=song"
            if ed in ("元", "金", "遼", "蒙古", "西夏"):
                return "misclassification_ljy", \
                    f"author({a.get('name')}) entity.dynasty={ed}，疑遼金元誤入明"
            if ed == "清" or ed == "清末":
                return "misclassification_qing", \
                    f"author({a.get('name')}) entity.dynasty={ed}，疑清誤入明"
            if ed == "南明":
                resolved.append((ed, "entity")); continue
            # Entity.dynasty 在 AMBIGUOUS（如三國晉）
            if ad in AMBIGUOUS:
                return "manual_ambiguous_authdyn", \
                    f"author.dynasty={ad} 歧義，entity.dynasty={ed or 'null'}"
            if ed in AMBIGUOUS:
                return "manual_ambiguous_entitydyn", \
                    f"author.dynasty=null 但 entity.dynasty={ed} 歧義（非明系）"
            if ad is None and ed is None:
                return "manual_null_entity", \
                    f"author.dynasty=null 且 entity.dynasty=null/cbdb=cid={cid or '?'} 無結論"
            return "manual_other", f"author.dynasty={ad}, entity.dynasty={ed}，無結論"
        # 無 entity 關聯
        if ad in AMBIGUOUS:
            return "manual_ambiguous_noentity", f"author.dynasty={ad} 歧義且無 entity 關聯"
        return "manual_null_noentity", f"author.dynasty=null 且無 entity 關聯"

    dyns = set(r[0] for r in resolved)
    if len(dyns) == 1:
        d0 = next(iter(dyns))
        return "high_confidence_fill", f"author.dynasty={d0} 一致可補"
    # 明清、明末清初、南明 混合：統一歸「明」（跨明/南明）？或取最廣值？— 取混合補 明
    if dyns <= {"明", "南明", "明末清初", "明清"}:
        if dyns == {"明清"}: return "high_confidence_fill", "author.dynasty=明清 → 補明"
        if "明清" in dyns:
            return "high_confidence_fill", f"author.dynasty={dyns} 跨明清，補明"
        return "high_confidence_fill", f"多作者 {dyns} 俱屬明系，補明"
    return "manual_mixed", f"author.dynasty={dyns} 含跨朝代非明系，需人工"


def main():
    works = {}; entities = {}
    cbdb = load_json(CACHE_PATH) or {}
    for fp in iter_work_files():
        d = load_json(fp)
        if d: works[d.get("id", fp.stem)] = d
    for fp in iter_entity_files():
        d = load_json(fp)
        if d: entities[d.get("id", fp.stem)] = d

    buckets = defaultdict(list)
    authdyn = Counter()
    mingw = [w for w in works.values() if w.get("period") == "ming"]
    for w in mingw:
        for a in (w.get("authors") or []):
            if isinstance(a, dict): authdyn[a.get("dynasty") or "null"] += 1
        b, rsn = classify(w, entities, cbdb)
        rec = {
            "work_id": w.get("id"), "title": w.get("title"),
            "dynasty": w.get("dynasty"), "bucket": b, "reason": rsn,
            "authors": [{"name": a.get("name"), "dynasty": a.get("dynasty"), "entity_id": a.get("entity_id")}
                        for a in (w.get("authors") or []) if isinstance(a, dict)],
            "sources": sources_of(w),
        }
        for a in rec["authors"]:
            e = entities.get(a.get("entity_id"))
            if e:
                cid, cdy = entity_cbdy(e, cbdb)
                a.update(entity_dynasty=e.get("dynasty"), entity_period=e.get("period"),
                         cbdb_c_dy=cdy, birth=e.get("birth_year"), death=e.get("death_year"))
        buckets[b].append(rec)

    # Entity 側
    ent_ming = [e for e in entities.values() if e.get("period") == "ming"]
    ent_no_dyn = []
    for e in ent_ming:
        if not e.get("dynasty"):
            cid, cdy = entity_cbdy(e, cbdb)
            ent_no_dyn.append({"entity_id": e.get("id"), "name": e.get("name"), "cbdb_c_dy": cdy})
    ent_ljy_no_per = []
    for e in entities.values():
        if e.get("dynasty") in MING_CANON and not e.get("period"):
            ent_ljy_no_per.append({"entity_id": e.get("id"), "name": e.get("name"), "dynasty": e.get("dynasty")})

    out = {
        "description": "明朝未決項深度調查（只讀輸出）",
        "summary": {
            "work_total": len(works),
            "entity_total": len(entities),
            "ming_work_total": len(mingw),
            "ming_work_without_dynasty": sum(1 for w in mingw if not w.get("dynasty")),
            "ming_author_dynasty_distribution": dict(authdyn.most_common()),
            "work_bucket_counts": {k: len(v) for k, v in sorted(buckets.items())},
            "ming_entity_total": len(ent_ming),
            "ming_entity_without_dynasty": len(ent_no_dyn),
            "entity_ming_dynasty_no_period": len(ent_ljy_no_per),
        },
        "work_buckets": {k: v for k, v in sorted(buckets.items())},
        "entity_without_dynasty": ent_no_dyn,
        "entity_ming_dynasty_no_period": ent_ljy_no_per,
    }
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("=== 明朝未決深查 ===")
    print(f"period=ming Work: {len(mingw)} (dynasty 空 {sum(1 for w in mingw if not w.get('dynasty'))})")
    print("author.dynasty 分布 top10:")
    for k,v in authdyn.most_common(10): print(f"  {str(k):12s} {v:>5}")
    print("Work 補全分組:")
    for k,v in sorted(buckets.items()): print(f"  {k:44s} {len(v):>5}")
    print(f"\nEntity period=ming: {len(ent_ming)} (dynasty 空 {len(ent_no_dyn)})")
    print(f"Entity 明系 但 period 空: {len(ent_ljy_no_per)}")
    print(f"\n輸出: {OUT_PATH}")


if __name__ == "__main__":
    main()
