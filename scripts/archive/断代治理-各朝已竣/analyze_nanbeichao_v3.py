#!/usr/bin/env python3
"""深入分析 entity.dynasty=宋 無生卒年的可判信號。"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def iter_work_files():
    return sorted(ROOT.glob("Work/?/?/?/*.json"))


def iter_entity_files():
    return sorted(ROOT.glob("Entity/?/?/?/*.json"))


def main():
    works = {}
    for fp in iter_work_files():
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        works[d.get("id", fp.stem)] = d

    entities = {}
    for fp in iter_entity_files():
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        entities[d.get("id", fp.stem)] = d

    eid_to_works = defaultdict(list)
    for wid, w in works.items():
        for a in w.get("authors", []) or []:
            if isinstance(a, dict):
                eid = a.get("entity_id")
                if eid:
                    eid_to_works[eid].append(w)

    # ========== 1. description.text 朝代詞信號 ==========
    print("=== entity.dynasty=宋 的 description.text 朝代詞信號 ===")
    # 定義朝代詞模式
    patterns = {
        "南朝宋": [r"南朝宋", r"劉宋", r"刘宋", r"宋\（劉", r"宋\(劉"],
        "北宋": [r"北宋"],
        "南宋": [r"南宋"],
        "南唐": [r"南唐"],
        "宋末元初": [r"宋末元初", r"宋末"],
        "明": [r"明[朝代]"],
        "清": [r"清[朝代]"],
        "元": [r"元[朝代]"],
    }
    desc_signal = Counter()
    desc_samples = defaultdict(list)
    for e in entities.values():
        if e.get("dynasty") != "宋":
            continue
        desc = e.get("description", {})
        text = desc.get("text", "") if isinstance(desc, dict) else ""
        if not text:
            continue
        matched = None
        for label, pats in patterns.items():
            for pat in pats:
                if re.search(pat, text):
                    matched = label
                    break
            if matched:
                break
        if matched:
            desc_signal[matched] += 1
            if len(desc_samples[matched]) < 2:
                desc_samples[matched].append((e.get("primary_name"), text[:150]))
        else:
            desc_signal["無朝代詞"] += 1
    for k, v in desc_signal.most_common():
        print(f"  {k:20s} {v:>5}")
    print("\n  抽樣:")
    for k, samples in desc_samples.items():
        for name, text in samples:
            print(f"    [{k}] {name}: {text}")

    # ========== 2. cbdb_match 字段 ==========
    print("\n=== entity 的 external_ids 結構抽樣 ===")
    for eid, e in list(entities.items())[:5]:
        ext = e.get("external_ids", {})
        print(f"  {e.get('primary_name')}: {ext}")

    # ========== 3. 無生卒年 entity 的 Work period 信號 ==========
    print("\n=== entity.dynasty=宋 無生卒年 → 對應 Work.period 分布 ===")
    no_year_period = Counter()
    for eid, e in entities.items():
        if e.get("dynasty") != "宋":
            continue
        if e.get("birth_year") or e.get("death_year"):
            continue
        ws = eid_to_works.get(eid, [])
        if not ws:
            no_year_period["無 Work"] += 1
            continue
        ps = Counter(w.get("period") or "null" for w in ws)
        if len(ps) == 1:
            no_year_period[list(ps.keys())[0]] += 1
        else:
            no_year_period["multiple"] += 1
    for k, v in no_year_period.most_common():
        print(f"  {k:20s} {v:>5}")

    # ========== 4. 無生卒年 entity 的 Work indexed_by.source 分布 ==========
    print("\n=== entity.dynasty=宋 無生卒年 → Work indexed_by.source 分布 ===")
    src_dist = Counter()
    for eid, e in entities.items():
        if e.get("dynasty") != "宋":
            continue
        if e.get("birth_year") or e.get("death_year"):
            continue
        ws = eid_to_works.get(eid, [])
        for w in ws:
            for item in w.get("indexed_by", []) or []:
                if isinstance(item, dict):
                    src_dist[item.get("source", "")] += 1
    for k, v in src_dist.most_common(15):
        print(f"  {k:30s} {v:>5}")

    # ========== 5. 看 author.dynasty=晉 的 entity 為何沒被規範 ==========
    print("\n=== author.dynasty=晉 的 entity.dynasty 分布 ===")
    jin_entity_dyn = Counter()
    for w in works.values():
        for a in w.get("authors", []) or []:
            if isinstance(a, dict) and a.get("dynasty") == "晉":
                eid = a.get("entity_id")
                if eid:
                    e = entities.get(eid)
                    if e:
                        jin_entity_dyn[e.get("dynasty") or "null"] += 1
    for k, v in jin_entity_dyn.most_common():
        print(f"  entity.dynasty={k:20s} {v:>5}")

    # ========== 6. entity.dynasty=晉 的生卒年信號 ==========
    print("\n=== entity.dynasty=晉 的生卒年信號 ===")
    jin_year = Counter()
    for e in entities.values():
        if e.get("dynasty") != "晉":
            continue
        by = e.get("birth_year")
        dy = e.get("death_year")
        years = [y for y in [by, dy] if y is not None]
        if not years:
            jin_year["無生卒年"] += 1
        elif max(years) < 265:
            jin_year["<265 (三國或更早)"] += 1
        elif min(years) <= 316:
            jin_year["265-316 (西晉)"] += 1
        elif min(years) < 420:
            jin_year["317-419 (東晉)"] += 1
        else:
            jin_year[">=420 (南北朝或更晚)"] += 1
    for k, v in jin_year.most_common():
        print(f"  {k:30s} {v:>5}")

    # ========== 7. author.dynasty=梁 的 entity 分布 ==========
    print("\n=== author.dynasty=梁 的 entity.dynasty 分布 ===")
    liang_entity_dyn = Counter()
    for w in works.values():
        for a in w.get("authors", []) or []:
            if isinstance(a, dict) and a.get("dynasty") == "梁":
                eid = a.get("entity_id")
                if eid:
                    e = entities.get(eid)
                    if e:
                        liang_entity_dyn[e.get("dynasty") or "null"] += 1
    for k, v in liang_entity_dyn.most_common():
        print(f"  entity.dynasty={k:20s} {v:>5}")

    # ========== 8. entity.dynasty=梁 的生卒年信號 ==========
    print("\n=== entity.dynasty=梁 的生卒年信號 ===")
    liang_year = Counter()
    for e in entities.values():
        if e.get("dynasty") != "梁":
            continue
        by = e.get("birth_year")
        dy = e.get("death_year")
        years = [y for y in [by, dy] if y is not None]
        if not years:
            liang_year["無生卒年"] += 1
        elif max(years) < 502:
            liang_year["<502 (南朝梁前)"] += 1
        elif min(years) <= 557:
            liang_year["502-557 (南朝梁)"] += 1
        elif min(years) < 907:
            liang_year["558-906 (非梁)"] += 1
        elif min(years) <= 923:
            liang_year["907-923 (後梁)"] += 1
        else:
            liang_year[">=924 (非梁)"] += 1
    for k, v in liang_year.most_common():
        print(f"  {k:30s} {v:>5}")

    # ========== 9. entity.dynasty=周 的生卒年信號 ==========
    print("\n=== entity.dynasty=周 的生卒年信號 ===")
    zhou_year = Counter()
    for e in entities.values():
        if e.get("dynasty") != "周":
            continue
        by = e.get("birth_year")
        dy = e.get("death_year")
        years = [y for y in [by, dy] if y is not None]
        if not years:
            zhou_year["無生卒年"] += 1
        elif max(years) < -256:
            zhou_year["<-256 (先秦周)"] += 1
        elif min(years) <= 581:
            zhou_year["557-581 (北周)"] += 1
        elif min(years) <= 960:
            zhou_year["951-960 (後周)"] += 1
        else:
            zhou_year["其他"] += 1
    for k, v in zhou_year.most_common():
        print(f"  {k:30s} {v:>5}")

    # ========== 10. entity.dynasty=齊 ==========
    print("\n=== entity.dynasty=齊 分析 ===")
    for e in entities.values():
        if e.get("dynasty") == "齊":
            by = e.get("birth_year")
            dy = e.get("death_year")
            print(f"  {e.get('primary_name')} ({by}-{dy})")


if __name__ == "__main__":
    main()
