#!/usr/bin/env python3
"""遼金元探勘：修復早前「D2 batch」CBDB自動比對誤配之4組人物。

早前一輪自動修復（dynasty_fix: 金→宋 per CBDB dy=15=宋）將4位人物
之dynasty由「金」改為「宋」，然其CBDB配對狀態皆為未經確認之
`pending_accept: relaxed_unique`。逐一核對indexed_by引文，元史
藝文志（元代官修）／補遼金元藝文志皆明確標示「金」：

  - 姚孝錫《雞肋集》：元史藝文志「金姚孝錫雞肋集」。
  - 韓孝彥《四聲篇海》《五音篇》：欽定四庫全書總目載完整生平
    「金韓孝彥撰...其書成於明昌、承安間」（明昌、承安皆金章宗
    年號），補遼金元藝文志/元史藝文志皆明載「金韓孝彥」。
  - 趙大中《風科集》：元史藝文志「金趙大中風科集」。
  - 施宜生《三桂老人集》《施宜生集》：補遼金元藝文志載「金施宜生
    （字明望，浦城人，翰林學士）」，元史藝文志同載「金」。
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
    ("1j96hjwlylnoo", "姚孝錫：元史藝文志「金姚孝錫雞肋集」，CBDB誤配（pending_accept）改「宋」，卸除並回復"),
    ("1j96hhvcr8mxt", "韓孝彥：欽定四庫全書總目載完整生平「金韓孝彥撰...成於明昌、承安間」，補遼金元藝文志/元史藝文志皆明載「金」，CBDB誤配改「宋」，卸除並回復"),
    ("1j96hjwlylno4", "趙大中：元史藝文志「金趙大中風科集」，CBDB誤配（pending_accept）改「宋」，卸除並回復"),
    ("1j96hhvcrjvje", "施宜生：補遼金元藝文志載「金施宜生（字明望，浦城人，翰林學士）」，元史藝文志同載「金」，CBDB誤配改「宋」，卸除並回復"),
]


def main():
    widx = build_work_index()
    eidx = build_entity_index()
    fixed_works = 0

    for eid, note in FIXES:
        ent_p = eidx[eid]
        ent = load(ent_p)
        ent["dynasty"] = "金"
        ent["period"] = "liao-jin-yuan"
        ent["period_basis"] = f"據 dynasty「金」（2026-08-13 遼金元探勘：{note}）"
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
            a[0]["dynasty"] = "金"
            a[0].pop("dynasty_basis", None)
            if j.get("dynasty") is not None:
                j["dynasty"] = "金"
            j["period"] = "liao-jin-yuan"
            j["period_basis"] = f"據 authors[0].dynasty「金」（2026-08-13 遼金元探勘：{note}）"
            save(p, j, get_indent(p))
            fixed_works += 1

    print(f"fixed_works={fixed_works}")


if __name__ == "__main__":
    main()
