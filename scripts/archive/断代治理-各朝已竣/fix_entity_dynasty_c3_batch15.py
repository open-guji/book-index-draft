#!/usr/bin/env python3
"""
C3 batch15：4 個明遺民 Entity 批量修復 (dynasty 清→明)
所有 4 個 Entity 的 CBDB 來源都是 cbdb_dy=20 (= 明)，但被錯標為 dynasty=清！
和 commit 14 鄺露是完全相同的錯誤模式

1. 朱明鎬 (1j96hjwlxcpko)：1607(萬曆35年)~1652(順治9)，字昭芑，太倉人，明諸生，入清不仕，著《史糾》
2. 王介之 (1j96hjwlxcpj7)：1606(萬曆34)~1686(康熙25)，字石子/石崖，王夫之兄，明崇禎15年舉人，入清隱居不仕
3. 戴笠   (1j96hjwlxcpjo)：?~1682(康熙21)，字曼公/耕野，吳江人，明諸生，後為僧，著《永陵傳信錄》(記嘉靖朝事)
4. 呂毖   (1j96hjwlxny1i)：1611(萬曆39)~1664(康熙3)，字貞九/桴庵，崇德人，明崇禎3年舉人，入清不仕

同步：Entity 文件 + index/entities + 關聯 Work 的 author.dynasty/period/dynasty
"""
import json, os

FIXES = [
    {
        "eid": "1j96hjwlxcpko",
        "name": "朱明鎬",
        "basis": "CBDB dy=20=明 (cbdb_id=74191)；1607萬曆三十五年生，明諸生，太倉人，入清不仕，順治九年卒（46歲）。著《史糾》考訂諸史，明遺民"
    },
    {
        "eid": "1j96hjwlxcpj7",
        "name": "王介之",
        "basis": "CBDB dy=20=明 (cbdb_id=69080)；1606萬曆三十四年生，王夫之長兄，明崇禎十五年壬午科舉人，入清隱居耐園不仕，康熙二十五年卒。明遺民，學者稱石崖先生"
    },
    {
        "eid": "1j96hjwlxcpjo",
        "name": "戴笠",
        "basis": "CBDB dy=20=明 (cbdb_id=91684)；明諸生，吳江人，字曼公，後出家為僧，別號耕野、貞孝，卒康熙二十一年。著《永陵傳信錄》記明嘉靖朝故事，明遺民"
    },
    {
        "eid": "1j96hjwlxny1i",
        "name": "呂毖",
        "basis": "CBDB dy=20=明 (cbdb_id=73787)；1611萬曆三十九年生，崇德(今桐鄉)人，明崇禎三年庚午科舉人，入清不仕，康熙三年卒。字貞九號桴庵，明遺民"
    }
]

# 收集關聯 Work 用於 index/works 同步
work_ids_to_update = set()

for fix in FIXES:
    print(f"\n=== Entity: {fix['name']} ({fix['eid']}): dynasty 清→明 ===")
    # 找 Entity 文件
    efp = None
    for root, _, files in os.walk("/workspace/Entity"):
        for f in files:
            if f.startswith(fix["eid"]) and f.endswith(".json"):
                efp = os.path.join(root, f)
                break
        if efp: break
    with open(efp, "r", encoding="utf-8") as f:
        e = json.load(f)

    e["dynasty"] = "明"
    e["period"] = "ming"
    e["period_basis"] = f"據 dynasty『明』自動歸併（修正：CBDB 來源 cbdb_dy=20=明；{fix['basis']}）"
    ext_ids = e.get("external_ids", {})
    ext_ids["cbdb_match"] = ext_ids.get("cbdb_match", "") + " ; dynasty_fix: 清→明 per CBDB dy=20"
    e["external_ids"] = ext_ids
    with open(efp, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"  Entity saved: dynasty=明, period=ming")

    # 記錄關聯 Work
    for w in e.get("works", []):
        work_ids_to_update.add((w["work_id"], fix["name"], fix["eid"]))

# 同步 index/entities
print("\n=== index/entities 同步 ===")
for fn in sorted(os.listdir("/workspace/index/entities")):
    if not fn.endswith(".json"): continue
    p = f"/workspace/index/entities/{fn}"
    with open(p, "r", encoding="utf-8") as f:
        idx = json.load(f)
    dirty = False
    for fix in FIXES:
        if fix["eid"] in idx:
            ee = idx[fix["eid"]]
            if ee.get("dynasty") != "明" or ee.get("period") != "ming":
                ee["dynasty"] = "明"
                ee["period"] = "ming"
                dirty = True
    if dirty:
        with open(p, "w", encoding="utf-8") as f2:
            json.dump(idx, f2, ensure_ascii=False, indent=2)
            f2.write("\n")
        print(f"  index/entities/{fn}: 4 Entity dynasty→明 period→ming")

# 同步關聯 Work（author.dynasty、Work.period/dynasty）
print("\n=== 關聯 Work 同步 ===")
updated_work_paths = []
for wid, author_name, eid in work_ids_to_update:
    wfp = None
    for root, _, files in os.walk("/workspace/Work"):
        for f in files:
            if f.startswith(wid) and f.endswith(".json") and "/collated_edition/" not in os.path.join(root, f):
                wfp = os.path.join(root, f)
                break
        if wfp: break
    if not wfp: continue
    with open(wfp, "r", encoding="utf-8") as f:
        w = json.load(f)
    dirty = False
    for a in w.get("authors", []):
        if a.get("name") == author_name:
            if a.get("dynasty") != "明":
                a["dynasty"] = "明"
                dirty = True
            if not a.get("dynasty_basis"):
                a["dynasty_basis"] = f"Entity {eid}={author_name}=明人（CBDB dy=20=明，明遺民）"
                dirty = True
            if a.get("entity_id") != eid:
                a["entity_id"] = eid
                dirty = True
    # 重新计算 Work period/dynasty：如果作者是明，且原 period=qing，则改为 ming
    if any(a.get("dynasty") == "明" for a in w.get("authors", [])):
        if w.get("period") == "qing":
            w["period"] = "ming"
            w["period_basis"] = f"據 authors[0].dynasty『明』（{author_name} 修正為明遺民）"
            dirty = True
        if w.get("dynasty") == "清":
            w["dynasty"] = "明"
            w["dynasty_basis"] = "author_propagation"
            dirty = True
    if dirty:
        with open(wfp, "w", encoding="utf-8") as f:
            json.dump(w, f, ensure_ascii=False, indent=2)
            f.write("\n")
        updated_work_paths.append(wid)
        print(f"  Work {wid} 《{w.get('title','')}》: author.dynasty/Work.period 修正為明")

# 同步 index/works
print("\n=== index/works 同步 ===")
all_wids = set(w[0] for w in work_ids_to_update) | set(updated_work_paths)
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
            for k in ["dynasty", "period"]:
                if e.get(k) != actual.get(k):
                    e[k] = actual.get(k)
                    dirty = True
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
