#!/usr/bin/env python3
"""以原文替換方式修復整理本 section 中明確可重連的 work_id。

只處理單數 work_id 欄位，避免重排大型 collated JSON。
"""

import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TODAY = "2026-08-09"

FIXES = [
    ("Work/1/e/v/1evcs059gkvls/collated_edition/樂類.json", "1evcs08ebhq0w", "1evgoqiohfw1s", "信都芳《刪注樂書》"),
    ("Work/1/e/v/1evjk1whvmznk/collated_edition/史部.json", "1evgpk3y61rsw", "1ev3bayp8fwu8", "古今游名山記總綠"),
    ("Work/1/e/v/1evjk1whvmznk/collated_edition/史部.json", "1ev3bb0acvbi8", "1evkpofydbe2o", "牧津"),
    ("Work/1/e/v/1eve1ei9whji8/collated_edition/經部一·易類.json", "1evf0g32tvbi8", "1evf0fpzcuigw", "陸績《周易日月變例》"),
    ("Work/1/e/v/1eve1ei9whji8/collated_edition/經部四·禮類.json", "1evfaajklk2yo", "1evfa9g12f8xs", "曹充《慶氏禮章句》"),
    ("Work/1/e/v/1ev88ee9jw6ps/collated_edition/五行類.json", "1evdid3qjb6kg", "1evdibiaetds0", "王宇《周易佔林》"),
    ("Work/1/e/v/1evfu57n5n37k/collated_edition/甲部經錄·論語類.json", "1evcpcuxvkcu8", "1evgor83scydc", "爾雅圖"),
    ("Work/1/e/v/1ev3bb4qxubr4/collated_edition/子類下.json", "1evka8sutay9s", "1evkpgeelz1ts", "寓簡"),
    ("Work/1/e/v/1ev3bb4qxubr4/collated_edition/史類.json", "1evgphn7j18n4", "1evgpgzijtyww", "唐典"),
    ("Work/1/e/v/1ev3bb4qxubr4/collated_edition/史類.json", "1evgpj7at79j4", "1evgphec5e41s", "嘉祐名臣傳"),
    ("Work/1/e/v/1ev3bb4qxubr4/collated_edition/經類.json", "1evkaclbu13b4", "1evkpgdu9zk00", "周易輯聞"),
    ("Work/1/e/v/1ev3bb4qxubr4/collated_edition/經類.json", "1evgoqhyz3pxc", "1ev3b9zu5pkao", "讀禮疑圖"),
    ("Work/1/e/v/1ev3bb4qxubr4/collated_edition/經類.json", "1evetxcz2boxs", "1evgor8mryo00", "爾雅音略"),
    ("Work/1/e/v/1eve1eig5jn5s/collated_edition/卷四.json", "1evftexb01yio", "1evcmoaxw2yv4", "駱統集"),
    ("Work/1/e/v/1evdiulq07rwg/collated_edition/雜家類.json", "1evjxlz977kzk", "1ev3bc1kw8feo", "方齋補莊"),
    ("Work/1/e/v/1eve1ek5qq9kw/collated_edition/全文.json", "1evgbzxtv2z28", "1evrfi1ev8e80", "素問玄機原病式"),
    ("Work/1/e/v/1evjxczyavy80/collated_edition/史部.json", "1evdic0gbf7y8", "1ev3bag5k581s", "皇明繩武編擬續大學衍義"),
    ("Work/1/e/v/1evjxczyavy80/collated_edition/史部.json", "1evjr1oajxkhs", "1ev3bax124yyo", "黃山志定本"),
    ("Work/1/e/v/1evjxczyavy80/collated_edition/史部.json", "1ev3bb0acvbi8", "1evkpofydbe2o", "牧津"),
    ("Work/1/e/u/1eujf2fs4v280/collated_edition/juan003.json", "1evkaclbu13b4", "1evkpgdu9zk00", "周易輯聞"),
    ("Work/1/e/u/1eujf2fs4v280/collated_edition/juan080.json", "1evjxl2gx2a68", "1evkpofydbe2o", "牧津"),
    ("Work/1/e/u/1eujf2fs4v280/collated_edition/juan121.json", "1evka8sutay9s", "1evkpgeelz1ts", "寓簡"),
]


def main():
    grouped = defaultdict(list)
    for file, old, new, reason in FIXES:
        grouped[file].append((old, new, reason))

    fixed = []
    for file, fixes in grouped.items():
        path = ROOT / file
        text = path.read_text(encoding="utf-8")
        for old, new, reason in fixes:
            needle = f'"work_id": "{old}"'
            repl = f'"work_id": "{new}"'
            count = text.count(needle)
            if count == 0:
                raise RuntimeError(f"{file}: missing {needle}")
            text = text.replace(needle, repl)
            fixed.append({"file": file, "old_id": old, "new_id": new, "count": count, "reason": reason})
        path.write_text(text, encoding="utf-8")

    report = {
        "date": TODAY,
        "issue": "整理本 section 單數 work_id 指向未生成或已不存在的 Work。",
        "principle": "僅以原文替換修復人工篩過的單候選，避免重排大型 JSON；不處理 work_ids 陣列與通名假陽性。",
        "fixed_occurrences": sum(item["count"] for item in fixed),
        "fixed": fixed,
    }
    out = ROOT / ".claude" / "known-issues" / "整理本落空work_id_round1已修復.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"fixed_occurrences": report["fixed_occurrences"]}, ensure_ascii=False, indent=2))
    print(out.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
