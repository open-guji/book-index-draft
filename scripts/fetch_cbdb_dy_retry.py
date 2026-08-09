#!/usr/bin/env python3
"""重試失敗的 CBDB 查詢（低並發 + 延時）。"""
from __future__ import annotations

import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / ".claude" / "known-issues" / "cbdb_dy_cache.json"
TO_QUERY_PATH = ROOT / ".claude" / "known-issues" / "cbdb_to_query.json"
API_URL = "https://cbdb.fas.harvard.edu/cbdbapi/person.php"


def query_one(cbdb_id: int) -> dict:
    url = f"{API_URL}?id={cbdb_id}&o=json"
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 book-index-draft"})
            with urllib.request.urlopen(req, timeout=25) as resp:
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
            if "429" in str(e):
                time.sleep(2 * (attempt + 1))
                continue
            return {"cbdb_id": cbdb_id, "error": str(e)}
    return {"cbdb_id": cbdb_id, "error": "max_retries"}


def main():
    to_query = json.loads(TO_QUERY_PATH.read_text(encoding="utf-8"))
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
    to_fetch = [int(k) for k in to_query.keys() if str(k) not in cache]
    print(f"需重試: {len(to_fetch)} 個")

    results = {}
    errors = []
    done = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=5) as pool:
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
            if done % 50 == 0:
                elapsed = time.time() - start
                rate = done / elapsed if elapsed > 0 else 0
                eta = (len(to_fetch) - done) / rate if rate > 0 else 0
                print(f"  進度: {done}/{len(to_fetch)} ({rate:.1f}/s, ETA {eta:.0f}s)", flush=True)
                cache.update(results)
                CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    cache.update(results)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"\n完成: 成功 {len(results)}, 失敗 {len(errors)}, 緩存總量 {len(cache)}")


if __name__ == "__main__":
    main()
