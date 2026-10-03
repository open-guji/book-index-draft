#!/usr/bin/env python3
"""
fix_ming_round1.py — 明朝未決項高置信修復（Round 1）

period=ming Work 共 10435，全數 dynasty 空。

修復：
1. 單/多 author.dynasty ∈ {明,南明,明末清初,明清} → Work.dynasty=明，
   author.dynasty 空但 Entity.dynasty=明系 → 補明。
2. 誤入明桶：
   · Entity.dynasty=元/金/遼 ∧ Entity.period=liao-jin-yuan → Work.period=liao-jin-yuan, dynasty=Entity.dynasty
   · Entity.dynasty=清 → Work.period=qing, dynasty=清
   · Entity.dynasty=晉 → Work.period=jin, dynasty=晉
   · 朱熹（南宋）→ Work.period=song, dynasty=南宋（已知人物）
3. manual_null_entity 12 條：唯一主來源明史藝文志 → Work.dynasty=明 (gazetteer_propagation)
4. Entity.dynasty ∈ {明,南明,明末清初,明清} 但 period 空 → period=ming (period_basis=synonym)
5. author.dynasty 覆蓋：若 author.dynasty null 但 Entity.dynasty 明系/非明系（誤入），同步補 author.dynasty。
6. 同步 index（Work.dynasty / Work.period / Entity.period）。

留 Round 2：380 no_author 用明史藝文志的 gazetteer_propagation + 其他規則細化。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MING_CANON = {"明", "南明", "明末清初", "明清"}
# 非明的 entity.dynasty → (new_period, new_dynasty)
MISCLASS_MAP = {
    "元": ("liao-jin-yuan", "元"),
    "金": ("liao-jin-yuan", "金"),
    "遼": ("liao-jin-yuan", "遼"),
    "蒙古": ("liao-jin-yuan", "蒙古"),
    "西夏": ("liao-jin-yuan", "西夏"),
    "金元": ("liao-jin-yuan", "金元"),
    "遼金元": ("liao-jin-yuan", "遼金元"),
    "清": ("qing", "清"),
    "清末": ("qing", "清"),
    "晉": ("jin", "晉"),
    "南宋": ("song", "南宋"),
    "北宋": ("song", "北宋"),
    "宋": ("song", "宋"),
    "隋唐": ("sui-tang", "隋唐"),
    "三國": ("three-kingdoms", "三國"),
    "南北朝": ("nanbeichao", "南北朝"),
}
MING_DYNASTY_ONLY_GAZETTEERS = {"明史藝文志"}  # 明本朝斷代志；SCHEMA 自驗下幾乎 100% 明


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def load_json(fp: Path):
    return json.loads(fp.read_text(encoding="utf-8"))


def write_json(fp: Path, data):
    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iter_work_files(): return sorted(ROOT.glob("Work/?/?/?/*.json"))
def iter_entity_files(): return sorted(ROOT.glob("Entity/?/?/?/*.json"))


def append_note(obj, text):
    old = obj.get("ai_note") or ""
    marker = f"[ming-round1: {text}]"
    if marker not in old:
        obj["ai_note"] = (old + " " + marker).strip()


def entity_cbdy(e, cbdb_cache):
    ext = e.get("external_ids", {})
    cid = ext.get("cbdb_id") if isinstance(ext, dict) else None
    if not cid: return None, None
    entry = cbdb_cache.get(str(cid))
    if not entry or "error" in entry: return str(cid), None
    return str(cid), str(entry.get("dynasty_id", ""))


def resolve(authors, emap, cbdb_cache):
    """為每個作者解出朝代；回傳 list of (dyn, kind, (eid, canon_for_override))"""
    out = []
    for a in authors:
        ad = a.get("dynasty")
        eid = a.get("entity_id")
        ent = emap.get(eid) if eid else None
        ed = ent.get("dynasty") if ent else None
        ep = ent.get("period") if ent else None
        # 特殊：朱熹（朱夫子 南宋）無 entity 關聯
        if not ent and a.get("name") == "朱熹":
            out.append(("南宋", "known_figure", (None, None, "song", "南宋")))
            continue
        if ad in MING_CANON:
            out.append(("明", "direct", (None, None, None, None)))
            continue
        if ad in MISCLASS_MAP:
            np_, nd_ = MISCLASS_MAP[ad]
            # author 標了非明（通常是對的），只有 entity 與之不一致才 override
            if ed and ed in MING_CANON:
                out.append(("明", "entity_override", (eid, None, None, None)))  # 以 entity=明為準
            else:
                out.append((nd_ or ad, "direct_misclass", (None, None, np_, nd_)))
            continue
        if ad is None and ed in MING_CANON:
            out.append(("明", "entity", (eid, ed, None, None)))
            continue
        if ed in MISCLASS_MAP:
            np_, nd_ = MISCLASS_MAP[ed]
            out.append((nd_, "entity_misclass", (eid, ed, np_, nd_)))
            continue
        # Entity.dynasty=null 但 Work.period=ming + indexed_by⊆明史藝文志（由調用方據 gazetteer 補）
        out.append((None, "unresolved", (eid, ed, None, None)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    commit = not args.dry_run

    stats = Counter()
    changed_work_ids = set()
    changed_entity_ids = set()
    skipped = []

    works = {}; work_paths = {}
    for fp in iter_work_files():
        d = load_json(fp); works[d.get("id", fp.stem)] = d; work_paths[d.get("id", fp.stem)] = fp
    entities = {}; entity_paths = {}
    for fp in iter_entity_files():
        d = load_json(fp); entities[d.get("id", fp.stem)] = d; entity_paths[d.get("id", fp.stem)] = fp
    cbdb_cache = load_json(ROOT / ".claude" / "known-issues" / "cbdb_dy_cache.json") or {}

    # A. Work 修復
    for wid, w in works.items():
        if w.get("period") != "ming": continue
        if w.get("dynasty"): continue
        authors = [a for a in (w.get("authors", []) or []) if isinstance(a, dict)]
        if not authors:
            stats["A.work.skipped.no_author"] += 1
            continue  # Round 2

        resolved = resolve(authors, entities, cbdb_cache)
        dyns = set(r[0] for r in resolved if r[0])
        changes = False

        # 判定新 period / dynasty
        new_dyn = None
        new_per = None  # None 表示不變（保持 ming）
        per_basis = None
        dyn_basis = None
        note = None

        # Case 1: 全部都解出且一致為明系
        if dyns and dyns <= {"明", "南明", "明末清初", "明清"}:
            new_dyn = "明"
            dyn_basis = "author_propagation"
            note = f"author.dynasty 集合={sorted(dyns)} → dynasty=明"
            stats["A.work.dynasty_filled.ming"] += 1

        # Case 2: 全部解出一致為某個非明（誤入移出）
        elif len(dyns) == 1:
            d0 = next(iter(dyns))
            r0 = next(r for r in resolved if r[0] == d0)
            kind = r0[1]
            # 查表找 period
            target_per = None
            for ed_, (p_, nd_) in MISCLASS_MAP.items():
                if d0 == nd_: target_per = p_; break
            if target_per:
                new_dyn = d0
                new_per = target_per
                dyn_basis = "entity_propagation" if kind in ("entity_misclass", "entity") else "author_propagation"
                per_basis = "cross_check"
                note = f"誤入明：移出 period=ming→{target_per}, dynasty={d0}（kind={kind}）"
                stats[f"A.work.misclass_to_{target_per}.{d0}"] += 1
            else:
                # 無法確定 period，保留 ming，補 dynasty 用 gazetteer fallback（明史藝文志）
                srcs = set()
                for s in (w.get("indexed_by") or []):
                    if isinstance(s, dict) and s.get("source"): srcs.add(s["source"])
                if srcs and srcs <= MING_DYNASTY_ONLY_GAZETTEERS:
                    new_dyn = "明"
                    dyn_basis = "gazetteer_propagation"
                    note = "author.dynasty 未決；indexed_by⊆明史藝文志 → 補明（gazetteer）"
                    stats["A.work.dynasty_filled.ming_gazetteer_fallback"] += 1
                else:
                    stats["A.work.skipped.unresolved"] += 1
                    skipped.append({"work_id": wid, "title": w.get("title"),
                                    "reason": f"dynasty 集合={dyns} 且 period 無法決定，sources={sorted(srcs)}"})
                    continue

        # Case 3: 部分未決（含 None）— 嘗試 gazetteer 補明
        elif not dyns or None in [r[0] for r in resolved]:
            # 所有 resolved 都要嘛=明 要不=None（沒有非明），才能用 gazetteer
            # 即 dyns == set() or dyns <= MING_CANON
            non_ming_dyns = dyns - {"明", "南明", "明末清初", "明清"}
            if non_ming_dyns:
                stats["A.work.skipped.mixed"] += 1
                skipped.append({"work_id": wid, "title": w.get("title"),
                                "reason": f"含非明 author.dynasty={non_ming_dyns}"})
                continue
            # 用明史藝文志
            srcs = set()
            for s in (w.get("indexed_by") or []):
                if isinstance(s, dict) and s.get("source"): srcs.add(s["source"])
            # 也接受 mixed，但明系作者 majority 已佔
            # 簡化：只要 source 包含明史藝文志（或無明系 source 但所有 resolved author 是明 or null）
            # 對於 manual_null_entity 12 條通常唯一來源=明史藝文志
            # 對於 mixed no_entity 3 條：朱熹→宋（resolved 已抓）、楊景賢+楊東來=元末明初+明→補明 OK
            # 所以此桶僅針對 author 全未解 or 明+null 混，有明史藝文志就補明
            if srcs <= MING_DYNASTY_ONLY_GAZETTEERS and srcs:
                new_dyn = "明"
                dyn_basis = "gazetteer_propagation"
                note = f"author 部分未決；indexed_by⊆明史藝文志 → 補明。authors 狀態={[(r[0],r[1]) for r in resolved]}"
                stats["A.work.dynasty_filled.ming_gazetteer"] += 1
            else:
                # 含其他來源：棄權
                stats["A.work.skipped.mixed_sources"] += 1
                skipped.append({"work_id": wid, "title": w.get("title"),
                                "reason": f"author 未決且 sources={sorted(srcs)} 超出明史藝文志"})
                continue
        else:
            # 多 dyns 非明系（罕見）— 棄權
            stats["A.work.skipped.multi_nonming"] += 1
            skipped.append({"work_id": wid, "title": w.get("title"),
                            "reason": f"author.dynasty={sorted(dyns)} 含多非明"})
            continue

        # 寫入 Work
        if new_dyn:
            w["dynasty"] = new_dyn
            w["dynasty_basis"] = dyn_basis
            changes = True
        if new_per:
            w["period"] = new_per
            w["period_basis"] = per_basis or "cross_check"
            changes = True
        append_note(w, note or f"dynasty null→{new_dyn}")

        # 同步作者層：author.dynasty null 但 entity.dynasty 明系/非明 要覆蓋
        for a, r in zip(authors, resolved):
            dyn, kind, extra = r
            if kind in ("entity", "entity_misclass"):
                eid = extra[0]; ed = extra[1]
                if eid and a.get("dynasty") is None and ed:
                    a["dynasty"] = ed
                    append_note(w, f"author({a.get('name')}) dynasty null→{ed} (依 Entity)")
                    stats["A.work.author_dynasty_override"] += 1
                    changes = True
            elif kind == "known_figure":
                # 朱熹
                a["dynasty"] = "南宋"
                append_note(w, f"author({a.get('name')}) dynasty null→南宋 (known_figure)")
                stats["A.work.author_dynasty_override.known_figure"] += 1
                changes = True

        w["updated_at"] = now_iso()
        if changes:
            changed_work_ids.add(wid)

    # B. Entity.period 補：dynasty ∈ MING_CANON 且 period 空
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn not in MING_CANON or e.get("period"): continue
        e["period"] = "ming"
        e["period_basis"] = "synonym"
        append_note(e, f"period null→ming (據 dynasty={dyn})")
        e["updated_at"] = now_iso()
        stats[f"B.entity.period_filled.{dyn}"] += 1
        changed_entity_ids.add(eid)

    if commit:
        for wid in changed_work_ids:
            write_json(work_paths[wid], works[wid])
        for eid in changed_entity_ids:
            write_json(entity_paths[eid], entities[eid])

        idx_dir = ROOT / "index"
        for shard_fp in sorted((idx_dir / "works").glob("*.json")):
            shard = load_json(shard_fp)
            changed_idx = False
            for wid, entry in shard.items():
                if not isinstance(entry, dict) or wid not in changed_work_ids or wid not in works: continue
                wk = works[wid]
                if entry.get("dynasty") != wk.get("dynasty"):
                    entry["dynasty"] = wk.get("dynasty")
                    changed_idx = True
                    stats["C.index.work.dynasty_sync"] += 1
                if entry.get("period") != wk.get("period"):
                    entry["period"] = wk.get("period")
                    changed_idx = True
                    stats["C.index.work.period_sync"] += 1
            if changed_idx:
                write_json(shard_fp, shard)
                stats["C.index.work.shards_changed"] += 1

        for shard_fp in sorted((idx_dir / "entities").glob("*.json")):
            shard = load_json(shard_fp)
            changed_idx = False
            for eid, entry in shard.items():
                if not isinstance(entry, dict) or eid not in changed_entity_ids or eid not in entities: continue
                e = entities[eid]
                if entry.get("period") != e.get("period"):
                    entry["period"] = e.get("period")
                    changed_idx = True
                    stats["C.index.entity.period_sync"] += 1
            if changed_idx:
                write_json(shard_fp, shard)
                stats["C.index.entity.shards_changed"] += 1

    print("=== 明朝未決 Round 1 統計 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:52s} {v:>6}")
    remaining = [(w.get("id"), w.get("title")) for w in works.values()
                 if w.get("period") == "ming" and not w.get("dynasty")]
    print(f"\nperiod=ming 仍空 dynasty: {len(remaining)}")
    for wid, title in remaining[:12]: print(f"  {wid} {title}")
    print(f"\n棄權 {len(skipped)} 樣本:")
    for s in skipped[:6]: print(f"  {s['work_id']} {s['title']} — {s['reason'][:120]}")


if __name__ == "__main__":
    main()
