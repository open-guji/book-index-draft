#!/usr/bin/env python3
"""
C1 batch12：4 個嚴重同名異人+斷代錯誤修復
1. 華嚴法界境 德清：明憨山大師 vs Entity 元升(南宋1163~1217，名字都不對) → 移 entity_id
2. 道德經注 王珪：元王珪(字君璋，常熟) vs Entity 北宋王珪(1019~1085，字禹玉，華陽宰相) → 移 entity_id
3. 蠡海集 王逵：明初錢塘王逵(洪武永樂間) vs Entity 北宋王逵(991~1072) → 移 entity_id（四庫總目詳細考證過）
4. 諸路轉運司編勑：『陳彭年』=姓陳名彭年(北宋人961~1017) → 被誤拆為 name=彭年+dynasty=南朝陳！
   → author.name 彭年→陳彭年，dynasty 南朝陳→北宋，period nanbeichao→song；移除 entity_id=明彭年(1505~1566)
"""
import json, os

def find_work(wid):
    for root, _, files in os.walk("/workspace/Work"):
        for f in files:
            if f.startswith(wid) and f.endswith(".json") and "/collated_edition/" not in os.path.join(root, f):
                return os.path.join(root, f)
    return None

# 1. 華嚴法界境 德清
wid = "1evdidd5s2znk"
fp = find_work(wid)
with open(fp, "r", encoding="utf-8") as f:
    w1 = json.load(f)
for a in w1["authors"]:
    if a.get("name") == "德清":
        a["dynasty_basis"] = "明史藝文志：『德清《華嚴法界境》一卷...』——即憨山德清(1546~1623)，明代四大高僧之一，字澄印，號憨山，全椒人"
        if "entity_id" in a:
            del a["entity_id"]
w1["ai_note"] = w1.get("ai_note", "") + " [C1-fix: needs-review(critical) 同名異人 Entity 移除。原 entity_id=1j96hhvcrjvhe=元升(南宋1163~1217)，名字即與『德清』不符！本書作者係明憨山大師(1546~1623)。需人工查 CBDB 建立正確 Entity 並關聯]"
with open(fp, "w", encoding="utf-8") as f:
    json.dump(w1, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[FIX1] {wid} 華嚴法界境：移除元升(南宋) Entity（名字都不對！）")

# 2. 道德經注 王珪
wid = "1evgbzfgq57uo"
fp = find_work(wid)
with open(fp, "r", encoding="utf-8") as f:
    w2 = json.load(f)
for a in w2["authors"]:
    if a.get("name") == "王珪":
        a["dynasty_basis"] = "元史藝文志：『王珪道德經注』，字君璋，常熟人（元人）"
        if "entity_id" in a:
            del a["entity_id"]
w2["ai_note"] = w2.get("ai_note", "") + " [C1-fix: needs-review(critical) 同名異人 Entity 移除。原 entity_id=1j967bgl89icn=北宋王珪(1019~1085，字禹玉，華陽人，北宋宰相)，字號籍貫朝代均不符！本書作者係元王珪(字君璋，常熟人)。需人工查 CBDB 建立正確 Entity 並關聯]"
with open(fp, "w", encoding="utf-8") as f:
    json.dump(w2, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[FIX2] {wid} 道德經注：移除北宋宰相王珪 Entity（字君璋常熟 vs 字禹玉華陽）")

# 3. 蠡海集 王逵
wid = "1evkpxffmr7k0"
fp = find_work(wid)
with open(fp, "r", encoding="utf-8") as f:
    w3 = json.load(f)
for a in w3["authors"]:
    if a.get("name") == "王逵":
        a["dynasty_basis"] = "四庫全書總目提要詳考：舊本題宋王逵撰，糾正為『明黃姬水《貧士傳》載王逵錢塘人，足一跛，洪武永樂間人』——與三個宋王逵（仁宗時轉運使/天禧進士濮陽人/紹興中淄州人）均不吻合；書中引趙緣督(至元後)，必非宋人"
        if "entity_id" in a:
            del a["entity_id"]
w3["ai_note"] = w3.get("ai_note", "") + " [C1-fix: needs-review(critical) 同名異人 Entity 移除。原 entity_id=1j967bgl70k5j=北宋王逵(991~1072，真宗仁宗時官員)，四庫總目詳細考證此書作者係明初錢塘王逵(洪武永樂間)，引趙緣督說已至元後，不可能為北宋王逵。需人工查 CBDB 建立正確 Entity 並關聯]"
with open(fp, "w", encoding="utf-8") as f:
    json.dump(w3, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[FIX3] {wid} 蠡海集：移除北宋王逵 Entity（四庫總目考证明初錢塘跛腳王逵）")

# 4. 諸路轉運司編勑 陳彭年（最嚴重：name 被誤寫『彭年』，dynasty 誤『南朝陳』，period 誤 nanbeichao！）
wid = "1evgpivar79xc"
fp = find_work(wid)
with open(fp, "r", encoding="utf-8") as f:
    w4 = json.load(f)
new_authors = []
for a in w4["authors"]:
    if a.get("name") == "彭年":
        new_a = {
            "name": "陳彭年",
            "role": a.get("role", "撰"),
            "dynasty": "北宋",
            "dynasty_basis": "國史經籍志：『《諸路轉運司編勑》三十卷（陳彭年）』——『陳彭年』=姓陳名彭年(961~1017)，字永年，江西南城人，北宋真宗時大臣，重修《廣韻》、編《冊府元龜》，非『南朝陳·彭年』（將姓氏誤作朝代）"
        }
        # 原 entity_id=1j967c148wsnm=明彭年(1505~1566)，完全不对，不复制
        new_authors.append(new_a)
    else:
        new_authors.append(a)
w4["authors"] = new_authors
w4["period"] = "song"
w4["period_basis"] = "據 authors[0].dynasty『北宋』（陳彭年961~1017，北宋）"
w4["dynasty"] = "北宋"
w4["dynasty_basis"] = "author_propagation"
w4["ai_note"] = w4.get("ai_note", "") + " [C1-fix(critical): 作者姓名斷代雙重錯誤修復！原誤：name=彭年,dynasty=南朝陳,period=nanbeichao，連同 Entity=1j967c148wsnm=明彭年(1505~1566) 全錯！國史經籍志原文『陳彭年』=姓陳名彭年，即北宋陳彭年(961~1017，字永年，南城人)。→ 已修正 author.name=dynasty=period + 移除錯誤 Entity。needs-review(critical): 需人工查 CBDB 關聯正確北宋陳彭年 Entity]"
with open(fp, "w", encoding="utf-8") as f:
    json.dump(w4, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[FIX4] {wid} 諸路轉運司編勑：CRITICAL FIX『陳彭年』=姓陳名彭年(北宋)")
print(f"       原：name=彭年,dynasty=南朝陳,period=nanbeichao + Entity=明彭年(1505~1566)")
print(f"       → 已全部修正 + needs-review")

# 同步 index
changes = [("1evdidd5s2znk", w1), ("1evgbzfgq57uo", w2), ("1evkpxffmr7k0", w3), ("1evgpivar79xc", w4)]
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
