#!/usr/bin/env python3
"""修复 chk.py 报出的 Entity→Work 单向残留。

本轮只处理两类：
1. 高置信补回 Work.authors[].entity_id：梁武帝萧衍《孝子传》。
2. 其余 32 条为旧批次改作者/置空 entity_id 后残留在 Entity.works 的 stale 回连，删除 Entity 侧 works 条目。
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


ADD_WORK_AUTHOR_LINKS = [
    {
        "work_id": "1evgpj1gsd3wg",
        "title": "孝子傳",
        "entity_id": "1j967afjav1vw",
        "entity_name": "蕭衍",
        "author_name": "蕭衍",
        "role": "撰",
        "dynasty": "南朝梁",
        "period": "nanbeichao",
        "basis": "國史經籍志作「梁武帝」，即梁武帝蕭衍；Entity 1j967afjav1vw 已為南朝梁蕭衍。",
    }
]


REMOVE_ENTITY_WORK_LINKS = [
    ("1j96hjwlxny3u", "1ev7xm2sm7vgg", "臣說賦作者保留殘名「說」，原竇說回連為舊誤配"),
    ("1j96hjwlyaf4v", "1evfuuthi4w00", "遠游志作者已改為殘名「續」，非釋福登"),
    ("1j96ad68m1zpc", "1evgpnggtt62o", "莊子講疏作者張機未證即張仲景"),
    ("1j96h8rw7vhih", "1evgojczezi80", "合浦珠作者清徐震，非明徐震"),
    ("1j96hhvcrjvhe", "1evdidd5s2znk", "華嚴法界境作者德清，非元升"),
    ("1j96hjwlxny3q", "1ev7xkh7f48w0", "臣彭作者保留殘名「彭」，原釋紹明回連為舊誤配"),
    ("1j96hhvcrjviq", "1evfuvlzosow0", "靖恭堂銘作者劉昞，非劉銑"),
    ("1j96ha8kt5jwg", "1evfuvlh38npc", "老子注作者「氏」為不詳殘名，不應回連人物 Entity"),
    ("1j96hel2x07wg", "1ev3badi9bxmo", "靖炎兩朝見聞錄作者陳東，非殘名東"),
    ("1j96hhvcrjvj7", "1evga65pp3g1s", "太極圖解釋義作者元許珍，非北宋許珍"),
    ("1j96hjwlyaf61", "1evga3af5tbls", "太祖實錄作者完顏宗弼，非舒庭謨"),
    ("1j96hfvnmujnk", "1evgpmxxxalmo", "忠經 Work 註明原海鵬 entity_id 為錯誤關聯"),
    ("1j967bgl89icn", "1evgbzfgq57uo", "道德經注作者元王珪，非北宋王珪"),
    ("1j967c148wsnm", "1evgpivar79xc", "諸路轉運司編勑作者陳彭年，非殘名彭年"),
    ("1j96hfxgmpfk0", "1evgpo81ykc8w", "蘇耽傳作者已置佚名，原長殘名回連為舊誤配"),
    ("1j96hei5hwzk0", "1evr5e3mfaxxj", "左氏膏肓作者何休，非殘名掾何休始"),
    ("1j96hgd6jn18g", "1evdidlitufwg", "兩都賦作者已改桑悅並另有 Entity"),
    ("1j967cp21969z", "1evdie3p8va4g", "夢觀集作者釋守仁，非林富"),
    ("1j96hldyxbt34", "1ev7xkh9dz474", "待詔臣饒心術作者保留殘名饒，不回連釋祖賢"),
    ("1j96a9eeaj4sg", "1evfubme77qio", "禮記音作者謝模，非謝沈"),
    ("1j96kegcdkkcg", "1evfuuz7xqsqo", "甄異記作者戴祚，非戴逵"),
    ("1j968k0jdrlz7", "1evke141j8b28", "二十四史作者已置佚名，非司馬遷單撰"),
    ("1j96kejeblo8w", "1evgomnkx23uo", "兒女英雄傳 Work 註明原文康 Entity 為錯誤關聯"),
    ("1j96hjwlxny11", "1ev3bbmslhvr4", "天文書作者明柯洽，非南朝宋柯洽"),
    ("1j96hjwlylnqg", "1evgq9ln4jxmo", "西廵類稿作者吳廷舉，非張相侯"),
    ("1j96hfxdvfytc", "1evgpo5vxv0g0", "周義山內傳作者周義山，非殘名人居紫陽山"),
    ("1j96h8rw790e2", "1ev3bcmg50bnk", "雲間雜記作者已置佚名，非劉文耀"),
    ("1j967bgl70k5j", "1evkpxffmr7k0", "蠡海集作者明王逵，非北宋王逵"),
    ("1j96hhvcr8my2", "1ev3bb5v90l4w", "宋史闡幽作者明許浩，非清許浩"),
    ("1j96hjwlxny3v", "1ev7xm2takdts", "臣義賦作者保留殘名義，原董葵回連為舊誤配"),
    ("1j96hhvcrjvh2", "1ev3bdii6aa68", "茶山老人遺集作者元沈貞，非朝鮮沈貞"),
    ("1jae2gjvgxkba", "1ev3ba9nc3qbk", "增修復古編作者已改吳均且 entity_id 置空，謝堃回連為舊誤配"),
]


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def index_by_id(kind: str):
    out = {}
    for p in sorted((ROOT / kind).glob("?/?/?/*.json")):
        try:
            data = load_json(p)
        except Exception:
            continue
        out[data["id"]] = (p, data)
    return out


def load_work_index():
    idx = {}
    shard_path = {}
    for shard in "0123456789abcdef":
        p = ROOT / "index" / "works" / f"{shard}.json"
        data = load_json(p)
        for wid in data:
            idx[wid] = data
            shard_path[wid] = p
    return idx, shard_path


def main():
    works = index_by_id("Work")
    entities = index_by_id("Entity")
    work_index, work_index_paths = load_work_index()
    changed_work_index_paths = set()
    stats = {
        "work.author_entity_id_added": 0,
        "work.dynasty_period_set": 0,
        "entity.stale_work_link_removed": 0,
        "index.work_synced": 0,
    }

    for item in ADD_WORK_AUTHOR_LINKS:
        wid = item["work_id"]
        wpath, work = works[wid]
        matched = False
        for author in work.get("authors") or []:
            if author.get("name") == item["author_name"] and author.get("role") == item["role"]:
                author["entity_id"] = item["entity_id"]
                author["dynasty"] = item["dynasty"]
                author["dynasty_basis"] = "entity_work_oneway_round1:" + item["basis"]
                matched = True
                stats["work.author_entity_id_added"] += 1
                break
        if not matched:
            raise RuntimeError(f"author not found for {wid}")
        if work.get("dynasty") != item["dynasty"] or work.get("period") != item["period"]:
            work["dynasty"] = item["dynasty"]
            work["dynasty_basis"] = "entity_work_oneway_round1:" + item["basis"]
            work["period"] = item["period"]
            work["period_basis"] = f"據 dynasty「{item['dynasty']}」自動歸併"
            stats["work.dynasty_period_set"] += 1
        note = f"[entity-work-oneway-round1: 補回 {item['entity_name']} entity_id；{item['basis']}]"
        work["ai_note"] = (work.get("ai_note", "") + "\n\n" + note).strip()
        work["updated_at"] = now_iso()
        dump_json(wpath, work)

        if wid in work_index:
            entry = work_index[wid][wid]
            entry["author"] = item["author_name"]
            entry["role"] = item["role"]
            entry["dynasty"] = item["dynasty"]
            entry["period"] = item["period"]
            changed_work_index_paths.add(work_index_paths[wid])
            stats["index.work_synced"] += 1

    for eid, wid, reason in REMOVE_ENTITY_WORK_LINKS:
        epath, entity = entities[eid]
        before = len(entity.get("works") or [])
        entity["works"] = [x for x in (entity.get("works") or []) if x.get("work_id") != wid]
        after = len(entity["works"])
        if after != before:
            note = f"[entity-work-oneway-round1: 移除 stale works 回連 {wid}；{reason}]"
            entity["ai_note"] = (entity.get("ai_note", "") + "\n\n" + note).strip()
            entity["updated_at"] = now_iso()
            dump_json(epath, entity)
            stats["entity.stale_work_link_removed"] += before - after
        else:
            raise RuntimeError(f"stale link not found: {eid}->{wid}")

    for p in changed_work_index_paths:
        # All entries sharing the shard are in the same dict object; dump once.
        any_wid = next(wid for wid, sp in work_index_paths.items() if sp == p)
        dump_json(p, work_index[any_wid])

    report = {
        "description": "人物↔作品單向 Round 1：修復 Entity→Work 單向殘留",
        "scope": "處理 chk.py 報出的 33 條人物→作品單向；高置信補回 1 條 Work 作者 entity_id，其餘 32 條移除 Entity.works stale 回連。",
        "added_work_author_links": ADD_WORK_AUTHOR_LINKS,
        "removed_entity_work_links": [
            {"entity_id": eid, "work_id": wid, "reason": reason}
            for eid, wid, reason in REMOVE_ENTITY_WORK_LINKS
        ],
        "stats": stats,
    }
    dump_json(ROOT / ".claude" / "known-issues" / "人物作品單向_round1已修復.json", report)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
