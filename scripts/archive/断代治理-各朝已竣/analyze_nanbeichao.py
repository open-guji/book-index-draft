#!/usr/bin/env python3
"""分析 period=nanbeichao 的 dynasty 分布，找出南北朝拆分需要處理的歧義值。"""
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

    print(f"Work 總數: {len(works)}")
    print(f"Entity 總數: {len(entities)}")

    # 1. Work.period 分布
    print("\n=== Work.period 分布 ===")
    work_period = Counter()
    for w in works.values():
        work_period[w.get("period") or "null"] += 1
    for k, v in work_period.most_common():
        print(f"  {k:20s} {v:>6}")

    # 2. period=nanbeichao 下 dynasty 分布
    print("\n=== period=nanbeichao 下 dynasty 分布 (Work) ===")
    nb_dyn = Counter()
    for w in works.values():
        if w.get("period") == "nanbeichao":
            nb_dyn[w.get("dynasty") or "null"] += 1
    for k, v in nb_dyn.most_common():
        print(f"  {k:20s} {v:>6}")

    # 3. Work.author[].dynasty 分布（所有 Work，但篩選 nanbeichao 相關 dynasty 值）
    # 看哪些 dynasty 值在 authors 中出現
    print("\n=== Work.author.dynasty 分布 (整庫) ===")
    adyn = Counter()
    for w in works.values():
        for a in w.get("authors", []) or []:
            if isinstance(a, dict):
                adyn[a.get("dynasty") or "null"] += 1
    for k, v in adyn.most_common(40):
        print(f"  {k:20s} {v:>6}")

    # 4. Entity.dynasty 分布
    print("\n=== Entity.dynasty 分布 ===")
    edyn = Counter()
    for e in entities.values():
        edyn[e.get("dynasty") or "null"] += 1
    for k, v in edyn.most_common(40):
        print(f"  {k:20s} {v:>6}")

    # 5. 關鍵歧義值深入分析
    # 對每個歧義值，看 entity 中 cbdb_id 對應的 c_dy 分布
    # 我們沒有 cbdb c_dy 表，但可以看 entity 中的 cbdb_id 和 entity 自帶 dynasty
    # 以及 birth_year/death_year
    print("\n=== 歧義值分析：宋 (Entity) ===")
    # entity cbdb_id 可能對應 c_dy, 我們看 cbdb_dy 是否有信號
    song_entities = []
    for eid, e in entities.items():
        if e.get("dynasty") == "宋":
            song_entities.append(e)
    print(f"  dynasty=宋 entity 總數: {len(song_entities)}")
    # 看 cbdb_id, birth/death year 分布
    cbdb_present = sum(1 for e in song_entities if e.get("external_ids", {}).get("cbdb_id"))
    print(f"  有 cbdb_id: {cbdb_present}")
    by_dist = Counter()
    dy_dist = Counter()
    for e in song_entities:
        by = e.get("birth_year")
        dy = e.get("death_year")
        by_dist[by] += 1
        dy_dist[dy] += 1
    # 按 birth_year 範圍判斷
    nanbei = 0
    song_beisong = 0
    song_nansong = 0
    unknown = 0
    for e in song_entities:
        by = e.get("birth_year")
        dy = e.get("death_year")
        y = by or dy
        if y is None:
            unknown += 1
        elif y < 420:
            nanbei += 1
        elif y < 960:
            nanbei += 1  # 可能是南朝宋(420-479) 或五代(907-960)
            # 420-479 = 南朝宋
            # 479-960 = 非南朝宋，可能是五代
        elif y < 1279:
            # 960-1279 北宋/南宋
            if y < 1127:
                song_beisong += 1
            else:
                song_nansong += 1
        else:
            unknown += 1
    print(f"  生卒年<960 (含南朝宋/五代): {nanbei}")
    print(f"  生卒年 960-1126 (北宋): {song_beisong}")
    print(f"  生卒年 1127-1279 (南宋): {song_nansong}")
    print(f"  無生卒年: {unknown}")

    # 6. 還看 cbdb_dy 是否在 entity 有（檢查字段）
    print("\n=== 檢查 Entity 是否有 cbdb_dy 信號 ===")
    has_cbdb_dy = 0
    for e in entities.values():
        ext = e.get("external_ids", {})
        if isinstance(ext, dict):
            if "cbdb_dy" in ext or "cbdb_dynasty" in ext:
                has_cbdb_dy += 1
                if has_cbdb_dy <= 3:
                    print(f"  例: {e.get('primary_name')} ext={ext}")
                break
    print(f"  有 cbdb_dy/dynasty 字段的 entity: {has_cbdb_dy}")

    # 7. 看 entity 的 dynasty_basis 分布
    print("\n=== Entity.dynasty_basis 分布（所有歧義值）===")
    for target_dyn in ["宋", "魏", "梁", "周", "齊", "陳", "晉"]:
        ec = Counter()
        for e in entities.values():
            if e.get("dynasty") == target_dyn:
                ec[e.get("dynasty_basis") or "null"] += 1
        total = sum(ec.values())
        if total:
            print(f"\n  dynasty={target_dyn} (entity 總數 {total})")
            for k, v in ec.most_common(10):
                print(f"    {k:50s} {v:>5}")

    # 8. Work.indexed_by 著錄之志分布（對 dynasty=宋 的 Work）
    print("\n=== dynasty=宋 的 Work 之 indexed_by.source 分布 ===")
    source_dist = Counter()
    song_work_count = 0
    for w in works.values():
        if w.get("dynasty") == "宋":
            song_work_count += 1
            for item in w.get("indexed_by", []) or []:
                if isinstance(item, dict):
                    source_dist[item.get("source", "")] += 1
    print(f"  dynasty=宋 Work 總數: {song_work_count}")
    for k, v in source_dist.most_common(20):
        print(f"    {k:30s} {v:>5}")

    # 9. dynasty=梁 的 Work
    print("\n=== dynasty=梁 的 Work 分析 ===")
    liang_work = 0
    liang_period = Counter()
    for w in works.values():
        if w.get("dynasty") == "梁":
            liang_work += 1
            liang_period[w.get("period") or "null"] += 1
    print(f"  dynasty=梁 Work 總數: {liang_work}")
    for k, v in liang_period.most_common():
        print(f"    period={k:20s} {v:>5}")

    # 10. dynasty=齊
    print("\n=== dynasty=齊 的 Work 分析 ===")
    qi_work = 0
    qi_period = Counter()
    for w in works.values():
        if w.get("dynasty") == "齊":
            qi_work += 1
            qi_period[w.get("period") or "null"] += 1
    print(f"  dynasty=齊 Work 總數: {qi_work}")
    for k, v in qi_period.most_common():
        print(f"    period={k:20s} {v:>5}")

    # 11. dynasty=周
    print("\n=== dynasty=周 的 Work 分析 ===")
    zhou_work = 0
    zhou_period = Counter()
    for w in works.values():
        if w.get("dynasty") == "周":
            zhou_work += 1
            zhou_period[w.get("period") or "null"] += 1
    print(f"  dynasty=周 Work 總數: {zhou_work}")
    for k, v in zhou_period.most_common():
        print(f"    period={k:20s} {v:>5}")

    # 12. dynasty=魏 (三國魏/北魏) - 三國兩晉可能還有未解的
    print("\n=== dynasty=魏 的 Work 分析（看三國兩晉是否已清理）===")
    wei_work = 0
    wei_period = Counter()
    for w in works.values():
        if w.get("dynasty") == "魏":
            wei_work += 1
            wei_period[w.get("period") or "null"] += 1
    print(f"  dynasty=魏 Work 總數: {wei_work}")
    for k, v in wei_period.most_common():
        print(f"    period={k:20s} {v:>5}")

    # 13. dynasty=陳
    print("\n=== dynasty=陳 的 Work 分析 ===")
    chen_work = 0
    chen_period = Counter()
    for w in works.values():
        if w.get("dynasty") == "陳":
            chen_work += 1
            chen_period[w.get("period") or "null"] += 1
    print(f"  dynasty=陳 Work 總數: {chen_work}")
    for k, v in chen_period.most_common():
        print(f"    period={k:20s} {v:>5}")

    # 14. dynasty=晉 殘留 (應該被三國兩晉進程處理過了)
    print("\n=== dynasty=晉 殘留 ===")
    jin_work = 0
    jin_period = Counter()
    for w in works.values():
        if w.get("dynasty") == "晉":
            jin_work += 1
            jin_period[w.get("period") or "null"] += 1
    print(f"  dynasty=晉 Work 總數: {jin_work}")
    for k, v in jin_period.most_common():
        print(f"    period={k:20s} {v:>5}")

    # 15. entity_id 關聯：dynasty=宋 的 entity 對應的 cbdb_id 範圍
    print("\n=== dynasty=宋 entity 的 cbdb_id 對應 c_dy 推斷 ===")
    # 由於沒有 cbdb 表，只能看 cbdb_id 的存在性
    # 嘗試通過 entity 的 cbdb_id 來區分南北宋
    # 但真正能區分的是 birth_year/death_year
    song_entity_with_year = 0
    song_entity_nbdist = Counter()  # 南朝宋 vs 北宋 vs 南宋
    for e in song_entities:
        by = e.get("birth_year")
        dy = e.get("death_year")
        if by is None and dy is None:
            continue
        song_entity_with_year += 1
        # 用任一可用年份
        years = [y for y in [by, dy] if y is not None]
        if max(years) < 420:
            song_entity_nbdist["前420(秦漢以前)"] += 1
        elif min(years) < 479:
            song_entity_nbdist["南朝宋(420-479)"] += 1
        elif min(years) < 960:
            song_entity_nbdist["五代/未定(479-960)"] += 1
        elif min(years) < 1127:
            song_entity_nbdist["北宋(960-1127)"] += 1
        else:
            song_entity_nbdist["南宋(1127-1279)"] += 1
    print(f"  有生卒年: {song_entity_with_year}/{len(song_entities)}")
    for k, v in song_entity_nbdist.most_common():
        print(f"    {k:30s} {v:>5}")


if __name__ == "__main__":
    main()
