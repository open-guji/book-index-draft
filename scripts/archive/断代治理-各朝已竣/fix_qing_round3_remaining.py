#!/usr/bin/env python3
"""
fix_qing_round3_remaining.py — 清朝整理 Round 3：处理 Round 2 剩余疑点与抽查发现

范围：
- 《九经术疏》：原“泉之”是残名，志书原文“宋泉之”应作人名；清人吴省兰关联错误。
- 《本草要诀》：原“嘉庆”误连清仁宗；志书原文“梁嘉庆”应作人名，朝代不强判。
- 《御选宋诗》：补清代 dynasty/period 与张豫章 Entity 关联；合并同名无作者 Work。

安全边界：
- 不据“宋泉之”“梁嘉庆”首字强判朝代；二者 dynasty/period 留空。
- 不删除 Book；只把重复 Work 的 Book 回指到保留 Work，并删除空壳重复 Work。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / ".claude" / "known-issues" / "清朝整理_round3_未決.json"

KEEP_JJ = "1evgorqt3jw8w"      # 九經術䟽（國史經籍志）
DUP_JJ = "1evcs0rquay2o"       # 宋泉之九經術疏（新唐書藝文志，題名含作者）
KEEP_YS = "1evkphixywge8"      # 御選宋詩（有張豫章修訂 note）
DUP_YS = "1evkpxw3uuups"       # 御選宋詩（空作者，文淵閣本）
ZHANG_EID = "1j967afjb6adi"
WUSL_EID = "1jae2gjvh8suw"
JIAQING_EID = "1j96hjwlylnq9"


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


def find_book(bid: str) -> Path:
    return next(ROOT.glob(f"Book/?/?/?/{bid}-*.json"))


def remove_work_from_entity(e, wid, stats):
    old = e.get("works") or []
    new = [x for x in old if not (isinstance(x, dict) and x.get("work_id") == wid)]
    if len(new) != len(old):
        e["works"] = new
        e["updated_at"] = now_iso()
        stats["entity.work_unlink"] += 1
        return True
    return False


def add_work_to_entity(e, wid, role, stats):
    works = e.setdefault("works", [])
    if not any(isinstance(x, dict) and x.get("work_id") == wid for x in works):
        works.append({"work_id": wid, "role": role})
        e["updated_at"] = now_iso()
        stats["entity.work_link"] += 1
        return True
    return False


def merge_indexed_by(dst, src, stats):
    items = dst.setdefault("indexed_by", [])
    seen = {
        (x.get("source"), x.get("source_bid"), x.get("title_info"), x.get("summary"))
        for x in items
        if isinstance(x, dict)
    }
    for x in src.get("indexed_by", []) or []:
        if not isinstance(x, dict):
            continue
        key = (x.get("source"), x.get("source_bid"), x.get("title_info"), x.get("summary"))
        if key not in seen:
            items.append(x)
            seen.add(key)
            stats["work.indexed_by_merged"] += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    commit = args.commit or not args.dry_run

    stats = Counter()
    changed_work_ids = set()
    changed_entity_ids = set()
    changed_book_ids = set()
    deleted_work_paths = []

    # A. 《九經術疏》：残名补全，误关联清吴省兰解除，并合并新唐书空壳条目。
    jj_fp = find_work(KEEP_JJ)
    jj = load_json(jj_fp)
    dup_jj_fp = find_work(DUP_JJ)
    dup_jj = load_json(dup_jj_fp)
    merge_indexed_by(jj, dup_jj, stats)
    if jj.get("title") != "九經術疏":
        jj["title"] = "九經術疏"
        stats["work.title_normalized"] += 1
    jj["authors"] = [{
        "name": "宋泉之",
        "role": "撰",
        "dynasty_basis": "qing_round3:志书原文“宋泉之”作撰人全名，非“宋代泉之”",
    }]
    jj["dynasty"] = None
    jj["period"] = None
    jj.pop("dynasty_basis", None)
    jj.pop("period_basis", None)
    jj["ai_note"] = (
        (jj.get("ai_note") or "")
        + "\n\n2026-08-09 修：原作者“泉之”误连清人吴省兰；据《国史经籍志》“（宋泉之）”与《新唐书艺文志》“宋泉之九经术疏九卷”，"
          "“宋泉之”应作撰人全名。朝代无强证据，暂不补 dynasty/period。合并原空壳 Work 1evcs0rquay2o。"
    ).strip()
    jj["updated_at"] = now_iso()
    changed_work_ids.add(KEEP_JJ)
    stats["work.author_fix"] += 1
    stats["work.duplicate_merged"] += 1

    wusl_fp = find_entity(WUSL_EID)
    wusl = load_json(wusl_fp)
    if remove_work_from_entity(wusl, KEEP_JJ, stats):
        changed_entity_ids.add(WUSL_EID)

    # B. 《本草要诀》：残名补全，解除清仁宗误关联。
    bc_fp = find_work("1evgq4n14oge8")
    bc = load_json(bc_fp)
    bc["authors"] = [{
        "name": "梁嘉慶",
        "role": "撰",
        "dynasty_basis": "qing_round3:国史经籍志原文“梁嘉庆”作撰人全名，非清嘉庆帝",
    }]
    bc["dynasty"] = None
    bc["period"] = None
    bc.pop("dynasty_basis", None)
    bc.pop("period_basis", None)
    bc["ai_note"] = (
        (bc.get("ai_note") or "")
        + "\n\n2026-08-09 修：原作者“嘉庆”误连清仁宗。按《国史经籍志》“《本草要诀》一卷（梁嘉庆）”，"
          "作者改为梁嘉庆；朝代无强证据，暂不补 dynasty/period。"
    ).strip()
    bc["updated_at"] = now_iso()
    changed_work_ids.add("1evgq4n14oge8")
    stats["work.author_fix"] += 1

    jq_fp = find_entity(JIAQING_EID)
    jq = load_json(jq_fp)
    if remove_work_from_entity(jq, "1evgq4n14oge8", stats):
        changed_entity_ids.add(JIAQING_EID)

    # C. 《御选宋诗》：补清代字段、张豫章 Entity，合并空作者同名 Work。
    ys_fp = find_work(KEEP_YS)
    ys = load_json(ys_fp)
    dup_ys_fp = find_work(DUP_YS)
    dup_ys = load_json(dup_ys_fp)
    ys["dynasty"] = "清"
    ys["period"] = "qing"
    ys["dynasty_basis"] = "qing_round3:ai_note 已据康熙四十八年张豫章刻本与四库薈要本说明实编者"
    ys["period_basis"] = "据 dynasty「清」自动归并"
    ys["authors"] = [{
        "name": "張豫章",
        "role": "敕編",
        "dynasty": "清",
        "entity_id": ZHANG_EID,
        "dynasty_basis": "qing_round3:張豫章 Entity 已为清代",
    }]
    books = ys.setdefault("books", [])
    for bid in dup_ys.get("books", []) or []:
        if bid not in books:
            books.append(bid)
            stats["work.book_merged"] += 1
            b_fp = find_book(bid)
            b = load_json(b_fp)
            if b.get("work_id") != KEEP_YS:
                b["work_id"] = KEEP_YS
                b["updated_at"] = now_iso()
                write_json(b_fp, b) if commit else None
                changed_book_ids.add(bid)
                stats["book.work_id_redirect"] += 1
    ys["ai_note"] = (
        (ys.get("ai_note") or "")
        + "\n\n2026-08-09 修：补 dynasty=清、period=qing，并回连张豫章 Entity。合并同名空作者 Work 1evkpxw3uuups 之文渊阁本书册。"
    ).strip()
    ys["updated_at"] = now_iso()
    changed_work_ids.add(KEEP_YS)
    stats["work.qing_fixed"] += 1
    stats["work.duplicate_merged"] += 1

    zhang_fp = find_entity(ZHANG_EID)
    zhang = load_json(zhang_fp)
    if add_work_to_entity(zhang, KEEP_YS, "敕編", stats):
        changed_entity_ids.add(ZHANG_EID)

    # D. 更新整理本 section 的 duplicate work_id 指向。
    section_updates = [
        (ROOT / "Work/1/e/v/1evcs059gkvls/collated_edition/曆算類.json", DUP_JJ, KEEP_JJ),
    ]
    changed_section_files = []
    for fp, old, new in section_updates:
        data = load_json(fp)
        changed = False
        for sec in data:
            if isinstance(sec, dict) and sec.get("work_id") == old:
                sec["work_id"] = new
                changed = True
                stats["section.work_id_redirect"] += 1
        if changed:
            if commit:
                write_json(fp, data)
            changed_section_files.append(str(fp.relative_to(ROOT)))

    # E. 写回索引与删除重复 Work。
    duplicate_work_ids = {DUP_JJ, DUP_YS}
    deleted_work_paths = [str(dup_jj_fp), str(dup_ys_fp)]

    if commit:
        write_json(jj_fp, jj)
        write_json(bc_fp, bc)
        write_json(ys_fp, ys)
        write_json(wusl_fp, wusl)
        write_json(jq_fp, jq)
        write_json(zhang_fp, zhang)

        for shard_fp in sorted((ROOT / "index" / "works").glob("*.json")):
            shard = load_json(shard_fp)
            changed = False
            for wid in list(shard):
                if wid in duplicate_work_ids:
                    del shard[wid]
                    changed = True
                    stats["index.work.deleted"] += 1
            for wid in changed_work_ids:
                if wid not in shard:
                    continue
                w = {KEEP_JJ: jj, "1evgq4n14oge8": bc, KEEP_YS: ys}[wid]
                entry = shard[wid]
                if entry.get("title") != w.get("title"):
                    entry["title"] = w.get("title")
                    changed = True
                    stats["index.work.title_sync"] += 1
                author = (w.get("authors") or [{}])[0].get("name") if w.get("authors") else None
                if entry.get("author") != author:
                    entry["author"] = author
                    changed = True
                    stats["index.work.author_sync"] += 1
                role = (w.get("authors") or [{}])[0].get("role") if w.get("authors") else None
                if entry.get("role") != role:
                    entry["role"] = role
                    changed = True
                    stats["index.work.role_sync"] += 1
                for key in ("dynasty", "period"):
                    if entry.get(key) != w.get(key):
                        entry[key] = w.get(key)
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
                e = {WUSL_EID: wusl, JIAQING_EID: jq, ZHANG_EID: zhang}[eid]
                entry = shard[eid]
                for key in ("dynasty", "period"):
                    if entry.get(key) != e.get(key):
                        entry[key] = e.get(key)
                        changed = True
                        stats[f"index.entity.{key}_sync"] += 1
            if changed:
                write_json(shard_fp, shard)
                stats["index.entity.shards_changed"] += 1

        for fp in (dup_jj_fp, dup_ys_fp):
            fp.unlink()

        unresolved = {
            "description": "清朝整理 Round 3 后未决清单",
            "scope": "处理 Round 2 剩余 Work 疑点；宋泉之、梁嘉庆只修残名/误关联，不强判朝代。",
            "remaining_work_items": [
                {
                    "work_id": KEEP_JJ,
                    "title": "九經術疏",
                    "authors": ["宋泉之"],
                    "note": "作者全名已修；朝代缺外部强证据，暂不补 dynasty/period。",
                },
                {
                    "work_id": "1evgq4n14oge8",
                    "title": "本草要訣",
                    "authors": ["梁嘉慶"],
                    "note": "作者全名已修；朝代缺外部强证据，暂不补 dynasty/period。",
                },
            ],
            "merged_duplicate_work_ids": sorted(duplicate_work_ids),
            "changed_section_files": changed_section_files,
            "stats": dict(stats),
        }
        write_json(OUT_PATH, unresolved)

    print("=== 清朝整理 Round 3 统计 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:32s} {v:>5}")
    print("changed_work_ids", sorted(changed_work_ids))
    print("changed_entity_ids", sorted(changed_entity_ids))
    print("changed_book_ids", sorted(changed_book_ids))
    print("delete_work_files", deleted_work_paths)
    print(f"输出: {OUT_PATH}")


if __name__ == "__main__":
    main()
