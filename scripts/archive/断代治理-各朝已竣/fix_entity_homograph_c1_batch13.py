#!/usr/bin/env python3
"""
C1 batch13：3 個修復
1. 陰符玄解 黃帝：dynasty 清→上古傳說（與 Entity 一致）；needs-review 說明：清乾隆刊本『玄解』=注解，非原經，實際注解者不詳，題黃帝著係沿用古偽題
2. 太極圖解釋義 許珍：元許珍 vs Entity 北宋許珍 → 移 entity_id
3. 春秋纂 蔡深：元蔡深(字淵仲，樂平人，元史志) vs 明蔡深(明史志)；Entity=元蔡深 → author.dynasty 明→元，needs-review 標註同名異書合併
"""
import json, os

def find_work(wid):
    for root, _, files in os.walk("/workspace/Work"):
        for f in files:
            if f.startswith(wid) and f.endswith(".json") and "/collated_edition/" not in os.path.join(root, f):
                return os.path.join(root, f)
    return None

# 1. 陰符玄解 黃帝（dynasty 清 → 上古傳說）
wid = "1evkpvygwkq2o"
fp = find_work(wid)
with open(fp, "r", encoding="utf-8") as f:
    w1 = json.load(f)
for a in w1["authors"]:
    if a.get("name") == "黃帝":
        a["dynasty"] = "上古傳說"
        a["dynasty_basis"] = "黃帝係上古傳說帝王，《陰符經》舊題黃帝撰（學界公認偽托）。註：此 Work 係『陰符玄解』=《陰符經》注解，國立故宮博物院善本舊籍著錄『清乾隆三十七年(1772)壬辰林笏堂刊本』——實際注解者為清人但不詳，題黃帝著沿用古偽題"
w1["period"] = "qing"
w1["period_basis"] = "edition_propagation：國立故宮博物院善本舊籍著錄『清乾隆三十七年(1772)壬辰林笏堂刊本』——據刊刻時代定 period；但作者為偽題上古黃帝，兩者不矛盾"
w1["dynasty"] = "清"
w1["dynasty_basis"] = "edition_propagation（內容為清代注解；雖偽題上古黃帝撰，但實際成書時代為清）"
w1["ai_note"] = w1.get("ai_note", "") + " [C1-fix(critical): author.dynasty 荒謬錯『清』→ 改為『上古傳說』（題黃帝撰係偽托《陰符經》古作者）。Work.dynasty/period 仍保留 qing（依據清乾隆三十七年刊本+內容為清人注解）。needs-review: 應核對原書確認注解者真實姓名，或拆分為『黃帝撰陰符經』+『清無名氏玄解』兩層]"
with open(fp, "w", encoding="utf-8") as f:
    json.dump(w1, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[FIX1] {wid} 陰符玄解：黃帝 dynasty 清→上古傳說；Work.dynasty=清仍保留(清代注解本)；needs-review 拆分")

# 2. 太極圖解釋義 許珍
wid = "1evga65pp3g1s"
fp = find_work(wid)
with open(fp, "r", encoding="utf-8") as f:
    w2 = json.load(f)
for a in w2["authors"]:
    if a.get("name") == "許珍":
        a["dynasty_basis"] = "補遼金元藝文志：『元許珍太極圖解釋義一卷』"
        if "entity_id" in a:
            del a["entity_id"]
w2["ai_note"] = w2.get("ai_note", "") + " [C1-fix: needs-review(critical) 同名異人 Entity 移除。原 entity_id=1j96hhvcrjvj7=北宋許珍，與本書作者元許珍不同朝代。需人工查 CBDB 建立正確元許珍 Entity 並關聯]"
with open(fp, "w", encoding="utf-8") as f:
    json.dump(w2, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[FIX2] {wid} 太極圖解釋義：移除北宋許珍 Entity（同名異人）")

# 3. 春秋纂 蔡深（元+明同名異書合併）
wid = "1evdibrm3anls"
fp = find_work(wid)
with open(fp, "r", encoding="utf-8") as f:
    w3 = json.load(f)
for a in w3["authors"]:
    if a.get("name") == "蔡深":
        a["dynasty"] = "元"
        a["dynasty_basis"] = "元史藝文志：『元蔡深（字淵仲，江西樂平人）春秋纂十卷』——有字籍更詳細優先；明史藝文志僅題『蔡深《春秋纂》十卷』，或係重複著錄元蔡深書，或為另一明蔡深同名異書"
        # Entity 1j967da96anvk 本身是元蔡深，不衝突，保留
w3["period"] = "liao-jin-yuan"
w3["period_basis"] = "據 authors[0].dynasty『元』（元史藝文志有字籍更詳盡，優先）"
w3["dynasty"] = "元"
w3["dynasty_basis"] = "author_propagation"
w3["ai_note"] = w3.get("ai_note", "") + " [C1-fix: author.dynasty 明→元，period ming→liao-jin-yuan。needs-review: 兩志衝突——元史藝文志=元蔡深(字淵仲江西樂平人)；明史藝文志=明蔡深（無字籍）。優先採元史志有字籍者，但存在『元蔡深+明蔡深兩部春秋纂十卷被合併』的同名異書風險，需人工核對 CBDB 是否有兩蔡深]"
with open(fp, "w", encoding="utf-8") as f:
    json.dump(w3, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[FIX3] {wid} 春秋纂：dynasty 明→元，period ming→liao-jin-yuan；needs-review 兩志同名異書")

# 同步 index
changes = [("1evkpvygwkq2o", w1), ("1evga65pp3g1s", w2), ("1evdibrm3anls", w3)]
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
            if "authors" in e:
                new_auths = []
                for wa in w.get("authors", []):
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
        print(f"[SYNC] index/works/{fn}")
