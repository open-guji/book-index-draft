#!/usr/bin/env python3
"""
fix_song_round4.py — 宋代整理第四轮：继续外部资料人工词典判定

本轮延续 Round 3 的保守策略：
- 只处理已查到明确时代线索的高频作者。
- “宋”但无南北或具体纪年线索者跳过。
- 释延寿等跨五代吴越/宋初、政治归属不稳者暂不归北宋。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / ".claude" / "known-issues" / "宋代整理_round4_未決.json"

GENERIC_NAMES = {"佚名", "不著撰人", "□□", "", None}
PERIOD_BY_DYNASTY = {
    "北宋": "song",
    "南宋": "song",
    "南朝宋": "nanbeichao",
}

# name: (dynasty, basis)
MANUAL_FIGURES = {
    # 北宋
    "陳景元": ("北宋", "manual_round4:陳景元《道德真經藏室纂微篇》熙寧五年(1072)進呈→北宋"),
    # 南宋
    "李曾伯": ("南宋", "manual_round4:李曾伯《班馬字類補遺》序署景定甲子(1264)，另有《可齋雜藁》→南宋"),
    "嚴羽": ("南宋", "manual_round4:嚴羽《滄浪詩話》成於南宋理宗紹定、淳祐年間→南宋"),
    "楊輝": ("南宋", "manual_round4:楊輝南宋數學家，《續古摘奇算法》約1275成書→南宋"),
    "鄭思肖": ("南宋", "manual_round4:鄭思肖為南宋遺民，著《心史》《鄭所南先生文集》→南宋"),
    "陳湻": ("南宋", "manual_round4:陳湻即陳淳，朱熹門人，著《性理字義/北溪字義》→南宋"),
    "陳景沂": ("南宋", "manual_round4:陳景沂《全芳備祖》編成於理宗寶慶至端平年間→南宋"),
    "陳顯微": ("南宋", "manual_round4:陳顯微嘉定、端平間臨安佑聖觀道士，《周易參同契解》端平元年刊→南宋"),
    "魏仲舉": ("南宋", "manual_round4:魏仲舉《五百家注音辯昌黎先生文集》慶元六年(1200)家塾刻→南宋"),
    "宋伯仁": ("南宋", "manual_round4:宋伯仁理宗嘉熙時人，《梅花喜神譜》1261序→南宋"),
    "楊伯喦": ("南宋", "manual_round4:楊伯喦嘉熙、淳祐、寶祐間仕宦，著《六帖補》《九經補韻》→南宋"),
    "葉士龍": ("南宋", "manual_round4:葉士龍整理朱熹語錄成《晦庵先生語錄類要》，朱子殁後文獻→南宋"),
    "王子俊": ("南宋", "manual_round4:王子俊寧宗嘉定七年(1214)辭歸，著《格齋四六/三松集》→南宋"),
    "稅與權": ("南宋", "manual_round4:稅與權《易學啟蒙小傳》成於淳祐八年(1248)→南宋"),
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
        wid = d.get("id", fp.stem)
        works[wid] = d
        work_paths[wid] = fp
    for fp in iter_entity_files():
        d = load_json(fp)
        eid = d.get("id", fp.stem)
        entities[eid] = d
        entity_paths[eid] = fp

    for wid, w in works.items():
        work_changed = False
        for a in w.get("authors", []) or []:
            if not isinstance(a, dict) or a.get("dynasty") != "宋":
                continue
            name = a.get("name")
            if name in GENERIC_NAMES:
                continue
            item = MANUAL_FIGURES.get(name)
            if not item:
                continue
            new_dyn, basis = item
            a["dynasty"] = new_dyn
            a["dynasty_basis"] = basis
            stats[f"A.author.宋->{new_dyn}"] += 1
            work_changed = True
            if a.get("entity_id"):
                updated_author_by_entity[a["entity_id"]].add(new_dyn)

        if work_changed:
            dyns = set()
            for a in w.get("authors", []) or []:
                if not isinstance(a, dict) or a.get("name") in GENERIC_NAMES:
                    continue
                if a.get("dynasty") in PERIOD_BY_DYNASTY:
                    dyns.add(a.get("dynasty"))
            if len(dyns) == 1 and (not w.get("dynasty") or w.get("dynasty") == "宋"):
                new_dyn = next(iter(dyns))
                w["dynasty"] = new_dyn
                w["dynasty_basis"] = f"据本轮人工资料 author.dynasty「{new_dyn}」补全"
                stats[f"A.work.dynasty_filled.{new_dyn}"] += 1
                if not w.get("period"):
                    w["period"] = PERIOD_BY_DYNASTY[new_dyn]
                    w["period_basis"] = f"据本轮人工资料 author.dynasty「{new_dyn}」自动归并"
                    stats[f"A.work.period_filled.{new_dyn}"] += 1
            w["updated_at"] = now_iso()
            changed_work_ids.add(wid)

    for eid, dyns in updated_author_by_entity.items():
        if len(dyns) != 1:
            continue
        e = entities.get(eid)
        if not e or e.get("dynasty") != "宋":
            continue
        new_dyn = next(iter(dyns))
        e["dynasty"] = new_dyn
        e["dynasty_basis"] = f"author_round4_manual_propagation:{new_dyn}"
        e["period"] = PERIOD_BY_DYNASTY[new_dyn]
        e["period_basis"] = f"据 dynasty「{new_dyn}」自动归并"
        e["updated_at"] = now_iso()
        changed_entity_ids.add(eid)
        stats[f"B.entity.宋->{new_dyn}"] += 1

    for eid, e in entities.items():
        if e.get("dynasty") != "宋":
            continue
        item = MANUAL_FIGURES.get(e.get("primary_name"))
        if not item:
            continue
        new_dyn, basis = item
        e["dynasty"] = new_dyn
        e["dynasty_basis"] = basis
        e["period"] = PERIOD_BY_DYNASTY[new_dyn]
        e["period_basis"] = f"据 dynasty「{new_dyn}」自动归并"
        e["updated_at"] = now_iso()
        changed_entity_ids.add(eid)
        stats[f"C.entity_by_name.宋->{new_dyn}"] += 1

    unresolved = {
        "description": "宋代整理 Round 4 后未决清单",
        "manual_figures_count": len(MANUAL_FIGURES),
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

    print("=== 宋代整理 Round 4 统计 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:44s} {v:>6}")
    print("\n未决：")
    print(f"  Work.dynasty=宋: {len(unresolved['remaining_work_dynasty_song'])}")
    print(f"  Author.dynasty=宋: {len(unresolved['remaining_author_dynasty_song'])}")
    print(f"  Entity.dynasty=宋: {len(unresolved['remaining_entity_dynasty_song'])}")
    print(f"  输出: {OUT_PATH}")


if __name__ == "__main__":
    main()
