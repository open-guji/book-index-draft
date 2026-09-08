#!/usr/bin/env python3
"""
fix_qing_round5_remaining_audit.py — 清朝整理 Round 5：剩余疑点与继续抽查

处理：
- 《雅倫》并入既有《雅論》：同为费经虞撰、费密补、二十六卷；《雅倫》视作题名异写/OCR，保留为 additional_titles。
- 费经虞 Entity 由“清”改为“明末清初”，period 留空，避免跨明清人物继续机械传播。
- 《陸希聲春秋通例》：多源明示唐陆希声，修正 Work/author dynasty。
- 《春秋闡微纂類義統》：抽查相邻条目发现赵匡误作清，清史稿/经义考均指唐赵匡，修正 Work 与 Entity。

保留：
- 《九經術疏》宋泉之、《本草要訣》梁嘉庆仍缺外部强证据，不强判 dynasty/period。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / ".claude" / "known-issues" / "清朝整理_round5_疑點抽查.json"
ROUND3_PATH = ROOT / ".claude" / "known-issues" / "清朝整理_round3_未決.json"
ROUND4_PATH = ROOT / ".claude" / "known-issues" / "清朝整理_round4_抽查.json"

YALUN = "1evjrac8kbb40"
YALUN_BOOK = "11qki06nnd8u8"
YALUN_KEEP = "1ev3bf2p9hhj4"
FEI_JINGYU = "1j967afjajtd0"
FEI_MI = "1j967afjav1tz"

LU_WORK = "1evcsw7pci9kw"
LU_EID = "1j967afjb6ae7"
ZHAO_WORK = "1evcsw7pkxo8w"
ZHAO_EID = "1j96hjwlxny4i"

NEW_TANG_CHUNQIU = ROOT / "Work/1/e/v/1evcs059gkvls/collated_edition/春秋類.json"


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


def merge_unique_dicts(dst: list, src: list, keys: tuple[str, ...], stats: Counter, stat_key: str):
    seen = {
        tuple(item.get(k) for k in keys)
        for item in dst
        if isinstance(item, dict)
    }
    for item in src or []:
        if not isinstance(item, dict):
            continue
        key = tuple(item.get(k) for k in keys)
        if key in seen:
            continue
        dst.append(item)
        seen.add(key)
        stats[stat_key] += 1


def add_work_to_entity(e: dict, wid: str, role: str, stats: Counter):
    works = e.setdefault("works", [])
    if not any(isinstance(x, dict) and x.get("work_id") == wid for x in works):
        works.append({"work_id": wid, "role": role})
        e["updated_at"] = now_iso()
        stats["entity.work_link"] += 1


def sync_work_index(work_data: dict[str, dict], deleted: set[str], stats: Counter):
    for shard_fp in sorted((ROOT / "index" / "works").glob("*.json")):
        shard = load_json(shard_fp)
        changed = False
        for wid in list(shard):
            if wid in deleted:
                del shard[wid]
                changed = True
                stats["index.work.deleted"] += 1
        for wid, w in work_data.items():
            if wid not in shard:
                continue
            entry = shard[wid]
            first_author = (w.get("authors") or [{}])[0] if w.get("authors") else {}
            fields = {
                "title": w.get("title"),
                "author": first_author.get("name"),
                "role": first_author.get("role"),
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


def sync_entity_index(entity_data: dict[str, dict], stats: Counter):
    for shard_fp in sorted((ROOT / "index" / "entities").glob("*.json")):
        shard = load_json(shard_fp)
        changed = False
        for eid, e in entity_data.items():
            if eid not in shard:
                continue
            entry = shard[eid]
            for key in ("dynasty", "period"):
                if entry.get(key) != e.get(key):
                    entry[key] = e.get(key)
                    changed = True
                    stats[f"index.entity.{key}_sync"] += 1
        if changed:
            write_json(shard_fp, shard)
            stats["index.entity.shards_changed"] += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    commit = args.commit or not args.dry_run

    stats = Counter()
    changed_work: dict[str, dict] = {}
    changed_entity: dict[str, dict] = {}
    changed_books: dict[str, dict] = {}
    changed_sections = []
    delete_work_paths = []

    # A. 《雅倫》并入《雅論》。
    yalun_fp = find_work(YALUN)
    yalun = load_json(yalun_fp)
    yalu_fp = find_work(YALUN_KEEP)
    yalu = load_json(yalu_fp)
    yalu.setdefault("additional_titles", [])
    if "雅倫" not in yalu["additional_titles"]:
        yalu["additional_titles"].append("雅倫")
        stats["work.additional_title_added"] += 1
    merge_unique_dicts(
        yalu.setdefault("indexed_by", []),
        yalun.get("indexed_by") or [],
        ("source", "source_bid", "title_info", "summary"),
        stats,
        "work.indexed_by_merged",
    )
    merge_unique_dicts(
        yalu.setdefault("resources", []),
        yalun.get("resources") or [],
        ("id", "url"),
        stats,
        "work.resource_merged",
    )
    if any("image" in (r.get("types") or []) for r in yalu.get("resources") or [] if isinstance(r, dict)):
        yalu["_has_image"] = True
    books = yalu.setdefault("books", [])
    for bid in yalun.get("books") or []:
        if bid not in books:
            books.append(bid)
            stats["work.book_merged"] += 1
        b_fp = find_book(bid)
        b = load_json(b_fp)
        if b.get("work_id") != YALUN_KEEP:
            b["work_id"] = YALUN_KEEP
            b["updated_at"] = now_iso()
            changed_books[bid] = b
            stats["book.work_id_redirect"] += 1
    yalu["authors"] = [
        {
            "name": "費經虞",
            "role": "撰",
            "dynasty": "明",
            "entity_id": FEI_JINGYU,
            "dynasty_basis": "qing_round5:四库总目《雅論》与四库存目《雅倫》均作明费经虞撰",
        },
        {
            "name": "費密",
            "role": "補",
            "dynasty": "清",
            "entity_id": FEI_MI,
            "dynasty_basis": "qing_round5:四库总目称其子密增补；四库存目/续修四库均作清费密补",
        },
    ]
    yalu["dynasty"] = "明"
    yalu["period"] = "ming"
    yalu["dynasty_basis"] = "qing_round5:《雅論/雅倫》主撰者为明费经虞，清费密为补者"
    yalu["period_basis"] = "据 dynasty「明」自动归并"
    yalu["ai_note"] = (
        (yalu.get("ai_note") or "")
        + "\n\n2026-08-09 抽查修：将《雅倫》1evjrac8kbb40 并入本条。《雅論》《雅倫》同为二十六卷、费经虞撰、费密补；"
          "四库总目与四库存目均支持主撰者作明费经虞。保留“雅倫”为 additional_titles，并迁入续修四库/存目著录、资源与书册。"
    ).strip()
    yalu["updated_at"] = now_iso()
    changed_work[YALUN_KEEP] = yalu
    delete_work_paths.append(str(yalun_fp))
    stats["work.duplicate_merged"] += 1

    fei_jy_fp = find_entity(FEI_JINGYU)
    fei_jy = load_json(fei_jy_fp)
    if fei_jy.get("dynasty") != "明末清初":
        fei_jy["dynasty"] = "明末清初"
        fei_jy["dynasty_basis"] = "qing_round5:1599-1671 跨明清；四库总目《雅論》作明费经虞，清史稿《蜀诗》又录其清代著作"
        stats["entity.dynasty->明末清初"] += 1
    if fei_jy.get("period") is not None:
        fei_jy["period"] = None
        stats["entity.period->null"] += 1
    fei_jy["period_basis"] = "跨 ming/qing，逐条判"
    fei_jy["ai_note"] = (
        (fei_jy.get("ai_note") or "")
        + "\n\n2026-08-09 抽查修：费经虞生卒 1599-1671，且同库《雅論》作明费经虞、《蜀诗》见清史稿著录，"
          "改为跨代值“明末清初”，period 留空，作品层逐条判。"
    ).strip()
    fei_jy["updated_at"] = now_iso()
    changed_entity[FEI_JINGYU] = fei_jy

    fei_mi_fp = find_entity(FEI_MI)
    fei_mi = load_json(fei_mi_fp)
    add_work_to_entity(fei_mi, YALUN_KEEP, "補", stats)
    changed_entity[FEI_MI] = fei_mi

    # B. 《陸希聲春秋通例》移出清代误传。
    lu_fp = find_work(LU_WORK)
    lu = load_json(lu_fp)
    lu["authors"] = [
        {
            "name": "陸希聲",
            "role": "撰",
            "dynasty": "唐",
            "entity_id": LU_EID,
            "dynasty_basis": "qing_round5:清史稿、崇文总目、新唐书、国史经籍志、经义考均指陆希声/唐陆希声",
        }
    ]
    lu["dynasty"] = "唐"
    lu["period"] = "sui-tang"
    lu["dynasty_basis"] = "qing_round5:多种书目著录指唐陆希声《春秋通例》"
    lu["period_basis"] = "据 dynasty「唐」自动归并"
    lu["ai_note"] = (
        (lu.get("ai_note") or "")
        + "\n\n2026-08-09 抽查修：清史稿作“唐陆希声《春秋通例》一卷”，崇文总目作“唐陆希声撰”，"
          "国史经籍志、新唐书、经义考亦均指陆希声；本条此前 dynasty=清 系作者字段误传，今改唐/sui-tang，并回连陆希声 Entity。"
    ).strip()
    lu["updated_at"] = now_iso()
    changed_work[LU_WORK] = lu

    lu_e_fp = find_entity(LU_EID)
    lu_e = load_json(lu_e_fp)
    add_work_to_entity(lu_e, LU_WORK, "撰", stats)
    changed_entity[LU_EID] = lu_e

    nt = load_json(NEW_TANG_CHUNQIU)
    nt_sections = nt.get("sections") if isinstance(nt, dict) else nt
    nt_changed = False
    for item in nt_sections or []:
        if isinstance(item, dict) and item.get("title") == "陸希聲春秋通例" and item.get("work_id") != LU_WORK:
            item["work_id"] = LU_WORK
            nt_changed = True
            stats["section.work_id_redirect"] += 1
    if nt_changed:
        changed_sections.append(str(NEW_TANG_CHUNQIU.relative_to(ROOT)))

    # C. 抽查相邻条目：《春秋闡微纂類義統》赵匡误作清。
    zhao_fp = find_work(ZHAO_WORK)
    zhao = load_json(zhao_fp)
    zhao["authors"] = [
        {
            "name": "趙匡",
            "role": "撰",
            "dynasty": "唐",
            "entity_id": ZHAO_EID,
            "dynasty_basis": "qing_round5:清史稿作唐赵匡《春秋阐微纂类义统》；经义考作赵匡",
        }
    ]
    zhao["dynasty"] = "唐"
    zhao["period"] = "sui-tang"
    zhao["dynasty_basis"] = "qing_round5:清史稿作唐赵匡《春秋阐微纂类义统》，经义考同指赵匡"
    zhao["period_basis"] = "据 dynasty「唐」自动归并"
    zhao["ai_note"] = (
        (zhao.get("ai_note") or "")
        + "\n\n2026-08-09 抽查修：清史稿著录“唐赵匡《春秋阐微纂类义统》一卷”，经义考亦以赵匡为撰者；"
          "此前 dynasty=清 系误传，今改唐/sui-tang，并修正赵匡 Entity。宋史艺文志本地整理本该邻近段仍疑有撰人串位，另列观察。"
    ).strip()
    zhao["updated_at"] = now_iso()
    changed_work[ZHAO_WORK] = zhao

    zhao_e_fp = find_entity(ZHAO_EID)
    zhao_e = load_json(zhao_e_fp)
    if zhao_e.get("dynasty") != "唐":
        zhao_e["dynasty"] = "唐"
        zhao_e["dynasty_basis"] = "qing_round5:仅关联《春秋阐微纂类义统》，来源指唐赵匡"
        stats["entity.dynasty->唐"] += 1
    if zhao_e.get("period") != "sui-tang":
        zhao_e["period"] = "sui-tang"
        zhao_e["period_basis"] = "据 dynasty「唐」自动归并"
        stats["entity.period->sui-tang"] += 1
    zhao_e["ai_note"] = (
        (zhao_e.get("ai_note") or "")
        + "\n\n2026-08-09 抽查修：前次因 Work 误传为清而卸除唐代判断；现据清史稿/经义考复核，"
          "本人物为唐赵匡，关联《春秋阐微纂类义统》。"
    ).strip()
    zhao_e["updated_at"] = now_iso()
    changed_entity[ZHAO_EID] = zhao_e

    if commit:
        for wid, data in changed_work.items():
            write_json(find_work(wid), data)
        for eid, data in changed_entity.items():
            write_json(find_entity(eid), data)
        for bid, data in changed_books.items():
            write_json(find_book(bid), data)
        if nt_changed:
            write_json(NEW_TANG_CHUNQIU, nt)

        sync_work_index(changed_work, {YALUN}, stats)
        sync_entity_index(changed_entity, stats)

        round3 = {
            "description": "清朝整理 Round 3 后未决清单",
            "scope": "Round 5 后复核：宋泉之、梁嘉庆仍只修残名/误关联，不强判朝代。",
            "remaining_work_items": [
                {
                    "work_id": "1evgorqt3jw8w",
                    "title": "九經術疏",
                    "authors": ["宋泉之"],
                    "note": "作者全名已修；另见《旧唐书经籍志》有宋泉之《九章术疏》九卷，疑题名讹混，但仍缺外部强证据，不补 dynasty/period。",
                },
                {
                    "work_id": "1evgq4n14oge8",
                    "title": "本草要訣",
                    "authors": ["梁嘉慶"],
                    "note": "作者全名已修；外部检索未得可靠佐证，暂不补 dynasty/period。",
                },
            ],
            "merged_duplicate_work_ids": ["1evcs0rquay2o", "1evkpxw3uuups"],
            "stats_note": "本文件保留 Round 3 残名未决；Round 5 另见 清朝整理_round5_疑點抽查.json。",
        }
        write_json(ROUND3_PATH, round3)

        round4 = load_json(ROUND4_PATH)
        round4["deferred"] = [
            {
                "work_id": "1evgorqt3jw8w",
                "title": "九經術疏",
                "note": "移交 Round 5 后仍未决：疑与宋泉之《九章术疏》相关，但缺外部强证据。",
            },
            {
                "work_id": "1evgq4n14oge8",
                "title": "本草要訣",
                "note": "移交 Round 5 后仍未决：梁嘉庆缺外部强证据。",
            },
        ]
        round4["round5_note"] = "原 deferred《雅倫》《陸希聲春秋通例》已在 Round 5 处理。"
        write_json(ROUND4_PATH, round4)

        report = {
            "description": "清朝整理 Round 5：剩余疑点与继续抽查",
            "fixed": [
                {
                    "work_id": YALUN_KEEP,
                    "title": "雅論",
                    "merged_from": YALUN,
                    "dynasty": "明",
                    "basis": "《雅論/雅倫》均为二十六卷；四库总目、四库存目支持明费经虞撰，清费密补。",
                },
                {
                    "work_id": LU_WORK,
                    "title": "陸希聲春秋通例",
                    "dynasty": "唐",
                    "basis": "清史稿、崇文总目、新唐书、国史经籍志、经义考均指陆希声/唐陆希声。",
                },
                {
                    "work_id": ZHAO_WORK,
                    "title": "春秋闡微纂類義統",
                    "dynasty": "唐",
                    "basis": "清史稿作唐赵匡；经义考作赵匡。",
                },
            ],
            "entity_fixed": [
                {
                    "entity_id": FEI_JINGYU,
                    "name": "費經虞",
                    "dynasty": "明末清初",
                    "period": None,
                    "basis": "1599-1671 跨明清；作品层逐条判。",
                },
                {
                    "entity_id": ZHAO_EID,
                    "name": "趙匡",
                    "dynasty": "唐",
                    "period": "sui-tang",
                    "basis": "关联作品复核为唐赵匡。",
                },
            ],
            "remaining": [
                {
                    "work_id": "1evgorqt3jw8w",
                    "title": "九經術疏",
                    "reason": "宋泉之题名/人名已修；疑与《九章术疏》相邻，但外部证据不足。",
                },
                {
                    "work_id": "1evgq4n14oge8",
                    "title": "本草要訣",
                    "reason": "梁嘉庆缺外部强证据。",
                },
            ],
            "audit_observations": [
                "抽查《春秋通例》相邻条目时发现《春秋闡微纂類義統》赵匡误作清，已修。",
                "新唐书春秋类整理本中“陸希聲春秋通例”原误指向《春秋》原典 Work，已重定向到本条。",
                "宋史艺文志本地整理本春秋类邻近数条疑有撰人串位，暂只修作品层高置信朝代，不批量改源整理本。",
            ],
            "changed_section_files": changed_sections,
            "delete_work_files_after_review": delete_work_paths,
            "stats": dict(stats),
        }
        write_json(OUT_PATH, report)

    print("=== 清朝整理 Round 5 统计 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:36s} {v:>5}")
    print("changed_work_ids", sorted(changed_work))
    print("changed_entity_ids", sorted(changed_entity))
    print("changed_book_ids", sorted(changed_books))
    print("changed_section_files", changed_sections)
    print("delete_work_files", delete_work_paths)
    print(f"输出: {OUT_PATH}")


if __name__ == "__main__":
    main()
