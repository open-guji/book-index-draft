#!/usr/bin/env python3
"""统计 CBDB dy 与 Entity.dynasty 不匹配的分组分布"""
import json, os, re
from collections import defaultdict

DY_MAP = {
    "2": "西漢", "3": "東漢",
    "8": "南朝宋", "9": "南朝齊", "10": "南朝梁", "11": "南朝陳",
    "15": "隋", "16": "唐",
    "18": "宋", "19": "遼金元", "20": "明", "21": "清", "22": "民國"
}

groups = defaultdict(list)  # (cbdb_dy, expected, entity_dy) -> [(eid, name, birth, death)]

for root, _, files in os.walk("/workspace/Entity"):
    for f in files:
        if not f.endswith(".json"): continue
        fp = os.path.join(root, f)
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                e = json.load(fh)
        except:
            continue
        if e.get("type") != "entity" or e.get("subtype") != "people": continue
        ext = e.get("external_ids", {})
        cbdb_source = ext.get("cbdb_source", "")
        m = re.search(r"cbdb_dy=(\d+)", cbdb_source)
        if not m: continue
        cbdb_dy = m.group(1)
        expected = DY_MAP.get(cbdb_dy, "?")
        entity_dy = e.get("dynasty", "")
        if not expected or not entity_dy: continue
        # 简单等价检查
        equiv = {
            "宋": ["北宋", "南宋"],
            "遼金元": ["遼", "金", "元"],
            "明": ["南明"],
            "清": [],
        }
        if entity_dy == expected: continue
        if entity_dy in equiv.get(expected, []): continue
        groups[(cbdb_dy, expected, entity_dy)].append((e["id"], e.get("primary_name",""), e.get("birth_year"), e.get("death_year"), len(e.get("works",[]))))

# 按 (cbdb_dy, entity_dy) 聚合
agg = defaultdict(list)
for (cbdb_dy, expected, entity_dy), items in groups.items():
    agg[(cbdb_dy, expected, entity_dy)] = items

# 排序输出
print(f"总计 {sum(len(v) for v in agg.values())} 个不匹配，按 (CBDB dy→期望, Entity当前) 分组：\n")
for (cbdb_dy, expected, entity_dy), items in sorted(agg.items(), key=lambda x: -len(x[1])):
    print(f"  CBDB dy={cbdb_dy}→{expected} vs Entity='{entity_dy}': {len(items)} 个")
    if len(items) <= 5:
        for eid, name, by, dy, wc in items:
            print(f"    {eid} {name} ({by}~{dy}) works={wc}")
    else:
        for eid, name, by, dy, wc in items[:3]:
            print(f"    {eid} {name} ({by}~{dy}) works={wc}")
        print(f"    ... 还有 {len(items)-3} 个")
    print()
