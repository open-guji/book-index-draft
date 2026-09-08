#!/usr/bin/env python3
"""
fetch_song_index_year.py — 补查 dynasty=宋 Entity 的 CBDB IndexYear

只处理当前库中 Entity.dynasty == "宋" 且已有 cbdb_id、缓存 index_year 为空者。
用于宋代拆分北宋/南宋，不触碰其他时期。
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


def iter_entity_files():
    return sorted(ROOT.glob("Entity/?/?/?/*.json"))


def query_index_year(cbdb_id: int) -> dict:
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
            return {"cbdb_id": cbdb_id, "index_year": basic.get("IndexYear", "")}
        except Exception as exc:
            if attempt < 3:
                time.sleep(2 ** attempt)
                continue
            return {"cbdb_id": cbdb_id, "error": str(exc)}
    return {"cbdb_id": cbdb_id, "error": "max retries"}


def main():
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    song_cbdb_ids = set()
    for fp in iter_entity_files():
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("dynasty") != "宋":
            continue
        ext = d.get("external_ids", {})
        cbdb_id = ext.get("cbdb_id") if isinstance(ext, dict) else None
        if cbdb_id:
            song_cbdb_ids.add(str(cbdb_id))

    to_fetch = []
    for cid in sorted(song_cbdb_ids, key=lambda x: int(x)):
        entry = cache.get(cid)
        if not entry or "error" in entry:
            continue
        if str(entry.get("dynasty_id", "")) != "15":
            continue
        if entry.get("index_year"):
            continue
        to_fetch.append(int(cid))

    print(f"宋 Entity cbdb_id: {len(song_cbdb_ids)}")
    print(f"需补查 IndexYear: {len(to_fetch)}")
    if not to_fetch:
        return

    results = {}
    errors = []
    done = 0
    start = time.time()
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(query_index_year, cid): cid for cid in to_fetch}
        for fut in as_completed(futures):
            cid = futures[fut]
            result = fut.result()
            if "error" in result:
                errors.append((cid, result["error"]))
            else:
                results[str(cid)] = result.get("index_year", "")
            done += 1
            if done % 50 == 0:
                elapsed = time.time() - start
                print(f"  进度: {done}/{len(to_fetch)}，耗时 {elapsed:.1f}s", flush=True)
                for k, v in results.items():
                    cache[k]["index_year"] = v
                CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    for k, v in results.items():
        cache[k]["index_year"] = v
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    elapsed = time.time() - start
    print(f"完成: 成功 {len(results)}, 失败 {len(errors)}, 耗时 {elapsed:.1f}s")
    if errors:
        print("失败样本:")
        for cid, err in errors[:10]:
            print(f"  {cid}: {err}")


if __name__ == "__main__":
    main()
