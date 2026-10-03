#!/usr/bin/env python3
"""
C1 batch11：3 個同名異人實體關聯錯誤修復（跨表檢查發現）
1. 宋史闡幽 許浩：author.dynasty=明(字複齋，弘治中) vs Entity 清許浩(1693~1738) → 移除 entity_id
2. 天文書 柯洽：author.dynasty=明(字九疑，天臺人，洪武刻本) vs Entity 南朝宋柯洽 → 移除 entity_id
3. 茶山老人遺集 沈貞：author.dynasty=元(字元吉號茶山老人，長興人，入明不仕) vs Entity 朝鮮沈貞(1471~1531) → 移除 entity_id
"""
import json, os

def find_work(wid):
    for root, _, files in os.walk("/workspace/Work"):
        for f in files:
            if f.startswith(wid) and f.endswith(".json") and "/collated_edition/" not in os.path.join(root, f):
                return os.path.join(root, f)
    return None

# 1. 許浩
wid = "1ev3bb5v90l4w"
fp = find_work(wid)
with open(fp, "r", encoding="utf-8") as f:
    w1 = json.load(f)
for a in w1["authors"]:
    if a.get("name") == "許浩":
        a["dynasty_basis"] = "四庫全書總目：『明許浩撰。浩字複齋，餘姚人。弘治中以貢生官桐城縣教諭。』四庫存目叢書：明崇禎元年許鏘刻本"
        if "entity_id" in a:
            del a["entity_id"]
w1["ai_note"] = w1.get("ai_note", "") + " [C1-fix: needs-review(critical) 同名異人 Entity 移除。原 entity_id=1j96hhvcr8my2=清許浩(1693~1738，康熙~乾隆)，非本書明中期許浩(字複齋，弘治中，與邱濬同時)。需人工查 CBDB 建立正確 Entity 並關聯]"
with open(fp, "w", encoding="utf-8") as f:
    json.dump(w1, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[FIX1] {wid} 宋史闡幽：移除清許浩 Entity，補 dynasty_basis")

# 2. 柯洽
wid = "1ev3bbmslhvr4"
fp = find_work(wid)
with open(fp, "r", encoding="utf-8") as f:
    w2 = json.load(f)
for a in w2["authors"]:
    if a.get("name") == "柯洽":
        a["dynasty_basis"] = "四庫全書總目：『明柯洽撰。洽字九疑，天臺人。』識典古籍：洪武十六年內府刻本"
        if "entity_id" in a:
            del a["entity_id"]
w2["ai_note"] = w2.get("ai_note", "") + " [C1-fix: needs-review(critical) 同名異人 Entity 移除。原 entity_id=1j96hjwlxny11=南朝宋柯洽，非本書明柯洽(字九疑，天臺人，洪武刻本)。需人工查 CBDB 建立正確 Entity 並關聯]"
with open(fp, "w", encoding="utf-8") as f:
    json.dump(w2, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[FIX2] {wid} 天文書：移除南朝宋柯洽 Entity，補 dynasty_basis")

# 3. 沈貞
wid = "1ev3bdii6aa68"
fp = find_work(wid)
with open(fp, "r", encoding="utf-8") as f:
    w3 = json.load(f)
for a in w3["authors"]:
    if a.get("name") == "沈貞":
        a["dynasty_basis"] = "四庫全書總目：『元沈貞撰。貞字元吉，自號茶山老人，長興人，入明不仕。』（元遺民，朝代歸元）"
        if "entity_id" in a:
            del a["entity_id"]
w3["ai_note"] = w3.get("ai_note", "") + " [C1-fix: needs-review(critical) 同名異人 Entity 移除。原 entity_id=1j96hhvcrjvh2=朝鮮沈貞(1471~1531，朝鮮王朝)，非本書元沈貞(字元吉，號茶山老人，浙江長興人，入明不仕)。需人工查 CBDB 建立正確 Entity 並關聯]"
with open(fp, "w", encoding="utf-8") as f:
    json.dump(w3, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[FIX3] {wid} 茶山老人遺集：移除朝鮮沈貞 Entity，補 dynasty_basis")

# 同步 index (不需要改 period/dynasty，因為作者朝代沒有變，只是移除錯誤 entity_id 並補 basis)
# 检查 index 中是否有 entity_id 字段，如果有就同步删除
changes = [("1ev3bb5v90l4w", w1), ("1ev3bbmslhvr4", w2), ("1ev3bdii6aa68", w3)]
import os
for fn in sorted(os.listdir("/workspace/index/works")):
    if not fn.endswith(".json"): continue
    p = f"/workspace/index/works/{fn}"
    with open(p, "r", encoding="utf-8") as f:
        idx = json.load(f)
    dirty = False
    for wid, w in changes:
        if wid in idx:
            e = idx[wid]
            if "authors" in e:
                # index authors: 可能有 entity_id
                for i, a in enumerate(e["authors"]):
                    if a.get("name") in ["許浩", "柯洽", "沈貞"]:
                        # 用 work 里的 authors 信息覆盖 index
                        work_authors = [x for x in w["authors"] if x["name"] == a["name"]]
                        if work_authors:
                            wa = work_authors[0]
                            new_a = {"name": wa["name"], "dynasty": wa.get("dynasty")}
                            if wa.get("dynasty_basis"):
                                new_a["dynasty_basis"] = wa["dynasty_basis"]
                            e["authors"][i] = new_a
                            dirty = True
    if dirty:
        with open(p, "w", encoding="utf-8") as f2:
            json.dump(idx, f2, ensure_ascii=False, indent=2)
            f2.write("\n")
        print(f"[SYNC] index/works/{fn}: authors entity_id 移除 + dynasty_basis 同步")
