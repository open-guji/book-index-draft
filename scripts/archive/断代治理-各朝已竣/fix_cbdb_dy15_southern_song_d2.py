#!/usr/bin/env python3
"""
D2：修正 CBDB DY_MAP + 修復真衝突
1. dy=15(=宋) vs Entity='南朝宋' 的 6 個：宋朝人被誤標為南朝宋（"宋"字混淆）
2. dy=15(=宋) vs Entity='唐' 的 5 個：宋朝人被誤標為唐
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

# 目標：dy=15(=宋) vs Entity='南朝宋' + '唐'
TARGETS = {
    # 南朝宋（6个）
    "1j96h8rw7k8x8": ("袁王壽", "南朝宋", "宋"),
    "1j96h8rw7k8x2": ("晏乂", "南朝宋", "宋"),
    "1j96hjwlxny11": ("柯洽", "南朝宋", "宋"),
    "1j96hhvcrv408": ("林伯順", "南朝宋", "宋"),
    "1j96h8rw7k8xc": ("虞綽", "南朝宋", "宋"),
    "1j96h8rw7k8y6": ("陳延之", "南朝宋", "宋"),
    # 唐（5个）
    "1j96hjwlylnq1": ("武密", "唐", "宋"),
    "1j96hjwlylnpx": ("裴煜", "唐", "宋"),
    "1j96hjwlxcpig": ("郭京", "唐", "宋"),
    "1j96hjwlxcphx": ("唐仲", "唐", "宋"),
    "1j96hjwlylnpz": ("李冀", "唐", "宋"),
}

all_work_ids = set()
for eid, (name, old_dyn, new_dyn) in TARGETS.items():
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
    print(f"[FIX] {eid} {name} ({by}~{dy}): dynasty {old_dyn}→{new_dyn} (CBDB dy=15=宋)")
    
    e["dynasty"] = new_dyn
    e["period"] = "song"
    e["period_basis"] = f"據 dynasty『宋』自動歸併（修正：CBDB 來源 cbdb_dy=15=宋；原誤標為『{old_dyn}』，疑因『宋』字混淆——南朝宋/宋/唐 導致同名混淆）"
    ext["cbdb_match"] = ext.get("cbdb_match", "") + f" ; dynasty_fix: {old_dyn}→{new_dyn} per CBDB dy=15=宋 (D2 batch)"
    e["external_ids"] = ext
    with open(efp, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=2)
        f.write("\n")
    
    for w in e.get("works", []):
        all_work_ids.add((w["work_id"], name, eid))

# 同步 index/entities
print("\n=== index/entities 同步 ===")
for fn in sorted(os.listdir("/workspace/index/entities")):
    if not fn.endswith(".json"): continue
    p = f"/workspace/index/entities/{fn}"
    with open(p, "r", encoding="utf-8") as f:
        idx = json.load(f)
    dirty = False
    for eid, (name, old_dyn, new_dyn) in TARGETS.items():
        if eid in idx:
            ee = idx[eid]
            if ee.get("dynasty") != new_dyn:
                ee["dynasty"] = new_dyn
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
            TARGETS_old = {eid: (name, old, new) for eid, (name, old, new) in TARGETS.items()}
            if eid in TARGETS_old:
                old_dyn = TARGETS_old[eid][1]
                if a.get("dynasty") == old_dyn:
                    a["dynasty"] = TARGETS_old[eid][2]
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
