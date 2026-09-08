#!/usr/bin/env python3
"""
B2 清初刊本 batch9：玉夏齋傳奇 + 定情人 補 period/dynasty（均清初刊本，無作者 → 據 edition 判清，needs-review）
"""
import json, os

def find_path(wid):
    for root, _, files in os.walk("/workspace/Work"):
        for f in files:
            if f.startswith(wid) and f.endswith(".json") and "/collated_edition/" not in os.path.join(root, f):
                return os.path.join(root, f)
    return None

def fix(wid, title, edition):
    fp = find_path(wid)
    with open(fp, "r", encoding="utf-8") as f:
        w = json.load(f)
    w["period"] = "qing"
    w["period_basis"] = f"edition_propagation: 國立故宮博物院善本舊籍著錄本為『{edition}』，具體作者與成書年代無記載，據刊刻時代歸入清代（needs-review：應考證創作年代）"
    w["dynasty"] = "清"
    w["dynasty_basis"] = "edition_propagation (清初刊本，無作者時以刊刻時代兜底)"
    w["ai_note"] = w.get("ai_note", "") + " [B2-fix: 無作者，據清初刊本兜底 period=qing, dynasty=清；needs-review: 應考證創作年代究係明或清]"
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(w, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"[FIX] {wid} {title}: period qing, dynasty 清 (edition_propagation)")
    return w

w1 = fix("1evkq4ckohce8", "玉夏齋傳奇", "清初刊本")
w2 = fix("1evkq4gof5w5c", "新鐫批評繡像秘本定情人", "清初刊本")

# index 同步
import glob
changes = [("1evkq4ckohce8", w1), ("1evkq4gof5w5c", w2)]
for fn in sorted(os.listdir("/workspace/index/works")):
    if not fn.endswith(".json"): continue
    p = f"/workspace/index/works/{fn}"
    with open(p, "r", encoding="utf-8") as f:
        idx = json.load(f)
    dirty = False
    for wid, w in changes:
        if wid in idx:
            e = idx[wid]
            for k in ["dynasty", "period"]:
                if e.get(k) != w.get(k):
                    e[k] = w.get(k)
                    dirty = True
    if dirty:
        with open(p, "w", encoding="utf-8") as f2:
            json.dump(idx, f2, ensure_ascii=False, indent=2)
            f2.write("\n")
        print(f"[SYNC] index/works/{fn}")
