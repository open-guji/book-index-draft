#!/usr/bin/env python3
"""
C2 batch14：Entity + 關聯 Work 雙向修復
1. 鄺露(Entity 1j96hjwlxcpk6)：dynasty 清→明（CBDB dy=20=明；1604-1650 明萬曆生，順治七年抗清殉節，公認明人）
   → 同步 Entity.period qing→ming；同步所有關聯 Work 的 author.dynasty (若为清改明)、index/entities、index/works

2. 趙汸 Work(東山集 1evdidf017abk)：author.dynasty 明→元（Entity=元趙汸正確；四庫標元趙汸，主要活動在元，卒洪武二年僅1369一年）
   → 同步 Work.period ming→liao-jin-yuan；同步 index/works
"""
import json, os

# ========== 1. 鄺露 Entity ==========
print("=" * 60)
print("[ENTITY FIX 1] 鄺露(1j96hjwlxcpk6): dynasty 清→明")
eid = "1j96hjwlxcpk6"
efp = None
for root, _, files in os.walk("/workspace/Entity"):
    for f in files:
        if f.startswith(eid) and f.endswith(".json"):
            efp = os.path.join(root, f)
            break
    if efp: break
with open(efp, "r", encoding="utf-8") as f:
    e = json.load(f)
e["dynasty"] = "明"
e["period"] = "ming"
e["period_basis"] = "據 dynasty『明』自動歸併（修正：CBDB來源 cbdb_dy=20=明；1604萬曆三十二年生，1650順治七年清破廣州抱琴殉節，抗清明遺民，學界公認明人）"
# 保存外部信息
e["external_ids"]["cbdb_match"] = e.get("external_ids", {}).get("cbdb_match", "") + " ; dynasty_fix: 清→明 per CBDB dy=20"
with open(efp, "w", encoding="utf-8") as f:
    json.dump(e, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"  Entity dynasty 清→明, period qing→ming (CBDB dy=20)")
kuanglu_works = [x["work_id"] for x in e.get("works", [])]

# 同步 index/entities
for fn in sorted(os.listdir("/workspace/index/entities")):
    if not fn.endswith(".json"): continue
    p = f"/workspace/index/entities/{fn}"
    with open(p, "r", encoding="utf-8") as f:
        idx = json.load(f)
    if eid in idx:
        ee = idx[eid]
        if ee.get("dynasty") != "明" or ee.get("period") != "ming":
            ee["dynasty"] = "明"
            ee["period"] = "ming"
            with open(p, "w", encoding="utf-8") as f2:
                json.dump(idx, f2, ensure_ascii=False, indent=2)
                f2.write("\n")
            print(f"  [SYNC] index/entities/{fn}: dynasty→明, period→ming")
        break

# 同步鄺露的關聯 Work（赤雅 1ev3basigfo5c 等）
for wid in kuanglu_works:
    for root, _, files in os.walk("/workspace/Work"):
        found = False
        for f in files:
            if f.startswith(wid) and f.endswith(".json") and "/collated_edition/" not in os.path.join(root, f):
                wfp = os.path.join(root, f)
                with open(wfp, "r", encoding="utf-8") as fh:
                    w = json.load(fh)
                dirty = False
                for a in w.get("authors", []):
                    if a.get("name") == "鄺露":
                        if a.get("dynasty") != "明" or a.get("entity_id") != eid:
                            a["dynasty"] = "明"
                            if not a.get("dynasty_basis"):
                                a["dynasty_basis"] = "Entity 1j96hjwlxcpk6=鄺露(1604~1650)，CBDB dy=20=明，抗清殉節明人"
                            a["entity_id"] = eid
                            dirty = True
                if w.get("period") == "qing" or w.get("dynasty") == "清":
                    # 重新计算 period/dynasty 基准
                    if any(a.get("dynasty") == "明" for a in w.get("authors", [])):
                        w["period"] = "ming"
                        w["period_basis"] = "據 authors[].dynasty『明』"
                        w["dynasty"] = "明"
                        w["dynasty_basis"] = "author_propagation (鄺露修正為明人)"
                        dirty = True
                if dirty:
                    with open(wfp, "w", encoding="utf-8") as fh2:
                        json.dump(w, fh2, ensure_ascii=False, indent=2)
                        fh2.write("\n")
                    print(f"  [SYNC Work] {wid} {w.get('title','')}: author.dynasty→明, Work.period/dynasty→明")
                found = True
                break
        if found: break

# ========== 2. 趙汸 Work 東山集 ==========
print()
print("[WORK FIX 2] 東山集(1evdidf017abk): author.dynasty 明→元")
wid = "1evdidf017abk"
wfp = None
for root, _, files in os.walk("/workspace/Work"):
    for f in files:
        if f.startswith(wid) and f.endswith(".json") and "/collated_edition/" not in os.path.join(root, f):
            wfp = os.path.join(root, f)
            break
    if wfp: break
with open(wfp, "r", encoding="utf-8") as f:
    w = json.load(f)
for a in w.get("authors", []):
    if a.get("name") == "趙汸":
        a["dynasty"] = "元"
        a["dynasty_basis"] = "Entity 1j967afjbhiwy=趙汸(1319~1369)，字子常號東山，元史藝文志+四庫總目均標元趙汸（主要活動在元，卒洪武二年僅一年）；四庫中著作多入元"
w["period"] = "liao-jin-yuan"
w["period_basis"] = "據 authors[0].dynasty『元』"
w["dynasty"] = "元"
w["dynasty_basis"] = "author_propagation"
w["ai_note"] = w.get("ai_note", "") + " [C2-fix: author.dynasty 明→元，period ming→liao-jin-yuan。趙汸(1319-1369)元延祐六年生，元至正時成名，明洪武二年僅卒一年，學界歸元人]"
with open(wfp, "w", encoding="utf-8") as f:
    json.dump(w, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"  東山集 {wid}: author.dynasty→元, period→liao-jin-yuan, dynasty→元")

# 同步 index/works (鄺露關聯 Works + 趙汸東山集)
print()
kuanglu_works_all = set(kuanglu_works) | {"1ev3basigfo5c"}  # ensure 赤雅 included
all_work_ids = kuanglu_works_all | {"1evdidf017abk"}
for fn in sorted(os.listdir("/workspace/index/works")):
    if not fn.endswith(".json"): continue
    p = f"/workspace/index/works/{fn}"
    with open(p, "r", encoding="utf-8") as f:
        idx = json.load(f)
    dirty = False
    for wid in all_work_ids:
        if wid in idx:
            e = idx[wid]
            # 从实际 Work 取最新值
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
        print(f"[SYNC] index/works/{fn}")
