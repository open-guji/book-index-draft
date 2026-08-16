#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""survey_cbdb_coverage.py — 本庫作者 × CBDB 匹配普查（只讀不改）。

CBDB 側資料不在本庫，需先備妥人物名冊 CSV：

    git clone --depth 1 https://github.com/cbdb-project/biogref_CBDB
    python3 scripts/survey_cbdb_coverage.py --cbdb biogref_CBDB/data.csv

該名冊 660,628 人，欄位 person_id / person_name / gender / born_year /
died_year / dynasty / jiguan（CC BY-NC-SA）。

**該名冊不含著作資料**，故本腳本只能回答「作者匹配率」，不能回答
「雙方作品孰多孰寡」——後者需 CBDB 的 BIOG_TEXT_DATA／TEXT_CODES 表，
須自 Harvard 或 HuggingFace 取完整 SQLite（官方 GitHub 鏡像 cbdb_sqlite
只放 Git LFS 指標，匿名通道取不到內容）。

朝代對映的四個坑（皆經抽樣證實，改動前務必重驗）：
  · CBDB「吳」是十國吳（楊行密、李德誠），不是三國吳
  · CBDB「周」是武周（東方虬、牛希濟等唐人），不是西周
  · CBDB「漢前」是先秦（孔丘、管仲、顏回），不是秦漢
  · CBDB「後漢」混指東漢（寇恂、丁邯）與五代後漢（劉知遠），須作兩義處理
未校正前這四處共製造 4 條假錯配。
"""
import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

# ── CBDB 朝代 → 本庫 period ──
CBDB_DY2PERIOD = {
    "漢前": "pre-qin",
    "贏秦": "qin-han", "秦漢": "qin-han", "西漢": "qin-han",
    "東漢": "qin-han", "新": "qin-han",
    "三國": "three-kingdoms", "三國魏": "three-kingdoms",
    "三國吳": "three-kingdoms", "三國蜀": "three-kingdoms",
    "晉": "jin", "西晉": "jin", "東晉": "jin",
    "前秦": "jin", "後秦": "jin", "西秦": "jin", "前燕": "jin", "後燕": "jin",
    "南燕": "jin", "西燕": "jin", "北燕": "jin", "前涼": "jin", "後涼": "jin",
    "西涼": "jin", "北涼": "jin", "前趙": "jin", "後趙": "jin", "代": "jin",
    "南北朝": "nanbeichao", "北魏": "nanbeichao", "東魏": "nanbeichao",
    "西魏": "nanbeichao", "北齊": "nanbeichao", "北周": "nanbeichao",
    "宋(劉)": "nanbeichao", "南齊": "nanbeichao", "南梁": "nanbeichao",
    "東梁": "nanbeichao", "西梁": "nanbeichao", "陳": "nanbeichao",
    "隋": "sui-tang", "唐": "sui-tang", "鄭（王世充）": "sui-tang", "周": "sui-tang",
    "五代": "five-dynasties", "後梁": "five-dynasties", "後唐": "five-dynasties",
    "後晉": "five-dynasties", "後周": "five-dynasties", "吳": "five-dynasties",
    "南唐": "five-dynasties", "前蜀": "five-dynasties", "後蜀": "five-dynasties",
    "吳越": "five-dynasties", "閩國": "five-dynasties", "南漢": "five-dynasties",
    "北漢": "five-dynasties", "南平": "five-dynasties", "吳(楊)": "five-dynasties",
    "楚(馬)": "five-dynasties",
    "宋": "song",
    "遼": "liao-jin-yuan", "西遼": "liao-jin-yuan", "金": "liao-jin-yuan",
    "元": "liao-jin-yuan", "西夏": "liao-jin-yuan", "偽齊": "liao-jin-yuan",
    "明": "ming", "北元": "ming",
    "清": "qing",
    "中華民國": "modern", "中華人民共和國": "modern",
    "朝鮮": "_korea", "韓國": "_korea", "高麗": "_korea", "新羅": "_korea",
}
# 一名兩義者
AMBIG = {"後漢": {"qin-han", "five-dynasties"}}

PERIOD_ORDER = ["pre-qin", "qin-han", "three-kingdoms", "jin", "nanbeichao",
                "sui-tang", "five-dynasties", "song", "liao-jin-yuan",
                "ming", "qing", "modern"]
PIDX = {p: i for i, p in enumerate(PERIOD_ORDER)}
PERIOD_CN = {"pre-qin": "先秦", "qin-han": "秦漢", "three-kingdoms": "三國",
             "jin": "晉", "nanbeichao": "南北朝", "sui-tang": "隋唐",
             "five-dynasties": "五代", "song": "宋", "liao-jin-yuan": "遼金元",
             "ming": "明", "qing": "清", "modern": "近現代"}

CLS = ["姓名不見於CBDB", "同名但無同期者", "同期同名唯一", "同期同名多人"]


def cps(dy):
    """該 CBDB 朝代相容的 period 集合。"""
    if dy in AMBIG:
        return AMBIG[dy]
    v = CBDB_DY2PERIOD.get(dy)
    return {v} if v else set()


def norm_name(s):
    return re.sub(r"\s+", "", s).strip() if s else ""


def has_radical_block(s):
    """姓名混入 CJK 部首補充區／康熙部首——字形同而碼位異，比對必落空。"""
    return any(0x2E80 <= ord(c) <= 0x2FFF for c in (s or ""))


def load_cbdb(path):
    by_name = defaultdict(list)
    by_id = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            nm = norm_name(r["person_name"])
            try:
                pid = int(r["person_id"])
            except ValueError:
                continue
            def yr(v):
                return int(v) if v.lstrip("-").isdigit() else 0
            rec = (pid, r["dynasty"], yr(r["born_year"]), yr(r["died_year"]))
            by_id[pid] = (nm, rec[1], rec[2], rec[3])
            if nm:
                by_name[nm].append(rec)
    return by_name, by_id


def scan_repo(root):
    """單次全庫掃描，抽出 Entity 與 Work 作者欄。"""
    work_title = {}
    for f in os.listdir(root / "index" / "works"):
        d = json.loads((root / "index" / "works" / f).read_text(encoding="utf-8"))
        for wid, v in d.items():
            work_title[wid] = v.get("title")

    ents = []
    for dirpath, _, files in os.walk(root / "Entity"):
        for fn in files:
            if not fn.endswith(".json"):
                continue
            try:
                d = json.loads((Path(dirpath) / fn).read_text(encoding="utf-8"))
            except Exception:
                continue
            if d.get("type") != "entity":
                continue
            ext = d.get("external_ids") or {}
            wids = [w.get("work_id") for w in (d.get("works") or []) if w.get("work_id")]
            ents.append({
                "id": d.get("id"), "name": d.get("primary_name"),
                "alt": [(a.get("name") if isinstance(a, dict) else a)
                        for a in (d.get("alt_names") or [])
                        if (a.get("name") if isinstance(a, dict) else a)],
                "dynasty": d.get("dynasty"), "period": d.get("period"),
                "birth": d.get("birth_year"), "death": d.get("death_year"),
                "wids": wids,
                "wtitles": [work_title[w] for w in wids if work_title.get(w)],
                "cbdb_id": ext.get("cbdb_id"),
                "cbdb_match": ext.get("cbdb_match"),
                "cbdb_source": ext.get("cbdb_source") or "",
            })

    slots = []
    for dirpath, _, files in os.walk(root / "Work"):
        p = Path(dirpath)
        # 只取 Work/x/y/z/ 下的主檔，跳過 collated_edition / fragments
        if p.parent.parent.parent.name != "Work":
            continue
        for fn in files:
            if not fn.endswith(".json"):
                continue
            try:
                d = json.loads((p / fn).read_text(encoding="utf-8"))
            except Exception:
                continue
            if d.get("type") != "work":
                continue
            for a in (d.get("authors") or []):
                slots.append({"name": a.get("name"), "entity_id": a.get("entity_id"),
                              "wperiod": d.get("period")})
    return ents, slots


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--cbdb", required=True, help="biogref_CBDB/data.csv 之路徑")
    args = ap.parse_args()
    root = Path(args.root)

    by_name, by_id = load_cbdb(args.cbdb)
    print(f"CBDB 名冊 {len(by_id)} 人，相異姓名 {len(by_name)}")
    ents, slots = scan_repo(root)
    print(f"本庫 Entity {len(ents)}，Work 作者著錄槽 {len(slots)}\n")

    # ── A. 既有 cbdb_id 體檢 ──
    print("=" * 64, "\nA. 既有 cbdb_id 體檢\n", "=" * 64, sep="")
    has_id = [e for e in ents if e["cbdb_id"]]
    print(f"已標 cbdb_id {len(has_id)}/{len(ents)} = {len(has_id)/len(ents)*100:.1f}%")
    chk, far = Counter(), []
    for e in has_id:
        try:
            rec = by_id.get(int(e["cbdb_id"]))
        except (TypeError, ValueError):
            chk["id 非數字"] += 1
            continue
        if not rec:
            chk["id 不在現行名冊"] += 1
            continue
        cnm, cdy = rec[0], rec[1]
        ok_name = norm_name(e["name"]) == cnm or cnm in [norm_name(a) for a in e["alt"]]
        cset = cps(cdy)
        ok_period = (e["period"] is None or not cset or e["period"] in cset)
        chk[f"姓名{'合' if ok_name else '不合'}／期{'合' if ok_period else '不合'}"] += 1
        if ok_name and not ok_period and e["period"] in PIDX:
            d = [abs(PIDX[e["period"]] - PIDX[x]) for x in cset if x in PIDX]
            if d and min(d) >= 2:      # 鄰期是改朝換代之際的正常差異，不算
                far.append((e, rec, min(d)))
    for k, v in chk.most_common():
        print(f"  {k}: {v} ({v/len(has_id)*100:.1f}%)")

    print(f"\n  隔 2 期以上的疑似錯配 {len(far)} 條：")
    fixable = 0
    for e, rec, d in sorted(far, key=lambda x: -x[2]):
        right = [x for x in by_name.get(norm_name(e["name"]), [])
                 if e["period"] in cps(x[1])]
        if right:
            fixable += 1
            tag = f"★可改正 → {[x[0] for x in right][:3]}"
        else:
            tag = "CBDB 無同期同名者"
        print(f"    {e['name']:<8} 本庫{str(e['dynasty']):<5} 作品{len(e['wids']):<3} "
              f"現配 {e['cbdb_id']}({rec[1]}) 隔{d}期  {tag}")
    print(f"  小計：可改正 {fixable}，CBDB 確無其人 {len(far)-fixable}")

    # ── B. 獨立重配 ──
    print("\n" + "=" * 64, "\nB. 獨立重配（不看既有標記）\n", "=" * 64, sep="")
    by_p, overall, resolvable = defaultdict(Counter), Counter(), Counter()
    unclaimed = defaultdict(list)
    for e in ents:
        nm, ep = norm_name(e["name"]), e["period"]
        cands = by_name.get(nm, [])
        if not cands:
            c = "姓名不見於CBDB"
        else:
            same = cands if ep is None else [x for x in cands if ep in cps(x[1])]
            if not same:
                c = "同名但無同期者"
            elif len(same) == 1:
                c = "同期同名唯一"
                if not e["cbdb_id"]:
                    unclaimed[ep].append(e)
            else:
                c = "同期同名多人"
                if e["birth"] or e["death"]:
                    hit = [x for x in same
                           if (e["birth"] and x[2] == e["birth"])
                           or (e["death"] and x[3] == e["death"])]
                    resolvable["生卒年可定一人" if len(hit) == 1 else "生卒年仍不能定"] += 1
                else:
                    resolvable["本庫無生卒年"] += 1
        overall[c] += 1
        by_p[ep][c] += 1

    for c in CLS:
        print(f"  {c}: {overall[c]} ({overall[c]/len(ents)*100:.1f}%)")
    print("\n分期：")
    print(f"{'期':<8}{'人數':>6}  " + "".join(f"{c:>15}" for c in CLS))
    for p in PERIOD_ORDER + [None]:
        cc = by_p.get(p)
        if not cc:
            continue
        t = sum(cc.values())
        row = f"{PERIOD_CN.get(p,'未標期'):<8}{t:>6}  "
        for c in CLS:
            row += f"{cc[c]:>7}({cc[c]/t*100:>4.0f}%)"
        print(row)
    print("\n同名多人的化解：", dict(resolvable))
    nu = sum(len(v) for v in unclaimed.values())
    print(f"\n未認領的高置信匹配（同期同名唯一而本庫無 cbdb_id）：{nu}")
    for p in PERIOD_ORDER + [None]:
        if unclaimed.get(p):
            names = "、".join(e["name"] for e in unclaimed[p][:5])
            print(f"    {PERIOD_CN.get(p,'未標期'):<6} {len(unclaimed[p]):>4}   {names}")

    # ── C. work_recall 分母判定 ──
    print("\n" + "=" * 64, "\nC. work_recall 分母判定\n", "=" * 64, sep="")
    pat = re.compile(r"work_recall_([\d.]+)")
    mid = []
    for e in ents:
        m = pat.search(e["cbdb_source"])
        if not m:
            continue
        try:
            r = float(m.group(1))
        except ValueError:
            continue
        if 0.001 < r < 0.999:      # 0 與 1 對任何分母皆成立，無判別力
            mid.append((e, r))

    def feasible(r, n):
        return n > 0 and any(abs(k / n - r) <= 0.0051 for k in range(n + 1))

    print(f"0<recall<1 者 {len(mid)} 筆：")
    for lbl, off in [("我方作品數 n", 0), ("n+1（對照）", 1), ("n+2（對照）", 2)]:
        ok = tot = 0
        for e, r in mid:
            n = len(e["wids"]) + off
            if n <= 0:
                continue
            tot += 1
            ok += feasible(r, n)
        print(f"  分母={lbl}: {ok}/{tot} = {ok/tot*100:.1f}% 可行")
    print("  分母若非我方作品數，則此欄量的是『CBDB 有的我方有多少』，"
          "不可當作我方作品的完整度使用。")

    # ── D. Work 作者著錄槽貫通率 ──
    print("\n" + "=" * 64, "\nD. Work 作者著錄槽 → Entity → CBDB\n", "=" * 64, sep="")
    ent_by_id = {e["id"]: e for e in ents}
    sc = Counter()
    for s in slots:
        eid = s.get("entity_id")
        if not eid:
            sc["未繫 entity"] += 1
        elif eid not in ent_by_id:
            sc["繫了幽靈 entity"] += 1
        elif ent_by_id[eid]["cbdb_id"]:
            sc["繫 entity 且有 cbdb_id"] += 1
        else:
            sc["繫 entity 但無 cbdb_id"] += 1
    for k, v in sc.most_common():
        print(f"  {k}: {v} ({v/len(slots)*100:.1f}%)")

    # ── E. 髒記錄 ──
    print("\n" + "=" * 64, "\nE. 順帶掃出的髒記錄\n", "=" * 64, sep="")
    # 兩類非人名：無撰人之謂（佚名／敕撰）、官銜合著之辭黏連（…等奉敕）
    dirty = [e for e in ents if e["name"]
             and re.search(r"[<>]|待刪|待删|闕名|不著撰人|佚名|奉敕|敕撰", e["name"])]
    nw = sum(len(e["wids"]) for e in dirty)
    print(f"  primary_name 非人名者：{len(dirty)} 條，掛作品 {nw} 部")
    for e in sorted(dirty, key=lambda x: -len(x["wids"]))[:10]:
        print(f"    {e['name']!r} 作品{len(e['wids'])}")
    print("    ↑「…等奉敕」是官銜／合著之辭黏連，應剝為個人"
          "（保和殿大學士張廷玉等奉敕 → 張廷玉）；"
          "「佚名」「敕撰」是『無撰人』之謂，本不該立為 Entity。")
    single = [e for e in ents if e["name"] and len(e["name"].strip()) == 1]
    print(f"  primary_name 只有一字（殘名嫌疑）：{len(single)}  "
          f"{'、'.join(e['name'] for e in single[:12])}")
    rad = [e for e in ents if has_radical_block(e["name"])]
    print(f"  姓名含部首補充區／表意描述符（比對必落空）：{len(rad)}  "
          f"{'、'.join(e['name'] for e in rad[:6])}")


if __name__ == "__main__":
    main()
