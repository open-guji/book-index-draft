#!/usr/bin/env python3
"""檢查 CBDB 緩存中 dynasty_birth_name/death_name 是否區分北宋/南宋。"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / ".claude" / "known-issues" / "cbdb_dy_cache.json"


def main():
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    print(f"緩存總量: {len(cache)}")

    # 只看 c_dy=15 的
    song_entries = [v for v in cache.values() if v.get("dynasty_id") == "15"]
    print(f"c_dy=15 (宋) 條數: {len(song_entries)}")

    # dynasty_birth_name 分布
    birth_dist = Counter()
    death_dist = Counter()
    for e in song_entries:
        bn = e.get("dynasty_birth_name", "")
        dn = e.get("dynasty_death_name", "")
        birth_dist[bn or "(空)"] += 1
        death_dist[dn or "(空)"] += 1

    print("\ndynasty_birth_name 分布:")
    for k, v in birth_dist.most_common():
        print(f"  {k:15s} {v:>5}")

    print("\ndynasty_death_name 分布:")
    for k, v in death_dist.most_common():
        print(f"  {k:15s} {v:>5}")

    # 看 year_birth/year_death 分布
    print("\nyear_birth 分布:")
    yb_dist = Counter()
    for e in song_entries:
        yb = e.get("year_birth", "")
        yb_dist[yb or "(空)"] += 1
    print(f"  有 year_birth: {sum(v for k, v in yb_dist.items() if k != '(空)')}")
    print(f"  無 year_birth: {yb_dist.get('(空)', 0)}")

    # 抽樣看幾條
    print("\n抽樣 (前 10 條):")
    for e in song_entries[:10]:
        print(f"  cbdb_id={e['cbdb_id']} {e.get('ch_name','')} | "
              f"dy={e.get('dynasty_name')} birth={e.get('dynasty_birth_name')}/{e.get('year_birth')} "
              f"death={e.get('dynasty_death_name')}/{e.get('year_death')}")

    # 看 dynasty_birth_name 能否區分北宋/南宋
    print("\n=== 用 dynasty_birth_name 區分北宋/南宋 ===")
    beisong = sum(1 for e in song_entries if e.get("dynasty_birth_name") == "北宋")
    nansong = sum(1 for e in song_entries if e.get("dynasty_birth_name") == "南宋")
    other = sum(1 for e in song_entries if e.get("dynasty_birth_name") not in ("北宋", "南宋", ""))
    empty = sum(1 for e in song_entries if not e.get("dynasty_birth_name"))
    print(f"  dynasty_birth_name=北宋: {beisong}")
    print(f"  dynasty_birth_name=南宋: {nansong}")
    print(f"  dynasty_birth_name=其他: {other}")
    print(f"  dynasty_birth_name=空: {empty}")

    # 用 death_name 補充
    print("\n=== 用 dynasty_death_name 補充 ===")
    beisong_d = sum(1 for e in song_entries if e.get("dynasty_death_name") == "北宋")
    nansong_d = sum(1 for e in song_entries if e.get("dynasty_death_name") == "南宋")
    print(f"  dynasty_death_name=北宋: {beisong_d}")
    print(f"  dynasty_death_name=南宋: {nansong_d}")

    # 合併 birth+death 能判定的
    beisong_total = sum(1 for e in song_entries
                        if e.get("dynasty_birth_name") == "北宋" or e.get("dynasty_death_name") == "北宋")
    nansong_total = sum(1 for e in song_entries
                        if e.get("dynasty_birth_name") == "南宋" or e.get("dynasty_death_name") == "南宋")
    # 同時有北宋和南宋的（跨南北宋）
    both = sum(1 for e in song_entries
               if (e.get("dynasty_birth_name") == "北宋" and e.get("dynasty_death_name") == "南宋"))
    print(f"\n  合併判定北宋(含跨): {beisong_total}")
    print(f"  合併判定南宋(含跨): {nansong_total}")
    print(f"  跨南北宋(生北宋卒南宋): {both}")


if __name__ == "__main__":
    main()
