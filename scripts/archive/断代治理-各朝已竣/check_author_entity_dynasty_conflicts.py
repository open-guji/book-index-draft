#!/usr/bin/env python3
"""
C1: 跨表檢查：Work.author 有 entity_id 時，比對 author.dynasty 與 Entity.dynasty 是否一致
目標：找出實體關聯錯誤（如同合浦珠：Work 是清，關聯的 Entity 是明）
"""
import json, os, sys

# 倉根自本檔位置推得，不寫死容器路徑——舊值 /workspace/... 在別的容器
# 佈局下寫成，移倉之後 glob 掃不到任何檔而**靜默地什麼都不做**。
# 2026-08-24 已為此漏掉 4,121 條 period_upper，見 plans/全庫普查 附二。
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROD = os.path.join(os.path.dirname(_ROOT), 'book-index')

# 先把 Entity 讀入內存
entities = {}
for root, _, files in os.walk(os.path.join(_ROOT, "Entity")):
    for f in files:
        if f.endswith(".json"):
            fp = os.path.join(root, f)
            try:
                with open(fp, "r", encoding="utf-8") as fh:
                    e = json.load(fh)
                if e.get("type") == "entity" and e.get("subtype") == "people" and "dynasty" in e:
                    entities[e["id"]] = {"name": e.get("primary_name"), "dynasty": e["dynasty"], "birth_year": e.get("birth_year"), "death_year": e.get("death_year")}
            except Exception:
                pass
print(f"[INFO] 已載入 {len(entities)} 個人物 Entity")

# 檢查 Work
conflicts = []  # (work_id, title, author_name, author_dynasty, eid, entity_name, entity_dynasty)
checked = 0
for root, _, files in os.walk(os.path.join(_ROOT, "Work")):
    for f in files:
        if not f.endswith(".json"): continue
        fp = os.path.join(root, f)
        if "/collated_edition/" in fp: continue
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                w = json.load(fh)
        except Exception:
            continue
        if w.get("type") != "work": continue
        if not w.get("authors"): continue
        for a in w["authors"]:
            eid = a.get("entity_id")
            if not eid: continue
            checked += 1
            if eid not in entities: continue
            e = entities[eid]
            a_dyn = a.get("dynasty")
            e_dyn = e["dynasty"]
            # 僅考慮 author 與 Entity 都有 dynasty 且不同
            if not a_dyn or not e_dyn: continue
            # 等價同義（遼金元/遼/金/元 可互換）
            def is_equiv(d1, d2):
                if d1 == d2: return True
                eq = {
                    "遼金元": ["遼", "金", "元"],
                    "元": ["遼金元"],
                    "金": ["遼金元"],
                    "遼": ["遼金元"],
                    "南宋": ["宋"],
                    "北宋": ["宋"],
                    "宋": ["南宋", "北宋"],
                }
                return d2 in eq.get(d1, [])
            if is_equiv(a_dyn, e_dyn): continue
            conflicts.append({
                "work_id": w["id"],
                "title": w.get("title", ""),
                "author_name": a.get("name", ""),
                "author_dynasty": a_dyn,
                "author_basis": a.get("dynasty_basis", ""),
                "eid": eid,
                "entity_name": e["name"],
                "entity_dynasty": e_dyn,
                "entity_by": f"{e.get('birth_year','?')}~{e.get('death_year','?')}",
                "work_period": w.get("period", ""),
                "work_dynasty": w.get("dynasty", ""),
            })

print(f"[INFO] 檢查了 {checked} 個有 entity_id 的 author，發現 {len(conflicts)} 個衝突\n")
for c in conflicts:
    print(f"  Work: {c['work_id']} 《{c['title']}》")
    print(f"    Author: {c['author_name']} [{c['author_dynasty']}]  (basis: {c['author_basis'] or 'N/A'})")
    print(f"    Entity: {c['eid']}={c['entity_name']} [{c['entity_dynasty']}]  ({c['entity_by']})")
    print(f"    Work.period={c['work_period']} Work.dynasty={c['work_dynasty']}")
    print()
