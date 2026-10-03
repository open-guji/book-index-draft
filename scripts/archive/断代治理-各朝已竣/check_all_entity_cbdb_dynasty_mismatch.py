#!/usr/bin/env python3
"""
C5 batch17：全量 Entity 掃描查找 CBDB dyn_code 與 Entity.dynasty 不匹配
CBDB dy 映射：
  2=西漢 3=東漢 4=三國 5=西晉 6=東晉 7=五胡十六國
  8=南朝宋 9=南朝齊 10=南朝梁 11=南朝陳
  12=北魏 13=北齊 14=北周 15=隋 16=唐
  17=五代 18=宋 19=遼金西夏元  20=明 21=清 22=民國
"""
import json, os, re

DY_MAP = {
    "2": "西漢", "3": "東漢",
    "8": "南朝宋", "9": "南朝齊", "10": "南朝梁", "11": "南朝陳",
    "15": "隋", "16": "唐",
    "18": "宋",
    "19": "遼金元",
    "20": "明",
    "21": "清",
    "22": "中華民國"
}

# 等價集合：cbdb 代碼 vs Entity.dynasty 的多種寫法可互換
EQUIV = {
    "西漢": ["漢", "秦漢", "兩漢", "前漢"],
    "東漢": ["漢", "秦漢", "兩漢", "後漢"],
    "南朝宋": ["宋", "南北朝", "南朝", "南北"],
    "南朝齊": ["齊", "南北朝", "南朝", "南北"],
    "南朝梁": ["梁", "南北朝", "南朝", "南北"],
    "南朝陳": ["陳", "南北朝", "南朝", "南北"],
    "隋": ["隋唐"],
    "唐": ["隋唐"],
    "宋": ["北宋", "南宋", "宋末元初", "宋遼金"],
    "遼金元": ["遼", "金", "西夏", "元"],
    "明": ["南明"],
    "清": [],
    "中華民國": ["民國"],
}

def is_match(cbdb_dy: str, entity_dy: str) -> bool:
    if not cbdb_dy or not entity_dy: return True
    # 精確匹配
    expected = DY_MAP.get(cbdb_dy)
    if not expected: return True  # 不認識的代碼跳過
    if entity_dy == expected: return True
    # 等價
    if entity_dy in EQUIV.get(expected, []): return True
    # 反向：expected 在 entity_dy 的等價裡
    for k, lst in EQUIV.items():
        if entity_dy == k and expected in lst: return True
    return False

conflicts = []  # (eid, name, cbdb_id, cbdb_dy, expected, entity_dy, birth, death, work_count)
total = 0
checked = 0
for root, _, files in os.walk("/workspace/Entity"):
    for f in files:
        if not f.endswith(".json"): continue
        total += 1
        fp = os.path.join(root, f)
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                e = json.load(fh)
        except Exception:
            continue
        if e.get("type") != "entity" or e.get("subtype") != "people": continue
        ext = e.get("external_ids", {})
        cbdb_source = ext.get("cbdb_source", "")
        if not cbdb_source: continue
        m = re.search(r"cbdb_dy=(\d+)", cbdb_source)
        if not m: continue
        cbdb_dy = m.group(1)
        entity_dy = e.get("dynasty", "")
        checked += 1
        if not is_match(cbdb_dy, entity_dy):
            conflicts.append({
                "eid": e["id"],
                "name": e.get("primary_name", ""),
                "cbdb_id": ext.get("cbdb_id"),
                "cbdb_dy": cbdb_dy,
                "expected": DY_MAP.get(cbdb_dy, "?"),
                "entity_dy": entity_dy,
                "birth": e.get("birth_year"),
                "death": e.get("death_year"),
                "works": len(e.get("works", []))
            })

print(f"[INFO] 遍歷 {total} Entity 文件，其中 {checked} 個有 CBDB dy 標記")
print(f"[INFO] 發現 {len(conflicts)} 個 CBDB dy 與 Entity.dynasty 不匹配\n")
for c in conflicts:
    print(f"  {c['eid']} {c['name']}: CBDB dy={c['cbdb_dy']}→{c['expected']}  vs  Entity dynasty='{c['entity_dy']}'  ({c['birth']}~{c['death']})  works={c['works']}")
