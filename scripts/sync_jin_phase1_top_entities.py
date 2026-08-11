#!/usr/bin/env python3
"""晉朝探勘分期第一階段：250條「entity存在但dynasty仍籠統『晉』」批次
中出現頻次最高之人物，逐位以生卒年/仕歷核校後訂正。

比照西漢探勘方法，僅收錄有把握者：
"""
import json
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

CLASSIFICATIONS = {
    "徐邈": ("東晉", "344-397，字仙民，東晉著名經學家，遍注群經"),
    "竺法護": ("西晉", "231-308，西晉佛經翻譯家"),
    "徐苗": ("東晉", "字叔胄，撰《五經同異評》，東晉初期人"),
    "應貞": ("西晉", "應璩之子，晉武帝時人，卒於太康元年（280）前後"),
    "范宜": ("東晉", "范甯，339-401，東晉穀梁注疏名家（范宜為范甯異寫）"),
    "范甯": ("東晉", "339-401，東晉穀梁注疏名家"),
    "王長文": ("西晉", "228-320，蜀郡人，撰《通玄經》等，主要西晉時人"),
    "張湛": ("東晉", "《列子注》作者，東晉人"),
    "李彤": ("西晉", "字仲羲，撰《字讀》，西晉人"),
    "楊方": ("東晉", "撰《五經鉤沈》，東晉初人"),
    "支敏度": ("東晉", "佛經翻譯家，東晉初渡江"),
    "鳩摩羅什課": ("後秦", "鳩摩羅什（344-413），401年後於後秦姚興迎入長安譯經，非晉人"),
    "晉灼": ("西晉", "注《漢書》，西晉人"),
    "許遜": ("東晉", "239-374，淨明道祖師，主要活動於東晉"),
}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, data, indent=2):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
        f.write("\n")


def get_indent(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    lines = raw.split("\n")
    if len(lines) > 1:
        cand = len(lines[1]) - len(lines[1].lstrip(" "))
        if cand > 0:
            return cand
    return 2


def build_work_index():
    idx = {}
    for s in SHARDS:
        d = load(ROOT / "index" / "works" / f"{s}.json")
        for wid, entry in d.items():
            idx[wid] = ROOT / entry["path"]
    return idx


def main():
    widx = build_work_index()

    ent_by_id = {}
    for f in glob.glob(str(ROOT / "Entity" / "**" / "*.json"), recursive=True):
        try:
            j = load(Path(f))
        except Exception:
            continue
        eid = j.get("id")
        if eid:
            ent_by_id[eid] = Path(f)

    fixed_entities = set()
    fixed_works = 0

    for wid, path in widx.items():
        try:
            j = load(path)
        except Exception:
            continue
        if j.get("period") != "jin":
            continue
        a = j.get("authors")
        if not a or a[0].get("dynasty") != "晉":
            continue
        name = a[0].get("name")
        eid = a[0].get("entity_id")
        if not eid or name not in CLASSIFICATIONS:
            continue

        target_dyn, basis = CLASSIFICATIONS[name]
        a[0]["dynasty"] = target_dyn
        if j.get("dynasty") == "晉":
            j["dynasty"] = target_dyn
        j["period_basis"] = f"據 authors[0].dynasty「{target_dyn}」（原作籠統「晉」，2026-08-11 晉朝探勘分期第一階段訂正：{basis}）"
        save(path, j, get_indent(path))
        fixed_works += 1

        if eid in ent_by_id and eid not in fixed_entities:
            ent = load(ent_by_id[eid])
            if ent.get("dynasty") in (None, "晉"):
                ent["dynasty"] = target_dyn
                ent["ai_note"] = ent.get("ai_note", "") + f" 2026-08-11：晉朝探勘分期第一階段訂正——{basis}，dynasty改為「{target_dyn}」。"
                save(ent_by_id[eid], ent, get_indent(ent_by_id[eid]))
                fixed_entities.add(eid)

    print(f"fixed works: {fixed_works}, fixed entities: {len(fixed_entities)}")


if __name__ == "__main__":
    main()
