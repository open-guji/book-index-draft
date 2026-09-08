#!/usr/bin/env python3
"""
fix_nanbeichao_round1.py — 南北朝（含宋/梁/齊/周/晉/魏/蜀/吳歧義值）朝代拆分 第一輪

處理 entity 和 author 層的歧義 dynasty 值（Work 頂層已基本規範）。

Batch A: CBDB c_dy 判定（entity 層，1381 個有 cbdb_id）
  - c_dy=28 → 南朝宋；c_dy=15 + birth/death_name=北宋/南宋 → 北宋/南宋
  - c_dy=23 → 西晉；c_dy=27 → 東晉；c_dy=44 → 南朝梁；c_dy=32 → 南朝齊
  - c_dy=24 → 南朝陳；c_dy=30 → 北魏；c_dy=35 → 北齊；c_dy=31 → 北周
  - c_dy=1 → 西周；c_dy=34 → 後梁；c_dy=49 → 後周
  - c_dy=15 + 有年份 → 按年份判北宋/南宋

Batch B: 歷史人物詞典（無 cbdb_id 的 entity）
  - 南朝宋/梁/齊/陳、北魏/齊/周、先秦、北宋/南宋知名人物

Batch C: 隋志上限信號
  - author.dynasty=宋 + Work 見於隋志 → 南朝宋（排除先秦人物）

Batch D: Work.period 信號
  - author.dynasty=X + Work.period=nanbeichao → 南朝X
  - author.dynasty=周 + Work.period=pre-qin → 先秦周

Batch E: Entity→Author 傳播
Batch F: Author→Entity 反向傳播
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / ".claude" / "known-issues" / "cbdb_dy_cache.json"

# CBDB c_dy 碼 → 規範朝代名
CDY_TO_CANON = {
    "1": "西周", "2": "東周", "3": "春秋", "4": "南北朝",
    "5": "隋", "6": "唐", "7": "五代", "13": "唐", "15": "宋",
    "16": "遼", "17": "金", "18": "元", "19": "明", "20": "清",
    "21": "中華民國", "22": "中華人民共和國", "23": "西晉", "24": "南朝陳",
    "25": "東漢", "26": "三國魏", "27": "東晉", "28": "南朝宋",
    "29": "西漢", "30": "北魏", "31": "北周", "32": "南朝齊",
    "34": "後梁", "35": "北齊", "37": "西梁", "40": "西魏",
    "41": "東魏", "42": "三國吳", "44": "南朝梁", "46": "新",
    "47": "後唐", "48": "後晉", "49": "後周", "52": "後漢",
    "53": "三國蜀", "61": "秦", "68": "十六國", "77": "武周",
    "79": "元", "80": "南明", "82": "晉", "83": "漢",
}

# 歧義 dynasty 值（需要拆分的）
AMBIGUOUS = {"宋", "晉", "梁", "周", "齊", "魏", "吳", "蜀", "陳", "三國", "南北朝", "南朝", "北朝"}

# 不動的 dynasty（已規範或非歧義）
SKIP_DYNASTIES = {
    None, "南朝宋", "南朝梁", "南朝齊", "南朝陳", "北魏", "北齊", "北周",
    "西晉", "東晉", "北宋", "南宋", "後梁", "後周", "西周", "東周",
    "春秋", "戰國", "春秋齊", "春秋吳", "戰國齊", "戰國楚", "戰國趙",
    "三國魏", "三國蜀", "三國吳", "前蜀", "後蜀", "楊吳", "南唐",
    "秦", "西漢", "東漢", "新", "隋", "唐", "武周", "五代",
    "後唐", "後晉", "後漢", "遼", "西夏", "金", "元", "明", "清",
    "中華民國", "中華人民共和國", "先秦", "上古", "上古傳說", "夏", "商",
    "前涼", "前秦", "後秦", "西燕", "北涼", "偽齊", "蒙古",
    "日本", "江戶時代", "朝鮮", "新羅", "韓國", "英國", "美國", "比利時",
    "秦漢", "隋唐", "南北朝", "南朝", "北朝", "三國", "五代", "晉",
    "宋末元初", "明末清初", "元末明初",
}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def iter_work_files():
    return sorted(ROOT.glob("Work/?/?/?/*.json"))


def iter_entity_files():
    return sorted(ROOT.glob("Entity/?/?/?/*.json"))


# ========== Batch B: 歷史人物詞典 ==========
# 無 cbdb_id 的 entity，用歷史人物詞典直接判定
HISTORICAL_FIGURES = {
    # === 南朝宋 (420-479) ===
    "劉裕": "南朝宋",  # 宋武帝
    "劉義隆": "南朝宋",  # 宋文帝
    "劉義慶": "南朝宋",  # 世說新語
    "謝靈運": "南朝宋",
    "顏延之": "南朝宋",
    "鮑照": "南朝宋",
    "鮑明遠": "南朝宋",  # 鮑照字明遠
    "裴松之": "南朝宋",  # 三國志注
    "范曄": "南朝宋",  # 後漢書
    "徐爰": "南朝宋",  # 宋書參與者
    "何承天": "南朝宋",
    "劉敬叔": "南朝宋",  # 異苑
    "荀柔之": "南朝宋",  # 周易繫辭注
    "劉謙之": "南朝宋",  # 晉紀
    "釋法顯": "南朝宋",  # 佛國記
    "法顯": "南朝宋",
    "范歆": "南朝宋",  # 周易義
    "姜道盛": "南朝宋",  # 尚書集釋
    "裴景仁": "南朝宋",  # 秦記
    "盛弘之": "南朝宋",  # 荊州記
    "沈懷逺": "南朝宋",  # 南越志
    "沈懷遠": "南朝宋",
    "江邃": "南朝宋",  # 文釋
    "崔凱": "南朝宋",  # 喪服難問
    "蔡超宗": "南朝宋",  # 集注喪服經傳
    "李叔之": "南朝宋",  # 莊子義疏
    "任豫": "南朝宋",  # 禮論條牒（宋任豫）
    "謝莊": "南朝宋",
    "劉鑠": "南朝宋",
    "宗炳": "南朝宋",
    "曇無讖": "南朝宋",

    # === 南朝梁 (502-557) ===
    "蕭衍": "南朝梁",  # 梁武帝
    "蕭統": "南朝梁",  # 昭明太子
    "蕭綱": "南朝梁",  # 梁簡文帝
    "蕭繹": "南朝梁",  # 梁元帝
    "沈約": "南朝梁",
    "江淹": "南朝梁",
    "劉勰": "南朝梁",  # 文心雕龍
    "鍾嶸": "南朝梁",  # 詩品
    "鍾榮": "南朝梁",  # 鍾嶸異體
    "陶弘景": "南朝梁",
    "庾肩吾": "南朝梁",
    "徐陵": "南朝梁",
    "庾信": "南朝梁",  # 跨梁北周，按主要活動歸梁
    "劉孝標": "南朝梁",  # 劉峻
    "劉峻": "南朝梁",
    "王僧孺": "南朝梁",
    "陸倕": "南朝梁",
    "任昉": "南朝梁",
    "謝朓": "南朝梁",  # 主要活動在齊梁之際
    "吳均": "南朝梁",
    "周興嗣": "南朝梁",  # 千字文
    "慧皎": "南朝梁",  # 高僧傳
    "寶唱": "南朝梁",
    "阮孝緒": "南朝梁",  # 七錄
    "顧野王": "南朝梁",  # 玉篇（跨梁陳）

    # === 南朝齊 (479-502) ===
    "蕭道成": "南朝齊",  # 齊高帝
    "明僧紹": "南朝齊",
    "虞羲": "南朝齊",
    "王巾": "南朝齊",
    "王融": "南朝齊",
    "王儉": "南朝齊",
    "劉瓛": "南朝齊",
    "劉琳": "南朝齊",  # 周易乾坤義

    # === 南朝陳 (557-589) ===
    "陳霸先": "南朝陳",
    "徐陵": "南朝陳",  # 跨梁陳

    # === 北魏 (386-534) ===
    "拓跋宏": "北魏",  # 孝文帝
    "元宏": "北魏",
    "崔浩": "北魏",
    "崔鴻": "北魏",  # 十六國春秋
    "信都芳": "北魏",
    "李謐": "北魏",
    "常景": "北魏",
    "溫子昇": "北魏",
    "酈道元": "北魏",  # 水經注
    "賈思同": "北魏",
    "賈思勰": "北魏",  # 齊民要術

    # === 北齊 (550-577) ===
    "高歡": "北齊",
    "高洋": "北齊",
    "魏收": "北齊",  # 魏書
    "顏之推": "北齊",  # 顏氏家訓

    # === 北周 (557-581) ===
    "宇文泰": "北周",
    "宇文邕": "北周",
    "庾信": "北周",  # 跨梁北周

    # === 先秦周 ===
    "老子": "先秦",
    "莊周": "先秦",
    "孔子": "先秦",
    "墨翟": "先秦",
    "墨子": "先秦",
    "孫武": "先秦",
    "吳起": "先秦",
    "列御寇": "先秦",
    "尹喜": "先秦",
    "卜商": "先秦",
    "曾參": "先秦",
    "申不害": "先秦",
    "晏嬰": "春秋齊",
    "陳仲子": "戰國齊",
    "范蠡": "春秋",
    "文種": "春秋",
    "黃歇": "戰國",
    "張儀": "戰國",
    "樂毅": "戰國",
    "惠施": "戰國",
    "公孫鞅": "戰國",
    "商鞅": "戰國",
    "信陵君魏無忌": "戰國",
    "萇弘": "春秋",
    "景差": "戰國",
    "荊軻": "戰國",
    "尹文": "戰國",
    "尹佚": "先秦",
    "辛甲": "先秦",
    "鐸椒": "春秋",
    "成公生": "戰國",
    "董無心": "戰國",
    "公孫尼子": "戰國",
    "公孫固": "戰國",
    "公子牟": "戰國",
    "黃疵": "戰國",
    "胡非子": "戰國",
    "捷子": "戰國",
    "羋嬰": "戰國",
    "宓不齊": "春秋",
    "漆雕啟": "春秋",
    "世碩": "戰國",
    "隨巢子": "戰國",
    "田俅": "戰國",
    "田駢": "戰國",
    "王孫子": "戰國",
    "徐子": "戰國",
    "蜎淵": "戰國",
    "鄭長者": "戰國",
    "周史大弢": "戰國",
    "鮑子": "春秋",
    "別成子": "戰國",
    "兒良": "戰國",
    "公乘不仁": "戰國",
    "景子": "戰國",
    "蒲苴子": "戰國",
    "唐勒": "戰國",
    "陰通成": "戰國",
    "長盧子": "戰國",
    "文子": "戰國",
    "孫休": "戰國",
    "周生": "先秦",

    # === 三國魏（殘留）===
    "劉卲": "三國魏",  # 人物志
    "劉邵": "三國魏",
    "張楫": "三國魏",  # 廣雅
    "張揖": "三國魏",

    # === 三國蜀 ===
    "李譔": "三國蜀",  # 古文易注解

    # === 前蜀/後蜀 ===
    "毋昭裔": "後蜀",
    "毛文錫": "前蜀",
    "韋縠": "後蜀",  # 才調集
    "孟㫤": "後蜀",  # 孟昶
    "孟昶": "後蜀",
    "馮涓": "前蜀",
    "蒲䖍觀": "前蜀",  # 易軌
    "稅安禮": "後蜀",  # 地理指掌圖
    "馮繼先": "後蜀",  # 春秋名號歸一圖

    # === 北宋知名人物 ===
    "歐陽修": "北宋",
    "蘇軾": "北宋",
    "蘇轍": "北宋",
    "王安石": "北宋",
    "司馬光": "北宋",
    "曾鞏": "北宋",
    "黃庭堅": "北宋",
    "米芾": "北宋",
    "周敦頤": "北宋",
    "張載": "北宋",
    "程顥": "北宋",
    "程頤": "北宋",
    "邵雍": "北宋",
    "沈括": "北宋",
    "晏殊": "北宋",
    "柳永": "北宋",
    "范仲淹": "北宋",
    "韓琦": "北宋",
    "富弼": "北宋",
    "文彥博": "北宋",
    "包拯": "北宋",
    "蘇洵": "北宋",
    "秦觀": "北宋",
    "晁補之": "北宋",
    "張耒": "北宋",
    "陳師道": "北宋",
    "李清照": "北宋",  # 跨南北宋，按主要活動歸北宋
    "岳飛": "南宋",  # 主要活動在南宋
    "陸游": "南宋",
    "辛棄疾": "南宋",
    "朱熹": "南宋",
    "張栻": "南宋",
    "呂祖謙": "南宋",
    "陸九淵": "南宋",
    "葉適": "南宋",
    "陳亮": "南宋",
    "范成大": "南宋",
    "楊萬里": "南宋",
    "文天祥": "南宋",
    "真德秀": "南宋",
    "魏了翁": "南宋",
    "洪邁": "南宋",
    "洪适": "南宋",
    "洪遵": "南宋",
    "鄭樵": "南宋",
    "袁樞": "南宋",
    "李燾": "南宋",
    "李心傳": "南宋",
    "王應麟": "南宋",
    "馬端臨": "南宋",  # 文獻通考（宋末元初，歸南宋）

    # === 後梁（五代）===
    # 後梁人物較少在古籍目錄中，暫不列

    # === 後周（五代）===
    "王朴": "後周",
    "竇儼": "後周",

    # === 楊吳 ===
    "沈顔": "楊吳",  # 沈顏
    "沈顏": "楊吳",
}

# 先秦人物 dynasty=周 的特殊處理：先秦周 → 先秦/西周/東周/春秋/戰國
# 但很多 dynasty=周 的先秦人物，其實應該是「春秋」或「戰國」
# 用 HISTORICAL_FIGURES 詞典判定


def load_cbdb_cache():
    if not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def has_sui_zhi(indexed_by):
    for item in indexed_by or []:
        if isinstance(item, dict) and item.get("source") == "隋書經籍志":
            return True
    return False


def has_han_zhi(indexed_by):
    """見於漢書藝文志 → 必是先秦/秦漢人"""
    for item in indexed_by or []:
        if isinstance(item, dict) and item.get("source") == "漢書藝文志":
            return True
    return False


def only_song_shi_sources(indexed_by):
    """只被宋史藝文志/宋史藝文志補著錄 → 趙宋"""
    sources = set()
    for item in indexed_by or []:
        if isinstance(item, dict):
            sources.add(item.get("source", ""))
    if not sources:
        return False
    song_only = {"宋史藝文志", "宋史藝文志補"}
    return sources <= song_only


def song_dynasty_from_cbdb(cbdb_entry: dict, entity_birth_year, entity_death_year) -> tuple[str | None, str]:
    """從 CBDB 緩存條目判定宋 → 北宋/南宋/南朝宋"""
    cdy = cbdb_entry.get("dynasty_id", "")
    birth_name = cbdb_entry.get("dynasty_birth_name", "")
    death_name = cbdb_entry.get("dynasty_death_name", "")

    # c_dy=28 → 南朝宋
    if cdy == "28":
        return "南朝宋", f"cbdb:c_dy=28→南朝宋"

    # c_dy=15 → 趙宋，需分北/南
    if cdy == "15":
        # 先看 CBDB 的 dynasty_birth/death_name
        if "北宋" in (birth_name, death_name) and "南宋" not in (birth_name, death_name):
            return "北宋", f"cbdb:birth/death_name=北宋"
        if "南宋" in (birth_name, death_name) and "北宋" not in (birth_name, death_name):
            return "南宋", f"cbdb:birth/death_name=南宋"
        # 跨南北宋（生北宋卒南宋）→ 歸南宋（按卒年）
        if "南宋" in death_name:
            return "南宋", f"cbdb:death_name=南宋(跨)"
        if "北宋" in death_name:
            return "北宋", f"cbdb:death_name=北宋"
        # CBDB 無北/南分，用年份
        # 先用 CBDB 的 year_birth/year_death
        cbdb_yb = cbdb_entry.get("year_birth", "")
        cbdb_yd = cbdb_entry.get("year_death", "")
        try:
            cbdb_yb = int(cbdb_yb) if cbdb_yb and int(cbdb_yb) > 0 else None
        except (ValueError, TypeError):
            cbdb_yb = None
        try:
            cbdb_yd = int(cbdb_yd) if cbdb_yd and int(cbdb_yd) > 0 else None
        except (ValueError, TypeError):
            cbdb_yd = None
        # 再用 entity 自帶生卒年
        yb = cbdb_yb or entity_birth_year
        yd = cbdb_yd or entity_death_year
        years = [y for y in [yb, yd] if y is not None]
        if years:
            if min(years) >= 960 and min(years) < 1127:
                return "北宋", f"cbdb:year={min(years)}→北宋"
            if min(years) >= 1127 and min(years) < 1279:
                return "南宋", f"cbdb:year={min(years)}→南宋"
            if min(years) >= 1279:
                return None, f"cbdb:c_dy=15 but year={min(years)}>1279, 疑誤標"
        # c_dy=15 但無年份 → 標北宋（CBDB 判定為趙宋，但分不出北/南）
        # 留 null 更安全，但考慮到北宋人物遠多於南宋，且 CBDB 明確標為 c_dy=15
        # 暫留 null，由其他信號補充
        return None, f"cbdb:c_dy=15 but no year/北南宋區分"

    # c_dy=其他 → 非 宋，誤標
    canon = CDY_TO_CANON.get(str(cdy))
    if canon and canon != "宋":
        return canon, f"cbdb:c_dy={cdy}→{canon}(誤標宋)"

    return None, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    commit = args.commit or not args.dry_run

    stats = Counter()

    print("載入 Work / Entity / CBDB cache ...")
    works = {}
    work_paths = {}
    for fp in iter_work_files():
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        wid = d.get("id", fp.stem)
        works[wid] = d
        work_paths[wid] = fp

    entities = {}
    entity_paths = {}
    for fp in iter_entity_files():
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        eid = d.get("id", fp.stem)
        entities[eid] = d
        entity_paths[eid] = fp

    cbdb_cache = load_cbdb_cache()
    print(f"  Work: {len(works)}, Entity: {len(entities)}, CBDB cache: {len(cbdb_cache)}")

    # 建立 eid -> works 映射
    eid_to_works = defaultdict(list)
    for wid, w in works.items():
        for a in w.get("authors", []) or []:
            if isinstance(a, dict):
                eid = a.get("entity_id")
                if eid:
                    eid_to_works[eid].append(w)

    # ========== Batch A: CBDB c_dy 判定（entity 層）==========
    print("\n=== Batch A: CBDB c_dy 判定 ===")
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn not in AMBIGUOUS:
            continue
        ext = e.get("external_ids", {})
        cbdb_id = ext.get("cbdb_id") if isinstance(ext, dict) else None
        if not cbdb_id:
            continue
        entry = cbdb_cache.get(str(cbdb_id))
        if not entry or "error" in entry:
            continue

        cdy = entry.get("dynasty_id", "")
        by = e.get("birth_year")
        dy = e.get("death_year")

        # 宋的特殊處理
        if dyn == "宋":
            new_dyn, basis = song_dynasty_from_cbdb(entry, by, dy)
            if new_dyn and new_dyn != dyn:
                e["dynasty"] = new_dyn
                e["dynasty_basis"] = basis
                e["updated_at"] = now_iso()
                stats[f"A.entity.宋→{new_dyn}"] += 1
            continue

        # 其他歧義值：直接用 c_dy 映射
        canon = CDY_TO_CANON.get(str(cdy))
        if canon and canon != dyn:
            # 特殊處理：dynasty=南北朝 不輕易改（太粗）
            if dyn == "南北朝" and canon in ("南朝宋", "南朝梁", "南朝齊", "南朝陳", "北魏", "北齊", "北周"):
                e["dynasty"] = canon
                e["dynasty_basis"] = f"cbdb:c_dy={cdy}→{canon}"
                e["updated_at"] = now_iso()
                stats[f"A.entity.南北朝→{canon}"] += 1
            elif dyn != "南北朝":
                e["dynasty"] = canon
                e["dynasty_basis"] = f"cbdb:c_dy={cdy}→{canon}"
                e["updated_at"] = now_iso()
                stats[f"A.entity.{dyn}→{canon}"] += 1

    # ========== Batch B: 歷史人物詞典（無 cbdb_id 的 entity）==========
    print("\n=== Batch B: 歷史人物詞典 ===")
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn not in AMBIGUOUS:
            continue
        name = e.get("primary_name", "")
        if name in HISTORICAL_FIGURES:
            new_dyn = HISTORICAL_FIGURES[name]
            if new_dyn != dyn:
                e["dynasty"] = new_dyn
                e["dynasty_basis"] = f"historical_dict:{name}→{new_dyn}"
                e["updated_at"] = now_iso()
                stats[f"B.entity.{dyn}→{new_dyn}"] += 1

    # ========== Batch C: 隋志上限信號（entity 層）==========
    # entity.dynasty=宋 + 對應 Work 見於隋志 → 南朝宋
    # 但排除見於漢志的（那是先秦人物，dynasty=宋 是誤標）
    print("\n=== Batch C: 隋志上限信號 ===")
    for eid, e in entities.items():
        if e.get("dynasty") != "宋":
            continue
        ws = eid_to_works.get(eid, [])
        if not ws:
            continue
        has_suizhi = False
        has_hanzhi = False
        for w in ws:
            if has_sui_zhi(w.get("indexed_by", [])):
                has_suizhi = True
            if has_han_zhi(w.get("indexed_by", [])):
                has_hanzhi = True
        if has_hanzhi:
            # 見於漢志 → 先秦/秦漢人，dynasty=宋 是誤標
            e["dynasty"] = "先秦"
            e["dynasty_basis"] = "catalog_bound:漢書藝文志→先秦"
            e["updated_at"] = now_iso()
            stats["C.entity.宋→先秦(漢志)"] += 1
        elif has_suizhi:
            e["dynasty"] = "南朝宋"
            e["dynasty_basis"] = "catalog_bound:隋書經籍志→南朝宋"
            e["updated_at"] = now_iso()
            stats["C.entity.宋→南朝宋(隋志)"] += 1

    # ========== Batch D: Work.period 信號（entity 層）==========
    print("\n=== Batch D: Work.period 信號 ===")
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn not in AMBIGUOUS:
            continue
        ws = eid_to_works.get(eid, [])
        if not ws:
            continue
        # 取這些 work 的 period
        periods = set()
        for w in ws:
            p = w.get("period")
            if p:
                periods.add(p)
        if len(periods) != 1:
            continue
        per = periods.pop()

        # dynasty=宋 + period=nanbeichao → 南朝宋
        if dyn == "宋" and per == "nanbeichao":
            e["dynasty"] = "南朝宋"
            e["dynasty_basis"] = "work_period:nanbeichao→南朝宋"
            e["updated_at"] = now_iso()
            stats["D.entity.宋→南朝宋"] += 1
        # dynasty=梁 + period=nanbeichao → 南朝梁
        elif dyn == "梁" and per == "nanbeichao":
            e["dynasty"] = "南朝梁"
            e["dynasty_basis"] = "work_period:nanbeichao→南朝梁"
            e["updated_at"] = now_iso()
            stats["D.entity.梁→南朝梁"] += 1
        # dynasty=齊 + period=nanbeichao → 南朝齊（默認，北齊人物極少在此庫）
        elif dyn == "齊" and per == "nanbeichao":
            e["dynasty"] = "南朝齊"
            e["dynasty_basis"] = "work_period:nanbeichao→南朝齊(默認)"
            e["updated_at"] = now_iso()
            stats["D.entity.齊→南朝齊"] += 1
        # dynasty=周 + period=pre-qin → 先秦
        elif dyn == "周" and per == "pre-qin":
            e["dynasty"] = "先秦"
            e["dynasty_basis"] = "work_period:pre-qin→先秦"
            e["updated_at"] = now_iso()
            stats["D.entity.周→先秦"] += 1
        # dynasty=晉 + period=jin → 不改（period 已對，需分西/東晉，留後續）
        # dynasty=魏 + period=nanbeichao → 北魏
        elif dyn == "魏" and per == "nanbeichao":
            e["dynasty"] = "北魏"
            e["dynasty_basis"] = "work_period:nanbeichao→北魏"
            e["updated_at"] = now_iso()
            stats["D.entity.魏→北魏"] += 1
        # dynasty=魏 + period=three-kingdoms → 三國魏
        elif dyn == "魏" and per == "three-kingdoms":
            e["dynasty"] = "三國魏"
            e["dynasty_basis"] = "work_period:three-kingdoms→三國魏"
            e["updated_at"] = now_iso()
            stats["D.entity.魏→三國魏"] += 1

    # ========== Batch E: Entity→Author 傳播 ==========
    print("\n=== Batch E: Entity→Author 傳播 ===")
    entity_dyn_map = {}
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn and dyn not in AMBIGUOUS and dyn not in SKIP_DYNASTIES:
            # 新規範值
            entity_dyn_map[eid] = dyn
        elif dyn in ("南朝宋", "南朝梁", "南朝齊", "南朝陳", "北魏", "北齊", "北周",
                      "西晉", "東晉", "北宋", "南宋", "後梁", "後周", "西周", "東周",
                      "先秦", "春秋", "戰國", "春秋齊", "春秋吳", "戰國齊", "戰國楚",
                      "三國魏", "三國蜀", "三國吳", "前蜀", "後蜀", "楊吳"):
            entity_dyn_map[eid] = dyn

    for wid, w in works.items():
        changed = False
        for a in w.get("authors", []) or []:
            if not isinstance(a, dict):
                continue
            adyn = a.get("dynasty")
            if adyn not in AMBIGUOUS:
                continue
            eid = a.get("entity_id")
            if eid and eid in entity_dyn_map:
                new_dyn = entity_dyn_map[eid]
                if new_dyn != adyn:
                    a["dynasty"] = new_dyn
                    a["dynasty_basis"] = f"entity_propagation:{eid}"
                    stats[f"E.author.{adyn}→{new_dyn}"] += 1
                    changed = True
        if changed:
            w["updated_at"] = now_iso()

    # ========== Batch F: Author→Entity 反向傳播 ==========
    print("\n=== Batch F: Author→Entity 反向傳播 ===")
    author_name_dyn = defaultdict(set)
    for wid, w in works.items():
        for a in w.get("authors", []) or []:
            if isinstance(a, dict):
                dyn = a.get("dynasty")
                if dyn and dyn not in AMBIGUOUS:
                    author_name_dyn[a.get("name", "")].add(dyn)

    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn not in AMBIGUOUS:
            continue
        name = e.get("primary_name", "")
        if name in author_name_dyn:
            c = author_name_dyn[name]
            if len(c) == 1:
                new_dyn = c.pop()
                if new_dyn != dyn:
                    e["dynasty"] = new_dyn
                    e["dynasty_basis"] = "author_propagation:round1"
                    e["updated_at"] = now_iso()
                    stats[f"F.entity.{dyn}→{new_dyn}"] += 1

    # ========== 寫入 ==========
    if commit:
        print("\n寫入 Entity ...")
        for eid, e in entities.items():
            fp = entity_paths[eid]
            fp.write_text(json.dumps(e, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("寫入 Work ...")
        for wid, w in works.items():
            fp = work_paths[wid]
            fp.write_text(json.dumps(w, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        # ========== 同步 index 分片 ==========
        # Round 1 改了 entity.dynasty（頂層）與 work.authors[].dynasty。
        # index/entities 存 entity 頂層 dynasty，需同步；
        # index/works 存 work 頂層 dynasty（Round 1 未改），但一併同步以保持一致。
        # 同步原則：以源文件為準，刷新 index 條目的 dynasty 與 period。
        print("\n同步 index/entities 分片 ...")
        idx_dir = ROOT / "index"
        CANON_TO_PER = {
            "南朝宋": "nanbeichao", "南朝齊": "nanbeichao", "南朝梁": "nanbeichao",
            "南朝陳": "nanbeichao", "北魏": "nanbeichao", "北齊": "nanbeichao",
            "北周": "nanbeichao", "西晉": "jin", "東晉": "jin",
            "北宋": "song", "南宋": "song",
            "後梁": "five-dynasties", "後周": "five-dynasties",
            "前蜀": "five-dynasties", "後蜀": "five-dynasties", "楊吳": "five-dynasties",
            "西周": "pre-qin", "東周": "pre-qin", "春秋": "pre-qin",
            "戰國": "pre-qin", "先秦": "pre-qin",
            "春秋齊": "pre-qin", "春秋吳": "pre-qin", "春秋魯": "pre-qin",
            "春秋晉": "pre-qin", "戰國齊": "pre-qin", "戰國楚": "pre-qin", "戰國趙": "pre-qin",
            "三國魏": "three-kingdoms", "三國蜀": "three-kingdoms", "三國吳": "three-kingdoms",
        }
        ent_shards_changed = 0
        for shard_fp in sorted((idx_dir / "entities").glob("*.json")):
            shard = json.loads(shard_fp.read_text(encoding="utf-8"))
            shard_changed = False
            for eid, entry in shard.items():
                if not isinstance(entry, dict):
                    continue
                e = entities.get(eid)
                if not e:
                    continue
                new_dyn = e.get("dynasty")
                if entry.get("dynasty") != new_dyn:
                    entry["dynasty"] = new_dyn
                    shard_changed = True
                    stats["idx.entity.dynasty_sync"] += 1
                # period：若源文件有 period，覆蓋；否則按規範 dynasty 推
                src_per = e.get("period")
                new_per = src_per or CANON_TO_PER.get(new_dyn)
                if new_per and entry.get("period") != new_per:
                    entry["period"] = new_per
                    shard_changed = True
                    stats["idx.entity.period_sync"] += 1
            if shard_changed:
                shard_fp.write_text(
                    json.dumps(shard, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                ent_shards_changed += 1
        stats["idx.entity.shards_changed"] = ent_shards_changed

        print("同步 index/works 分片 ...")
        wk_shards_changed = 0
        for shard_fp in sorted((idx_dir / "works").glob("*.json")):
            shard = json.loads(shard_fp.read_text(encoding="utf-8"))
            shard_changed = False
            for wid, entry in shard.items():
                if not isinstance(entry, dict):
                    continue
                w = works.get(wid)
                if not w:
                    continue
                new_dyn = w.get("dynasty")
                if entry.get("dynasty") != new_dyn:
                    entry["dynasty"] = new_dyn
                    shard_changed = True
                    stats["idx.work.dynasty_sync"] += 1
                src_per = w.get("period")
                if src_per and entry.get("period") != src_per:
                    entry["period"] = src_per
                    shard_changed = True
                    stats["idx.work.period_sync"] += 1
            if shard_changed:
                shard_fp.write_text(
                    json.dumps(shard, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                wk_shards_changed += 1
        stats["idx.work.shards_changed"] = wk_shards_changed

    # ========== 報告 ==========
    print("\n=== 統計 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:50s} {v:>6}")

    # 剩餘未解
    remaining = Counter()
    for e in entities.values():
        dyn = e.get("dynasty")
        if dyn in AMBIGUOUS:
            remaining[f"entity.{dyn}"] += 1
    for w in works.values():
        for a in w.get("authors", []) or []:
            if isinstance(a, dict):
                dyn = a.get("dynasty")
                if dyn in AMBIGUOUS:
                    remaining[f"author.{dyn}"] += 1
    print(f"\n=== 剩餘未解 ===")
    for k, v in sorted(remaining.items()):
        print(f"  {k:30s} {v:>6}")

    # 輸出未解清單
    unresolved_entities = []
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn in AMBIGUOUS:
            unresolved_entities.append({
                "id": eid,
                "name": e.get("primary_name", ""),
                "dynasty": dyn,
                "birth_year": e.get("birth_year"),
                "death_year": e.get("death_year"),
                "has_cbdb": bool(e.get("external_ids", {}).get("cbdb_id")),
            })
    unresolved_authors = []
    for wid, w in works.items():
        for a in w.get("authors", []) or []:
            if isinstance(a, dict):
                dyn = a.get("dynasty")
                if dyn in AMBIGUOUS:
                    unresolved_authors.append({
                        "work_id": wid,
                        "work_title": w.get("title", ""),
                        "author_name": a.get("name", ""),
                        "dynasty": dyn,
                        "entity_id": a.get("entity_id"),
                    })

    out_path = ROOT / ".claude" / "known-issues" / "南北朝未決.json"
    out_path.write_text(json.dumps({
        "unresolved_entities": unresolved_entities,
        "unresolved_authors": unresolved_authors,
        "stats": dict(stats),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n未決清單已保存: {out_path}")


if __name__ == "__main__":
    main()
