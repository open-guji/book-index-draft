#!/usr/bin/env python3
"""收集所有 dynasty 為歧義值且有 cbdb_id 的 entity，輸出待查詢清單。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

AMBIGUOUS_DYNASTIES = {"宋", "晉", "梁", "周", "齊", "魏", "吳", "蜀", "陳", "三國", "南北朝", "南朝", "北朝"}


def iter_entity_files():
    return sorted(ROOT.glob("Entity/?/?/?/*.json"))


def main():
    to_query = {}  # cbdb_id -> [entity_ids]
    by_dynasty = {}
    for fp in iter_entity_files():
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        dyn = d.get("dynasty")
        if dyn not in AMBIGUOUS_DYNASTIES:
            continue
        ext = d.get("external_ids", {})
        cbdb_id = ext.get("cbdb_id") if isinstance(ext, dict) else None
        if not cbdb_id:
            continue
        cbdb_id = int(cbdb_id)
        to_query.setdefault(cbdb_id, []).append(d.get("id"))
        by_dynasty.setdefault(dyn, 0)
        by_dynasty[dyn] += 1

    print(f"待查詢 cbdb_id 總數: {len(to_query)}")
    print(f"對應 entity 總數: {sum(len(v) for v in to_query.values())}")
    print("\n按 dynasty 分布:")
    for k, v in sorted(by_dynasty.items(), key=lambda x: -x[1]):
        print(f"  {k:10s} {v:>5}")

    # 保存
    out = {str(k): v for k, v in to_query.items()}
    out_path = ROOT / ".claude" / "known-issues" / "cbdb_to_query.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已保存待查詢清單: {out_path}")


if __name__ == "__main__":
    main()
