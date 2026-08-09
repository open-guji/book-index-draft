#!/usr/bin/env python3
"""
fix_song_round3.py — 宋代整理第三轮：外部资料人工词典判定

证据类型：
1. 人名/别称 + 代表作，经外部书目、四库提要、百科/专业平台等资料核实。
2. 书目自身描述中的明确纪年，如《古三坟》记北宋元丰七年。

安全边界：
- 只处理 MANUAL_FIGURES 中列出的高置信姓名。
- 通用作者名（佚名、不著撰人）默认不按姓名批量传播；仅单独处理《古三坟》。
- 若同一 Work 的非通用作者分属不同朝代，则不补顶层 dynasty。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / ".claude" / "known-issues" / "宋代整理_round3_未決.json"

GENERIC_NAMES = {"佚名", "不著撰人", "□□", "", None}
PERIOD_BY_DYNASTY = {
    "北宋": "song",
    "南宋": "song",
    "南朝宋": "nanbeichao",
}

# name: (dynasty, basis)
# 只收入本轮已查证且能明确拆到北宋/南宋/南朝宋的一批。
MANUAL_FIGURES = {
    # 北宋
    "胡援": ("北宋", "manual_round3:胡瑗《周易口義》为北宋；库内作胡援，按题名对应判北宋"),
    "張子": ("北宋", "manual_round3:張子即張載，1020-1077，《橫渠易說》作者→北宋"),
    "伊川程子": ("北宋", "manual_round3:伊川程子即程頤，1033-1107，《易傳》作者→北宋"),
    "邵子": ("北宋", "manual_round3:邵子即邵雍，1011-1077，《皇極經世書》作者→北宋"),
    "王惟一": ("北宋", "manual_round3:王惟一約987-1067，《銅人腧穴鍼灸圖經》成於1026→北宋"),
    "釋文瑩": ("北宋", "manual_round3:釋文瑩《湘山野錄》《玉壺清話》記宋初至熙寧事→北宋"),
    "董汲": ("北宋", "manual_round3:董汲《小兒斑疹備急方論》約刊11世紀末→北宋"),
    "劉道醇": ("北宋", "manual_round3:劉道醇活動於1057年前後，《聖朝名畫評》→北宋"),
    "董逌": ("北宋", "manual_round3:董逌政和間官徽猷閣待制，《廣川書跋》《廣川畫跋》→北宋"),
    "寇宗奭": ("北宋", "manual_round3:寇宗奭《本草衍義》成書於政和年間→北宋"),
    # 南宋
    "陸遊": ("南宋", "manual_round3:陸遊1125-1210，放翁，《入蜀記》《劍南詩稿》→南宋"),
    "楊士瀛": ("南宋", "manual_round3:楊士瀛《仁齋直指方》景定五年1264成書→南宋"),
    "黃昇": ("南宋", "manual_round3:黃昇《花庵詞選》淳祐九年1249成書→南宋"),
    "陳思": ("南宋", "manual_round3:陳思為南宋理宗朝刻書家，著《書小史》《寶刻叢編》→南宋"),
    "金履祥": ("南宋", "manual_round3:金履祥《資治通鑑前編》，德祐初被召→南宋"),
    "李龏": ("南宋", "manual_round3:李龏江湖派詩人，《剪綃集》《梅花衲》見南宋群賢小集→南宋"),
    "李幼武": ("南宋", "manual_round3:李幼武輯南渡以後四朝名臣言行，續朱熹書→南宋"),
    "杜大珪": ("南宋", "manual_round3:杜大珪編《名臣碑傳琬琰集》，收北宋至南宋碑傳→南宋"),
    "陳自明": ("南宋", "manual_round3:陳自明南宋醫學家，《婦人大全良方》嘉熙元年1237→南宋"),
    "戴復古": ("南宋", "manual_round3:戴復古為南宋江湖詩派，《石屏集》《石屏詞》→南宋"),
    "洪適": ("南宋", "manual_round3:洪適金石家，著《隸釋》《隸續》《盤洲集》→南宋"),
    "俞文豹": ("南宋", "manual_round3:俞文豹南宋理宗淳祐間在世，著《吹劍錄》《清夜錄》→南宋"),
    "方聞一": ("南宋", "manual_round3:方聞一《大易粹言》南宋淳熙中輯→南宋"),
    "馮椅": ("南宋", "manual_round3:馮椅1140-1232，朱熹弟子，《厚齋易學》→南宋"),
    # 南朝宋误混入赵宋整理的残留
    "謝瞻": ("南朝宋", "manual_round3:謝瞻385-421，南朝宋詩人→南朝宋"),
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

    # A. 人工词典更新 authors
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

    # B. 反向更新 Entity：作者行指向同一 entity 且证据唯一
    for eid, dyns in updated_author_by_entity.items():
        if len(dyns) != 1:
            continue
        e = entities.get(eid)
        if not e or e.get("dynasty") != "宋":
            continue
        new_dyn = next(iter(dyns))
        e["dynasty"] = new_dyn
        e["dynasty_basis"] = f"author_round3_manual_propagation:{new_dyn}"
        e["period"] = PERIOD_BY_DYNASTY[new_dyn]
        e["period_basis"] = f"据 dynasty「{new_dyn}」自动归并"
        e["updated_at"] = now_iso()
        changed_entity_ids.add(eid)
        stats[f"B.entity.宋->{new_dyn}"] += 1

    # C. 无 author entity 传播时，直接按 primary_name 更新 Entity
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

    # D. 单独处理《古三坟》：记录自带北宋元丰七年线索
    for wid, w in works.items():
        if w.get("title") != "古三墳" or w.get("dynasty") != "宋":
            continue
        w["dynasty"] = "北宋"
        w["dynasty_basis"] = "manual_round3:description 明记北宋元豐七年(1084)張商英得書→北宋"
        if not w.get("period"):
            w["period"] = "song"
            w["period_basis"] = "据 dynasty「北宋」自动归并"
        for a in w.get("authors", []) or []:
            if isinstance(a, dict) and a.get("dynasty") == "宋" and a.get("name") == "佚名":
                a["dynasty"] = "北宋"
                a["dynasty_basis"] = "manual_round3:《古三墳》据北宋元豐七年成书线索归北宋"
                stats["D.author.佚名宋->北宋"] += 1
        w["updated_at"] = now_iso()
        changed_work_ids.add(wid)
        stats["D.work.古三墳.宋->北宋"] += 1

    # E. 未决清单
    unresolved = {
        "description": "宋代整理 Round 3 后未决清单",
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
                    stats["E.index.work.dynasty_sync"] += 1
                    changed = True
                if entry.get("period") != w.get("period"):
                    entry["period"] = w.get("period")
                    stats["E.index.work.period_sync"] += 1
                    changed = True
            if changed:
                write_json(shard_fp, shard)
                stats["E.index.work.shards_changed"] += 1

        for shard_fp in sorted((idx_dir / "entities").glob("*.json")):
            shard = load_json(shard_fp)
            changed = False
            for eid, entry in shard.items():
                if not isinstance(entry, dict) or eid not in changed_entity_ids:
                    continue
                e = entities[eid]
                if entry.get("dynasty") != e.get("dynasty"):
                    entry["dynasty"] = e.get("dynasty")
                    stats["E.index.entity.dynasty_sync"] += 1
                    changed = True
                if entry.get("period") != e.get("period"):
                    entry["period"] = e.get("period")
                    stats["E.index.entity.period_sync"] += 1
                    changed = True
            if changed:
                write_json(shard_fp, shard)
                stats["E.index.entity.shards_changed"] += 1

        unresolved["stats"] = dict(stats)
        write_json(OUT_PATH, unresolved)

    print("=== 宋代整理 Round 3 统计 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:44s} {v:>6}")
    print("\n未决：")
    print(f"  Work.dynasty=宋: {len(unresolved['remaining_work_dynasty_song'])}")
    print(f"  Author.dynasty=宋: {len(unresolved['remaining_author_dynasty_song'])}")
    print(f"  Entity.dynasty=宋: {len(unresolved['remaining_entity_dynasty_song'])}")
    print(f"  输出: {OUT_PATH}")


if __name__ == "__main__":
    main()
