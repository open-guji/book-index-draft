#!/usr/bin/env python3
"""
fix_three_kingdoms_jin.py — 三國·兩晉朝代拆分腳本

策略（五階段，依 SKILL.md「先讀後批」原則）：
  Phase 1: indexed_by 三國藝文志 → 安全定三國魏/吳（零判斷）
  Phase 2: work.top dynasty=None 填充（period 已定者）
  Phase 3: 歷史人物詞典 → 西晉/東晉/三國魏/三國吳
  Phase 4: Entity↔Author 雙向傳播
  Phase 5: 棄權清單輸出

用法:
  python3 scripts/fix_three_kingdoms_jin.py --dry-run   # 預覽
  python3 scripts/fix_three_kingdoms_jin.py --commit     # 執行
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ========== Phase 3: 歷史人物詞典 ==========
# 收錄三國兩晉知名人物，按朝代歸類。
# 依據：正史本傳、學界通用斷代。
# 每條記 (canonical_name, dynasty, note)
# alias 含字、號、別名等。

HISTORICAL_FIGURES = {
    # --- 西晉 (265-316) ---
    "杜預": ("西晉", "杜預(222-284)，字元凱，京兆杜陵人，西晉名將兼經學家"),
    "陳壽": ("西晉", "陳壽(233-297)，字承祚，撰《三國志》"),
    "張華": ("西晉", "張華(232-300)，字茂先，西晉政治家文學家"),
    "左思": ("西晉", "左思(約250-305)，字太沖，西晉文學家"),
    "陸機": ("西晉", "陸機(261-303)，字士衡，西晉文學家"),
    "陸雲": ("西晉", "陸雲(262-303)，字士龍，陸機之弟"),
    "潘岳": ("西晉", "潘岳(247-300)，字安仁，西晉文學家"),
    "潘安": ("西晉", "潘安即潘岳(247-300)"),
    "束皙": ("西晉", "束皙(261-300後)，字廣微，西晉學者"),
    "束晢": ("西晉", "束晢即束皙"),
    "荀勗": ("西晉", "荀勗(?-289)，字公曾，西晉目錄學家"),
    "荀勗": ("西晉", "荀勗(?-289)"),
    "裴秀": ("西晉", "裴秀(224-271)，字季彥，西晉地圖學家"),
    "皇甫謐": ("西晉", "皇甫謐(215-282)，字士安，西晉醫學家史學家"),
    "司馬彪": ("西晉", "司馬彪(約246-306)，字紹統，西晉史學家"),
    "摯虞": ("西晉", "摯虞(?-311)，字仲洽，西晉文學家"),
    "華嶠": ("西晉", "華嶠(?-293)，字叔駿，西晉史學家"),
    "陳壽": ("西晉", "陳壽(233-297)"),
    "傅玄": ("西晉", "傅玄(217-278)，字休奕，西晉政治家文學家"),
    "傅咸": ("西晉", "傅咸(239-294)，字長虞，傅玄之子"),
    "張載": ("西晉", "張載，字孟陽，西晉文學家（非北宋張載）"),
    "張協": ("西晉", "張協，字景陽，張載之弟"),
    "夏侯湛": ("西晉", "夏侯湛(243-291)，字孝若"),
    "和嶠": ("西晉", "和嶠(?-292)，字長輿"),
    "劉寶": ("西晉", "劉寶，西晉人物"),
    "王讚": ("西晉", "王讚，西晉文學家"),
    "棗據": ("西晉", "棗據，字彥考，西晉文學家"),
    "棗腆": ("西晉", "棗腆，棗據之弟"),
    "張敏": ("西晉", "張敏，西晉人物"),
    "摯虞": ("西晉", "摯虞(?-311)"),

    # --- 東晉 (317-420) ---
    "郭璞": ("東晉", "郭璞(276-324)，字景純，東晉文學家訓詁學家"),
    "葛洪": ("東晉", "葛洪(283-343)，字稚川，東晉道教學者"),
    "王羲之": ("東晉", "王羲之(303-361)，字逸少，東晉書法家"),
    "陶淵明": ("東晉", "陶淵明(365-427)，一名潛，東晉詩人"),
    "陶潛": ("東晉", "陶潛即陶淵明(365-427)"),
    "干寶": ("東晉", "干寶(?-336)，字令升，東晉史學家"),
    "常璩": ("東晉", "常璩(約291-361)，字道將，東晉史學家"),
    "謝安": ("東晉", "謝安(320-385)，字安石，東晉政治家"),
    "孫綽": ("東晉", "孫綽(314-371)，字興公，東晉文學家"),
    "慧遠": ("東晉", "慧遠(334-416)，東晉僧人"),
    "法顯": ("東晉", "法顯(337-422)，東晉僧人旅行家"),
    "慧皎": ("東晉", "慧皎(497-554)實為梁代，此處不收"),
    "王獻之": ("東晉", "王獻之(344-386)，字子敬，王羲之之子"),
    "謝玄": ("東晉", "謝玄(343-388)，字幼度，東晉名將"),
    "謝靈運": ("東晉", "謝靈運(385-433)，東晉南朝宋詩人"),
    "范曄": ("東晉", "范曄(398-445)實為南朝宋，此處不收"),
    "袁宏": ("東晉", "袁宏(328-376)，字彥伯，東晉史學家文學家"),
    "伏滔": ("東晉", "伏滔，東晉文學家"),
    "曹毗": ("東晉", "曹毗，字輔佐，東晉文學家"),
    "李充": ("東晉", "李充，字弘度，東晉目錄學家"),
    "徐廣": ("東晉", "徐廣(352-425)，字野民，東晉史學家"),
    "何晏": ("三國魏", "何晏(?-249)，字平叔，三國魏玄學家"),
    "王弼": ("三國魏", "王弼(226-249)，字輔嗣，三國魏玄學家"),
    "王弼輔嗣": ("三國魏", "王弼字輔嗣(226-249)"),
    "陳群": ("三國魏", "陳群(?-237)，字長文，三國魏政治家"),
    "張揖": ("三國魏", "張揖，字稚讓，三國魏訓詁學家"),
    "王粲": ("三國魏", "王粲(177-217)，字仲宣，建安七子之一"),
    "曹植": ("三國魏", "曹植(192-232)，字子建，三國魏詩人"),
    "曹丕": ("三國魏", "曹丕(187-226)，字子桓，三國魏文帝"),
    "應璩": ("三國魏", "應璩(190-252)，字休璉，三國魏文學家"),
    "高堂隆": ("三國魏", "高堂隆(?-約237)，字升平，三國魏天文學家"),
    "邯鄲綽": ("三國魏", "邯鄲綽，三國魏人物"),
    "鄞鄲綽": ("三國魏", "鄞鄲綽即邯鄲綽，三國魏人物"),
    "荀煇": ("三國魏", "荀煇，三國魏人物"),
    "糜信": ("三國魏", "糜信，三國魏經學家"),
    "鍾會": ("三國魏", "鍾會(225-264)，字士季，三國魏將領"),
    "劉劭": ("三國魏", "劉劭，字孔才，三國魏人物，撰《人物志》"),
    "王象": ("三國魏", "王象，三國魏學者"),
    "卞蘭": ("三國魏", "卞蘭，三國魏文學家"),
    "任嘏": ("三國魏", "任嘏，三國魏人物"),
    "蘇林": ("三國魏", "蘇林，字孝友，三國魏訓詁學家"),
    "孟康": ("三國魏", "孟康，字公休，三國魏人物"),
    "韋昭": ("三國吳", "韋昭(204-273)，字弘嗣，三國吳史學家"),
    "韋曜": ("三國吳", "韋曜即韋昭(204-273)，避司馬昭諱改"),
    "陸績": ("三國吳", "陸績(188-219)，字公紀，三國吳天文學家"),
    "陸績公紀": ("三國吳", "陸績字公紀(188-219)"),
    "徐整": ("三國吳", "徐整，三國吳學者"),
    "吳範": ("三國吳", "吳範，三國吳太史令"),
    "太史令吳範": ("三國吳", "吳範，三國吳太史令"),
    "楊泉": ("三國吳", "楊泉，三國吳思想家"),
    "張紘": ("三國吳", "張紘(153-212)，字子綱，三國吳謀臣"),
    "張溫": ("三國吳", "張溫，三國吳人物"),
    "閔鴻": ("三國吳", "閔鴻，三國吳文學家"),
    "支謙": ("三國吳", "支謙，三國吳譯經僧"),
    "陸璣": ("三國吳", "陸璣，三國吳學者，撰《毛詩草木鳥獸蟲魚疏》"),
    "程令陸璣": ("三國吳", "陸璣，三國吳學者"),
    "華核": ("三國吳", "華核，三國吳史學家"),
    "薛瑩": ("三國吳", "薛瑩，三國吳史學家"),
    "韋弘嗣": ("三國吳", "韋弘嗣即韋昭(204-273)"),
    "譙周": ("三國蜀", "譙周(201-270)，字允南，三國蜀學者"),
    "郤正": ("三國蜀", "郤正，三國蜀人物"),
    "諸葛亮": ("三國蜀", "諸葛亮(181-234)，字孔明，三國蜀丞相"),
    "諸葛武侯": ("三國蜀", "諸葛武侯即諸葛亮(181-234)"),
    "秦宓": ("三國蜀", "秦宓，三國蜀人物"),
    "陳壽": ("西晉", "陳壽(233-297)原三國蜀人，入晉後撰三國志"),
}

# 移除明顯錯誤的條目
_HISTORICAL_FIGURES = {}
for name, (dyn, note) in HISTORICAL_FIGURES.items():
    if "此處不收" not in note:
        _HISTORICAL_FIGURES[name] = (dyn, note)
HISTORICAL_FIGURES = _HISTORICAL_FIGURES


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def iter_work_files():
    return sorted(ROOT.glob("Work/?/?/?/*.json"))


def iter_entity_files():
    return sorted(ROOT.glob("Entity/?/?/?/*.json"))


def has_sanguo_zhiyuan(indexed_by):
    """indexed_by 中是否含三國藝文志"""
    for item in indexed_by:
        if isinstance(item, dict):
            src = str(item.get("source", ""))
            if "三國" in src and "藝文" in src:
                return True
    return False


def load_all_works():
    """載入全部 Work，返回 {work_id: data} 和 {work_id: file_path}"""
    works = {}
    paths = {}
    for fp in iter_work_files():
        d = json.loads(fp.read_text(encoding="utf-8"))
        wid = d.get("id", fp.stem)
        works[wid] = d
        paths[wid] = fp
    return works, paths


def load_all_entities():
    """載入全部 Entity"""
    entities = {}
    paths = {}
    for fp in iter_entity_files():
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        eid = d.get("id", fp.stem)
        entities[eid] = d
        paths[eid] = fp
    return entities, paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    commit = args.commit or not args.dry_run

    stats = Counter()
    changes = []  # (file_path, old_data, new_data)

    print("載入 Work / Entity ...")
    works, work_paths = load_all_works()
    entities, entity_paths = load_all_entities()
    print(f"  Work: {len(works)}, Entity: {len(entities)}")

    # ========== Phase 1: indexed_by 三國藝文志 ==========
    print("\n=== Phase 1: indexed_by 三國藝文志 ===")

    for wid, w in works.items():
        ib = w.get("indexed_by", [])
        if not has_sanguo_zhiyuan(ib):
            continue
        changed = False

        # work.author dynasty=魏 → 三國魏
        for a in w.get("authors", []) or []:
            if not isinstance(a, dict):
                continue
            if a.get("dynasty") == "魏":
                a["dynasty"] = "三國魏"
                a["dynasty_basis"] = "indexed_by:三國藝文志"
                changed = True
                stats["p1.author.魏→三國魏"] += 1
            elif a.get("dynasty") == "吳":
                a["dynasty"] = "三國吳"
                a["dynasty_basis"] = "indexed_by:三國藝文志"
                changed = True
                stats["p1.author.吳→三國吳"] += 1
            elif a.get("dynasty") == "三國":
                # 三國 → 看作者名判斷
                name = a.get("name", "")
                if name in HISTORICAL_FIGURES:
                    dyn, note = HISTORICAL_FIGURES[name]
                    a["dynasty"] = dyn
                    a["dynasty_basis"] = f"manual:historical_figure({note})"
                    changed = True
                    stats["p1.author.三國→specific"] += 1

        # work.top dynasty
        if w.get("dynasty") == "魏":
            w["dynasty"] = "三國魏"
            w["dynasty_basis"] = "indexed_by:三國藝文志"
            changed = True
            stats["p1.work.魏→三國魏"] += 1
        elif w.get("dynasty") == "吳":
            w["dynasty"] = "三國吳"
            w["dynasty_basis"] = "indexed_by:三國藝文志"
            changed = True
            stats["p1.work.吳→三國吳"] += 1
        elif w.get("dynasty") == "三國":
            # 看 authors 判斷
            author_dyns = set()
            for a in w.get("authors", []) or []:
                if isinstance(a, dict) and a.get("dynasty"):
                    author_dyns.add(a["dynasty"])
            if len(author_dyns) == 1:
                w["dynasty"] = author_dyns.pop()
                w["dynasty_basis"] = "author_propagation:唯一作者朝代"
                changed = True
                stats["p1.work.三國→specific"] += 1

        if changed:
            w["updated_at"] = now_iso()
            stats["p1.works_changed"] += 1

    # Phase 1 Entity: 通過 entity.works 找三國藝文志 indexed work
    # 建 work_id → has_sanguo 索引
    work_sanguo_map = {}
    for wid, w in works.items():
        if has_sanguo_zhiyuan(w.get("indexed_by", [])):
            work_sanguo_map[wid] = True

    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn not in ("魏", "吳", "三國"):
            continue
        entity_works = e.get("works", [])
        has_sg = False
        for ew in entity_works:
            if isinstance(ew, dict) and ew.get("work_id") in work_sanguo_map:
                has_sg = True
                break
        if not has_sg:
            continue

        if dyn == "魏":
            e["dynasty"] = "三國魏"
            e["dynasty_basis"] = "entity_works_indexed:三國藝文志"
            e["updated_at"] = now_iso()
            stats["p1.entity.魏→三國魏"] += 1
        elif dyn == "吳":
            e["dynasty"] = "三國吳"
            e["dynasty_basis"] = "entity_works_indexed:三國藝文志"
            e["updated_at"] = now_iso()
            stats["p1.entity.吳→三國吳"] += 1
        elif dyn == "三國":
            name = e.get("primary_name", "")
            if name in HISTORICAL_FIGURES:
                dyn2, note = HISTORICAL_FIGURES[name]
                e["dynasty"] = dyn2
                e["dynasty_basis"] = f"manual:historical_figure({note})"
                e["updated_at"] = now_iso()
                stats["p1.entity.三國→specific"] += 1

    # ========== Phase 2: work.top dynasty=None 填充 ==========
    print("\n=== Phase 2: work.top dynasty=None 填充 ===")

    for wid, w in works.items():
        if w.get("dynasty") is not None:
            continue
        per = w.get("period")
        if per not in ("three-kingdoms", "jin"):
            continue

        # 從 authors 推導
        author_dyns = []
        for a in w.get("authors", []) or []:
            if isinstance(a, dict) and a.get("dynasty"):
                author_dyns.append(a["dynasty"])

        if not author_dyns:
            # 無作者，用 period 粗設
            if per == "three-kingdoms":
                w["dynasty"] = "三國"
                w["dynasty_basis"] = "period_fallback:three-kingdoms→三國"
                w["updated_at"] = now_iso()
                stats["p2.work.→三國(no_author)"] += 1
            elif per == "jin":
                w["dynasty"] = "晉"
                w["dynasty_basis"] = "period_fallback:jin→晉"
                w["updated_at"] = now_iso()
                stats["p2.work.→晉(no_author)"] += 1
        else:
            unique_dyns = set(author_dyns)
            if len(unique_dyns) == 1:
                w["dynasty"] = author_dyns[0]
                w["dynasty_basis"] = "author_propagation:唯一作者朝代"
                w["updated_at"] = now_iso()
                stats["p2.work.→author_dynasty(unique)"] += 1
            else:
                # 多作者不同朝代，取多數
                from collections import Counter as C2
                dyn_ctr = C2(author_dyns)
                top_dyn, top_cnt = dyn_ctr.most_common(1)[0]
                if top_cnt > len(author_dyns) / 2:
                    w["dynasty"] = top_dyn
                    w["dynasty_basis"] = f"author_propagation:多數作者朝代({top_cnt}/{len(author_dyns)})"
                    w["updated_at"] = now_iso()
                    stats["p2.work.→author_dynasty(majority)"] += 1
                else:
                    # 無法決定，用 period 粗設
                    if per == "three-kingdoms":
                        w["dynasty"] = "三國"
                        w["dynasty_basis"] = "period_fallback:three-kingdoms→三國(authors_mixed)"
                    elif per == "jin":
                        w["dynasty"] = "晉"
                        w["dynasty_basis"] = "period_fallback:jin→晉(authors_mixed)"
                    w["updated_at"] = now_iso()
                    stats["p2.work.→period_fallback(mixed)"] += 1

    # ========== Phase 3: 歷史人物詞典 ==========
    print("\n=== Phase 3: 歷史人物詞典 ===")

    # Entity
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn not in ("晉", "魏", "吳", "三國"):
            continue
        name = e.get("primary_name", "")
        if name in HISTORICAL_FIGURES:
            new_dyn, note = HISTORICAL_FIGURES[name]
            if new_dyn != dyn:
                e["dynasty"] = new_dyn
                e["dynasty_basis"] = f"manual:historical_figure({note})"
                e["updated_at"] = now_iso()
                stats[f"p3.entity.{dyn}→{new_dyn}"] += 1

    # Work.author
    for wid, w in works.items():
        for a in w.get("authors", []) or []:
            if not isinstance(a, dict):
                continue
            dyn = a.get("dynasty")
            if dyn not in ("晉", "魏", "吳", "三國"):
                continue
            name = a.get("name", "")
            if name in HISTORICAL_FIGURES:
                new_dyn, note = HISTORICAL_FIGURES[name]
                if new_dyn != dyn:
                    a["dynasty"] = new_dyn
                    a["dynasty_basis"] = f"manual:historical_figure({note})"
                    if "updated_at" not in w or not w.get("_p3_changed"):
                        w["_p3_changed"] = True
                    stats[f"p3.author.{dyn}→{new_dyn}"] += 1
        if w.pop("_p3_changed", False):
            w["updated_at"] = now_iso()

    # ========== Phase 4: Entity↔Author 雙向傳播 ==========
    print("\n=== Phase 4: Entity↔Author 雙向傳播 ===")

    # 4a: Entity 已分類 → 傳播到其 Work 的 authors
    # 建 entity_id → dynasty 索引（只含已細分的）
    entity_dynasty_map = {}
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn in ("三國魏", "三國蜀", "三國吳", "西晉", "東晉"):
            entity_dynasty_map[eid] = dyn

    for wid, w in works.items():
        for a in w.get("authors", []) or []:
            if not isinstance(a, dict):
                continue
            dyn = a.get("dynasty")
            if dyn not in ("晉", "魏", "吳", "三國"):
                continue
            eid = a.get("entity_id")
            if eid and eid in entity_dynasty_map:
                new_dyn = entity_dynasty_map[eid]
                if new_dyn != dyn:
                    a["dynasty"] = new_dyn
                    a["dynasty_basis"] = f"entity_propagation:entity_id={eid}"
                    w["updated_at"] = now_iso()
                    stats[f"p4a.author.{dyn}→{new_dyn}"] += 1

    # 4b: Work.author 已分類 → 傳播到同名 Entity
    # 建 (name, dynasty) → set 索引，從 work.authors 中取已細分的
    author_name_dynasty = defaultdict(set)
    for wid, w in works.items():
        for a in w.get("authors", []) or []:
            if not isinstance(a, dict):
                continue
            dyn = a.get("dynasty")
            if dyn in ("三國魏", "三國蜀", "三國吳", "西晉", "東晉"):
                author_name_dynasty[a.get("name", "")].add(dyn)

    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn not in ("晉", "魏", "吳", "三國"):
            continue
        name = e.get("primary_name", "")
        if name in author_name_dynasty:
            classified = author_name_dynasty[name]
            if len(classified) == 1:
                new_dyn = classified.pop()
                if new_dyn != dyn:
                    e["dynasty"] = new_dyn
                    e["dynasty_basis"] = f"author_propagation:同名作者唯一朝代"
                    e["updated_at"] = now_iso()
                    stats[f"p4b.entity.{dyn}→{new_dyn}"] += 1

    # ========== Phase 5: 棄權清單 ==========
    print("\n=== Phase 5: 棄權清單 ===")

    unresolved_entities = []
    unresolved_authors = []

    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn in ("晉", "魏", "吳", "三國"):
            unresolved_entities.append({
                "id": eid,
                "name": e.get("primary_name", ""),
                "dynasty": dyn,
                "period": e.get("period"),
            })

    for wid, w in works.items():
        for a in w.get("authors", []) or []:
            if not isinstance(a, dict):
                continue
            dyn = a.get("dynasty")
            if dyn in ("晉", "魏", "吳", "三國"):
                unresolved_authors.append({
                    "work_id": wid,
                    "work_title": w.get("title", "")[:30],
                    "author_name": a.get("name", ""),
                    "dynasty": dyn,
                })

    # ========== 寫入 ==========
    if commit:
        print("\n寫入 Work ...")
        written = 0
        for wid, w in works.items():
            fp = work_paths[wid]
            fp.write_text(json.dumps(w, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            written += 1
        print(f"  {written} Work files")

        print("寫入 Entity ...")
        written = 0
        for eid, e in entities.items():
            fp = entity_paths[eid]
            fp.write_text(json.dumps(e, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            written += 1
        print(f"  {written} Entity files")

    # ========== 報告 ==========
    print("\n=== 統計 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:50s} {v:>6}")

    print(f"\n=== 棄權清單 ===")
    print(f"  未解 Entity: {len(unresolved_entities)}")
    from collections import Counter as C2
    ent_ctr = C2(e["dynasty"] for e in unresolved_entities)
    for k, v in ent_ctr.most_common():
        print(f"    {k}: {v}")
    print(f"  未解 Work.author: {len(unresolved_authors)}")
    auth_ctr = C2(a["dynasty"] for a in unresolved_authors)
    for k, v in auth_ctr.most_common():
        print(f"    {k}: {v}")

    # 輸出棄權清單
    issues_dir = ROOT / ".claude" / "known-issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    issues_file = issues_dir / "三國兩晉未決.json"
    with open(issues_file, "w", encoding="utf-8") as f:
        json.dump({
            "unresolved_entities": unresolved_entities,
            "unresolved_authors": unresolved_authors,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  棄權清單已寫入: {issues_file}")


if __name__ == "__main__":
    main()
