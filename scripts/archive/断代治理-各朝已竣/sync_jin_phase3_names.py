#!/usr/bin/env python3
"""晉朝探勘分期第三階段：續查殘留「dynasty籠統『晉』」中頻次較高之
人物，以及兩組Entity同名分裂案例。

直接訂正（單一Entity，史實可斷）：
  - 劉智（1j96h8rw86q2s）：西晉，?-289，字子房，官至太常，劉寔之弟，
    見本條ai_note及外部查證（維基百科「劉智 (晉朝)」）。
  - 孫毓（1j96hl45pdgcg）：西晉經學家，字休朗，外部查證確認。
  - 楊偉（1j96h8rw7k8xk）：本條著錄自身載明「魏時為尚書郎...後入晋
    為征南軍司」，訂正為西晉。
  - 無蘭（1j96ha8yqrwu8）：著錄載明「無蘭，孝武時人」，所撰為佛經
    序（三十七品序/賢劫千佛經序），與東晉孝武帝崇佛之世相符，訂正
    為東晉。

Entity 分裂合併：
  - 索綏：1j96ha8qiuxvk（2作品：符命傳/六夷頌）與1j96hfcdqxgqo（1作品：
    涼春秋）為同一人，三作品之著錄皆引《前涼錄》，其一並載「綏字
    士艾，燉煌人，記室祭酒」，確係前涼（非晉朝）人物，逕予合併並
    訂正dynasty為「前涼」（period仍留jin，比照鳩摩羅什課→後秦之
    既有處理方式，不變動period bucket）。
  - 徐乾：1j96keg24atq8（2作品：春秋穀梁傳注/古履儀）與1j96hg4ntc9pc
    （1作品：徐乾集）皆為「給事中徐乾」，著錄載明「東晋莞人」，確係
    同一人，逕予合併，訂正為東晉。
"""
import json
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

DIRECT_ENTITY_FIX = {
    "1j96h8rw86q2s": ("西晉", "劉智：?-289，字子房，官至太常，劉寔之弟（維基百科「劉智 (晉朝)」條）"),
    "1j96hl45pdgcg": ("西晉", "孫毓：西晉經學家，字休朗"),
    "1j96h8rw7k8xk": ("西晉", "楊偉：本條著錄自載「魏時為尚書郎...後入晋為征南軍司」"),
    "1j96ha8yqrwu8": ("東晉", "無蘭：著錄載「孝武時人」，所撰為佛經序，與東晉孝武帝崇佛之世相符"),
}

MERGES = [
    ("1j96ha8qiuxvk", ["1j96hfcdqxgqo"], "前涼",
     "索綏：三作品著錄皆引《前涼錄》，其一載「綏字士艾，燉煌人，記室祭酒」，確係前涼人物"),
    ("1j96keg24atq8", ["1j96hg4ntc9pc"], "東晉",
     "徐乾：皆為「給事中徐乾」，著錄載「東晋莞人」"),
]


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


def shard_of(id_str, n=16):
    h = 0
    for c in id_str:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return h % n


def build_work_index():
    idx = {}
    for s in SHARDS:
        d = load(ROOT / "index" / "works" / f"{s}.json")
        for wid, entry in d.items():
            idx[wid] = ROOT / entry["path"]
    return idx


def build_entity_index():
    idx = {}
    for f in glob.glob(str(ROOT / "Entity" / "**" / "*.json"), recursive=True):
        try:
            j = load(Path(f))
        except Exception:
            continue
        if isinstance(j, dict) and j.get("id"):
            idx[j["id"]] = Path(f)
    return idx


def delete_entity(eid, ent_path):
    ent_path.unlink()
    s = shard_of(eid)
    p = ROOT / "index" / "entities" / f"{s:x}.json"
    d = load(p)
    if eid in d:
        del d[eid]
        save(p, d, indent=get_indent(p))


def main():
    widx = build_work_index()
    eidx = build_entity_index()

    fixed_works = 0
    fixed_entities = 0

    # 直接訂正：單一Entity dynasty修正 + 連動同步該Entity名下所有jin期
    # 且dynasty仍為籠統「晉」之Work
    for eid, (target_dyn, note) in DIRECT_ENTITY_FIX.items():
        ent_path = eidx[eid]
        ent = load(ent_path)
        ent["dynasty"] = target_dyn
        ent["ai_note"] = ent.get("ai_note", "") + f" 2026-08-11：晉朝探勘分期第三階段訂正——{note}，dynasty改為「{target_dyn}」。"
        save(ent_path, ent, get_indent(ent_path))
        fixed_entities += 1

        for w in ent.get("works", []):
            wid = w.get("work_id")
            p = widx.get(wid)
            if not p:
                continue
            j = load(p)
            a = j.get("authors")
            if not a or not isinstance(a, list):
                continue
            changed = False
            for au in a:
                if isinstance(au, dict) and au.get("entity_id") == eid and au.get("dynasty") == "晉":
                    au["dynasty"] = target_dyn
                    changed = True
            if changed:
                if j.get("dynasty") == "晉":
                    j["dynasty"] = target_dyn
                j["period_basis"] = f"據 authors[].dynasty「{target_dyn}」（原作籠統「晉」，2026-08-11 晉朝探勘分期第三階段訂正：{note}）"
                save(p, j, get_indent(p))
                fixed_works += 1

    # Entity 分裂合併
    for base_eid, donor_eids, target_dyn, note in MERGES:
        base_p = eidx[base_eid]
        base = load(base_p)
        base_works = {w["work_id"]: w for w in base.get("works", [])}
        base["dynasty"] = target_dyn

        for did in donor_eids:
            donor_p = eidx[did]
            donor = load(donor_p)
            for w in donor.get("works", []):
                base_works.setdefault(w["work_id"], w)
            delete_entity(did, donor_p)

        base["works"] = list(base_works.values())
        base["ai_note"] = base.get("ai_note", "") + f" 2026-08-11：晉朝探勘分期第三階段查出同名分裂——{note}，已合併。"
        save(base_p, base, get_indent(base_p))
        fixed_entities += 1

        for wid in base_works:
            p = widx.get(wid)
            if not p:
                continue
            j = load(p)
            changed = False
            for au in j.get("authors", []) or []:
                if isinstance(au, dict) and au.get("entity_id") in donor_eids:
                    au["entity_id"] = base_eid
                    au["dynasty"] = target_dyn
                    changed = True
                elif isinstance(au, dict) and au.get("entity_id") == base_eid and au.get("dynasty") == "晉":
                    au["dynasty"] = target_dyn
                    changed = True
            if changed:
                if j.get("dynasty") in ("晉", None):
                    j["dynasty"] = target_dyn
                j["period_basis"] = f"據 authors[].dynasty「{target_dyn}」（2026-08-11 晉朝探勘分期第三階段：{note}）"
                save(p, j, get_indent(p))
                fixed_works += 1

    print(f"fixed_works={fixed_works}, fixed_entities={fixed_entities}")


if __name__ == "__main__":
    main()
