#!/usr/bin/env python3
"""
D1：批量解除 needs-review (gazetteer_propagation) 的 Work
條件：明史藝文志標作者 + 該作者有 Entity 且 dynasty=明 → 解除 needs-review
"""
import json, os, re

# 加载所有 Entity
entities = {}
for root, _, files in os.walk("/workspace/Entity"):
    for f in files:
        if not f.endswith(".json"): continue
        try:
            with open(os.path.join(root, f), "r", encoding="utf-8") as fh:
                e = json.load(fh)
            if e.get("type") == "entity" and e.get("subtype") == "people":
                entities[e["id"]] = e
        except:
            pass

print(f"[INFO] 載入 {len(entities)} 個人物 Entity")

# 查找 needs-review (gazetteer_propagation) 的 Work
fixes = []
for root, _, files in os.walk("/workspace/Work"):
    for f in files:
        if not f.endswith(".json"): continue
        fp = os.path.join(root, f)
        if "/collated_edition/" in fp: continue
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                w = json.load(fh)
        except:
            continue
        note = w.get("ai_note", "")
        if "needs-review" not in note: continue
        if "gazetteer_propagation" not in note: continue
        # 检查是否有明史藝文志作为主志
        if "主志=明史藝文志" not in note: continue
        
        # 提取明史志條目作者
        m = re.search(r"條目作者：'([^']+)'", note)
        if not m: continue
        ming_author = m.group(1)
        if not ming_author: continue
        
        # 检查 Work 的 authors 中是否有此人，且有 entity_id
        author_info = None
        for a in w.get("authors", []):
            if a.get("name") == ming_author:
                author_info = a
                break
        if not author_info: continue
        
        eid = author_info.get("entity_id")
        if not eid: continue
        if eid not in entities: continue
        e = entities[eid]
        if e.get("dynasty") != "明": continue
        
        # 确认：明史志作者 + Entity dynasty=明 → 可解除 needs-review
        fixes.append({
            "wid": w["id"],
            "title": w.get("title", ""),
            "author": ming_author,
            "eid": eid,
            "entity_name": e.get("primary_name", ""),
            "filepath": fp,
            "note": note,
        })

print(f"[INFO] 找到 {len(fixes)} 個可解除 needs-review 的 Work\n")
for fx in fixes:
    print(f"  {fx['wid']} 《{fx['title']}》 作者={fx['author']} Entity={fx['eid']}({fx['entity_name']}) dynasty=明")

# 执行修复
print(f"\n=== 執行修復 ===")
for fx in fixes:
    with open(fx["filepath"], "r", encoding="utf-8") as f:
        w = json.load(f)
    
    # 移除 needs-review (gazetteer_propagation) 标记
    note = w["ai_note"]
    # 精确移除 "needs-review (gazetteer_propagation)" 
    old_nr = "needs-review (gazetteer_propagation)"
    new_note = note.replace(old_nr, f"needs-review RESOLVED (author_verified: 明史志條目作者={fx['author']} → Entity {fx['eid']} dynasty=明)")
    w["ai_note"] = new_note
    
    # 补充 author.dynasty_basis 如果缺失
    for a in w.get("authors", []):
        if a.get("name") == fx["author"] and not a.get("dynasty_basis"):
            a["dynasty_basis"] = f"Entity {fx['eid']}={fx['entity_name']} dynasty=明（明史藝文志條目作者）"
    
    with open(fx["filepath"], "w", encoding="utf-8") as f:
        json.dump(w, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"  [FIX] {fx['wid']} 《{fx['title']}》: needs-review → RESOLVED")

# 同步 index/works
print(f"\n=== index/works 同步 ===")
fixed_wids = set(fx["wid"] for fx in fixes)
for fn in sorted(os.listdir("/workspace/index/works")):
    if not fn.endswith(".json"): continue
    p = f"/workspace/index/works/{fn}"
    with open(p, "r", encoding="utf-8") as f:
        idx = json.load(f)
    dirty = False
    for wid in fixed_wids:
        if wid in idx:
            # index 可能不存 ai_note，但检查 authors 字段
            e = idx[wid]
            actual = None
            for root2, _, files2 in os.walk("/workspace/Work"):
                for f2 in files2:
                    if f2.startswith(wid) and f2.endswith(".json") and "/collated_edition/" not in os.path.join(root2, f2):
                        with open(os.path.join(root2, f2), "r", encoding="utf-8") as fh2:
                            actual = json.load(fh2)
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
