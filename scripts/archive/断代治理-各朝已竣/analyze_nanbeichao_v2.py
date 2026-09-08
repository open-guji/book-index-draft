#!/usr/bin/env python3
"""南北朝拆分前的精細分析：每個歧義值的可判定信號分布。"""
from __future__ import annotations

import json
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

    # 建立 entity_id -> entity 對應
    eid_to_entity = entities

    # ========== 對每個歧義 dynasty 值，分析其 Work 的 period 分布 ==========
    # 這能看出 author.dynasty=X 的 Work 主要落在哪個 period
    print("=== author.dynasty=X 的 Work.period 分布 ===")
    for target in ["宋", "魏", "梁", "周", "齊", "晉", "蜀", "吳", "陳"]:
        period_dist = Counter()
        author_count = 0
        author_with_eid = 0
        author_eid_resolved = 0  # entity_id 對應的 entity 已有規範 dynasty
        for w in works.values():
            for a in w.get("authors", []) or []:
                if isinstance(a, dict) and a.get("dynasty") == target:
                    author_count += 1
                    period_dist[w.get("period") or "null"] += 1
                    eid = a.get("entity_id")
                    if eid:
                        author_with_eid += 1
                        e = eid_to_entity.get(eid)
                        if e and e.get("dynasty") not in (target, None):
                            author_eid_resolved += 1
        print(f"\n  author.dynasty={target} (總 {author_count}, 有 entity_id {author_with_eid}, entity 已規範 {author_eid_resolved})")
        for k, v in period_dist.most_common(8):
            print(f"    period={k:20s} {v:>5}")

    # ========== author.dynasty=宋 但 entity 已規範 → 可直接傳播 ==========
    print("\n=== author.dynasty=宋 但其 entity 已規範 → 可傳播的統計 ===")
    transferable = Counter()
    for w in works.values():
        per = w.get("period")
        for a in w.get("authors", []) or []:
            if isinstance(a, dict) and a.get("dynasty") == "宋":
                eid = a.get("entity_id")
                if eid:
                    e = eid_to_entity.get(eid)
                    if e:
                        edyn = e.get("dynasty")
                        if edyn not in ("宋", None):
                            transferable[f"author.宋→{edyn} (period={per})"] += 1
    for k, v in transferable.most_common(20):
        print(f"  {k:50s} {v:>5}")
    print(f"  合計可傳播: {sum(transferable.values())}")

    # ========== 看 entity.dynasty=宋 的 entity 對應的 Work 之 period 分布 ==========
    print("\n=== entity.dynasty=宋 的 entity 對應 Work.period 分布 ===")
    # 反向：entity_id -> works
    eid_to_works = defaultdict(list)
    for wid, w in works.items():
        for a in w.get("authors", []) or []:
            if isinstance(a, dict):
                eid = a.get("entity_id")
                if eid:
                    eid_to_works[eid].append(w)
    period_dist = Counter()
    no_work = 0
    for eid, e in entities.items():
        if e.get("dynasty") != "宋":
            continue
        ws = eid_to_works.get(eid, [])
        if not ws:
            no_work += 1
            continue
        # 取這些 work 的 period 分布
        ps = Counter(w.get("period") or "null" for w in ws)
        # 如果只有一個 period，就用它
        if len(ps) == 1:
            period_dist[list(ps.keys())[0]] += 1
        else:
            period_dist["multiple"] += 1
    print(f"  無對應 Work 的 entity: {no_work}")
    for k, v in period_dist.most_common():
        print(f"    period={k:20s} {v:>5}")

    # ========== 著錄志上限分析：dynasty=宋 的 Work 是否見於隋志 ==========
    print("\n=== author.dynasty=宋 的 Work 是否見於隋志（隋志上限 = 南朝宋）===")
    # 如果 Work 被《隋書經籍志》著錄，那麼其作者只能是唐以前的人
    # 所以 author.dynasty=宋 + 見於隋志 → 必是南朝宋
    suizhi_count = 0
    suizhi_song_works = 0
    for w in works.values():
        has_sui = False
        for item in w.get("indexed_by", []) or []:
            if isinstance(item, dict) and item.get("source") == "隋書經籍志":
                has_sui = True
                break
        if not has_sui:
            continue
        suizhi_song_works += 1
        for a in w.get("authors", []) or []:
            if isinstance(a, dict) and a.get("dynasty") == "宋":
                suizhi_count += 1
    print(f"  見於隋志的 Work 總數: {suizhi_song_works}")
    print(f"  其中 author.dynasty=宋 的數量: {suizhi_count}")
    # 這個信號很強：見於隋志的 dynasty=宋 必是南朝宋（隋志成於唐初，趙宋之書不可能入）

    # ========== 看其他志的分布 ==========
    print("\n=== author.dynasty=宋 的 Work 之 indexed_by.source 分布 ===")
    source_dist = Counter()
    for w in works.values():
        for a in w.get("authors", []) or []:
            if isinstance(a, dict) and a.get("dynasty") == "宋":
                for item in w.get("indexed_by", []) or []:
                    if isinstance(item, dict):
                        source_dist[item.get("source", "")] += 1
                break  # 一個 work 只計一次
    for k, v in source_dist.most_common(20):
        print(f"    {k:30s} {v:>5}")

    # ========== 生卒年信號：dynasty=宋 entity 的 birth/death 年份分布 ==========
    print("\n=== entity.dynasty=宋 的生卒年信號 ===")
    sig = Counter()
    for e in entities.values():
        if e.get("dynasty") != "宋":
            continue
        by = e.get("birth_year")
        dy = e.get("death_year")
        years = [y for y in [by, dy] if y is not None]
        if not years:
            sig["無生卒年"] += 1
        elif max(years) < 420:
            sig["<420 (南朝宋前)"] += 1
        elif min(years) <= 479:
            sig["420-479 (南朝宋)"] += 1
        elif min(years) < 960:
            sig["480-959 (五代或更晚但不可能是南北宋)"] += 1
        elif min(years) < 1127:
            sig["960-1126 (北宋)"] += 1
        elif min(years) < 1279:
            sig["1127-1279 (南宋)"] += 1
        else:
            sig[">=1279 (元以後)"] += 1
    for k, v in sig.most_common():
        print(f"    {k:40s} {v:>5}")

    # ========== entity 有 cbdb_id 但無生卒年：嘗試從其他途徑 ==========
    print("\n=== entity.dynasty=宋 且有 cbdb_id 的分析 ===")
    cbdb_song = 0
    cbdb_song_no_year = 0
    for e in entities.values():
        if e.get("dynasty") != "宋":
            continue
        ext = e.get("external_ids", {})
        cbdb_id = ext.get("cbdb_id") if isinstance(ext, dict) else None
        if not cbdb_id:
            continue
        cbdb_song += 1
        if e.get("birth_year") is None and e.get("death_year") is None:
            cbdb_song_no_year += 1
    print(f"  有 cbdb_id: {cbdb_song}")
    print(f"  有 cbdb_id 但無生卒年: {cbdb_song_no_year}")
    # 這些可以從 CBDB 數據庫查 c_dy，但我們沒有 cbdb 表
    # 可以通過 entity 的 cbdb_match 字段看是否有信號

    # ========== 看 entity.description.text 是否有朝代線索 ==========
    print("\n=== entity.dynasty=宋 的 description.text 抽樣（前 5 個）===")
    sample_count = 0
    for eid, e in entities.items():
        if e.get("dynasty") != "宋":
            continue
        desc = e.get("description", {})
        text = desc.get("text", "") if isinstance(desc, dict) else ""
        if text and len(text) > 20:
            print(f"  [{e.get('primary_name')}] {text[:200]}")
            sample_count += 1
            if sample_count >= 5:
                break

    # ========== 看 author.dynasty=宋 的 Work 之 title 是否有朝代線索 ==========
    print("\n=== author.dynasty=宋 的 Work.title 抽樣（看是否有朝代詞）===")
    # 抽 20 個無生卒年的 entity 對應的 work
    sample = 0
    for eid, e in entities.items():
        if e.get("dynasty") != "宋":
            continue
        if e.get("birth_year") or e.get("death_year"):
            continue
        ws = eid_to_works.get(eid, [])
        if not ws:
            continue
        for w in ws[:1]:
            print(f"  entity={e.get('primary_name')} | work={w.get('title')} | period={w.get('period')}")
        sample += 1
        if sample >= 20:
            break


if __name__ == "__main__":
    main()
