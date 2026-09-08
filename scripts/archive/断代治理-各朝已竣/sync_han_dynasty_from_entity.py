#!/usr/bin/env python3
"""西漢範圍探勘之核心發現與修正：Entity 已有精確西漢／東漢分判，
Work 層級 authors[0].dynasty 卻停留於籠統「漢」，兩者長期未同步。

範圍：period=="qin-han" 之全部 Work，其 authors[0].entity_id 所指
Entity 之 dynasty 為「西漢」或「東漢」，而 Work 自身 authors[0].dynasty
仍作籠統「漢」者——僅同步此一方向（Entity 精、Work 粗），不觸碰
Entity 較粗（如「秦漢」）而 Work 已精之情形，亦不觸碰雙方分屬不同
朝代體系（如「三國魏」「唐」「新」「五代」等，須逐條人工判斷）之
情形——後者見另一批（本輪個別核實部分，詳見 fix_hanera_dynasty_bugs.py
之後續個別修正）。

本次同步範圍：Work.authors[0].dynasty == "漢" 且 Entity.dynasty in
{"西漢","東漢"}，逕以 Entity 之值覆寫 Work，並同步更新 period_basis
與（如存在）Work 頂層 dynasty 欄位。
"""
import json
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

SAFE_TARGETS = {"西漢", "東漢"}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    idx = {}
    for s in SHARDS:
        d = load(ROOT / "index" / "works" / f"{s}.json")
        for wid, entry in d.items():
            idx[wid] = ROOT / entry["path"]

    ent_dyn = {}
    for f in glob.glob(str(ROOT / "Entity" / "**" / "*.json"), recursive=True):
        try:
            j = load(Path(f))
        except Exception:
            continue
        eid = j.get("id")
        if eid:
            ent_dyn[eid] = j.get("dynasty")

    fixed = []
    for wid, path in idx.items():
        try:
            j = load(path)
        except Exception:
            continue
        if j.get("period") != "qin-han":
            continue
        authors = j.get("authors")
        if not authors:
            continue
        a0 = authors[0]
        if a0.get("dynasty") != "漢":
            continue
        eid = a0.get("entity_id")
        if not eid or eid not in ent_dyn:
            continue
        edyn = ent_dyn[eid]
        if edyn not in SAFE_TARGETS:
            continue

        a0["dynasty"] = edyn
        if j.get("dynasty") == "漢":
            j["dynasty"] = edyn
        j["period_basis"] = f"據 authors[0].dynasty「{edyn}」（原作籠統「漢」，2026-08-11 據所繫 Entity 之精確朝代同步訂正）"
        save(path, j)
        fixed.append((wid, j.get("title"), a0.get("name"), edyn))

    print(f"synced {len(fixed)} works")
    for f in fixed[:20]:
        print(" ", f)


if __name__ == "__main__":
    main()
