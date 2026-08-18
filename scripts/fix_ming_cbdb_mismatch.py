#!/usr/bin/env python3
"""明朝探勘：修復早前「D2 batch」CBDB自動比對誤配之5組人物。

早前一輪自動修復（dynasty_fix: 明→宋 per CBDB dy=15=宋）將5位人物
之dynasty由「明」改為「宋」，然其CBDB配對狀態皆為未經確認之
`pending_accept: relaxed_unique`。逐一核對indexed_by引文，明史
藝文志（明代官修）／欽定四庫全書總目皆明確標示「明」：

  - 張世賢《圖注難經》《圖注脈訣》：欽定四庫全書總目載完整生平
    「明張世賢撰，世賢字天成，寧波人，正德中名醫也」，明史藝文志
    同載。
  - 宗林《寒燈衍義》《香山夢ＢＯ集》：明史藝文志明載「宗林」。
  - 周紹稷《鄖陽府志》：明史藝文志明載「周紹稷」。
  - 張濡《先天易數》：明史藝文志明載「張濡」。
  - 黃芹《易圖識漏》：欽定四庫全書總目載完整生平「明黃芹撰，芹字
    德馨，號畏庵，龍岩人，蔡清之弟子也，正德九年以歲貢生官海陽
    縣訓導」，明史藝文志同載。
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


# (entity_id, note)
FIXES = [
    ("1j96hhvcrjvgg", "張世賢：欽定四庫全書總目載完整生平「明張世賢撰...正德中名醫也」，明史藝文志同載，CBDB誤配（pending_accept）改「宋」，卸除並回復"),
    ("1j96hhvcrjvhk", "宗林：明史藝文志明載「宗林」，CBDB誤配（pending_accept）改「宋」，卸除並回復"),
    ("1j96hjwlxz6l8", "周紹稷：明史藝文志明載「周紹稷」，CBDB誤配（pending_accept）改「宋」，卸除並回復"),
    ("1j96hjwlxz6lg", "張濡：明史藝文志明載「張濡」，CBDB誤配（pending_accept）改「宋」，卸除並回復"),
    ("1j96hjwlxcpij", "黃芹：欽定四庫全書總目載完整生平「明黃芹撰...正德九年以歲貢生官海陽縣訓導」，明史藝文志同載，CBDB誤配（pending_accept）改「宋」，卸除並回復"),
]


def main():
    widx = build_work_index()
    eidx = build_entity_index()
    fixed_works = 0

    for eid, note in FIXES:
        ent_p = eidx[eid]
        ent = load(ent_p)
        ent["dynasty"] = "明"
        ent["period"] = "ming"
        ent["period_basis"] = f"據 dynasty「明」（2026-08-13 明朝探勘：{note}）"
        ent["ai_note"] = ent.get("ai_note", "") + f" 2026-08-13：CBDB配對卸除（原cbdb_source: {ent.get('external_ids',{}).get('cbdb_source','')}），{note}。"
        ent["external_ids"] = {}
        ent.pop("dynasty_basis", None)
        ent.pop("birth_year", None)
        ent.pop("death_year", None)
        save(ent_p, ent, get_indent(ent_p))

        for w in ent.get("works", []):
            wid = w.get("work_id")
            p = widx.get(wid)
            if not p:
                continue
            j = load(p)
            a = j.get("authors")
            if not a or not isinstance(a, list) or not isinstance(a[0], dict):
                continue
            if a[0].get("entity_id") != eid:
                continue
            a[0]["dynasty"] = "明"
            a[0].pop("dynasty_basis", None)
            if j.get("dynasty") is not None:
                j["dynasty"] = "明"
            j["period"] = "ming"
            j["period_basis"] = f"據 authors[0].dynasty「明」（2026-08-13 明朝探勘：{note}）"
            save(p, j, get_indent(p))
            fixed_works += 1

    print(f"fixed_works={fixed_works}")


if __name__ == "__main__":
    main()
