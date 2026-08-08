#!/usr/bin/env python3
"""分析 CBDB c_dy 緩存數據的分布。"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / ".claude" / "known-issues" / "cbdb_dy_cache.json"
TO_QUERY_PATH = ROOT / ".claude" / "known-issues" / "cbdb_to_query.json"


# c_dy 碼 → 規範朝代名（依 SCHEMA.md）
CDY_MAP = {
    "0": "未詳", "1": "西周", "2": "春秋", "3": "春秋", "4": "南北朝",
    "5": "隋", "6": "唐", "7": "五代", "13": "唐", "15": "宋",
    "16": "遼", "17": "金", "18": "元", "19": "明", "20": "清",
    "21": "中華民國", "22": "中華人民共和國", "23": "西晉", "24": "南朝陳",
    "25": "東漢", "26": "三國魏", "27": "東晉", "28": "南朝宋",
    "29": "西漢", "30": "北魏", "31": "北周", "32": "南朝齊",
    "34": "後梁", "35": "北齊", "37": "西梁", "40": "西魏",
    "41": "東魏", "42": "三國吳", "44": "南朝梁", "46": "新",
    "47": "後唐", "48": "後晉", "49": "後周", "52": "後漢",
    "53": "三國蜀", "61": "秦", "68": "十六國", "77": "武周",
    "79": "元", "80": "南明", "82": "晉", "83": "漢",
}


def main():
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    to_query = json.loads(TO_QUERY_PATH.read_text(encoding="utf-8"))
    print(f"緩存總量: {len(cache)}")
    print(f"待查總量: {len(to_query)}")

    # 按 entity.dynasty 分組分析
    print("\n=== 按 entity 原始 dynasty 分組的 c_dy 分布 ===")
    by_orig = {}
    for cid_str, eid_list in to_query.items():
        entry = cache.get(cid_str)
        if not entry or "error" in entry:
            continue
        # 找 entity 的原始 dynasty（從 entity 文件讀太慢，用 to_query 的分組）
        # to_query 是 cbdb_id -> [entity_ids]，沒有 dynasty
        # 我們需要從 entity 文件讀 dynasty
        # 但這裡先按 c_dy 統計
        cdy = entry.get("dynasty_id", "")
        by_orig.setdefault(cdy, 0)
        by_orig[cdy] += 1

    print("\n所有已查詢 entity 的 c_dy 分布:")
    for k, v in sorted(by_orig.items(), key=lambda x: -x[1]):
        label = CDY_MAP.get(str(k), f"c_dy={k}")
        print(f"  c_dy={k:4s} ({label:10s}) {v:>5}")

    # 特別看 dynasty=宋 的 entity 的 c_dy 分布
    print("\n=== dynasty=宋 entity 的 c_dy 分布 ===")
    # 需要讀 entity 文件來判斷原始 dynasty
    # 但我們可以從 cbdb_to_query.json 的結構推斷
    # 實際上 collect 腳本是按 dynasty 收集的，但 to_query 只存了 cbdb_id -> [entity_ids]
    # 讓我直接讀 entity 文件
    import glob
    song_cdy = Counter()
    other_cdy = Counter()
    for fp in sorted(ROOT.glob("Entity/?/?/?/*.json")):
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        dyn = d.get("dynasty")
        if dyn not in ("宋", "晉", "梁", "周", "齊", "魏", "吳", "蜀", "陳", "三國", "南北朝"):
            continue
        ext = d.get("external_ids", {})
        cbdb_id = ext.get("cbdb_id") if isinstance(ext, dict) else None
        if not cbdb_id:
            continue
        entry = cache.get(str(cbdb_id))
        if not entry or "error" in entry:
            continue
        cdy = entry.get("dynasty_id", "")
        if dyn == "宋":
            song_cdy[cdy] += 1
        else:
            other_cdy[f"{dyn}:c_dy={cdy}({CDY_MAP.get(str(cdy),'?')})"] += 1

    print("dynasty=宋 的 c_dy 分布:")
    for k, v in song_cdy.most_common():
        label = CDY_MAP.get(str(k), f"c_dy={k}")
        print(f"  c_dy={k:4s} ({label:10s}) {v:>5}")

    print("\n其他歧義 dynasty 的 c_dy 分布:")
    for k, v in other_cdy.most_common(20):
        print(f"  {k:30s} {v:>5}")

    # 看能判定多少
    print("\n=== 判定預估 ===")
    # c_dy=28 → 南朝宋
    # c_dy=15 → 北宋/南宋（需生卒年進一步分）
    # c_dy=其他 → 誤標或需清理
    song_total = sum(song_cdy.values())
    song_28 = song_cdy.get("28", 0)  # 南朝宋
    song_15 = song_cdy.get("15", 0)  # 趙宋（需進一步分北宋/南宋）
    song_other = song_total - song_28 - song_15
    print(f"dynasty=宋 已查: {song_total}")
    print(f"  c_dy=28 (南朝宋): {song_28}")
    print(f"  c_dy=15 (趙宋，需進一步分): {song_15}")
    print(f"  c_dy=其他 (誤標/需清理): {song_other}")


if __name__ == "__main__":
    main()
