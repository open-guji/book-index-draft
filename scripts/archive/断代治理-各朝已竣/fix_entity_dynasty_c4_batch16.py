#!/usr/bin/env python3
"""
C4 batch16：反向 CBDB 導入批次 bug 修復（cbdb_dy=19=清，但 Entity.dynasty=明）
與 commit 14/15 明遺民(dy=20→清) 恰好是對稱反向錯誤！

4 Entity 清修復：
1. 廖文英 1j96hjwlxcpki (cbdb_id=550667, dy=19=清)：康熙中為南康知府，四庫標『國朝廖文英撰』，康熙十二年白鹿書院志刻本
2. 李衷燦 1j96hhvcrjvgp (cbdb_id=511421, dy=19=清)：四庫標『國朝李衷燦撰』，摘孫奇逢魏裔介成性(均清人)語，清史稿藝文志
3. 金約   1j96hjwlx1gyc (cbdb_id=572541, dy=19=清)：清史稿藝文志著錄『海道圖說十五卷 金約撰』——清人
4. 陳昆   1j96hjwlxcpk4 (cbdb_id=289658, dy=19=清)：清史稿『西夏事略十六卷 陳昆撰』

Work 西夏事略 (1ev3baqcz320w) 還發現同名異書合併：
 - 四庫總目(一卷)：偽題王稱(=王偁)撰=抄《東都事略·西夏傳》(宋人)
 - 清史稿(十六卷)：清陳昆撰
 → needs-review(critical) 標註同名異書合併
"""
import json, os

FIXES = [
    {
        "eid": "1j96hjwlxcpki",
        "name": "廖文英",
        "basis": "CBDB dy=19=清(cbdb_id=550667)；四庫全書總目『國朝廖文英撰』，康熙中為南康知府，修《白鹿書院志》十六卷，康熙十二年(1673)刻增修本；另著《正字通》已著錄"
    },
    {
        "eid": "1j96hhvcrjvgp",
        "name": "李衷燦",
        "basis": "CBDB dy=19=清(cbdb_id=511421)；四庫全書總目『國朝李衷燦撰』，《晚聞篇》摘宋周程五子至國朝(清)孫奇逢、魏裔介、成性諸人之語；清史稿藝文志著錄"
    },
    {
        "eid": "1j96hjwlx1gyc",
        "name": "金約",
        "basis": "CBDB dy=19=清(cbdb_id=572541)；清史稿藝文志：『海道圖說十五卷 金約撰』"
    },
    {
        "eid": "1j96hjwlxcpk4",
        "name": "陳昆",
        "basis": "CBDB dy=19=清(cbdb_id=289658)；清史稿藝文志：『西夏事略十六卷 陳昆撰』"
    }
]

# ========== Entity 修復 ==========
work_ids_to_update = set()
for fix in FIXES:
    print(f"\n=== Entity: {fix['name']} ({fix['eid']}): dynasty 明→清 ===")
    efp = None
    for root, _, files in os.walk("/workspace/Entity"):
        for f in files:
            if f.startswith(fix["eid"]) and f.endswith(".json"):
                efp = os.path.join(root, f)
                break
        if efp: break
    with open(efp, "r", encoding="utf-8") as f:
        e = json.load(f)
    e["dynasty"] = "清"
    e["period"] = "qing"
    e["period_basis"] = f"據 dynasty『清』自動歸併（修正：CBDB 來源 cbdb_dy=19=清；{fix['basis']}）"
    ext = e.get("external_ids", {})
    ext["cbdb_match"] = ext.get("cbdb_match", "") + " ; dynasty_fix: 明→清 per CBDB dy=19"
    e["external_ids"] = ext
    with open(efp, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"  Entity saved: dynasty=清, period=qing")
    for w in e.get("works", []):
        work_ids_to_update.add((w["work_id"], fix["name"], fix["eid"]))

# ========== index/entities 同步 ==========
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
            if ee.get("dynasty") != "清" or ee.get("period") != "qing":
                ee["dynasty"] = "清"
                ee["period"] = "qing"
                dirty = True
    if dirty:
        with open(p, "w", encoding="utf-8") as f2:
            json.dump(idx, f2, ensure_ascii=False, indent=2)
            f2.write("\n")
        print(f"  index/entities/{fn}: 4 Entity dynasty→清 period→qing")

# ========== 關聯 Work 修復 ==========
print("\n=== 關聯 Work 修復 ===")
updated_wids = set()
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
            if a.get("dynasty") != "清":
                a["dynasty"] = "清"
                dirty = True
            if not a.get("dynasty_basis") or (a.get("dynasty_basis") and "明" in a.get("dynasty_basis","")):
                # 找到对应 fix 写 basis
                for fix in FIXES:
                    if fix["name"] == author_name:
                        a["dynasty_basis"] = f"Entity {eid}={author_name}=清人（CBDB dy=19=清；{fix['basis'].split('：')[0]}）"
                        break
                dirty = True
    # Work period/dynasty: 如果原 period=ming 且作者是清，改清
    if any(a.get("dynasty") == "清" for a in w.get("authors", [])):
        if w.get("period") == "ming":
            w["period"] = "qing"
            w["period_basis"] = f"據 authors[0].dynasty『清』（{author_name} 修正為清）"
            dirty = True
        if w.get("dynasty") == "明":
            w["dynasty"] = "清"
            w["dynasty_basis"] = "author_propagation"
            dirty = True
    # 西夏事略特别处理：needs-review 同名异书
    if wid == "1ev3baqcz320w":
        note = w.get("ai_note", "")
        if "needs-review" not in note:
            w["ai_note"] = note + " [C4-fix: needs-review(critical) 同名異書合併！西夏事略存在兩書：① 四庫總目一卷本=偽題承議郎王稱(=王偁)撰，抄北宋王偁《東都事略·西夏傳》(宋人)，曹溶學海類編收之失考；② 清史稿藝文志十六卷本=清陳昆撰。本 Work 將宋一卷(偽題王偁)+清十六卷(陳昆) 兩同名異書合併，建議拆分為兩 Work。]"
            dirty = True
        print(f"  [NOTE] {wid} 西夏事略標註同名異書合併")
    if dirty:
        with open(wfp, "w", encoding="utf-8") as f:
            json.dump(w, f, ensure_ascii=False, indent=2)
            f.write("\n")
        updated_wids.add(wid)
        print(f"  Work {wid} 《{w.get('title','')}》: author.dynasty/Work.period→清")

# ========== index/works 同步 ==========
print("\n=== index/works 同步 ===")
all_wids = set(w[0] for w in work_ids_to_update) | updated_wids
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
