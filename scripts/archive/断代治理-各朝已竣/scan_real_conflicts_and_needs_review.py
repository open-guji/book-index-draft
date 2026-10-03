#!/usr/bin/env python3
"""
修正 CBDB dy 映射后重新扫描真冲突 + needs-review 统计
基于数据驱动：dy=6→唐, 15→宋, 18→元, 19→明, 20→清, 21→民國, 84→朝鮮
"""
import json, os, re
from collections import defaultdict

# 修正后的 CBDB dy 映射（数据驱动）
DY_MAP = {
    "2": "西漢", "3": "東漢",
    "6": "唐",
    "15": "宋",
    "18": "元",
    "19": "明",
    "20": "清",
    "21": "中華民國",
    "84": "朝鮮",
}

# 等价集合
def is_equiv(d1, d2):
    if d1 == d2: return True
    eq = {
        "宋": ["北宋", "南宋"],
        "元": ["遼金元", "遼", "金"],
        "明": ["南明"],
        "中華民國": ["民國"],
    }
    return d2 in eq.get(d1, []) or d1 in eq.get(d2, [])

conflicts = []
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
        expected = DY_MAP.get(cbdb_dy)
        if not expected: continue  # 跳过未知 dy
        entity_dy = e.get("dynasty", "")
        if not entity_dy: continue
        if is_equiv(expected, entity_dy): continue
        conflicts.append({
            "eid": e["id"],
            "name": e.get("primary_name", ""),
            "cbdb_dy": cbdb_dy,
            "expected": expected,
            "entity_dy": entity_dy,
            "birth": e.get("birth_year"),
            "death": e.get("death_year"),
            "works": len(e.get("works", []))
        })

# 分组
agg = defaultdict(list)
for c in conflicts:
    agg[(c["cbdb_dy"], c["expected"], c["entity_dy"])].append(c)

print(f"总计 {len(conflicts)} 个真冲突\n")
for (cbdb_dy, expected, entity_dy), items in sorted(agg.items(), key=lambda x: -len(x[1])):
    print(f"CBDB dy={cbdb_dy}→{expected} vs Entity='{entity_dy}': {len(items)} 个")
    if len(items) <= 8:
        for c in items:
            print(f"  {c['eid']} {c['name']} ({c['birth']}~{c['death']}) works={c['works']}")
    else:
        for c in items[:5]:
            print(f"  {c['eid']} {c['name']} ({c['birth']}~{c['death']}) works={c['works']}")
        print(f"  ... 还有 {len(items)-5} 个")
    print()

# needs-review 统计
print("\n=== needs-review Work 统计 ===")
nr_count = 0
nr_works = []
for root, _, files in os.walk("/workspace/Work"):
    for f in files:
        if not f.endswith(".json"): continue
        fp = os.path.join(root, f)
        if "/collated_edition/" in fp: continue
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                w = json.load(fh)
        except:
            continue
        note = w.get("ai_note", "")
        if "needs-review" in note:
            nr_count += 1
            nr_works.append((w["id"], w.get("title", ""), note[:120]))

print(f"总计 {nr_count} 个 needs-review Work\n")
for wid, title, note in nr_works[:20]:
    print(f"  {wid} 《{title}》")
    print(f"    {note}")
    print()
if nr_count > 20:
    print(f"  ... 还有 {nr_count-20} 个")
