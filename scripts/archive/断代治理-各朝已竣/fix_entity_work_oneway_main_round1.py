#!/usr/bin/env python3
"""修復 main 合併後回出的 Entity→Work 單向關聯。

處理原則：
- Work 作者與 Entity 明確同人者，只補 Work.authors[].entity_id。
- Work ai_note 或題名/作者已表明原 Entity 為誤繫者，刪除 Entity.works 中殘留 work_id。
- 同步受影響 Work 在 index/works 分片中的 author 欄位。
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TODAY = "2026-08-09"
SHARDS = "0123456789abcdef"

ADD_ENTITY_ID = {
    "1evgpj1gsd3wg": "1j967afjav1vw",  # 蕭衍《孝子傳》
    "1evgojczezi80": "1j96h8rw7vhih",  # 徐震《合浦珠》
    "1evdidd5s2znk": "1j96hhvcrjvhe",  # 德清《華嚴法界境》
    "1evga65pp3g1s": "1j96hhvcrjvj7",  # 許珍《太極圖解釋義》
    "1evgpmxxxalmo": "1j96hfvnmujnk",  # 海鵬《忠經》
    "1evgomnkx23uo": "1j96kejeblo8w",  # 文康《兒女英雄傳》
    "1ev3bbmslhvr4": "1j96hjwlxny11",  # 柯洽《天文書》
    "1evkpxffmr7k0": "1j967bgl70k5j",  # 王逵《蠡海集》
    "1ev3bb5v90l4w": "1j96hhvcr8my2",  # 許浩《宋史闡幽》
    "1ev3bdii6aa68": "1j96hhvcrjvh2",  # 沈貞《茶山老人遺集》
}

REMOVE_ENTITY_WORK = {
    ("1j96hjwlxny3u", "1ev7xm2sm7vgg"),  # 竇說 ↛ 漢志臣說賦
    ("1j96hjwlyaf4v", "1evfuuthi4w00"),  # 釋福登 ↛ 遠游志「續」
    ("1j96ad68m1zpc", "1evgpnggtt62o"),  # 張仲景 ↛ 張機《莊子講疏》
    ("1j96hjwlxny3q", "1ev7xkh7f48w0"),  # 釋紹明 ↛ 漢志臣彭
    ("1j96hhvcrjviq", "1evfuvlzosow0"),  # 劉銑 ↛ 劉昞
    ("1j96ha8kt5jwg", "1evfuvlh38npc"),  # 「氏」為殘字，非可立人物
    ("1j96hel2x07wg", "1ev3badi9bxmo"),  # 「東」殘名 ↛ 陳東
    ("1j96hjwlyaf61", "1evga3af5tbls"),  # 舒庭謨 ↛ 完顏宗弼
    ("1j967bgl89icn", "1evgbzfgq57uo"),  # 北宋王珪 ↛ 元王珪
    ("1j967c148wsnm", "1evgpivar79xc"),  # 明彭年 ↛ 北宋陳彭年
    ("1j96hfxgmpfk0", "1evgpo81ykc8w"),  # 誤截「人又有成武丁」
    ("1j96hei5hwzk0", "1evr5e3mfaxxj"),  # 誤截「掾何休始」
    ("1j96hgd6jn18g", "1evdidlitufwg"),  # 殘名 ↛ 桑悅
    ("1j967cp21969z", "1evdie3p8va4g"),  # 林富 ↛ 釋守仁
    ("1j96hldyxbt34", "1ev7xkh9dz474"),  # 釋祖賢 ↛ 漢志臣饒
    ("1j96a9eeaj4sg", "1evfubme77qio"),  # 謝沈 ↛ 謝模
    ("1j96kegcdkkcg", "1evfuuz7xqsqo"),  # 戴逵 ↛ 戴祚
    ("1j968k0jdrlz7", "1evke141j8b28"),  # 司馬遷 ↛ 二十四史總集
    ("1j96hjwlylnqg", "1evgq9ln4jxmo"),  # 張相侯 ↛ 吳廷舉
    ("1j96hfxdvfytc", "1evgpo5vxv0g0"),  # 誤截「人居紫陽山」
    ("1j96h8rw790e2", "1ev3bcmg50bnk"),  # 劉文耀 ↛ 佚名《雲間雜記》
    ("1j96hjwlxny3v", "1ev7xm2takdts"),  # 董葵 ↛ 漢志臣義賦
    ("1jae2gjvgxkba", "1ev3ba9nc3qbk"),  # 謝堃 ↛ 吳均
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def shard_of(id_str: str) -> str:
    h = 0
    for c in id_str:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return f"{h % 16:x}"


def paths_by_id(pattern: str):
    out = {}
    for path in ROOT.glob(pattern):
        data = load_json(path)
        if data.get("id"):
            out[data["id"]] = path
    return out


def sync_work_index(work_id: str, work: dict):
    shard = shard_of(work_id)
    path = ROOT / "index" / "works" / f"{shard}.json"
    data = load_json(path)
    entry = data.get(work_id)
    if not entry:
        return None
    old = entry.get("author")
    authors = work.get("authors") or []
    if authors and authors[0].get("name"):
        entry["author"] = authors[0]["name"]
    dump_json(path, data)
    return {"old_author": old, "new_author": entry.get("author"), "shard": shard}


def main():
    work_paths = paths_by_id("Work/*/*/*/*.json")
    entity_paths = paths_by_id("Entity/*/*/*/*.json")

    added = []
    removed = []
    index_synced = []

    for work_id, entity_id in ADD_ENTITY_ID.items():
        path = work_paths[work_id]
        work = load_json(path)
        authors = work.get("authors") or []
        if not authors:
            raise RuntimeError(f"{work_id} has no authors")
        before = authors[0].get("entity_id")
        authors[0]["entity_id"] = entity_id
        work["updated_at"] = TODAY
        dump_json(path, work)
        added.append(
            {
                "work_id": work_id,
                "work_title": work.get("title"),
                "work_path": path.relative_to(ROOT).as_posix(),
                "entity_id": entity_id,
                "old_entity_id": before,
                "author": authors[0].get("name"),
            }
        )
        synced = sync_work_index(work_id, work)
        if synced:
            index_synced.append({"work_id": work_id, **synced})

    for entity_id, work_id in sorted(REMOVE_ENTITY_WORK):
        path = entity_paths[entity_id]
        entity = load_json(path)
        before = entity.get("works") or []
        after = [item for item in before if item.get("work_id") != work_id]
        if len(after) == len(before):
            raise RuntimeError(f"{entity_id} did not contain {work_id}")
        entity["works"] = after
        entity["updated_at"] = TODAY
        dump_json(path, entity)
        removed.append(
            {
                "entity_id": entity_id,
                "entity_name": entity.get("primary_name"),
                "work_id": work_id,
                "entity_path": path.relative_to(ROOT).as_posix(),
            }
        )

    # 同步目前唯一的 index author 不符：蕭衍《孝子傳》。
    for work_id in ["1evgpj1gsd3wg"]:
        work = load_json(work_paths[work_id])
        synced = sync_work_index(work_id, work)
        if synced and not any(x["work_id"] == work_id for x in index_synced):
            index_synced.append({"work_id": work_id, **synced})

    report = {
        "date": TODAY,
        "issue": "main 更新後 Entity.works 與 Work.authors[].entity_id 出現單向殘留。",
        "principle": "可信同人補 Work 作者 entity_id；已知誤繫或殘名串位從 Entity.works 刪除。",
        "added_entity_id": added,
        "removed_entity_work": removed,
        "index_synced": index_synced,
        "counts": {
            "added_entity_id": len(added),
            "removed_entity_work": len(removed),
            "index_synced": len(index_synced),
        },
    }
    out = ROOT / ".claude" / "known-issues" / "人物作品單向_main_round1已修復.json"
    dump_json(out, report)
    print(json.dumps(report["counts"], ensure_ascii=False, indent=2))
    print(out.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
