#!/usr/bin/env python3
"""
B6：清賞錄 張翼 author.dynasty 補明
- 張翼字二星，餘杭人，明人（與包衡同撰《清賞錄》，明萬曆刻本）
- 庫中 2 個張翼 Entity 均非此人（1jae2gjvi6iho=金；1j96hjwlylno2=明初卒1393字子飛鶴慶侯）
"""
import json, os, hashlib

WID = "1ev3bc9a47qww"
fpath = None
for root, _, files in os.walk("/workspace/Work"):
    for f in files:
        if f.startswith(WID) and f.endswith(".json") and "/collated_edition/" not in os.path.join(root, f):
            fpath = os.path.join(root, f)
            break
    if fpath: break

with open(fpath, "r", encoding="utf-8") as f:
    w = json.load(f)

# authors[0] 是張翼，author[1] 是包衡
for a in w["authors"]:
    if a["name"] == "張翼":
        a["dynasty"] = "明"
        a["dynasty_basis"] = "四庫總目+明史藝文志標明人，與包衡同撰《清賞錄》，有明萬曆刻本。註：此張翼字二星，餘杭人，與庫中 1jae2gjvi6iho(金張翼)、1j96hjwlylno2(明初張翼1393卒字子飛) 為同名異人，尚未關聯正確 Entity"
    if a["name"] == "包衡":
        if not a.get("dynasty_basis"):
            a["dynasty_basis"] = "四庫總目+明史藝文志標明人，字彥平，秀水人。庫中無 Entity"

with open(fpath, "w", encoding="utf-8") as f:
    json.dump(w, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[OK] {WID} 清賞錄：張翼 author.dynasty null→明")

# 同步 index
h = hashlib.sha256(WID.encode()).hexdigest()
sh = h[:2]
idx_path = f"/workspace/index/works/{sh}.json"
dirty = False
with open(idx_path, "r", encoding="utf-8") as f:
    idx = json.load(f)
for entry in idx:
    if entry.get("id") == WID:
        for i, a in enumerate(entry.get("authors", [])):
            if a["name"] == "張翼":
                if a.get("dynasty") != "明":
                    entry["authors"][i]["dynasty"] = "明"
                    dirty = True
        break
if dirty:
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"[SYNC] works/{sh}.json：張翼 dynasty 同步")
else:
    print(f"[SKIP] works/{sh}.json")
