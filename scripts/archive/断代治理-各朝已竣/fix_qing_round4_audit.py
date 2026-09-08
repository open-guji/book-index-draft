#!/usr/bin/env python3
"""
fix_qing_round4_audit.py — 清朝整理 Round 4：抽查发现的明确误标

处理：
- 《坦斋通编》：四库总目、清史稿、书目答问均指宋邢凯。
- 《南北史合注》：Entity 已为明李清，四库总目详传亦明李清；同步 Work/author。
- 《农桑辑要》：四库总目明示元世祖时官撰，清史稿亦作元官撰。

保留：
- 《雅伦》明费经虞撰、清费密补，且费经虞 Entity 当前为清，需跨明清个案另查。
- 《陆希声春秋通例》题名/撰者与赵匡《春秋通例》关系复杂，原 ai_note 已标出，不机械改。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / ".claude" / "known-issues" / "清朝整理_round4_抽查.json"


WORK_FIXES = {
    "1ev3bbvwugs1s": {
        "dynasty": "宋",
        "period": "song",
        "basis": "四库总目称《说郛》题宋邢凯撰；清史稿/书目答问均作宋邢凯",
        "authors": [("邢凱", "撰", "宋", "1j96hjwlxny18")],
    },
    "1evjr03ihc2kg": {
        "dynasty": "明",
        "period": "ming",
        "basis": "四库总目 author_info=明李清撰；所连 Entity 已为明李清",
        "authors": [("李清", "撰", "明", "1j969m70q2eq0")],
    },
    "1ev3bbfhuhmv4": {
        "dynasty": "元",
        "period": "liao-jin-yuan",
        "basis": "四库总目称元世祖时官撰；清史稿作元官撰《农桑辑要》",
        "authors": [("官撰", "撰", "元", "1j96heojwm29s")],
    },
}


ENTITY_FIXES = {
    "1j96hjwlxny18": ("宋", "song", "四库总目/清史稿/书目答问均指宋邢凯《坦斋通编》"),
    "1j96heojwm29s": ("元", "liao-jin-yuan", "仅关联《农桑辑要》；来源明示元官撰"),
}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def load_json(fp: Path):
    return json.loads(fp.read_text(encoding="utf-8"))


def write_json(fp: Path, data):
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_work(wid):
    return next(ROOT.glob(f"Work/?/?/?/{wid}-*.json"))


def find_entity(eid):
    return next(ROOT.glob(f"Entity/?/?/?/{eid}-*.json"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    commit = args.commit or not args.dry_run

    stats = Counter()
    changed_work_ids = set()
    changed_entity_ids = set()
    work_data = {}
    entity_data = {}

    for wid, fix in WORK_FIXES.items():
        fp = find_work(wid)
        w = load_json(fp)
        work_data[wid] = (fp, w)
        if w.get("dynasty") != fix["dynasty"]:
            w["dynasty"] = fix["dynasty"]
            w["dynasty_basis"] = f"qing_round4_audit:{fix['basis']}"
            stats[f"work.dynasty->{fix['dynasty']}"] += 1
        if w.get("period") != fix["period"]:
            w["period"] = fix["period"]
            w["period_basis"] = f"据 dynasty「{fix['dynasty']}」自动归并"
            stats[f"work.period->{fix['period']}"] += 1
        w["authors"] = [
            {
                "name": name,
                "role": role,
                "dynasty": adyn,
                "entity_id": eid,
                "dynasty_basis": f"qing_round4_audit:{fix['basis']}",
            }
            for name, role, adyn, eid in fix["authors"]
        ]
        w["ai_note"] = (
            (w.get("ai_note") or "")
            + f"\n\n2026-08-09 抽查修：{fix['basis']}；同步 Work.dynasty/period 与作者 dynasty。"
        ).strip()
        w["updated_at"] = now_iso()
        changed_work_ids.add(wid)
        stats["work.author_rewritten"] += 1

    for eid, (dyn, period, basis) in ENTITY_FIXES.items():
        fp = find_entity(eid)
        e = load_json(fp)
        entity_data[eid] = (fp, e)
        if e.get("dynasty") != dyn:
            e["dynasty"] = dyn
            e["dynasty_basis"] = f"qing_round4_audit:{basis}"
            stats[f"entity.dynasty->{dyn}"] += 1
        if e.get("period") != period:
            e["period"] = period
            e["period_basis"] = f"据 dynasty「{dyn}」自动归并"
            stats[f"entity.period->{period}"] += 1
        e["ai_note"] = (
            (e.get("ai_note") or "")
            + f"\n\n2026-08-09 抽查修：{basis}。"
        ).strip()
        e["updated_at"] = now_iso()
        changed_entity_ids.add(eid)

    if commit:
        for fp, w in work_data.values():
            write_json(fp, w)
        for fp, e in entity_data.values():
            write_json(fp, e)

        for shard_fp in sorted((ROOT / "index" / "works").glob("*.json")):
            shard = load_json(shard_fp)
            changed = False
            for wid in changed_work_ids:
                if wid not in shard:
                    continue
                w = work_data[wid][1]
                entry = shard[wid]
                author = (w.get("authors") or [{}])[0].get("name")
                role = (w.get("authors") or [{}])[0].get("role")
                for key, val in [("author", author), ("role", role), ("dynasty", w.get("dynasty")), ("period", w.get("period"))]:
                    if entry.get(key) != val:
                        entry[key] = val
                        changed = True
                        stats[f"index.work.{key}_sync"] += 1
            if changed:
                write_json(shard_fp, shard)
                stats["index.work.shards_changed"] += 1

        for shard_fp in sorted((ROOT / "index" / "entities").glob("*.json")):
            shard = load_json(shard_fp)
            changed = False
            for eid in changed_entity_ids:
                if eid not in shard:
                    continue
                e = entity_data[eid][1]
                for key in ("dynasty", "period"):
                    if shard[eid].get(key) != e.get(key):
                        shard[eid][key] = e.get(key)
                        changed = True
                        stats[f"index.entity.{key}_sync"] += 1
            if changed:
                write_json(shard_fp, shard)
                stats["index.entity.shards_changed"] += 1

        report = {
            "description": "清朝整理 Round 4 抽查结果",
            "fixed": [
                {"work_id": wid, "title": work_data[wid][1].get("title"), "dynasty": fix["dynasty"], "basis": fix["basis"]}
                for wid, fix in WORK_FIXES.items()
            ],
            "deferred": [
                {
                    "work_id": "1evjrac8kbb40",
                    "title": "雅倫",
                    "note": "明费经虞撰、清费密补；费经虞 Entity 当前为清且另有关联 Work，需跨明清个案另查。",
                },
                {
                    "work_id": "1evcsw7pci9kw",
                    "title": "陸希聲春秋通例",
                    "note": "记录 ai_note 已指出陆希声/赵匡《春秋通例》关系复杂；暂不机械改。",
                },
            ],
            "stats": dict(stats),
        }
        write_json(OUT_PATH, report)

    print("=== 清朝整理 Round 4 抽查统计 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:34s} {v:>5}")
    print("changed_work_ids", sorted(changed_work_ids))
    print("changed_entity_ids", sorted(changed_entity_ids))
    print(f"输出: {OUT_PATH}")


if __name__ == "__main__":
    main()
