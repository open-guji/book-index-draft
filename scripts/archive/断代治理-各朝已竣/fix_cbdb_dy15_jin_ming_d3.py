#!/usr/bin/env python3
"""
D3：CBDB dy=15(=宋) vs Entity='金' 4個 + vs Entity='明' 10個 → 修正為宋
"""
import json, os, re

def find_entity(eid):
    for root, _, files in os.walk("/workspace/Entity"):
        for f in files:
            if f.startswith(eid) and f.endswith(".json"):
                return os.path.join(root, f)
    return None

def find_work(wid):
    for root, _, files in os.walk("/workspace/Work"):
        for f in files:
            if f.startswith(wid) and f.endswith(".json") and "/collated_edition/" not in os.path.join(root, f):
                return os.path.join(root, f)
    return None

# dy=15(=宋) vs Entity='金' 4個 + vs Entity='明' 10個
TARGETS = {
    # 金（4个）
    "1j96hhvcrjvje": ("施宜生", "金"),
    "1j96hhvcr8mxt": ("韓孝彥", "金"),
    "1j96hjwlylno4": ("趙大中", "金"),
    "1j96hjwlylnoo": ("姚孝錫", "金"),
    # 明（10个）
    "1j96hhvcrjvgg": ("張世賢", "明"),
    "1j96hjwlxz6l8": ("周紹稷", "明"),
    "1j96hjwlxcpij": ("黃芹", "明"),
    "1j96hjwlxz6lg": ("張濡", "明"),
    "1j96hhvcrjvhk": ("宗林", "明"),
    "1j96hjwlxz6lh": ("陳鎏", "明"),
    "1j96hhvcr8my2": ("許浩", "明"),  # 注意：这个之前 commit 11 已移除了 entity_id，但 Entity 本身可能还在
    "1j96hhvcrjvhx": ("王道", "明"),
    "1j96hjwlyaf6v": ("舒津", "明"),
    "1j96hjwlxcpid": ("陶琰", "明"),
}

all_work_ids = set()
fixed = 0
for eid, (name, old_dyn) in TARGETS.items():
    efp = find_entity(eid)
    if not efp:
        print(f"[SKIP] {eid} {name}: 找不到 Entity 文件")
        continue
    with open(efp, "r", encoding="utf-8") as f:
        e = json.load(f)
    
    if e.get("dynasty") != old_dyn:
        print(f"[SKIP] {eid} {name}: dynasty={e.get('dynasty')} ≠ {old_dyn}")
        continue
    
    # 验证 CBDB dy=15
    ext = e.get("external_ids", {})
    cbdb_source = ext.get("cbdb_source", "")
    m = re.search(r"cbdb_dy=(\d+)", cbdb_source)
    if not m or m.group(1) != "15":
        print(f"[SKIP] {eid} {name}: CBDB dy≠15 ({cbdb_source})")
        continue
    
    by = e.get("birth_year", "?")
    dy = e.get("death_year", "?")
    print(f"[FIX] {eid} {name} ({by}~{dy}): dynasty {old_dyn}→宋 (CBDB dy=15=宋)")
    
    e["dynasty"] = "宋"
    e["period"] = "song"
    e["period_basis"] = f"據 dynasty『宋』自動歸併（修正：CBDB 來源 cbdb_dy=15=宋；原誤標為『{old_dyn}』）"
    ext["cbdb_match"] = ext.get("cbdb_match", "") + f" ; dynasty_fix: {old_dyn}→宋 per CBDB dy=15=宋 (D3 batch)"
    e["external_ids"] = ext
    with open(efp, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=2)
        f.write("\n")
    fixed += 1
    
    for w in e.get("works", []):
        all_work_ids.add((w["work_id"], name, eid))

print(f"\n共修復 {fixed} 個 Entity")

# 同步 index/entities
print("\n=== index/entities 同步 ===")
for fn in sorted(os.listdir("/workspace/index/entities")):
    if not fn.endswith(".json"): continue
    p = f"/workspace/index/entities/{fn}"
    with open(p, "r", encoding="utf-8") as f:
        idx = json.load(f)
    dirty = False
    for eid, (name, old_dyn) in TARGETS.items():
        if eid in idx:
            ee = idx[eid]
            if ee.get("dynasty") != "宋":
                ee["dynasty"] = "宋"
                ee["period"] = "song"
                dirty = True
    if dirty:
        with open(p, "w", encoding="utf-8") as f2:
            json.dump(idx, f2, ensure_ascii=False, indent=2)
            f2.write("\n")
        print(f"  index/entities/{fn}")

# 同步關聯 Work
print("\n=== 關聯 Work 同步 ===")
updated_wids = set()
for wid, author_name, eid in all_work_ids:
    wfp = find_work(wid)
    if not wfp: continue
    with open(wfp, "r", encoding="utf-8") as f:
        w = json.load(f)
    dirty = False
    for a in w.get("authors", []):
        if a.get("name") == author_name:
            if eid in TARGETS:
                old_dyn = TARGETS[eid][1]
                if a.get("dynasty") == old_dyn:
                    a["dynasty"] = "宋"
                    dirty = True
                if not a.get("dynasty_basis"):
                    a["dynasty_basis"] = f"Entity {eid}={author_name} dynasty=宋（CBDB dy=15=宋，修正自{old_dyn}）"
                    dirty = True
    if dirty:
        with open(wfp, "w", encoding="utf-8") as f:
            json.dump(w, f, ensure_ascii=False, indent=2)
            f.write("\n")
        updated_wids.add(wid)
        print(f"  Work {wid} 《{w.get('title','')}》: author.dynasty→宋")

# 同步 index/works
print("\n=== index/works 同步 ===")
all_wids = set(w[0] for w in all_work_ids) | updated_wids
for fn in sorted(os.listdir("/workspace/index/works")):
    if not fn.endswith(".json"): continue
    p = f"/workspace/index/works/{fn}"
    with open(p, "r", encoding="utf-8") as f:
        idx = json.load(f)
    dirty = False
    for wid in all_wids:
        if wid in idx:
            e = idx[wid]
            actual = None
            for root, _, files in os.walk("/workspace/Work"):
                for f in files:
                    if f.startswith(wid) and f.endswith(".json") and "/collated_edition/" not in os.path.join(root, f):
                        with open(os.path.join(root, f), "r", encoding="utf-8") as fh:
                            actual = json.load(fh)
                        break
                if actual: break
            if not actual: continue
            if "authors" in e and actual.get("authors"):
                new_auths = []
                for wa in actual["authors"]:
                    na = {"name": wa["name"], "dynasty": wa.get("dynasty")}
                    if wa.get("dynasty_basis"):
                        na["dynasty_basis"] = wa["dynasty_basis"]
                    new_auths.append(na)
                if e["authors"] != new_auths:
                    e["authors"] = new_auths
                    dirty = True
    if dirty:
        with open(p, "w", encoding="utf-8") as f2:
            json.dump(idx, f2, ensure_ascii=False, indent=2)
            f2.write("\n")
        print(f"  index/works/{fn}")
