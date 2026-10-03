#!/usr/bin/env python3
"""fetch_index_year.py — 補充 CBDB 緩存中缺失的 IndexYear 字段。

針對 c_dy=15（趙宋）但 year_birth/year_death 為空的 cbdb_id，
再查 CBDB API 獲取 IndexYear（人物主要活動年份），
用於區分北宋（960-1126）/南宋（1127-1279）。

同時也補充其他歧義 c_dy（如 4=南北朝、28=南朝宋等）的 IndexYear，
用於輔助判定。

並發控制在 3，避免觸發 API 限流（429）。
"""
from __future__ import annotations

import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / ".claude" / "known-issues" / "cbdb_dy_cache.json"

API_URL = "https://cbdb.fas.harvard.edu/cbdbapi/person.php"


def query_index_year(cbdb_id: int) -> dict:
    """查詢單個 cbdb_id 的 IndexYear"""
    url = f"{API_URL}?id={cbdb_id}&o=json"
    for attempt in range(4):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 book-index-draft"}
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            person = (
                data.get("Package", {})
                .get("PersonAuthority", {})
                .get("PersonInfo", {})
                .get("Person", {})
            )
            basic = person.get("BasicInfo", {})
            if not basic:
                return {"cbdb_id": cbdb_id, "error": "no BasicInfo"}
            return {
                "cbdb_id": cbdb_id,
                "index_year": basic.get("IndexYear", ""),
            }
        except Exception as e:
            if attempt < 3:
                time.sleep(2 ** attempt)
                continue
            return {"cbdb_id": cbdb_id, "error": str(e)}
    return {"cbdb_id": cbdb_id, "error": "max retries"}


def main():
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    print(f"現有緩存: {len(cache)} 條")

    # 找出需要補充 IndexYear 的 cbdb_id
    # 條件：已有 dynasty_id 但無 index_year 字段
    to_fetch = []
    for cid, entry in cache.items():
        if "error" in entry:
            continue
        if "index_year" in entry:
            continue  # 已有
        # 只要沒有 index_year 字段就補充
        to_fetch.append(int(cid))

    print(f"需補充 IndexYear: {len(to_fetch)} 個")
    if not to_fetch:
        print("全部已有 IndexYear，無需查詢")
        return

    results = {}
    errors = []
    done = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(query_index_year, cid): cid for cid in to_fetch}
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
            if done % 50 == 0:
                elapsed = time.time() - start
                rate = done / elapsed if elapsed > 0 else 0
                eta = (len(to_fetch) - done) / rate if rate > 0 else 0
                print(
                    f"  進度: {done}/{len(to_fetch)} ({rate:.1f}/s, ETA {eta:.0f}s)",
                    flush=True,
                )
                # 定期保存
                for k, v in results.items():
                    if k in cache and "error" not in cache[k]:
                        cache[k]["index_year"] = v.get("index_year", "")
                CACHE_PATH.write_text(
                    json.dumps(cache, ensure_ascii=False), encoding="utf-8"
                )

    # 最終保存
    for k, v in results.items():
        if k in cache and "error" not in cache[k]:
            cache[k]["index_year"] = v.get("index_year", "")
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
