#!/usr/bin/env python3
"""隋唐探勘：修復早前「D2 batch」CBDB自動比對誤配之5筆案例。

早前一輪自動修復（dynasty_fix: 唐→宋 per CBDB dy=15=宋）將5位人物
之dynasty由「唐」改為「宋」，然其CBDB配對狀態皆為未經確認之
`pending_accept: relaxed_unique`。逐一核對indexed_by引文：

  - 郭京《周易舉正》：欽定四庫全書總目/崇文總目/直齋書錄解題皆
    明言「唐郭京撰」，且崇文總目載其官銜「蘇州司户叅軍」、生平
    「開元後人」——確為唐人，CBDB誤配。
  - 李冀《玄聖蘧廬》：國史經籍志載「唐李冀」——確為唐人，CBDB誤配。
  - 武密《古今通占鏡》：國史經籍志、新唐書藝文志（唐代自身之
    藝文志！）皆明載「唐武密」——確為唐人，CBDB誤配。
  - 裴煜《編吾亦書》：國史經籍志載「唐裴煜」——確為唐人，CBDB誤配。
  - 唐仲友《友帝王經世圖譜》：清史稿藝文志載「宋唐仲友」——real
    person真為南宋學者（1136-1188，與朱熹論戰知名），name欄原作
    「唐仲」，缺一「友」字，屬姓名截斷之資料品質問題（非CBDB誤配，
    此筆CBDB配對「宋」實為正確），逕予補全姓名，dynasty/period
    維持宋/song不變。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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
    for s in "0123456789abcdef":
        d = load(ROOT / "index" / "works" / f"{s}.json")
        for wid, entry in d.items():
            idx[wid] = ROOT / entry["path"]
    return idx


def build_entity_index():
    idx = {}
    for f in Path(ROOT / "Entity").rglob("*.json"):
        try:
            j = load(f)
        except Exception:
            continue
        if isinstance(j, dict) and j.get("id"):
            idx[j["id"]] = f
    return idx


# (work_id, entity_id, name, dynasty, period, note)
FIXES = [
    ("1ev0r90zaxrls", "1j96hjwlxcpig", "郭京", "唐", "sui-tang",
     "郭京：欽定四庫全書總目/崇文總目/直齋書錄解題皆明言「唐郭京撰」，CBDB誤配（pending_accept）改「宋」，卸除並回復"),
    ("1evgptnuvuccg", "1j96hjwlylnpz", "李冀", "唐", "sui-tang",
     "李冀：國史經籍志載「唐李冀」，CBDB誤配（pending_accept）改「宋」，卸除並回復"),
    ("1evgq1ijy9xq8", "1j96hjwlylnq1", "武密", "唐", "sui-tang",
     "武密：國史經籍志、新唐書藝文志皆明載「唐武密」，CBDB誤配（pending_accept）改「宋」，卸除並回復"),
    ("1evgppz2ewzcw", "1j96hjwlylnpx", "裴煜", "唐", "sui-tang",
     "裴煜：國史經籍志載「唐裴煜」，CBDB誤配（pending_accept）改「宋」，卸除並回復"),
]

# 唐仲友：name截斷，dynasty/period皆已正確
NAME_FIX = ("1evr5e3mc6kj9", "1j96hjwlxcphx", "唐仲友",
            "唐仲友（1136-1188，南宋學者，與朱熹論戰知名）：name欄原作「唐仲」，缺一「友」字，屬姓名截斷之資料品質問題，補全姓名；dynasty/period（宋/song）維持不變，CBDB配對本身正確")


def main():
    widx = build_work_index()
    eidx = build_entity_index()
    fixed = 0

    for wid, eid, name, dyn, period, note in FIXES:
        p = widx[wid]
        j = load(p)
        a0 = j["authors"][0]
        a0["name"] = name
        a0["dynasty"] = dyn
        a0.pop("dynasty_basis", None)
        if j.get("dynasty") is not None:
            j["dynasty"] = dyn
        j["period"] = period
        j["period_basis"] = f"據 authors[0].dynasty「{dyn}」（2026-08-13 隋唐探勘：{note}）"
        save(p, j, get_indent(p))

        ent_p = eidx[eid]
        ent = load(ent_p)
        ent["primary_name"] = name
        ent["dynasty"] = dyn
        ent["period"] = period
        ent["period_basis"] = f"據 dynasty「{dyn}」（2026-08-13 隋唐探勘：{note}）"
        ent["ai_note"] = ent.get("ai_note", "") + f" 2026-08-13：CBDB配對卸除（原cbdb_source: {ent.get('external_ids',{}).get('cbdb_source','')}），{note}。"
        ent["external_ids"] = {}
        ent.pop("dynasty_basis", None)
        save(ent_p, ent, get_indent(ent_p))
        fixed += 1

    wid, eid, name, note = NAME_FIX
    p = widx[wid]
    j = load(p)
    j["authors"][0]["name"] = name
    j["period_basis"] = j.get("period_basis", "") + f"（2026-08-13 隋唐探勘：{note}）"
    save(p, j, get_indent(p))

    ent_p = eidx[eid]
    ent = load(ent_p)
    ent["primary_name"] = name
    ent["ai_note"] = ent.get("ai_note", "") + f" 2026-08-13：{note}"
    save(ent_p, ent, get_indent(ent_p))
    fixed += 1

    print(f"fixed={fixed}")


if __name__ == "__main__":
    main()
