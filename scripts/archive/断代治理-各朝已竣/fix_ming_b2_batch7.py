#!/usr/bin/env python3
"""
B2 清初刊本 batch7-1：修正2個
1. 醉醒石：author.dynasty 清→明（indexed_by 明刊原本+明無名氏撰；東魯古狂生係明末人），Work.period qing→ming
2. 東度記：補 author.dynasty=明（方汝浩 Entity.dynasty=明），補 Work.period=ming，dynasty=明
"""
import json, os, hashlib

def find_wid_path(wid):
    for root, _, files in os.walk("/workspace/Work"):
        for f in files:
            if f.startswith(wid) and f.endswith(".json") and "/collated_edition/" not in os.path.join(root, f):
                return os.path.join(root, f)
    return None

# --- 1. 醉醒石 ---
wid1 = "1evgoadl4auio"
fp1 = find_wid_path(wid1)
with open(fp1, "r", encoding="utf-8") as f:
    w1 = json.load(f)
for a in w1["authors"]:
    if a["name"] == "東魯古狂生":
        a["dynasty"] = "明"
        a["dynasty_basis"] = "indexed_by 中國通俗小說書目明確標『明無名氏撰』『明刊原本』；此書係明末短篇話本小說集"
w1["period"] = "ming"
w1["period_basis"] = "據 authors[0].dynasty「明」"
w1["dynasty"] = "明"
w1["dynasty_basis"] = "author_propagation"
w1["ai_note"] = w1.get("ai_note", "") + " [B2-fix: 作者朝代清→明；舊『清東魯古狂生撰』與 indexed_by 『明無名氏撰/明刊原本』矛盾，按孫楷第書目定為明末作品]"
with open(fp1, "w", encoding="utf-8") as f:
    json.dump(w1, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[FIX1] {wid1} 醉醒石：東魯古狂生 dynasty 清→明，period qing→ming")

# --- 2. 東度記 ---
wid2 = "1evgosn8riwow"
fp2 = find_wid_path(wid2)
with open(fp2, "r", encoding="utf-8") as f:
    w2 = json.load(f)
for a in w2["authors"]:
    if a["name"] == "方汝浩":
        if not a.get("dynasty"):
            a["dynasty"] = "明"
            a["dynasty_basis"] = "Entity 1j969m70qdn9e dynasty=明，崇禎八年(1635)有東度記序，係明末小說家"
w2["period"] = "ming"
w2["period_basis"] = "據 authors[0].dynasty「明」"
w2["dynasty"] = "明"
w2["dynasty_basis"] = "author_propagation"
w2["ai_note"] = w2.get("ai_note", "") + " [B2-fix: 從方汝浩 Entity 補 period=ming, dynasty=明；書序崇禎乙亥(8年)]"
with open(fp2, "w", encoding="utf-8") as f:
    json.dump(w2, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[FIX2] {wid2} 東度記：方汝浩 author.dynasty 補明，Work period/dynasty 補明")

# --- index 同步 ---
def sync_idx(wid, w):
    found = False
    for fn in os.listdir("/workspace/index/works"):
        if not fn.endswith(".json"):
            continue
        p = f"/workspace/index/works/{fn}"
        with open(p, "r", encoding="utf-8") as f:
            idx = json.load(f)
        if wid in idx:
            e = idx[wid]
            dirty = False
            for k in ["dynasty", "period"]:
                if e.get(k) != w.get(k):
                    e[k] = w.get(k)
                    dirty = True
            if e.get("author") and w.get("authors"):
                first_auth = w["authors"][0]
                old_ad = None
                # 看 index entry 有没有作者 dynasty 字段
                if "dynasty" in e and first_auth.get("dynasty"):
                    if e.get("dynasty") != first_auth.get("dynasty"):
                        # 上面已经比过了
                        pass
            if dirty:
                with open(p, "w", encoding="utf-8") as f2:
                    json.dump(idx, f2, ensure_ascii=False, indent=2)
                    f2.write("\n")
                print(f"[SYNC] index/works/{fn}: {wid} dynasty/period 同步")
            found = True
            break
    if not found:
        print(f"[WARN] {wid} 不在 index works 中")

sync_idx(wid1, w1)
sync_idx(wid2, w2)
