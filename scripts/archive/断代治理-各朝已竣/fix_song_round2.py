#!/usr/bin/env python3
"""
fix_song_round2.py — 宋代整理第二轮：资料判定

高置信证据：
1. 库内同名已规范传播：同一作者名在 Entity 或其他 Work 作者中唯一对应 北宋/南宋。
2. 题名年号：题名含宋代年号且只命中北宋或南宋一侧。

安全边界：
- 若两类证据冲突，跳过。
- 不处理已有 period 且非 song 的 Work。
- 不处理「佚名」「不著撰人」等无可归属作者。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / ".claude" / "known-issues" / "宋代整理_round2_未決.json"
SONG_DYNASTIES = {"北宋", "南宋"}
GENERIC_NAMES = {"佚名", "不著撰人", "□□", "", None}

NORTH_SONG_NIANHAO = {
    "建隆", "乾德", "開寶", "太平興國", "雍熙", "端拱", "淳化", "至道",
    "咸平", "景德", "大中祥符", "天禧", "乾興", "天聖", "明道", "景祐",
    "寶元", "康定", "慶曆", "皇祐", "至和", "嘉祐", "治平", "熙寧",
    "元豐", "元祐", "紹聖", "元符", "建中靖國", "崇寧", "大觀", "政和",
    "重和", "宣和", "靖康",
}
SOUTH_SONG_NIANHAO = {
    "建炎", "紹興", "隆興", "乾道", "淳熙", "慶元", "嘉泰", "開禧",
    "嘉定", "寶慶", "紹定", "端平", "嘉熙", "淳祐", "寶祐", "開慶",
    "景定", "咸淳", "德祐", "祥興",
}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def load_json(fp: Path):
    return json.loads(fp.read_text(encoding="utf-8"))


def write_json(fp: Path, data):
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iter_work_files():
    return sorted(ROOT.glob("Work/?/?/?/*.json"))


def iter_entity_files():
    return sorted(ROOT.glob("Entity/?/?/?/*.json"))


def nianhao_evidence(title: str):
    hits = []
    for nh in NORTH_SONG_NIANHAO:
        if nh in title:
            hits.append(("北宋", nh))
    for nh in SOUTH_SONG_NIANHAO:
        if nh in title:
            hits.append(("南宋", nh))
    dyns = {d for d, _ in hits}
    if len(dyns) == 1:
        dyn = next(iter(dyns))
        words = "、".join(nh for _, nh in hits)
        return dyn, f"title_nianhao:{words}->{dyn}"
    if len(dyns) > 1:
        return None, "title_nianhao_conflict:" + "、".join(f"{d}:{nh}" for d, nh in hits)
    return None, None


def is_complex_author_name(name: str | None) -> bool:
    """复合作者串不在本轮整条更新，避免把后代整理者一并标为宋。"""
    if not name:
        return True
    return any(mark in name for mark in ("[", "]", "，", "、", "等"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    commit = args.commit or not args.dry_run

    works = {}
    work_paths = {}
    entities = {}
    entity_paths = {}
    stats = Counter()
    changed_work_ids = set()
    changed_entity_ids = set()
    updated_author_by_entity = defaultdict(set)

    for fp in iter_work_files():
        d = load_json(fp)
        works[d.get("id", fp.stem)] = d
        work_paths[d.get("id", fp.stem)] = fp
    for fp in iter_entity_files():
        d = load_json(fp)
        entities[d.get("id", fp.stem)] = d
        entity_paths[d.get("id", fp.stem)] = fp

    # A. 建立库内同名已规范证据
    name_to_dyn = defaultdict(set)
    for e in entities.values():
        if e.get("dynasty") in SONG_DYNASTIES:
            name_to_dyn[e.get("primary_name")].add(e.get("dynasty"))
    for w in works.values():
        for a in w.get("authors", []) or []:
            if isinstance(a, dict) and a.get("dynasty") in SONG_DYNASTIES:
                name_to_dyn[a.get("name")].add(a.get("dynasty"))

    # B. 更新 Author.dynasty=宋
    for wid, w in works.items():
        # 只处理 period 为空或已为 song 的 Work
        if w.get("period") not in (None, "song"):
            continue
        work_changed = False
        for a in w.get("authors", []) or []:
            if not isinstance(a, dict) or a.get("dynasty") != "宋":
                continue
            name = a.get("name")
            if name in GENERIC_NAMES or is_complex_author_name(name):
                continue

            evidences = []
            dyns = name_to_dyn.get(name, set())
            if len(dyns) == 1:
                dyn = next(iter(dyns))
                evidences.append((dyn, f"same_name_propagation:{name}->{dyn}"))

            ndyn, nbasis = nianhao_evidence(w.get("title") or "")
            if ndyn:
                evidences.append((ndyn, nbasis))

            if not evidences:
                continue
            evidence_dyns = {d for d, _ in evidences}
            if len(evidence_dyns) != 1:
                stats["skip.conflicting_evidence"] += 1
                continue

            new_dyn = next(iter(evidence_dyns))
            basis = "; ".join(b for _, b in evidences)
            a["dynasty"] = new_dyn
            a["dynasty_basis"] = basis
            stats[f"B.author.宋->{new_dyn}"] += 1
            work_changed = True
            if a.get("entity_id"):
                updated_author_by_entity[a["entity_id"]].add(new_dyn)

        if work_changed:
            # 若本 Work 所有非泛称作者的宋代朝代唯一，则补顶层
            author_dyns = set()
            for a in w.get("authors", []) or []:
                if isinstance(a, dict) and a.get("name") not in GENERIC_NAMES and a.get("dynasty") in SONG_DYNASTIES:
                    author_dyns.add(a.get("dynasty"))
            if len(author_dyns) == 1:
                new_dyn = next(iter(author_dyns))
                if not w.get("dynasty") or w.get("dynasty") == "宋":
                    w["dynasty"] = new_dyn
                    w["dynasty_basis"] = f"据本轮 author.dynasty「{new_dyn}」补全"
                    stats[f"B.work.dynasty_filled.{new_dyn}"] += 1
                if not w.get("period"):
                    w["period"] = "song"
                    w["period_basis"] = f"据本轮 author.dynasty「{new_dyn}」自动归并"
                    stats[f"B.work.period_filled.{new_dyn}"] += 1
            w["updated_at"] = now_iso()
            changed_work_ids.add(wid)

    # C. 根据已更新 Author 反向更新对应 Entity（仅所有证据一致时）
    for eid, dyns in updated_author_by_entity.items():
        if len(dyns) != 1:
            continue
        e = entities.get(eid)
        if not e or e.get("dynasty") != "宋":
            continue
        new_dyn = next(iter(dyns))
        e["dynasty"] = new_dyn
        e["dynasty_basis"] = f"author_round2_propagation:{new_dyn}"
        e["period"] = "song"
        e["period_basis"] = f"据 dynasty「{new_dyn}」自动归并"
        e["updated_at"] = now_iso()
        changed_entity_ids.add(eid)
        stats[f"C.entity.宋->{new_dyn}"] += 1

    # D. 生成未决清单
    unresolved = {
        "description": "宋代整理 Round 2 后未决清单",
        "remaining_work_dynasty_song": [],
        "remaining_author_dynasty_song": [],
        "remaining_entity_dynasty_song": [],
        "stats": dict(stats),
    }
    for wid, w in works.items():
        if w.get("dynasty") == "宋":
            unresolved["remaining_work_dynasty_song"].append({
                "work_id": wid,
                "title": w.get("title"),
                "period": w.get("period"),
            })
        for a in w.get("authors", []) or []:
            if isinstance(a, dict) and a.get("dynasty") == "宋":
                unresolved["remaining_author_dynasty_song"].append({
                    "work_id": wid,
                    "title": w.get("title"),
                    "work_period": w.get("period"),
                    "work_dynasty": w.get("dynasty"),
                    "author_name": a.get("name"),
                    "entity_id": a.get("entity_id"),
                })
    for eid, e in entities.items():
        if e.get("dynasty") == "宋":
            unresolved["remaining_entity_dynasty_song"].append({
                "entity_id": eid,
                "name": e.get("primary_name"),
                "period": e.get("period"),
                "cbdb_id": (e.get("external_ids") or {}).get("cbdb_id") if isinstance(e.get("external_ids"), dict) else None,
            })

    if commit:
        for wid in changed_work_ids:
            write_json(work_paths[wid], works[wid])
        for eid in changed_entity_ids:
            write_json(entity_paths[eid], entities[eid])
        idx_dir = ROOT / "index"
        for shard_fp in sorted((idx_dir / "works").glob("*.json")):
            shard = load_json(shard_fp)
            changed = False
            for wid, entry in shard.items():
                if not isinstance(entry, dict) or wid not in changed_work_ids:
                    continue
                w = works[wid]
                if entry.get("dynasty") != w.get("dynasty"):
                    entry["dynasty"] = w.get("dynasty")
                    stats["D.index.work.dynasty_sync"] += 1
                    changed = True
                if entry.get("period") != w.get("period"):
                    entry["period"] = w.get("period")
                    stats["D.index.work.period_sync"] += 1
                    changed = True
            if changed:
                write_json(shard_fp, shard)
                stats["D.index.work.shards_changed"] += 1
        for shard_fp in sorted((idx_dir / "entities").glob("*.json")):
            shard = load_json(shard_fp)
            changed = False
            for eid, entry in shard.items():
                if not isinstance(entry, dict) or eid not in changed_entity_ids:
                    continue
                e = entities[eid]
                if entry.get("dynasty") != e.get("dynasty"):
                    entry["dynasty"] = e.get("dynasty")
                    stats["D.index.entity.dynasty_sync"] += 1
                    changed = True
                if entry.get("period") != e.get("period"):
                    entry["period"] = e.get("period")
                    stats["D.index.entity.period_sync"] += 1
                    changed = True
            if changed:
                write_json(shard_fp, shard)
                stats["D.index.entity.shards_changed"] += 1
        unresolved["stats"] = dict(stats)
        write_json(OUT_PATH, unresolved)

    print("=== 宋代整理 Round 2 统计 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:42s} {v:>6}")
    print("\n未决：")
    print(f"  Work.dynasty=宋: {len(unresolved['remaining_work_dynasty_song'])}")
    print(f"  Author.dynasty=宋: {len(unresolved['remaining_author_dynasty_song'])}")
    print(f"  Entity.dynasty=宋: {len(unresolved['remaining_entity_dynasty_song'])}")
    print(f"  输出: {OUT_PATH}")


if __name__ == "__main__":
    main()
