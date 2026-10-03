#!/usr/bin/env python3
"""
investigate_qing_round2.py — 清朝整理 Round 2 调查脚本

只读输出：
- Round 1 未决 Work 的作者字段、entity_id、Work 来源、描述、同名 Entity 分布。
- Round 1 未决 Entity 的 CBDB c_dy / dynasty 缓存、关联 Work 与同名 Entity。
- 依据库内证据给出初步建议：清 / 宋 / 南朝 / 明 / 保留人工。
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_PATH = ROOT / ".claude" / "known-issues" / "清朝整理_round1_未決.json"
OUT_PATH = ROOT / ".claude" / "known-issues" / "清朝整理_round2_调查.json"
CBDB_CACHE = ROOT / ".claude" / "known-issues" / "cbdb_dy_cache.json"

DY_MAP = {
    "5": "南朝宋",
    "6": "唐",
    "15": "宋",
    "16": "遼",
    "17": "金",
    "18": "元",
    "19": "明",
    "20": "清",
    "21": "清",
}

PERIOD_BY_DYNASTY = {
    "南朝宋": "nanbeichao",
    "南朝梁": "nanbeichao",
    "宋": "song",
    "北宋": "song",
    "南宋": "song",
    "明": "ming",
    "清": "qing",
    "元": "liao-jin-yuan",
}


def load_json(fp: Path):
    return json.loads(fp.read_text(encoding="utf-8"))


def iter_work_files():
    return sorted(ROOT.glob("Work/?/?/?/*.json"))


def iter_entity_files():
    return sorted(ROOT.glob("Entity/?/?/?/*.json"))


def cbdb_dynasty(cache, cbdb_id):
    if cbdb_id is None:
        return None
    rec = cache.get(str(cbdb_id)) or cache.get(int(cbdb_id)) if isinstance(cache, dict) else None
    if not rec:
        return None
    if isinstance(rec, dict):
        raw = rec.get("c_dy") or rec.get("dynasty") or rec.get("dy")
    else:
        raw = rec
    raw = str(raw) if raw is not None else None
    return DY_MAP.get(raw, raw)


def summarize_work(w):
    desc = w.get("description")
    if isinstance(desc, str):
        desc_text = desc[:300]
    elif desc is None:
        desc_text = ""
    else:
        desc_text = json.dumps(desc, ensure_ascii=False)[:300]
    return {
        "work_id": w.get("id"),
        "title": w.get("title"),
        "dynasty": w.get("dynasty"),
        "period": w.get("period"),
        "authors": w.get("authors", []),
        "indexed_by": w.get("indexed_by", []),
        "description": desc_text,
    }


def author_entity_ids(w):
    ids = []
    for a in w.get("authors", []) or []:
        if isinstance(a, dict) and a.get("entity_id"):
            ids.append(a.get("entity_id"))
    return ids


def infer_from_title(title):
    if not title:
        return None, None
    qing_tokens = ["欽定", "御製", "皇朝", "圓明園", "兒女英雄傳", "明通鑑綱目", "清"]
    song_tokens = ["宋", "皇宋", "中興兩朝", "元城", "糖霜譜", "碧雞漫志", "嬾真子"]
    nan_tokens = ["江文通", "何水部", "道德經藏室纂微", "莊子章句音義"]
    ming_tokens = ["明通鑑", "明"]
    if any(t in title for t in nan_tokens):
        return "nanbeichao_or_song", "title_signal"
    if any(t in title for t in song_tokens):
        return "song", "title_signal"
    if any(t in title for t in qing_tokens):
        return "清", "title_signal"
    if any(t in title for t in ming_tokens):
        return "明", "title_signal"
    return None, None


def main():
    unresolved = load_json(IN_PATH)
    cache = load_json(CBDB_CACHE) if CBDB_CACHE.exists() else {}
    works = {}
    entities = {}
    entities_by_name = defaultdict(list)

    for fp in iter_work_files():
        w = load_json(fp)
        works[w.get("id", fp.stem)] = w
    for fp in iter_entity_files():
        e = load_json(fp)
        eid = e.get("id", fp.stem)
        entities[eid] = e
        entities_by_name[e.get("primary_name")].append(e)

    report = {
        "description": "清朝整理 Round 2 调查：库内证据 + CBDB cache + 同名 Entity 分布",
        "work_items": [],
        "entity_period_missing": [],
        "entity_period_conflict": [],
    }

    for item in unresolved["remaining_work_empty_dynasty_authors_all_qing_non_qing_period"]:
        wid = item["work_id"]
        w = works.get(wid, {})
        authors = []
        author_entity_periods = set()
        author_entity_dynasties = set()
        cbdb_dyns = set()
        same_name_entities = {}
        for a in w.get("authors", []) or []:
            if not isinstance(a, dict):
                continue
            eid = a.get("entity_id")
            ent = entities.get(eid) if eid else None
            cbdb_id = (ent.get("external_ids") or {}).get("cbdb_id") if ent and isinstance(ent.get("external_ids"), dict) else None
            cd = cbdb_dynasty(cache, cbdb_id)
            authors.append({
                "name": a.get("name"),
                "author_dynasty": a.get("dynasty"),
                "entity_id": eid,
                "entity_dynasty": ent.get("dynasty") if ent else None,
                "entity_period": ent.get("period") if ent else None,
                "cbdb_id": cbdb_id,
                "cbdb_dynasty": cd,
            })
            if ent and ent.get("period"):
                author_entity_periods.add(ent.get("period"))
            if ent and ent.get("dynasty"):
                author_entity_dynasties.add(ent.get("dynasty"))
            if cd:
                cbdb_dyns.add(cd)
            if a.get("name"):
                same_name_entities[a.get("name")] = [
                    {
                        "entity_id": e.get("id"),
                        "dynasty": e.get("dynasty"),
                        "period": e.get("period"),
                        "cbdb_id": (e.get("external_ids") or {}).get("cbdb_id") if isinstance(e.get("external_ids"), dict) else None,
                        "work_count": len(e.get("works", []) or []),
                    }
                    for e in entities_by_name.get(a.get("name"), [])
                ]

        title_guess, title_basis = infer_from_title(w.get("title"))
        suggestion = None
        basis = []
        if cbdb_dyns and len(cbdb_dyns) == 1:
            d = next(iter(cbdb_dyns))
            suggestion = d
            basis.append(f"cbdb_cache:{d}")
        elif len(author_entity_dynasties) == 1:
            d = next(iter(author_entity_dynasties))
            suggestion = d
            basis.append(f"entity_dynasty:{d}")
        if title_guess and (suggestion is None or title_guess == suggestion):
            suggestion = title_guess
            basis.append(title_basis)
        elif title_guess and suggestion and title_guess != suggestion:
            basis.append(f"title_conflict:{title_guess}")

        report["work_items"].append({
            **summarize_work(w),
            "authors_expanded": authors,
            "same_name_entities": same_name_entities,
            "suggestion": suggestion,
            "basis": basis,
        })

    for key, out_key in [
        ("remaining_entity_qing_period_missing", "entity_period_missing"),
        ("remaining_entity_qing_period_conflict", "entity_period_conflict"),
    ]:
        for item in unresolved[key]:
            e = entities.get(item["entity_id"], {})
            cbdb_id = (e.get("external_ids") or {}).get("cbdb_id") if isinstance(e.get("external_ids"), dict) else None
            cd = cbdb_dynasty(cache, cbdb_id)
            linked_works = [summarize_work(works.get(x.get("work_id"), {})) for x in e.get("works", []) or []]
            same = [
                {
                    "entity_id": x.get("id"),
                    "dynasty": x.get("dynasty"),
                    "period": x.get("period"),
                    "cbdb_id": (x.get("external_ids") or {}).get("cbdb_id") if isinstance(x.get("external_ids"), dict) else None,
                    "work_count": len(x.get("works", []) or []),
                }
                for x in entities_by_name.get(e.get("primary_name"), [])
            ]
            report[out_key].append({
                "entity_id": e.get("id"),
                "name": e.get("primary_name"),
                "dynasty": e.get("dynasty"),
                "period": e.get("period"),
                "cbdb_id": cbdb_id,
                "cbdb_dynasty": cd,
                "same_name_entities": same,
                "linked_works": linked_works,
                "suggestion": cd or (e.get("dynasty") if e.get("dynasty") in PERIOD_BY_DYNASTY else None),
            })

    OUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"输出: {OUT_PATH}")
    print(f"work_items={len(report['work_items'])}")
    print(f"entity_period_missing={len(report['entity_period_missing'])}")
    print(f"entity_period_conflict={len(report['entity_period_conflict'])}")
    from collections import Counter
    print("work_suggestion_counts:", Counter(x.get("suggestion") for x in report["work_items"]))
    print("entity_missing_suggestion_counts:", Counter(x.get("suggestion") for x in report["entity_period_missing"]))
    print("entity_conflict_suggestion_counts:", Counter(x.get("suggestion") for x in report["entity_period_conflict"]))


if __name__ == "__main__":
    main()
