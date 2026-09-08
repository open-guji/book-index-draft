#!/usr/bin/env python3
"""
fix_qing_round6_songshi_chunqiu_shift.py — 清朝整理 Round 6：抽查发现的宋史春秋类连续撰人串位

问题类：
宋史艺文志春秋类一段连续条目把“前一条书名 + 下一条作者”错拼，造成
《春秋折衷论》《三传释文》《春秋通例》《春秋阐微纂类义统》《集传春秋纂例》《春秋摘微》
等条目的 author/summary 串位，并向 Work.dynasty 传播出清代误标。

本轮只修可由库内多源闭环的连续串位段；不处理后续没有交叉证据的条目。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / ".claude" / "known-issues" / "清朝整理_round6_宋史春秋類串位.json"
SONGSHI_JSON = ROOT / "Work/1/e/v/1evcsw4kt579c/collated_edition/春秋類.json"
SONGSHI_TEXT = ROOT / "Work/1/e/v/1evcsw4kt579c/collated_edition/text/春秋類.md"


FIXES = {
    "1evcsw7ouei2o": {
        "title": "春秋折衷論",
        "summary": "陳岳《春秋折衷論》三十卷，《春秋災異録》六卷，《春秋諡族圖》五卷",
        "source_content": "陳岳《春秋折衷論》三十卷，《春秋災異録》六卷，《春秋諡族圖》五卷",
        "author": {"name": "陳岳", "role": "撰", "dynasty": "唐", "entity_id": "1j967cp1zdr3f"},
        "dynasty": "唐",
        "period": "sui-tang",
        "basis": "清史稿、国史经籍志、经义考均指唐陈岳；宋史整理本该段为连续撰人串位",
    },
    "1evcsw7p3rmdc": {
        "title": "三傳釋文",
        "summary": "陸德明《三傳釋文》八卷",
        "source_content": "陸德明《三傳釋文》八卷",
        "author": {"name": "陸德明", "role": "撰", "dynasty": "隋唐", "entity_id": "1j96a9e5yvbb4"},
        "dynasty": "隋唐",
        "period": "sui-tang",
        "basis": "陆德明为《经典释文》作者；宋史整理本该段为连续撰人串位",
    },
    "1evcsw7pci9kw": {
        "title": "陸希聲春秋通例",
        "summary": "陸希聲《春秋通例》三卷",
        "source_content": "陸希聲《春秋通例》三卷",
        "author": {"name": "陸希聲", "role": "撰", "dynasty": "唐", "entity_id": "1j967afjb6ae7"},
        "dynasty": "唐",
        "period": "sui-tang",
        "basis": "清史稿、崇文总目、国史经籍志、新唐书、经义考均指唐陆希声",
    },
    "1evcsw7pkxo8w": {
        "title": "春秋闡微纂類義統",
        "summary": "趙匡《春秋闡微纂類義統》十卷",
        "source_content": "趙匡《春秋闡微纂類義統》十卷",
        "author": {"name": "趙匡", "role": "撰", "dynasty": "唐", "entity_id": "1j96hjwlxny4i"},
        "dynasty": "唐",
        "period": "sui-tang",
        "basis": "清史稿、经义考均指唐赵匡；宋史整理本该段为连续撰人串位",
    },
    "1evcsw7ptd2ww": {
        "title": "集傳春秋纂例",
        "summary": "陸淳《集傳春秋纂例》十卷，又《春秋辨疑》七卷，《集注春秋微旨》三卷",
        "source_content": "陸淳《集傳春秋纂例》十卷，又《春秋辨疑》七卷，《集注春秋微旨》三卷",
        "author": {"name": "陸淳", "role": "撰", "dynasty": "唐", "entity_id": "1j967avzkeudf"},
        "dynasty": "唐",
        "period": "sui-tang",
        "basis": "四库总目、国史经籍志、书目答问均指唐陆淳；宋史整理本该段为连续撰人串位",
    },
    "1evcsw7q1h91c": {
        "title": "春秋摘微",
        "summary": "盧仝《春秋摘微》四卷",
        "source_content": "盧仝《春秋摘微》四卷",
        "author": {"name": "盧仝", "role": "撰", "dynasty": "唐"},
        "dynasty": "唐",
        "period": "sui-tang",
        "basis": "国史经籍志作卢仝；宋史整理本该段为连续撰人串位。库中暂无可复用卢仝 Entity，本轮不新建",
    },
}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def load_json(fp: Path):
    return json.loads(fp.read_text(encoding="utf-8"))


def write_json(fp: Path, data):
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_work(wid: str) -> Path:
    return next(ROOT.glob(f"Work/?/?/?/{wid}-*.json"))


def find_entity(eid: str) -> Path:
    return next(ROOT.glob(f"Entity/?/?/?/{eid}-*.json"))


def add_work_to_entity(e: dict, wid: str, role: str, stats: Counter):
    works = e.setdefault("works", [])
    if not any(isinstance(x, dict) and x.get("work_id") == wid for x in works):
        works.append({"work_id": wid, "role": role})
        e["updated_at"] = now_iso()
        stats["entity.work_link"] += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    commit = args.commit or not args.dry_run

    stats = Counter()
    changed_work: dict[str, dict] = {}
    changed_entity: dict[str, dict] = {}

    for wid, fix in FIXES.items():
        fp = find_work(wid)
        w = load_json(fp)
        # 修宋史艺文志 indexed_by 的串位摘要。
        for item in w.get("indexed_by") or []:
            if item.get("source_bid") == "1evcsw4kt579c":
                if item.get("summary") != fix["summary"]:
                    item["summary"] = fix["summary"]
                    stats["work.indexed_by_summary_fix"] += 1
                if not item.get("author_info"):
                    item["author_info"] = fix["author"]["name"]
                    stats["work.indexed_by_author_info_added"] += 1
        # 修 Work 作者与朝代。
        new_author = dict(fix["author"])
        new_author["dynasty_basis"] = f"qing_round6_songshi_chunqiu_shift:{fix['basis']}"
        if w.get("authors") != [new_author]:
            w["authors"] = [new_author]
            stats["work.author_rewritten"] += 1
        if w.get("dynasty") != fix["dynasty"]:
            w["dynasty"] = fix["dynasty"]
            w["dynasty_basis"] = f"qing_round6_songshi_chunqiu_shift:{fix['basis']}"
            stats[f"work.dynasty->{fix['dynasty']}"] += 1
        if w.get("period") != fix["period"]:
            w["period"] = fix["period"]
            w["period_basis"] = f"据 dynasty「{fix['dynasty']}」自动归并"
            stats[f"work.period->{fix['period']}"] += 1
        w["ai_note"] = (
            (w.get("ai_note") or "")
            + f"\n\n2026-08-09 抽查修：宋史艺文志春秋类该段存在连续撰人串位；本条按“{fix['summary']}”修正。{fix['basis']}。"
        ).strip()
        w["updated_at"] = now_iso()
        changed_work[wid] = w

        eid = fix["author"].get("entity_id")
        if eid:
            e_fp = find_entity(eid)
            e = load_json(e_fp)
            add_work_to_entity(e, wid, fix["author"]["role"], stats)
            changed_entity[eid] = e

    # 修宋史艺文志整理本 JSON。
    songshi = load_json(SONGSHI_JSON)
    for sec in songshi.get("sections") or []:
        wid = sec.get("work_id")
        if wid in FIXES and sec.get("content") != FIXES[wid]["source_content"]:
            sec["content"] = FIXES[wid]["source_content"]
            stats["section.content_fix"] += 1

    # 修宋史艺文志整理本文本。
    text = SONGSHI_TEXT.read_text(encoding="utf-8")
    replacements = {
        "《春秋折衷論》三十卷《春秋災異録》六卷《春秋諡族圖》五卷陸德明": "陳岳《春秋折衷論》三十卷，《春秋災異録》六卷，《春秋諡族圖》五卷",
        "《三傳釋文》八卷陸希聲": "陸德明《三傳釋文》八卷",
        "《春秋通例》三卷趙匡": "陸希聲《春秋通例》三卷",
        "《春秋闡微纂類義統》十卷陸淳": "趙匡《春秋闡微纂類義統》十卷",
        "《集傳春秋纂例》十卷又《春秋辨疑》七卷《集注春秋微旨》三卷盧仝": "陸淳《集傳春秋纂例》十卷，又《春秋辨疑》七卷，《集注春秋微旨》三卷",
        "《春秋摘微》四卷楊蘊": "盧仝《春秋摘微》四卷",
    }
    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new)
            stats["section.text_fix"] += 1

    if commit:
        for wid, w in changed_work.items():
            write_json(find_work(wid), w)
        for eid, e in changed_entity.items():
            write_json(find_entity(eid), e)
        write_json(SONGSHI_JSON, songshi)
        SONGSHI_TEXT.write_text(text, encoding="utf-8")

        for shard_fp in sorted((ROOT / "index" / "works").glob("*.json")):
            shard = load_json(shard_fp)
            changed = False
            for wid, w in changed_work.items():
                if wid not in shard:
                    continue
                entry = shard[wid]
                author = (w.get("authors") or [{}])[0].get("name") if w.get("authors") else None
                role = (w.get("authors") or [{}])[0].get("role") if w.get("authors") else None
                fields = {
                    "author": author,
                    "role": role,
                    "dynasty": w.get("dynasty"),
                    "period": w.get("period"),
                }
                for key, val in fields.items():
                    if entry.get(key) != val:
                        entry[key] = val
                        changed = True
                        stats[f"index.work.{key}_sync"] += 1
            if changed:
                write_json(shard_fp, shard)
                stats["index.work.shards_changed"] += 1

        report = {
            "description": "清朝整理 Round 6：抽查发现的宋史艺文志春秋类连续撰人串位",
            "problem_class": "宋史艺文志春秋类连续条目把前一书名与后一作者错拼，造成作者与朝代误传。",
            "fixed": [
                {
                    "work_id": wid,
                    "title": fix["title"],
                    "summary_fixed_to": fix["summary"],
                    "dynasty": fix["dynasty"],
                    "basis": fix["basis"],
                }
                for wid, fix in FIXES.items()
            ],
            "scope_boundary": "仅处理陈岳《春秋折衷论》至卢仝《春秋摘微》这一段多源可闭环的连续串位；不处理后续无交叉证据条目。",
            "changed_section_files": [
                str(SONGSHI_JSON.relative_to(ROOT)),
                str(SONGSHI_TEXT.relative_to(ROOT)),
            ],
            "stats": dict(stats),
        }
        write_json(OUT_PATH, report)

    print("=== 清朝整理 Round 6 宋史春秋类串位统计 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:38s} {v:>5}")
    print("changed_work_ids", sorted(changed_work))
    print("changed_entity_ids", sorted(changed_entity))
    print(f"输出: {OUT_PATH}")


if __name__ == "__main__":
    main()
