#!/usr/bin/env python3
"""
B4 二組 batch4-2：升級《國史》needs-review
- 雷叔聞 庫中無 Entity，無法確認朝代
- indexed_by 同時含 新唐書(國史106卷)、宋史(王旦《國史》120卷)、明史(雷叔聞《國史》40卷)
- 三朝同名異書合併，gazetteer_propagation 存疑
"""
import json, os

WID = "1evcs0bosd3wg"
fpath = None
for root, _, files in os.walk("/workspace/Work"):
    for f in files:
        if f.startswith(WID) and f.endswith(".json") and "/collated_edition/" not in os.path.join(root, f):
            fpath = os.path.join(root, f)
            break
    if fpath:
        break

with open(fpath, "r", encoding="utf-8") as f:
    w = json.load(f)

old_note = w["ai_note"]
# 升級 needs-review 級別，說明升級原因
new_prefix = "明史藝文志匹配：標題精確匹配但未能驗證作者（條目作者：'雷叔聞' 庫中無 Entity，朝代待考）。 indexed_by 同時含新唐書藝文志(國史106卷)、宋史藝文志(王旦《國史》120卷)、明史藝文志(雷叔聞《國史》40卷)，三朝同名異書合併於同一 Work，gazetteer_propagation 判斷 dynasty=明 存疑，建議人工核查雷叔聞朝代及是否拆分 Work。"
# 找 ming-round2
start = old_note.find("[ming-round2:")
if start >= 0:
    bracket = old_note[start:]
    # 替換 needs-review (gazetteer_propagation) -> needs-review (author_unverified + tri-dynasty_homograph_merged)
    bracket = bracket.replace("needs-review (gazetteer_propagation)", "needs-review (author_unverified: 雷叔聞無Entity + tri-dynasty_homograph_merged: 唐/宋/明三朝同名國史合併)")
    # 替換 prefix
    old_prefix_end = old_note[:start].rstrip()
    new_note = new_prefix + " " + bracket
    w["ai_note"] = new_note

with open(fpath, "w", encoding="utf-8") as f:
    json.dump(w, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[UPGRADE] {WID} 國史：needs-review (gazetteer_propagation) → author_unverified + tri-dynasty_homograph_merged")
