#!/usr/bin/env python3
"""
B2 清初刊本 batch10：春柳鶯補作者；合浦珠(徐震)解除錯誤 Entity（同名异人）
"""
import json, os

# 春柳鶯：清無名氏撰
fp = None
for root, _, files in os.walk("/workspace/Work"):
    for f in files:
        if f.startswith("1evgojcsnieio") and f.endswith(".json") and "/collated_edition/" not in os.path.join(root, f):
            fp = os.path.join(root, f)
            break
    if fp: break
with open(fp, "r", encoding="utf-8") as f:
    w1 = json.load(f)
w1["authors"] = [{"name": "無名氏", "role": "撰", "dynasty": "清", "dynasty_basis": "中國通俗小說書目：『清無名氏撰...大連圖書館藏本有康熙壬寅(元年=1662)吳門拚飲潛夫序』；題『南軒鶡冠史者編』"}]
w1["period"] = "qing"
w1["period_basis"] = "據 authors[0].dynasty「清」（康熙元年序，清初小說）"
w1["dynasty"] = "清"
w1["dynasty_basis"] = "author_propagation"
w1["ai_note"] = w1.get("ai_note", "") + " [B2-fix: 補作者清無名氏（南軒鶡冠史者），period=qing dynasty=清]"
with open(fp, "w", encoding="utf-8") as f:
    json.dump(w1, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[FIX1] 1evgojcsnieio 春柳鶯：補作者清無名氏, period qing, dynasty 清")

# 合浦珠：解除錯誤 Entity（同名异人）
fp = None
for root, _, files in os.walk("/workspace/Work"):
    for f in files:
        if f.startswith("1evgojczezi80") and f.endswith(".json") and "/collated_edition/" not in os.path.join(root, f):
            fp = os.path.join(root, f)
            break
    if fp: break
with open(fp, "r", encoding="utf-8") as f:
    w2 = json.load(f)
for a in w2["authors"]:
    if a["name"] == "徐震":
        a["dynasty"] = "清"
        a["dynasty_basis"] = "中國通俗小說書目：『清徐震撰。題「檇李散人編」。首樰文自序。』（清初刊本）"
        if "entity_id" in a:
            del a["entity_id"]
w2["period"] = "qing"
w2["period_basis"] = "據 authors[0].dynasty「清」（清初刊本，清徐震=檇李散人）"
w2["dynasty"] = "清"
w2["dynasty_basis"] = "author_propagation"
w2["ai_note"] = w2.get("ai_note", "") + " [B2-fix: needs-review(critical): 原本錯誤關聯 Entity 1j96h8rw7vhih=明徐震字起之(1546生)，實際本書作者係清徐震號檇李散人（清初小說家），為同名異人，已強制解除 entity_id，作者及 period/dynasty 修正為清。需人工新建正確 Entity 並關聯]"
with open(fp, "w", encoding="utf-8") as f:
    json.dump(w2, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[FIX2] 1evgojczezi80 合浦珠：解除錯誤明徐震 Entity，作者 dynasty→清，period qing，dynasty 清")
print("       needs-review(critical): 同名异人，Entity 1j96h8rw7vhih 係明人，非本書作者")

# 同步 index
changes = [("1evgojcsnieio", w1), ("1evgojczezi80", w2)]
for fn in sorted(os.listdir("/workspace/index/works")):
    if not fn.endswith(".json"): continue
    p = f"/workspace/index/works/{fn}"
    with open(p, "r", encoding="utf-8") as f:
        idx = json.load(f)
    dirty = False
    for wid, w in changes:
        if wid in idx:
            e = idx[wid]
            for k in ["dynasty", "period", "authors"]:
                if e.get(k) != w.get(k):
                    if k == "authors":
                        # index 中的 authors 是列表，可能只存 name
                        new_auths = [{"name": a["name"], "dynasty": a.get("dynasty")} for a in w.get("authors", [])]
                        e["authors"] = new_auths
                    else:
                        e[k] = w.get(k)
                    dirty = True
    if dirty:
        with open(p, "w", encoding="utf-8") as f2:
            json.dump(idx, f2, ensure_ascii=False, indent=2)
            f2.write("\n")
        print(f"[SYNC] index/works/{fn}")
