#!/usr/bin/env python3
"""
B3：昭忠錄(1ev3bais3hmo0)修復
- 四庫總目+元史藝文志均確定此書一卷本係『宋遺民所作，記宋末忠臣義士』
- 明史藝文志之『周璟《昭忠錄》五卷』係另一本明人同名書，兩書被錯誤合併於同一 Work
- 修正：author.dynasty 明→南宋；Work.period ming→song；Work.dynasty 明→南宋
- 標註 needs-review：宋遺民一卷本+明周璟五卷本同名異書合併，建議拆分
"""
import json, os

WID = "1ev3bais3hmo0"
fp = None
for root, _, files in os.walk("/workspace/Work"):
    for f in files:
        if f.startswith(WID) and f.endswith(".json") and "/collated_edition/" not in os.path.join(root, f):
            fp = os.path.join(root, f)
            break
    if fp: break

with open(fp, "r", encoding="utf-8") as f:
    w = json.load(f)

# author 修正
for a in w["authors"]:
    if a["name"] == "不著撰人":
        a["dynasty"] = "南宋"
        a["dynasty_basis"] = "四庫全書總目提要明確：『所記皆南宋末忠節事蹟...蓋宋遺民之所作也』。內容始紹定辛卯(1231)迄宋亡(1279)文天祥陸秀夫謝枋得等130人"

# Work period/dynasty 修正
w["period"] = "song"
w["period_basis"] = "四庫總目+元史藝文志均以為宋遺民作品，記宋末事，不應屬明/遼金元"
w["dynasty"] = "南宋"
w["dynasty_basis"] = "四庫全書總目提要：『蓋宋遺民之所作也』（宋遺民係宋人入元不仕，朝代仍歸南宋）"

# ai_note 添加 needs-review 说明同名异书合并
w["ai_note"] = w.get("ai_note", "") + " [B3-fix: author.dynasty 明→南宋，period ming→song，dynasty 明→南宋（四庫總目+元史藝文志確定為宋遺民記宋末事）；needs-review: 本 Work 同時著錄『宋遺民昭忠錄一卷』與『明周璟昭忠錄五卷』兩部同名異書（卷數1 vs 5，作者佚名 vs 周璟），係錯誤合併，建議拆分為兩個 Work]"

with open(fp, "w", encoding="utf-8") as f:
    json.dump(w, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[FIX] {WID} 昭忠錄：宋遺民作品，period ming→song, dynasty 明→南宋, author.dynasty 明→南宋")
print(f"[NOTE] needs-review: 宋遺民一卷+明周璟五卷同名異書合併待拆分")

# --- index works 同步 ---
for fn in os.listdir("/workspace/index/works"):
    if not fn.endswith(".json"):
        continue
    p = f"/workspace/index/works/{fn}"
    with open(p, "r", encoding="utf-8") as f:
        idx = json.load(f)
    if WID in idx:
        e = idx[WID]
        dirty = False
        for k in ["dynasty", "period"]:
            if e.get(k) != w.get(k):
                e[k] = w.get(k)
                dirty = True
        # author 字符串：index 中 author 字段是单个字符串名字，没有 dynasty，不管
        if dirty:
            with open(p, "w", encoding="utf-8") as f2:
                json.dump(idx, f2, ensure_ascii=False, indent=2)
                f2.write("\n")
            print(f"[SYNC] index/works/{fn}: dynasty→{w['dynasty']}, period→{w['period']}")
        break
