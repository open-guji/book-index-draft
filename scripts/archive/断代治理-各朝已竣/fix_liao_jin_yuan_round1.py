#!/usr/bin/env python3
"""
fix_liao_jin_yuan_round1.py — 遼金元未決項高置信修復（Round 1）

高置信修復：
1. period=liao-jin-yuan Work 補 Work.dynasty：
   - author.dynasty 俱屬 {遼,金,元,金元,蒙古,西夏,遼金元,偽齊} → 取集合決定
     · 單值 → 該值
     · 金+元 → 金元
     · 其他跨朝代組合 → 遼金元
   - author.dynasty 空 但 Entity.dynasty 屬遼金元規範 → 用 Entity.dynasty
   - author.dynasty 為歧義髒值（如三國魏）但 Entity.dynasty 屬遼金元規範 → 以 Entity 為準
2. misclassification_song（王厚之南宋誤入遼金元）：
   - Work.dynasty = 南宋
   - Work.period = song，period_basis = cross_check（CBDB c_dy=15）
   - 同步 author.dynasty = 南宋（取 Entity.dynasty）
3. Entity.dynasty ∈ {遼,金,元,蒙古,西夏,金元,遼金元,偽齊} 但 period 空者 → period=liao-jin-yuan。

不處理（棄權）：
- Work 無 authors（328 條，留人工）。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LJY_CANON = {"遼", "金", "元", "金元", "蒙古", "西夏", "遼金元", "偽齊"}
AMBIGUOUS = {
    "宋", "北宋", "南宋", "明", "清", "唐", "隋", "漢", "秦", "先秦",
    "三國", "三國魏", "南北朝", "五代", "隋唐", "明清", "漢魏", "春秋", "戰國"
}
DYN_TO_PERIOD = {
    "遼": "liao-jin-yuan", "西夏": "liao-jin-yuan",
    "金": "liao-jin-yuan", "蒙古": "liao-jin-yuan",
    "元": "liao-jin-yuan", "金元": "liao-jin-yuan",
    "遼金元": "liao-jin-yuan", "偽齊": "liao-jin-yuan",
    "南宋": "song", "北宋": "song",
}
CDY_SONG = {"15"}


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


def append_note(obj: dict, text: str):
    old = obj.get("ai_note") or ""
    marker = f"[ljy-round1: {text}]"
    if marker not in old:
        obj["ai_note"] = (old + " " + marker).strip()


def compute_work_dynasty(work: dict, entity_map: dict, cbdb_cache: dict):
    """回傳 (dynasty, period, basis, note, fix_author, fix_entity_period)。
    dynasty/period=None 表示不動；fix_author=(entity_id, new_dynasty)；
    fix_entity_period=(entity_id, new_period) 若需順便修 Entity.period。"""
    authors = [a for a in (work.get("authors", []) or []) if isinstance(a, dict)]
    if not authors:
        return None, None, None, "no_author 棄權", None, None

    # 先查是否所有 author.dynasty (或 entity.dynasty 回退) 屬 LJY
    resolved = []  # list of (resolved_dynasty, is_song)
    fix_author = None
    fix_entity_period = None
    for a in authors:
        ad = a.get("dynasty")
        if ad in LJY_CANON:
            resolved.append((ad, False))
            continue
        eid = a.get("entity_id")
        ent = entity_map.get(eid) if eid else None
        ed = ent.get("dynasty") if ent else None
        if ad is None and ed in LJY_CANON:
            resolved.append((ed, False))
            continue
        # CBDB 攔截：entity 是宋（c_dy=15）
        if ent:
            ext = ent.get("external_ids", {})
            cbdb_id = ext.get("cbdb_id") if isinstance(ext, dict) else None
            if cbdb_id:
                entry = cbdb_cache.get(str(cbdb_id))
                if entry and "error" not in entry and str(entry.get("dynasty_id", "")) in CDY_SONG:
                    canon = ed or CDY_SONG_TO_CANON.get(str(entry["dynasty_id"]), "南宋")
                    fix_author = (eid, canon)
                    fix_entity_period = (eid, "song")
                    resolved.append((canon, True))
                    continue
        # entity.dynasty 屬 LJY，而 author.dynasty 是歧義髒值（override）
        if ad in AMBIGUOUS and ed in LJY_CANON:
            fix_author = (eid, ed)
            resolved.append((ed, True))
            continue
        # 無法決定
        return None, None, None, f"author.dynasty={ad} 無結論，棄權", None, None

    dyns = set(r[0] for r in resolved)
    any_song = any(r[1] for r in resolved)
    # 若 resolved 含南宋/北宋（任何 is_song=True），且 dyns 俱屬宋系 → period=song
    new_per = None
    if any_song:
        song_canon = {"南宋", "北宋"}
        if dyns <= song_canon:
            new_per = "song"
    if len(dyns) == 1:
        d0 = next(iter(dyns))
        return d0, new_per, "author_propagation", f"據 author.dynasty 集合補「{d0}」", fix_author, fix_entity_period
    if dyns == {"金", "元"}:
        return "金元", None, "author_propagation", "多作者跨金/元 → 金元", fix_author, fix_entity_period
    return "遼金元", None, "author_propagation", f"多作者跨{dyns} → 遼金元", fix_author, fix_entity_period


CDY_SONG_TO_CANON = {"15": "南宋"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    commit = not args.dry_run

    stats = Counter()
    changed_work_ids = set()
    changed_entity_ids = set()
    skipped = []

    works = {}
    work_paths = {}
    for fp in iter_work_files():
        d = load_json(fp)
        works[d.get("id", fp.stem)] = d
        work_paths[d.get("id", fp.stem)] = fp

    entities = {}
    entity_paths = {}
    for fp in iter_entity_files():
        d = load_json(fp)
        entities[d.get("id", fp.stem)] = d
        entity_paths[d.get("id", fp.stem)] = fp

    cbdb_cache = load_json(ROOT / ".claude" / "known-issues" / "cbdb_dy_cache.json") or {}

    # A. Work 修復
    for wid, w in works.items():
        ljy_work = w.get("period") == "liao-jin-yuan"
        if not ljy_work:
            continue
        dyn_already = bool(w.get("dynasty"))
        need_fix_period = dyn_already and w.get("dynasty") in {"南宋", "北宋"} and w.get("period") == "liao-jin-yuan"
        if dyn_already and not need_fix_period:
            continue
        new_dyn, new_per, basis, note, fix_author, fix_entity_period = compute_work_dynasty(w, entities, cbdb_cache)
        if not new_dyn and not need_fix_period:
            stats["A.work.skipped"] += 1
            skipped.append({"work_id": wid, "title": w.get("title"), "reason": note or "無處置"})
            continue
        changed = False
        if new_dyn and not dyn_already:
            w["dynasty"] = new_dyn
            w["dynasty_basis"] = basis
            changed = True
        else:
            new_dyn = new_dyn or w.get("dynasty")
        # 若需改 period（誤入 song）
        if new_per:
            old_per = w.get("period")
            if old_per != new_per:
                w["period"] = new_per
                w["period_basis"] = "cross_check"
                append_note(w, f"period {old_per}→{new_per}; {note or 'dynasty 已為'+new_dyn+' 據 cross_check 改 period'}")
                changed = True
            stats[f"A.work.period_changed_to.{new_per}"] += 1
        elif not dyn_already:
            append_note(w, f"dynasty null→{new_dyn}; {note}")
        w["updated_at"] = now_iso()
        if not dyn_already:
            stats[f"A.work.dynasty_filled.{new_dyn}"] += 1

        # 同步 author.dynasty（override 情形）
        if fix_author:
            eid, new_ad = fix_author
            for a in (w.get("authors") or []):
                if isinstance(a, dict) and a.get("entity_id") == eid:
                    old_ad = a.get("dynasty")
                    a["dynasty"] = new_ad
                    append_note(w, f"author({a.get('name')}) dynasty {old_ad}→{new_ad} (依 Entity 覆蓋)")
                    stats["A.work.author_dynasty_override"] += 1
                    changed = True

        # 順便修對應 Entity.period（如 CBDB 指明宋系）
        if fix_entity_period:
            eid, new_ep = fix_entity_period
            if eid in entities:
                ent = entities[eid]
                if not ent.get("period"):
                    ent["period"] = new_ep
                    ent["period_basis"] = "cross_check"
                    append_note(ent, f"period null→{new_ep}; 據 CBDB c_dy 證為宋系")
                    ent["updated_at"] = now_iso()
                    stats[f"A.entity.period_fixed_by_crosscheck.{new_ep}"] += 1
                    changed_entity_ids.add(eid)

        if changed:
            changed_work_ids.add(wid)

    # B. Entity 補 period（dynasty 屬遼金元規範但 period 空）
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn not in DYN_TO_PERIOD:
            continue
        if dyn not in LJY_CANON:
            continue  # 只處理遼金元規範（南宋北宋等非本輪）
        if e.get("period"):
            continue
        new_per = DYN_TO_PERIOD[dyn]
        e["period"] = new_per
        e["period_basis"] = "synonym"
        append_note(e, f"period null→{new_per}; 據 dynasty={dyn} 派生")
        e["updated_at"] = now_iso()
        stats[f"B.entity.period_filled.{dyn}"] += 1
        changed_entity_ids.add(eid)

    # C. 同步 index 分片
    if commit:
        for wid, w in works.items():
            write_json(work_paths[wid], w)
        for eid, e in entities.items():
            write_json(entity_paths[eid], e)

        idx_dir = ROOT / "index"
        for shard_fp in sorted((idx_dir / "works").glob("*.json")):
            shard = load_json(shard_fp)
            changed = False
            for wid, entry in shard.items():
                if not isinstance(entry, dict) or wid not in changed_work_ids or wid not in works:
                    continue
                w = works[wid]
                if entry.get("dynasty") != w.get("dynasty"):
                    entry["dynasty"] = w.get("dynasty")
                    changed = True
                    stats["C.index.work.dynasty_sync"] += 1
                if entry.get("period") != w.get("period"):
                    entry["period"] = w.get("period")
                    changed = True
                    stats["C.index.work.period_sync"] += 1
            if changed:
                write_json(shard_fp, shard)
                stats["C.index.work.shards_changed"] += 1

        for shard_fp in sorted((idx_dir / "entities").glob("*.json")):
            shard = load_json(shard_fp)
            changed = False
            for eid, entry in shard.items():
                if not isinstance(entry, dict) or eid not in changed_entity_ids or eid not in entities:
                    continue
                e = entities[eid]
                if entry.get("period") != e.get("period"):
                    entry["period"] = e.get("period")
                    changed = True
                    stats["C.index.entity.period_sync"] += 1
            if changed:
                write_json(shard_fp, shard)
                stats["C.index.entity.shards_changed"] += 1

    print("=== 遼金元未決 Round 1 統計 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:46s} {v:>5}")

    remaining = []
    for w in works.values():
        if w.get("period") == "liao-jin-yuan" and not w.get("dynasty"):
            remaining.append((w.get("id"), w.get("title")))
    print(f"\nperiod=liao-jin-yuan 但 dynasty 仍空的 Work: {len(remaining)} (應=328 no_author + 0 其他)")
    for wid, title in remaining[:8]:
        print(f"  {wid} {title}")

    print(f"\n棄權總數: {len(skipped)}")
    for s in skipped[:5]:
        print(f"  {s['work_id']} {s['title']} — {s['reason']}")


if __name__ == "__main__":
    main()
