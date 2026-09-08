#!/usr/bin/env python3
"""批量查詢 CBDB API，獲取 cbdb_id → c_dy 映射。
用 ThreadPoolExecutor 並行查詢，結果緩存到本地 JSON。
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import time
import sys

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / ".claude" / "known-issues" / "cbdb_dy_cache.json"
TO_QUERY_PATH = ROOT / ".claude" / "known-issues" / "cbdb_to_query.json"

API_URL = "https://cbdb.fas.harvard.edu/cbdbapi/person.php"


def query_one(cbdb_id: int) -> dict:
    """查詢單個 cbdb_id，返回 {cbdb_id, dynasty_id, dynasty_name, birth_year, death_year, dynasty_birth_id, dynasty_death_id}"""
    url = f"{API_URL}?id={cbdb_id}&o=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 book-index-draft"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        person = data.get("Package", {}).get("PersonAuthority", {}).get("PersonInfo", {}).get("Person", {})
        basic = person.get("BasicInfo", {})
        if not basic:
            return {"cbdb_id": cbdb_id, "error": "no BasicInfo"}
        return {
            "cbdb_id": cbdb_id,
            "dynasty_id": basic.get("DynastyId", ""),
            "dynasty_name": basic.get("Dynasty", ""),
            "dynasty_birth_id": basic.get("DynastyBirthId", ""),
            "dynasty_birth_name": basic.get("DynastyBirth", ""),
            "dynasty_death_id": basic.get("DynastyDeathId", ""),
            "dynasty_death_name": basic.get("DynastyDeath", ""),
            "year_birth": basic.get("YearBirth", ""),
            "year_death": basic.get("YearDeath", ""),
            "ch_name": basic.get("ChName", ""),
        }
    except Exception as e:
        return {"cbdb_id": cbdb_id, "error": str(e)}


def main():
    # 載入待查詢清單
    to_query = json.loads(TO_QUERY_PATH.read_text(encoding="utf-8"))
    cbdb_ids = [int(k) for k in to_query.keys()]
    print(f"待查詢: {len(cbdb_ids)} 個 cbdb_id")

    # 載入已有緩存
    cache = {}
    if CACHE_PATH.exists():
        cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        print(f"已有緩存: {len(cache)} 條")

    # 篩選未查詢的
    to_fetch = [cid for cid in cbdb_ids if str(cid) not in cache]
    print(f"需新查詢: {len(to_fetch)} 個")

    if not to_fetch:
        print("全部已緩存，無需查詢")
        return

    # 並行查詢
    results = {}
    errors = []
    done = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = {pool.submit(query_one, cid): cid for cid in to_fetch}
        for fut in as_completed(futures):
            cid = futures[fut]
            try:
                r = fut.result()
                if "error" in r:
                    errors.append((cid, r["error"]))
                else:
                    results[str(cid)] = r
            except Exception as e:
                errors.append((cid, str(e)))
            done += 1
            if done % 100 == 0:
                elapsed = time.time() - start
                rate = done / elapsed
                eta = (len(to_fetch) - done) / rate if rate > 0 else 0
                print(f"  進度: {done}/{len(to_fetch)} ({rate:.1f}/s, ETA {eta:.0f}s)", flush=True)
                # 定期保存
                cache.update(results)
                CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    # 最終保存
    cache.update(results)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    elapsed = time.time() - start
    print(f"\n完成: 成功 {len(results)}, 失敗 {len(errors)}, 耗時 {elapsed:.1f}s")
    print(f"緩存總量: {len(cache)}")

    if errors:
        print(f"\n失敗樣本 (前 10):")
        for cid, err in errors[:10]:
            print(f"  cbdb_id={cid}: {err}")


if __name__ == "__main__":
    main()
