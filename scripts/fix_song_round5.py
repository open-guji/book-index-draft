#!/usr/bin/env python3
"""
fix_song_round5.py — 宋代整理第五轮：继续高置信人工词典判定

原则：
- 只处理有明确北宋/南宋时代线索的作者。
- “宋”但缺南北、跨靖康而主活动期不稳、或仅有泛泛书目著录者继续跳过。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / ".claude" / "known-issues" / "宋代整理_round5_未決.json"

GENERIC_NAMES = {"佚名", "不著撰人", "□□", "", None}
PERIOD_BY_DYNASTY = {
    "北宋": "song",
    "南宋": "song",
    "南朝宋": "nanbeichao",
}

# name: (dynasty, basis)
MANUAL_FIGURES = {
    # 北宋
    "高承": ("北宋", "manual_round5:《事物紀原》據南宋書目稱北宋元豐年間高承撰→北宋"),
    "魏泰": ("北宋", "manual_round5:魏泰《東軒筆錄》記北宋太祖至神宗六朝舊事，作者為北宋中後期人→北宋"),
    "張伯端": ("北宋", "manual_round5:張伯端984-1082，《悟真篇》熙寧八年(1075)成書→北宋"),
    # 南宋
    "王宗傳": ("南宋", "manual_round5:王宗傳淳熙八年(1181)進士，《童溪易傳》成書於南宋中期→南宋"),
    "李過": ("南宋", "manual_round5:李過為南宋人，撰《西溪易說》；自序在慶元戊午(1198)→南宋"),
    "毛晃": ("南宋", "manual_round5:毛晃南宋紹興二十一年進士，紹興三十二年編《增修互注禮部韻略》→南宋"),
    "葉紹翁": ("南宋", "manual_round5:葉紹翁南宋嘉定七年任官，寶慶元年起撰《四朝聞見錄》→南宋"),
    "黃幹": ("南宋", "manual_round5:黃幹1152-1221，朱熹門人/女婿，著《勉齋集》《儀禮經傳續》→南宋"),
    "魏峴": ("南宋", "manual_round5:魏峴1180-1250，《魏氏家藏方》成於寶慶丁亥(1227)，《它山水利備覽序》淳祐二年→南宋"),
    "桂萬榮": ("南宋", "manual_round5:桂萬榮南宋慶元二年進士，《棠陰比事》嘉定年間成書→南宋"),
    "陳鵠": ("南宋", "manual_round5:陳鵠《耆舊續聞》為南宋史料筆記，約生活於1140-1225後→南宋"),
    "費袞": ("南宋", "manual_round5:費袞《梁溪漫志》有紹熙三年自序、嘉泰改元跋→南宋"),
    "康與之": ("南宋", "manual_round5:康與之為南渡詞人，著《昨夢錄》《順庵樂府》→南宋"),
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
        e["dynasty_basis"] = f"author_round5_manual_propagation:{new_dyn}"
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
        "description": "宋代整理 Round 5 后未决清单",
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

    print("=== 宋代整理 Round 5 统计 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:44s} {v:>6}")
    print("\n未决：")
    print(f"  Work.dynasty=宋: {len(unresolved['remaining_work_dynasty_song'])}")
    print(f"  Author.dynasty=宋: {len(unresolved['remaining_author_dynasty_song'])}")
    print(f"  Entity.dynasty=宋: {len(unresolved['remaining_entity_dynasty_song'])}")
    print(f"  输出: {OUT_PATH}")


if __name__ == "__main__":
    main()
