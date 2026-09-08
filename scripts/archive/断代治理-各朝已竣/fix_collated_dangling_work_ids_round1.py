#!/usr/bin/env python3
"""修復整理本 section 中明確可重連的 work_ids 陣列項。

大型 collated JSON 只做原文替換；目標 Work 另補 emendated_by 回鏈。
"""

import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TODAY = "2026-08-09"
SOURCE_BID = "1evdlszdhf5z4"
SOURCE_TITLE = "隋書經籍志考證"

FIXES = [
    ("Work/1/e/v/1evdlszdhf5z4/collated_edition/經部十·小學類.json", 34, "1evetxczk47wg", "1evr5e3m8fpxs", "梁有《異字》一卷，朱育撰"),
    ("Work/1/e/v/1evdlszdhf5z4/collated_edition/經部十·小學類.json", 55, "1evetxczpqhog", "1evgord0rwydc", "梁有《常用字訓》一卷，殷仲堪撰"),
    ("Work/1/e/v/1evdlszdhf5z4/collated_edition/經部十·小學類.json", 57, "1evetxczraoe8", "1evfubyxuzabk", "梁有《文字要記》三卷，王義撰"),
    ("Work/1/e/v/1evdlszdhf5z4/collated_edition/集部二之一·別集類一.json", 11, "1evcmoan00wlc", "1evr5e3mj1sky", "《董仲舒集》一卷"),
    ("Work/1/e/v/1evdlszdhf5z4/collated_edition/經部六·春秋類.json", 3, "1evc5pdnauscg", "1evcpctyh2eww", "春秋左氏傳解誼三十一卷漢九江太守服虔注"),
    ("Work/1/e/v/1evdlszdhf5z4/collated_edition/經部六·春秋類.json", 116, "1evetzkh8nzsw", "1evfhb6yxhc74", "糜信理何氏漢議二卷 魏人撰"),
    ("Work/1/e/v/1evdlszdhf5z4/collated_edition/經部九·異說類.json", 26, "1evetxcxlvtog", "1evgoqv1c65fk", "梁有《孝經雌雄圖》三卷"),
    ("Work/1/e/v/1evdlszdhf5z4/collated_edition/經部九·異說類.json", 38, "1evetxcxwhw5c", "1evfubyhzr08w", "梁有郭文《金雄記》一卷"),
    ("Work/1/e/v/1evdlszdhf5z4/collated_edition/經部八·論語類.json", 45, "1evetxcyjwow0", "1evfubu4ppeyo", "梁有《論語隱》一卷，郭象撰，亡。"),
    ("Work/1/e/v/1evdlszdhf5z4/collated_edition/經部八·論語類.json", 60, "1evetxcyutzwg", "1evfubuhtczr4", "梁有《新書對張論》十卷，虞喜撰，亡。"),
    ("Work/1/e/v/1evdlszdhf5z4/collated_edition/經部八·論語類.json", 85, "1evc5pedns7pc", "1evgor83scydc", "爾雅圖十卷 郭璞撰"),
    ("Work/1/e/v/1evdlszdhf5z4/collated_edition/經部八·論語類.json", 86, "1evetxcz2boxs", "1evfubxke6fb4", "梁有《爾雅圖讚》二卷，郭璞撰，亡。"),
    ("Work/1/e/v/1evdlszdhf5z4/collated_edition/子部十一·天文家類.json", 4, "1evcmndtazx8g", "1evftes775fk0", "《渾天象注》一卷"),
    ("Work/1/e/v/1evdlszdhf5z4/collated_edition/史部十·雜傳類.json", 144, "1evcml3gi2sxs", "1ev3bcqnglvr4", "列仙傳贊三卷"),
    ("Work/1/e/v/1evdlszdhf5z4/collated_edition/史部十·雜傳類.json", 145, "1evcml3gi2sxs", "1ev3bcqnglvr4", "列仙傳贊二卷"),
]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def work_index():
    idx = {}
    for shard in "0123456789abcdef":
        idx.update(load_json(ROOT / "index" / "works" / f"{shard}.json"))
    return idx


def main():
    idx = work_index()
    file_groups = defaultdict(list)
    seen_pairs = defaultdict(set)
    work_titles = defaultdict(list)
    fixed = []

    for file, section_index, old, new, title_info in FIXES:
        pair = (old, new)
        if pair not in seen_pairs[file]:
            file_groups[file].append(pair)
            seen_pairs[file].add(pair)
        if title_info not in work_titles[new]:
            work_titles[new].append(title_info)
        fixed.append(
            {
                "file": file,
                "section_index": section_index,
                "old_id": old,
                "new_id": new,
                "title_info": title_info,
            }
        )

    for file, pairs in file_groups.items():
        path = ROOT / file
        text = path.read_text(encoding="utf-8")
        for old, new in pairs:
            old_text = f'"{old}"'
            new_text = f'"{new}"'
            count = text.count(old_text)
            if count == 0:
                raise RuntimeError(f"{file}: missing {old}")
            text = text.replace(old_text, new_text)
        path.write_text(text, encoding="utf-8")

    backlink_fixed = []
    for work_id, titles in sorted(work_titles.items()):
        entry = idx[work_id]
        path = ROOT / entry["path"]
        work = load_json(path)
        existing = (work.get("indexed_by") or []) + (work.get("emendated_by") or [])
        if any(item.get("source_bid") == SOURCE_BID for item in existing):
            continue
        title_info = "；".join(titles)
        record = {
            "source": SOURCE_TITLE,
            "source_bid": SOURCE_BID,
            "title_info": title_info,
            "summary": title_info,
        }
        if not isinstance(work.get("emendated_by"), list):
            work["emendated_by"] = []
        work["emendated_by"].append(record)
        work["updated_at"] = TODAY
        dump_json(path, work)
        backlink_fixed.append(
            {
                "work_id": work_id,
                "work_title": work.get("title"),
                "work_path": entry["path"],
                "emendated_by_added": record,
            }
        )

    report = {
        "date": TODAY,
        "issue": "整理本 section 的 work_ids 陣列含未生成或已不存在的 Work id。",
        "principle": "僅處理人工篩過的單候選；collated JSON 以原文替換避免重排；目標 Work 補回同一來源。",
        "fixed_sections": len(fixed),
        "fixed_backlinks": len(backlink_fixed),
        "fixed": fixed,
        "backlink_fixed": backlink_fixed,
    }
    out = ROOT / ".claude" / "known-issues" / "整理本落空work_ids_round1已修復.json"
    dump_json(out, report)
    print(json.dumps({"fixed_sections": len(fixed), "fixed_backlinks": len(backlink_fixed)}, ensure_ascii=False, indent=2))
    print(out.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
