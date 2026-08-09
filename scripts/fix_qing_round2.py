#!/usr/bin/env python3
"""
fix_qing_round2.py — 清朝整理 Round 2 高置信修复

处理范围：
- Round 1 留下的「Work.dynasty 为空、作者 dynasty 皆为清、但 period 非 qing」条目。
- 只处理书目提要/CBDB cache/题名与作者组合已经能高置信判定的显式白名单。
- 同步修正由清代机械传播造成的误关联 Entity.dynasty/period。

安全边界：
- 不处理泉之《九经术疏》、嘉庆《本草要诀》、张豫章《御选宋诗》等仍缺少足够证据的条目。
- 不做 Entity 合并；只修正已有关联 Entity 的 dynasty/period 与 Work 作者字段。
- 对同一误标 Entity 已关联的其他同朝作品，若 Work.dynasty 为空，也一并补全，避免 Entity 与 Work 不一致。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUND1_PATH = ROOT / ".claude" / "known-issues" / "清朝整理_round1_未決.json"
OUT_PATH = ROOT / ".claude" / "known-issues" / "清朝整理_round2_未決.json"


PERIOD_BY_DYNASTY = {
    "清": "qing",
    "宋": "song",
    "南朝梁": "nanbeichao",
}


# Work 级显式修复。basis 记录采用的最强证据。
WORK_FIXES = {
    # 四库总目/续修四库/宋史艺文志补等明示为宋
    "1ev3b9x5l0e0w": ("宋", "四库总目 author_info=宋陈经撰；CBDB 14390 dynasty_id=15"),
    "1ev3ba6ukmxog": ("宋", "四库总目 author_info=宋陈暘撰；CBDB 47561 dynasty_id=15"),
    "1ev3bablp6igw": ("宋", "四库总目 author_info=宋陈均撰；CBDB 10888 dynasty_id=15"),
    "1ev3bajo2dlhc": ("宋", "四库总目/存目丛书 author_info=宋赵起撰；CBDB 50087 dynasty_id=15"),
    "1ev3bbp1i58g0": ("宋", "四库总目 author_info=宋董史撰；CBDB 49680 dynasty_id=15"),
    "1ev3bbt3iebk0": ("宋", "四库总目 author_info=宋王灼撰；CBDB 35058 dynasty_id=15"),
    "1ev3bbwpfm70g": ("宋", "四库总目 author_info=宋马永卿编；CBDB 531265 dynasty_id=15"),
    "1ev3bbwq49xxc": ("宋", "四库总目同作者马永卿；CBDB 531265 dynasty_id=15"),
    "1ev3bd4hvs934": ("宋", "四库总目 author_info=宋陈杰撰；宋史艺文志补同题；CBDB 47405 dynasty_id=15"),
    "1ev3bf6chiygw": ("宋", "四库总目同作者王灼；CBDB 35058 dynasty_id=15"),
    "1evjr7c8gd340": ("宋", "续修四库全书 author_info=宋王灼撰；CBDB 35058 dynasty_id=15"),
    "1evjy4zyyc5j4": ("宋", "陈均同一 Entity；CBDB 10888 dynasty_id=15"),
    "1evkafylan0n4": ("宋", "陈均同一 Entity；CBDB 10888 dynasty_id=15"),
    "1evke9w39zcw0": ("宋", "清史稿艺文志 summary=宋徐总干《易传灯》四卷"),
    "1evkphntw29kw": ("宋", "董史同一 Entity；CBDB 49680 dynasty_id=15"),
    "1evkpxwp8xatc": ("宋", "四库总目/清史稿艺文志均指宋吴可《藏海诗话》"),
    "1evrbhp6a8ijb": ("宋", "宋史艺文志补收录刘开撰；CBDB 543857 dynasty_id=15"),
    "1evrbhp6a8ijc": ("宋", "宋史艺文志补收录刘开撰；CBDB 543857 dynasty_id=15"),
    "1evrbhp6a8ijd": ("宋", "宋史艺文志补收录刘开撰；CBDB 543857 dynasty_id=15"),
    "1evrbhp6ajqxu": ("宋", "宋史艺文志补收录郑侨撰；CBDB 11053 dynasty_id=15"),
    "1evrbhp6ajr2u": ("宋", "宋史艺文志补收录梁栋撰；CBDB 557120 dynasty_id=15"),

    # 四库总目/隋志/国史经籍志明示为梁
    "1ev3bbth1ciyo": ("南朝梁", "四库总目/存目丛书 author_info=梁江淹撰"),
    "1ev3bctqj7u9s": ("南朝梁", "四库总目 author_info=梁江淹撰；书目答问同题"),
    "1evetxcx017nk": ("南朝梁", "隋书经籍志考证 summary=梁有江淹《齐史》十三卷"),
    "1ev3bctr7943k": ("南朝梁", "四库总目 author_info=梁何逊撰；书目答问同题"),
    "1evgor4zqsf0g": ("南朝梁", "国史经籍志 author_info=梁鲍泉"),
    "1evcml0zqmg3k": ("南朝梁", "隋书经籍志考证引梁书本传鲍泉撰《新仪》"),
    "1evgpibstx7gg": ("南朝梁", "鲍泉同一 Entity；新唐志/国史经籍志同题"),
    "1evc5pehyaolc": ("南朝梁", "隋书经籍志 author_info=梁舍人鲍泉撰"),

    # 北宋陈景元，原误入 nanbeichao
    "1evgpndpf1e68": ("宋", "陈景元道教著作；国史经籍志同题，非南北朝"),
    "1evgpnhltyeww": ("宋", "陈景元道教著作；国史经籍志同题，非南北朝"),

    # 高置信清代条目
    "1evcpcuupmqkg": ("清", "书目答问=杭世骏《质疑》"),
    "1evgomnkx23uo": ("清", "中国通俗小说书目 summary=清文康撰"),
    "1evjqywczqeww": ("清", "续修四库全书收《寿栎庐仪礼奭固礼事图》"),
    "1evjqyx9qei2o": ("清", "续修四库全书 author_info=吴之英撰"),
    "1evkapoa9wkjk": ("清", "夏燮撰《明通鉴纲目》，清人著明史"),
    "1evke3zptkt1c": ("清", "清史稿艺文志/续修四库全书=(清)严元照撰"),
    "1evkpx76jn7k0": ("清", "四库总目 author_info=国朝茅星来撰；清史稿艺文志同题"),
    "1evkq1wa0fxts": ("清", "题名欽定金史語解，作者弘历"),
    "1evkq1wfkj20w": ("清", "题名欽定元史語解，作者弘历"),
    "1evkq20cr8740": ("清", "题名御製圆明园四十景诗，作者高宗乾隆"),
    "1evkq2561hv5s": ("清", "作者胤禛"),
    "1evkq2wg22sxs": ("清", "题名欽定中枢政考，作者尹继善"),
}


ENTITY_FIXES = {
    "1j967afjbsrj0": ("宋", "CBDB 14390 dynasty_id=15；四库总目宋陈经撰"),
    "1j967avzl1bgc": ("宋", "CBDB 47561 dynasty_id=15；四库总目宋陈暘撰"),
    "1j967avzlck07": ("宋", "CBDB 10888 dynasty_id=15；四库总目宋陈均撰"),
    "1j967avzlz13x": ("宋", "CBDB 50087 dynasty_id=15；四库总目宋赵起撰"),
    "1j967bgl6e34i": ("宋", "CBDB 49680 dynasty_id=15；四库总目宋董史撰"),
    "1j967bgl6pbmi": ("宋", "CBDB 35058 dynasty_id=15；四库总目宋王灼撰"),
    "1j96hjwlxcpht": ("宋", "CBDB 531265 dynasty_id=15；四库总目宋马永卿编"),
    "1j967c147clxm": ("宋", "CBDB 47405 dynasty_id=15；四库总目宋陈杰撰"),
    "1j96heismewao": ("宋", "清史稿艺文志 summary=宋徐总干《易传灯》四卷"),
    "1j96hldqqnsao": ("宋", "四库总目/清史稿艺文志均指宋吴可《藏海诗话》"),
    "1j969lr2t0ro4": ("宋", "CBDB 543857 dynasty_id=15；宋史艺文志补刘开撰"),
    "1j969lr2t0ro8": ("宋", "CBDB 11053 dynasty_id=15；宋史艺文志补郑侨撰"),
    "1j969lr2t0rph": ("宋", "CBDB 557120 dynasty_id=15；宋史艺文志补梁栋撰"),
    "1j96gmdzl5pfm": ("南朝梁", "四库总目/存目丛书梁江淹撰"),
    "1j96hjwlxny29": ("南朝梁", "四库总目梁何逊撰"),
    "1j96h8rw7k8w5": ("南朝梁", "隋书经籍志/国史经籍志均指梁鲍泉"),
    "1j96hhvcrv40c": ("宋", "陈景元道教著作，误入南北朝/清"),
}


STILL_UNRESOLVED_NOTES = {
    "1evgorqt3jw8w": "《九经术疏》虽见国史经籍志 author_info=宋泉之，但当前 entity_id 指向吴省兰，需回源确认人名与关联。",
    "1evgq4n14oge8": "《本草要诀》见国史经籍志 author_info=梁嘉庆；当前 Entity 为清嘉庆，疑同名/误关联，需补原始条目。",
    "1evkphixywge8": "《御选宋诗》题名可疑但缺少 indexed_by 证据，暂不据题名强判。",
}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def load_json(fp: Path):
    return json.loads(fp.read_text(encoding="utf-8"))


def write_json(fp: Path, data):
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iter_work_files():
    return sorted(ROOT.glob("Work/?/?/?/*.json"))


def iter_entity_files():
    return sorted(ROOT.glob("Entity/?/?/?/*.json"))


def apply_work_fix(w, new_dyn, basis, stats):
    changed = False
    new_period = PERIOD_BY_DYNASTY[new_dyn]
    if w.get("dynasty") != new_dyn:
        w["dynasty"] = new_dyn
        w["dynasty_basis"] = f"qing_round2:{basis}"
        changed = True
        stats[f"work.dynasty->{new_dyn}"] += 1
    if w.get("period") != new_period:
        w["period"] = new_period
        w["period_basis"] = f"据 dynasty「{new_dyn}」自动归并"
        changed = True
        stats[f"work.period->{new_period}"] += 1
    for a in w.get("authors", []) or []:
        if not isinstance(a, dict):
            continue
        eid = a.get("entity_id")
        if eid in ENTITY_FIXES or w.get("id") in WORK_FIXES:
            if a.get("dynasty") != new_dyn:
                a["dynasty"] = new_dyn
                a["dynasty_basis"] = f"qing_round2:{basis}"
                changed = True
                stats[f"author.dynasty->{new_dyn}"] += 1
    if changed:
        w["updated_at"] = now_iso()
    return changed


def apply_entity_fix(e, new_dyn, basis, stats):
    changed = False
    new_period = PERIOD_BY_DYNASTY[new_dyn]
    if e.get("dynasty") != new_dyn:
        e["dynasty"] = new_dyn
        e["dynasty_basis"] = f"qing_round2:{basis}"
        changed = True
        stats[f"entity.dynasty->{new_dyn}"] += 1
    if e.get("period") != new_period:
        e["period"] = new_period
        e["period_basis"] = f"据 dynasty「{new_dyn}」自动归并"
        changed = True
        stats[f"entity.period->{new_period}"] += 1
    if changed:
        e["updated_at"] = now_iso()
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    commit = args.commit or not args.dry_run

    works = {}
    work_paths = {}
    entities = {}
    entity_paths = {}
    stats = Counter()
    changed_work_ids = set()
    changed_entity_ids = set()

    for fp in iter_work_files():
        w = load_json(fp)
        wid = w.get("id", fp.stem)
        works[wid] = w
        work_paths[wid] = fp
    for fp in iter_entity_files():
        e = load_json(fp)
        eid = e.get("id", fp.stem)
        entities[eid] = e
        entity_paths[eid] = fp

    # A. 显式 Work 白名单修复
    for wid, (new_dyn, basis) in WORK_FIXES.items():
        w = works.get(wid)
        if not w:
            stats["missing.work_fix"] += 1
            continue
        if apply_work_fix(w, new_dyn, basis, stats):
            changed_work_ids.add(wid)

    # B. Entity 白名单修复
    for eid, (new_dyn, basis) in ENTITY_FIXES.items():
        e = entities.get(eid)
        if not e:
            stats["missing.entity_fix"] += 1
            continue
        if apply_entity_fix(e, new_dyn, basis, stats):
            changed_entity_ids.add(eid)

    # C. 对已修 Entity 关联 Work 做一致性补全（只覆盖空值或明显误标清）
    for eid in changed_entity_ids | set(ENTITY_FIXES):
        e = entities.get(eid)
        if not e:
            continue
        new_dyn = e.get("dynasty")
        if new_dyn not in PERIOD_BY_DYNASTY:
            continue
        basis = e.get("dynasty_basis", "qing_round2:entity consistency")
        for rel in e.get("works", []) or []:
            wid = rel.get("work_id") if isinstance(rel, dict) else None
            w = works.get(wid)
            if not w:
                continue
            # 不覆盖已有非清、非空的人工判断。
            if w.get("dynasty") not in (None, "清", new_dyn) and wid not in WORK_FIXES:
                continue
            if apply_work_fix(w, new_dyn, basis, stats):
                changed_work_ids.add(wid)

    # D. 输出 Round 2 后未决清单
    round1 = load_json(ROUND1_PATH)
    unresolved = {
        "description": "清朝整理 Round 2 后未决清单",
        "scope": "Round 2 只修书目/CBDB/题名作者组合高置信白名单；疑似同名异人或缺原始证据者保留。",
        "remaining_work_items": [],
        "remaining_entity_qing_period_missing": [],
        "remaining_entity_qing_period_conflict": [],
        "stats": dict(stats),
    }
    for item in round1.get("remaining_work_empty_dynasty_authors_all_qing_non_qing_period", []):
        wid = item["work_id"]
        if wid in WORK_FIXES:
            continue
        w = works.get(wid, {})
        if w.get("dynasty") and w.get("period") == PERIOD_BY_DYNASTY.get(w.get("dynasty")):
            continue
        out = dict(item)
        out["note"] = STILL_UNRESOLVED_NOTES.get(wid, "未纳入 Round 2 高置信白名单。")
        unresolved["remaining_work_items"].append(out)

    for eid, e in entities.items():
        if e.get("dynasty") != "清":
            continue
        if not e.get("period"):
            unresolved["remaining_entity_qing_period_missing"].append({
                "entity_id": eid,
                "name": e.get("primary_name"),
                "cbdb_id": (e.get("external_ids") or {}).get("cbdb_id") if isinstance(e.get("external_ids"), dict) else None,
                "works": e.get("works", []),
            })
        elif e.get("period") != "qing":
            unresolved["remaining_entity_qing_period_conflict"].append({
                "entity_id": eid,
                "name": e.get("primary_name"),
                "period": e.get("period"),
                "cbdb_id": (e.get("external_ids") or {}).get("cbdb_id") if isinstance(e.get("external_ids"), dict) else None,
                "works": e.get("works", []),
            })

    if commit:
        for wid in changed_work_ids:
            write_json(work_paths[wid], works[wid])
        for eid in changed_entity_ids:
            write_json(entity_paths[eid], entities[eid])

        for shard_fp in sorted((ROOT / "index" / "works").glob("*.json")):
            shard = load_json(shard_fp)
            changed = False
            for wid, entry in shard.items():
                if not isinstance(entry, dict) or wid not in changed_work_ids:
                    continue
                w = works[wid]
                for key in ("dynasty", "period"):
                    if entry.get(key) != w.get(key):
                        entry[key] = w.get(key)
                        stats[f"index.work.{key}_sync"] += 1
                        changed = True
            if changed:
                write_json(shard_fp, shard)
                stats["index.work.shards_changed"] += 1

        for shard_fp in sorted((ROOT / "index" / "entities").glob("*.json")):
            shard = load_json(shard_fp)
            changed = False
            for eid, entry in shard.items():
                if not isinstance(entry, dict) or eid not in changed_entity_ids:
                    continue
                e = entities[eid]
                for key in ("dynasty", "period"):
                    if entry.get(key) != e.get(key):
                        entry[key] = e.get(key)
                        stats[f"index.entity.{key}_sync"] += 1
                        changed = True
            if changed:
                write_json(shard_fp, shard)
                stats["index.entity.shards_changed"] += 1

        unresolved["stats"] = dict(stats)
        write_json(OUT_PATH, unresolved)

    print("=== 清朝整理 Round 2 统计 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:36s} {v:>6}")
    print(f"changed_work_ids={len(changed_work_ids)}")
    print(f"changed_entity_ids={len(changed_entity_ids)}")
    print(f"remaining_work_items={len(unresolved['remaining_work_items'])}")
    print(f"remaining_entity_qing_period_missing={len(unresolved['remaining_entity_qing_period_missing'])}")
    print(f"remaining_entity_qing_period_conflict={len(unresolved['remaining_entity_qing_period_conflict'])}")
    print(f"输出: {OUT_PATH}")


if __name__ == "__main__":
    main()
