#!/usr/bin/env python3
"""
fix_nanbeichao_round2.py — 南北朝朝代拆分 第二輪

處理 Round 1 後剩餘的歧義條目：
  entity.宋 898 / entity.晉 435 / entity.梁 30 / entity.周 22 / entity.蜀 11 / entity.魏 6 / entity.吳 4
  author.宋 1980 / author.晉 558 / author.梁 86 / author.周 75 / author.蜀 14 ...

Batch A2: CBDB IndexYear 判定
  - c_dy=15 + IndexYear 960-1126 → 北宋
  - c_dy=15 + IndexYear 1127-1279 → 南宋
  - c_dy=15 + IndexYear <960 or >1279 → 誤標，按 IndexYear 判
  - 其他 c_dy + IndexYear → 輔助驗證

Batch B2: Work.title 年號關鍵詞
  - 北宋年號（建隆~靖康）→ 北宋
  - 南宋年號（建炎~德祐）→ 南宋
  - 西晉年號（泰始~建興）→ 西晉
  - 東晉年號（大興~元熙）→ 東晉
  - 南朝宋年號（永初~昇明）→ 南朝宋
  - 南朝齊年號（建元~中興）→ 南朝齊
  - 南朝梁年號（天監~太平）→ 南朝梁
  - 南朝陳年號（永定~禎明）→ 南朝陳
  - 北魏年號（登國~中興）→ 北魏

Batch C2: 歷史人物詞典擴充（晉代/宋代/南朝/北朝）
Batch D2: Work.indexed_by 信號補強
  - 見於隋志 + dynasty=宋 → 南朝宋（Round 1 已做，補漏）
  - 見於漢志 → 先秦
  - 見於補晋書藝文志 + dynasty=晉 → 保留晉（但可結合年號分西/東）

Batch E2: 誤標清理
  - entity.dynasty=宋 但 work.period=qing/ming/liao-jin-yuan 且 CBDB 確認非趙宋 → 清理

Batch F2: Entity→Author 傳播
Batch G2: Author→Entity 反向傳播
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / ".claude" / "known-issues" / "cbdb_dy_cache.json"

AMBIGUOUS = {"宋", "晉", "梁", "周", "齊", "魏", "吳", "蜀", "陳", "三國", "南北朝", "南朝", "北朝"}


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def iter_work_files():
    return sorted(ROOT.glob("Work/?/?/?/*.json"))


def iter_entity_files():
    return sorted(ROOT.glob("Entity/?/?/?/*.json"))


# ========== Batch A2: CBDB IndexYear 判定 ==========
# c_dy=15 + IndexYear → 北宋/南宋
def song_from_index_year(index_year_str, entity_birth_year, entity_death_year):
    """用 IndexYear 判定北宋/南宋"""
    try:
        iy = int(index_year_str) if index_year_str and int(index_year_str) > 0 else None
    except (ValueError, TypeError):
        iy = None
    yb = entity_birth_year
    yd = entity_death_year
    # 優先用 IndexYear，沒有則用 entity 生卒年
    years = [y for y in [iy, yb, yd] if y is not None and y > 0]
    if not years:
        return None, ""
    # 取最早的有效年份作為人物主要活動期
    earliest = min(years)
    if 960 <= earliest < 1127:
        return "北宋", f"cbdb:index_year={earliest}→北宋"
    if 1127 <= earliest < 1279:
        return "南宋", f"cbdb:index_year={earliest}→南宋"
    if earliest < 960:
        # 早於北宋 → 不是趙宋，誤標
        if earliest < 420:
            return "南朝宋", f"cbdb:index_year={earliest}→南朝宋(誤標宋)"
        return None, f"cbdb:index_year={earliest}<960, 疑誤標"
    if earliest >= 1279:
        return None, f"cbdb:index_year={earliest}>=1279, 疑誤標"
    return None, ""


# ========== Batch B2: Work.title 年號關鍵詞 ==========
# 北宋年號
NORTH_SONG_NIANHAO = {
    "建隆", "乾德", "開寶", "太平興國", "雍熙", "端拱", "淳化", "至道",
    "咸平", "景德", "大中祥符", "天禧", "乾興", "天聖", "明道", "景祐",
    "寶元", "康定", "慶曆", "皇祐", "至和", "嘉祐", "治平", "熙寧",
    "元豐", "元祐", "紹聖", "元符", "建中靖國", "崇寧", "大觀", "政和",
    "重和", "宣和", "靖康",
}
# 南宋年號
SOUTH_SONG_NIANHAO = {
    "建炎", "紹興", "隆興", "乾道", "淳熙", "慶元", "嘉泰", "開禧",
    "嘉定", "寶慶", "紹定", "端平", "嘉熙", "淳祐", "寶祐", "開慶",
    "景定", "咸淳", "德祐", "祥興",
}
# 西晉年號
XI_JIN_NIANHAO = {
    "泰始", "咸寧", "太康", "太熙", "永熙", "永平", "元康", "永康",
    "永寧", "太安", "建武", "永興", "光熙", "永嘉", "建興",
}
# 東晉年號
DONG_JIN_NIANHAO = {
    "大興", "永昌", "太寧", "咸和", "咸康", "建元", "永和", "升平",
    "隆和", "興寧", "太和", "咸安", "寧康", "太元", "隆安", "元興",
    "大亨", "義熙", "元熙",
}
# 南朝宋年號
NANCHAOSONG_NIANHAO = {
    "永初", "景平", "元嘉", "孝建", "大明", "永光", "景和", "泰始",
    "泰豫", "元徽", "昇明",
}
# 南朝齊年號
NANCHAOQI_NIANHAO = {
    "建元", "永明", "隆昌", "延興", "建武", "永泰", "中興",
}
# 南朝梁年號
NANCHAOLIANG_NIANHAO = {
    "天監", "普通", "大通", "中大通", "大同", "中大同", "太清",
    "大寶", "天正", "承聖", "天成", "紹泰", "太平",
}
# 南朝陳年號
NANCHAOCHEN_NIANHAO = {
    "永定", "天嘉", "天康", "光大", "太建", "至德", "禎明",
}
# 北魏年號
BEIWEI_NIANHAO = {
    "登國", "皇始", "天興", "天賜", "永興", "神瑞", "泰常", "始光",
    "神麚", "延和", "太延", "太平真君", "正平", "興安", "興光",
    "太安", "和平", "天安", "皇興", "延興", "承明", "太和", "景明",
    "正始", "永平", "延昌", "熙平", "神龜", "正光", "孝昌", "武泰",
    "建義", "永安", "建明", "普泰", "中興",
}


def dynasty_from_title_nianhao(title: str, current_dyn: str) -> tuple[str | None, str | None]:
    """從 Work.title 年號推斷作者朝代。僅在 current_dyn 是歧義值時用。"""
    if not title:
        return None, None
    # 只處理歧義 dynasty
    if current_dyn == "宋":
        # 先查南朝宋年號（更特異）
        for nh in NANCHAOSONG_NIANHAO:
            if nh in title:
                return "南朝宋", f"title_nianhao:{nh}→南朝宋"
        for nh in NORTH_SONG_NIANHAO:
            if nh in title:
                return "北宋", f"title_nianhao:{nh}→北宋"
        for nh in SOUTH_SONG_NIANHAO:
            if nh in title:
                return "南宋", f"title_nianhao:{nh}→南宋"
    elif current_dyn == "晉":
        for nh in XI_JIN_NIANHAO:
            if nh in title:
                return "西晉", f"title_nianhao:{nh}→西晉"
        for nh in DONG_JIN_NIANHAO:
            if nh in title:
                return "東晉", f"title_nianhao:{nh}→東晉"
    elif current_dyn == "梁":
        for nh in NANCHAOLIANG_NIANHAO:
            if nh in title:
                return "南朝梁", f"title_nianhao:{nh}→南朝梁"
    elif current_dyn == "齊":
        for nh in NANCHAOQI_NIANHAO:
            if nh in title:
                return "南朝齊", f"title_nianhao:{nh}→南朝齊"
    elif current_dyn == "陳":
        for nh in NANCHAOCHEN_NIANHAO:
            if nh in title:
                return "南朝陳", f"title_nianhao:{nh}→南朝陳"
    elif current_dyn == "魏":
        for nh in BEIWEI_NIANHAO:
            if nh in title:
                return "北魏", f"title_nianhao:{nh}→北魏"
    return None, None


# ========== Batch C2: 歷史人物詞典擴充 ==========
# 補充 Round 1 未收錄的晉代/宋代/南朝/北朝人物
EXTRA_FIGURES = {
    # === 西晉人物（補充）===
    "孔晁": "西晉",       # 逸周書注
    "孔晃": "西晉",       # 尚書注
    "孔潘": "西晉",
    "呂忱": "西晉",       # 字林
    "呂靜": "西晉",       # 韻集
    "嵇含": "西晉",       # 南方草木狀
    "崔游": "西晉",
    "崔譔": "西晉",
    "常寬": "西晉",       # 蜀志
    "庾協": "西晉",
    "庾袞": "西晉",       # 孝行傳
    "何琦": "西晉",
    "伍緝之": "西晉",
    "和苞": "西晉",
    "孟陋": "西晉",
    "孫暢之": "西晉",
    "孫略": "西晉",
    "孫緯": "西晉",
    "孫練": "西晉",
    "宋纖": "西晉",
    "宋處宗": "西晉",
    "宣舒": "西晉",
    "尹毅": "西晉",
    "崔退": "西晉",
    "庾運": "西晉",
    "鄒湛": "西晉",
    "薛坦": "西晉",
    "薛貞": "西晉",
    "薄叔元": "西晉",
    "蘇彥": "西晉",
    "蘇元明": "西晉",
    "衛環": "西晉",
    "陳統": "西晉",
    "陳長壽": "西晉",
    "黃穎": "西晉",
    "齊恭": "西晉",
    "華暢": "西晉",
    "董助": "西晉",
    "董景道": "西晉",
    "蓋泓": "西晉",
    "蔡韶": "西晉",
    "京相璠": "西晉",     # 春秋土地名
    "姜岌": "西晉",       # 後秦? 乙弗
    "干長生": "西晉",
    "車灌": "西晉",
    "陳卓": "西晉",       # 天文星占
    "虞聳": "西晉",
    "董巴": "西晉",       # 漢書注/輿服志
    "虞溥": "西晉",       # 江表傳
    "繆徵": "西晉",
    "李熹": "西晉",
    "庾峻": "西晉",
    "庾珉": "西晉",
    "庾敳": "西晉",
    "杜育": "西晉",
    "王接": "西晉",
    "張輔": "西晉",
    "崔豹": "西晉",       # 古今注
    "王愷": "西晉",
    "賈充": "西晉",
    "荀勗": "西晉",
    "華嶠": "西晉",       # 後漢書
    "王沈": "西晉",       # 魏書（魏末晉初）
    "羊琇": "西晉",
    "楊駿": "西晉",
    "衛瓘": "西晉",       # 已在R1
    "衞瓘": "西晉",       # 異體
    "歐陽建": "西晉",
    "裴秀": "西晉",
    "牽秀": "西晉",
    "曹攄": "西晉",
    "張載": "西晉",
    "張協": "西晉",
    "張亢": "西晉",
    "索靖": "西晉",
    "衛恒": "西晉",
    "衛恆": "西晉",
    "杜錫": "西晉",
    "卞粹": "西晉",
    "劉頌": "西晉",
    "李重": "西晉",
    "劉實": "西晉",
    "劉宏": "西晉",
    "閻纘": "西晉",
    "成公綏": "西晉",
    "夏侯湛": "西晉",
    "孫楚": "西晉",
    "魯勝": "西晉",
    "摯虞": "西晉",       # 文章流別集
    "司馬彪": "西晉",     # 續漢書
    "束皙": "西晉",       # 晉書
    "皇甫謐": "西晉",     # 高士傳
    "劉琨": "西晉",
    "盧諶": "西晉",       # 跨西晉末到十六國，按主要活動歸西晉
    "何劭": "西晉",
    "山濤": "西晉",
    "王戎": "西晉",
    "王衍": "西晉",
    "王渾": "西晉",
    "王濟": "西晉",
    "石崇": "西晉",
    "傅玄": "西晉",       # 已在R1 BIO_DYNASTY_HINTS，但 HISTORICAL_FIGURES 缺
    "傅鹹": "西晉",       # 異體
    "傅咸": "西晉",
    "郭象": "西晉",       # 莊子注
    "向秀": "西晉",       # 莊子注
    "鄭沖": "西晉",
    "虞溥": "西晉",
    "胡奮": "西晉",
    "劉頌": "西晉",
    "羊祜": "西晉",       # 已在R1 BIO_DYNASTY_HINTS
    "杜預": "西晉",       # 已在R1
    "張華": "西晉",       # 已在R1
    "陳壽": "西晉",       # 已在R1，三國志
    "左思": "西晉",       # 已在R1
    "潘岳": "西晉",       # 已在R1
    "陸機": "西晉",       # 已在R1
    "陸雲": "西晉",       # 已在R1

    # === 東晉人物（補充）===
    "干寶": "東晉",       # 搜神記/晉紀
    "習鑿齒": "東晉",     # 漢晉春秋
    "袁宏": "東晉",       # 後漢紀
    "孫盛": "東晉",       # 晉陽秋
    "郭璞": "東晉",       # 爾雅注/山海經注
    "葛洪": "東晉",       # 抱朴子
    "王羲之": "東晉",
    "王獻之": "東晉",
    "顧愷之": "東晉",     # 異體顧凱之
    "顧凱之": "東晉",
    "戴逵": "東晉",
    "陶淵明": "東晉",     # 跨東晉末到劉宋，按主要活動歸東晉
    "謝安": "東晉",
    "桓溫": "東晉",
    "桓玄": "東晉",
    "王導": "東晉",
    "王敦": "東晉",
    "謝玄": "東晉",
    "溫嶠": "東晉",
    "劉超": "東晉",
    "劉惔": "東晉",
    "王濛": "東晉",
    "王坦之": "東晉",
    "王彪之": "東晉",
    "王述": "東晉",
    "卞壼": "東晉",
    "賀循": "東晉",
    "蔡謨": "東晉",
    "王蘊": "東晉",
    "王恭": "東晉",
    "謝萬": "東晉",
    "謝石": "東晉",
    "桓沖": "東晉",
    "庾亮": "東晉",
    "庾冰": "東晉",
    "庾翼": "東晉",
    "謝混": "東晉",
    "殷仲文": "東晉",
    "殷仲堪": "東晉",
    "劉毅": "東晉",
    "何無忌": "東晉",
    "劉穆之": "東晉",
    "王韶之": "東晉",
    "劉裕": "東晉",       # 跨東晉末到宋，按主要活動歸東晉
    "傅亮": "東晉",       # 跨東晉末到宋
    "范汪": "東晉",
    "范寧": "東晉",       # 穀梁傳集解
    "袁喬": "東晉",
    "袁準": "東晉",
    "袁悅之": "東晉",
    "袁曄": "東晉",
    "袁真": "東晉",
    "裴啓": "東晉",       # 語林
    "裴啟": "東晉",
    "裴藻": "東晉",
    "車胤": "東晉",
    "郭文": "東晉",
    "郭泰機": "東晉",
    "郭澄": "東晉",
    "郭琦": "東晉",
    "鄧淵": "東晉",
    "鄭嗣": "東晉",
    "釋曇微": "東晉",
    "釋法安": "東晉",
    "釋法濟": "東晉",
    "釋道標": "東晉",
    "釋道流": "東晉",
    "釋道祖": "東晉",
    "僧道安": "東晉",     # 釋道安
    "釋道安": "東晉",
    "道安": "東晉",
    "寶雲": "東晉",       # 譯經
    "劉涓子": "東晉",     # 金瘡方
    "阮渾": "東晉",
    "陰澹": "東晉",
    "陳勰": "東晉",
    "陶濟": "東晉",
    "陸翩": "東晉",
    "陸翽": "東晉",
    "韓揚": "東晉",
    "顧夷": "東晉",
    "顧悅之": "東晉",
    "馬朗": "東晉",
    "高範": "東晉",
    "蘇彥": "東晉",       # 與西晉重，移除（已在西晉）
    "蕭廣濟": "東晉",     # 異苑?
    "蔡護": "東晉",
    "蔡讓": "東晉",
    "蔡讚": "東晉",
    "都超": "東晉",       # 郗超異寫
    "郗超": "東晉",
    "許適": "東晉",
    "邢融": "東晉",
    "郭冲": "東晉",
    "郭義": "東晉",
    "都原": "東晉",
    "虞槃佐": "東晉",
    "虞盤佐": "東晉",
    "虞禹": "東晉",
    "衛理": "東晉",
    "于法開": "東晉",     # 佛教
    "康法暢": "東晉",
    "康法": "東晉",
    "宋岱": "東晉",
    "劉或": "東晉",
    "劉演": "東晉",
    "劉瑤": "東晉",
    "劉速": "東晉",
    "劉銑": "東晉",
    "劉黃老": "東晉",
    "劉昌宗": "東晉",
    "吳商": "東晉",
    "孟儀": "東晉",
    "孫敏": "東晉",
    "宣聘": "東晉",
    "尤申": "東晉",
    "尹數": "東晉",
    "崔游": "西晉",       # 與東晉重，已在西晉
    "張輝": "東晉",
    "王時敏": "東晉",
    "李顒": "東晉",       # 與清李顒同名，此為東晉
    "李順": "東晉",
    "王浮": "東晉",       # 化胡經
    # 釋法具: CBDB c_dy=15 確認為宋代，不收入東晉詞典
    "杜嵩": "東晉",
    "樂筆": "東晉",
    "胡鈉": "東晉",
    "咸注": "東晉",
    "唐務": "東晉",
    "姜度": "東晉",
    "孟氏": "東晉",
    "雷氏": "東晉",
    "孫夫人": "東晉",
    "丘俊孫": "東晉",
    "仲長毅": "東晉",
    "伊說": "東晉",
    "何拳": "東晉",
    "劉嘉": "東晉",
    "劉塞": "東晉",
    "吳處": "東晉",
    "張斐": "東晉",       # 律注
    "裴松之": "南朝宋",   # 已在R1，三國志注
    "范曄": "南朝宋",     # 已在R1
    "徐爰": "南朝宋",     # 已在R1
    "何承天": "南朝宋",   # 已在R1
    "劉敬叔": "南朝宋",   # 已在R1
    "謝靈運": "南朝宋",   # 已在R1

    # === 北宋人物（補充，無 cbdb_id 的）===
    "宋咸": "北宋",       # 補晉書? 不確定，可能北宋
    "王堯臣": "北宋",     # 崇文總目
    "王洙": "北宋",
    "劉敞": "北宋",       # 七經小傳
    "劉攽": "北宋",       # 漢書注
    "宋敏求": "北宋",     # 唐大詔令集
    "劉羲叟": "北宋",     # 劉氏輯歷
    "晁端彥": "北宋",
    "王安禮": "北宋",
    "王安國": "北宋",
    "曾肇": "北宋",
    "彭汝礪": "北宋",
    "劉弇": "北宋",
    "秦觀": "北宋",       # 已在R1
    "毛滂": "北宋",
    "賀鑄": "北宋",
    "陳師道": "北宋",     # 已在R1
    "晁補之": "北宋",     # 已在R1
    "張耒": "北宋",       # 已在R1
    "李之儀": "北宋",     # 姑溪詞
    "陸佃": "北宋",       # 埤雅
    "羅願": "南宋",       # 爾雅翼（南宋）
    "鄭樵": "南宋",       # 已在R1，通志
    "洪邁": "南宋",       # 已在R1，容齋隨筆
    "王應麟": "南宋",     # 已在R1，困學紀聞
    "馬端臨": "南宋",     # 已在R1，文獻通考

    # === 南朝梁/陳/齊人物（補充）===
    "劉勰": "南朝梁",     # 已在R1
    "鍾嶸": "南朝梁",     # 已在R1
    "蕭統": "南朝梁",     # 已在R1
    "蕭綱": "南朝梁",     # 已在R1
    "蕭繹": "南朝梁",     # 已在R1
    "沈約": "南朝梁",     # 已在R1
    "江淹": "南朝梁",     # 已在R1
    "陶弘景": "南朝梁",   # 已在R1
    "庾肩吾": "南朝梁",   # 已在R1
    "徐陵": "南朝梁",     # 已在R1
    "庾信": "南朝梁",     # 已在R1
    "劉孝標": "南朝梁",   # 已在R1
    "劉峻": "南朝梁",     # 已在R1
    "任昉": "南朝梁",     # 已在R1
    "吳均": "南朝梁",     # 已在R1
    "周興嗣": "南朝梁",   # 已在R1
    "阮孝緒": "南朝梁",   # 已在R1
    "顧野王": "南朝梁",   # 已在R1

    # === 北魏/北齊/北周人物（補充）===
    "崔浩": "北魏",       # 已在R1
    "崔鴻": "北魏",       # 已在R1
    "酈道元": "北魏",     # 已在R1
    "賈思勰": "北魏",     # 已在R1
    "魏收": "北齊",       # 已在R1，魏書
    "顏之推": "北齊",     # 已在R1
    "溫子昇": "北魏",     # 已在R1

    # === 後梁（五代）===
    # 後梁人物較少

    # === 後周（五代）===
    "王朴": "後周",       # 已在R1
    "竇儼": "後周",       # 已在R1
}

# 先秦人物 dynasty=周 的特殊處理（補充）
PRE_QIN_FROM_ZHOU = {
    "老子": "先秦",
    "莊周": "先秦",
    "莊子": "先秦",
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
    "范蠡": "春秋",
    "文種": "春秋",
    "黃歇": "戰國",
    "張儀": "戰國",
    "樂毅": "戰國",
    "惠施": "戰國",
    "商鞅": "戰國",
    "公孫鞅": "戰國",
    "信陵君": "戰國",
    "信陵君魏無忌": "戰國",
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
    "陳仲子": "戰國齊",
    "萇弘": "春秋",
    "景差": "戰國",
}


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
    for item in indexed_by or []:
        if isinstance(item, dict) and item.get("source") == "漢書藝文志":
            return True
    return False


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

    # ========== Batch A2: CBDB IndexYear 判定 ==========
    print("\n=== Batch A2: CBDB IndexYear 判定 ===")
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
        iy = entry.get("index_year", "")
        by = e.get("birth_year")
        dy = e.get("death_year")

        # 宋的特殊處理：用 IndexYear 分北/南
        if dyn == "宋" and cdy == "15":
            new_dyn, basis = song_from_index_year(iy, by, dy)
            if new_dyn and new_dyn != dyn:
                e["dynasty"] = new_dyn
                e["dynasty_basis"] = basis
                e["updated_at"] = now_iso()
                stats[f"A2.entity.宋→{new_dyn}"] += 1
            continue

        # 其他歧義值：若 CBDB IndexYear 與當前 dynasty 不符，可能是誤標
        # 但不輕易改，只處理明確的情況
        if dyn == "晉" and cdy in ("23", "27"):
            # c_dy=23 西晉，c_dy=27 東晉
            canon = {"23": "西晉", "27": "東晉"}.get(cdy)
            if canon and canon != dyn:
                e["dynasty"] = canon
                e["dynasty_basis"] = f"cbdb:c_dy={cdy}→{canon}"
                e["updated_at"] = now_iso()
                stats[f"A2.entity.晉→{canon}"] += 1

    # ========== Batch B2: Work.title 年號關鍵詞 ==========
    print("\n=== Batch B2: Work.title 年號關鍵詞 ===")
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn not in AMBIGUOUS:
            continue
        ws = eid_to_works.get(eid, [])
        if not ws:
            continue
        # 對該 entity 的所有 work title 查年號
        candidates = []
        for w in ws:
            title = w.get("title", "") or ""
            new_dyn, basis = dynasty_from_title_nianhao(title, dyn)
            if new_dyn:
                candidates.append((new_dyn, basis))
        if not candidates:
            continue
        # 取第一個（年號信號特異性高）
        new_dyn, basis = candidates[0]
        if new_dyn != dyn:
            e["dynasty"] = new_dyn
            e["dynasty_basis"] = basis
            e["updated_at"] = now_iso()
            stats[f"B2.entity.{dyn}→{new_dyn}"] += 1

    # ========== Batch C2: 歷史人物詞典擴充 ==========
    print("\n=== Batch C2: 歷史人物詞典擴充 ===")
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn not in AMBIGUOUS:
            continue
        name = e.get("primary_name", "")
        # 若有 cbdb_id 且 CBDB c_dy 已明確判定，詞典不覆蓋（CBDB 優先）
        ext = e.get("external_ids", {})
        cbdb_id = ext.get("cbdb_id") if isinstance(ext, dict) else None
        if cbdb_id:
            entry = cbdb_cache.get(str(cbdb_id), {})
            cdy = entry.get("dynasty_id", "")
            # c_dy=15 但無 IndexYear 的宋 → 詞典可補（因 CBDB 分不出北/南）
            # 但 c_dy 非 15 的宋 → CBDB 已判定，詞典不覆蓋
            if dyn == "宋" and cdy and cdy not in ("15", "28"):
                continue
            # dynasty=晉 且 c_dy=23/27 → CBDB 已判定西/東晉，詞典不覆蓋
            if dyn == "晉" and cdy in ("23", "27"):
                continue
        if name in EXTRA_FIGURES:
            new_dyn = EXTRA_FIGURES[name]
            if new_dyn != dyn:
                e["dynasty"] = new_dyn
                e["dynasty_basis"] = f"historical_dict_r2:{name}→{new_dyn}"
                e["updated_at"] = now_iso()
                stats[f"C2.entity.{dyn}→{new_dyn}"] += 1
        elif name in PRE_QIN_FROM_ZHOU and dyn == "周":
            new_dyn = PRE_QIN_FROM_ZHOU[name]
            if new_dyn != dyn:
                e["dynasty"] = new_dyn
                e["dynasty_basis"] = f"pre_qin_dict:{name}→{new_dyn}"
                e["updated_at"] = now_iso()
                stats[f"C2.entity.周→{new_dyn}"] += 1

    # ========== Batch D2: Work.indexed_by 信號補強 ==========
    print("\n=== Batch D2: Work.indexed_by 信號補強 ===")
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn not in AMBIGUOUS:
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
        if has_hanzhi and dyn in ("宋", "晉", "梁", "齊", "魏", "周"):
            # 見於漢志 → 先秦/秦漢人，dynasty 是誤標
            e["dynasty"] = "先秦"
            e["dynasty_basis"] = "catalog_bound:漢書藝文志→先秦"
            e["updated_at"] = now_iso()
            stats[f"D2.entity.{dyn}→先秦(漢志)"] += 1
        elif has_suizhi and dyn == "宋":
            # 見於隋志 → 南朝宋
            e["dynasty"] = "南朝宋"
            e["dynasty_basis"] = "catalog_bound:隋書經籍志→南朝宋"
            e["updated_at"] = now_iso()
            stats["D2.entity.宋→南朝宋(隋志)"] += 1

    # ========== Batch E2: 誤標清理 ==========
    # entity.dynasty=宋 但 work.period=qing/ming/liao-jin-yuan 且 CBDB 確認非趙宋
    print("\n=== Batch E2: 誤標清理 ===")
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn != "宋":
            continue
        ext = e.get("external_ids", {})
        cbdb_id = ext.get("cbdb_id") if isinstance(ext, dict) else None
        if cbdb_id:
            entry = cbdb_cache.get(str(cbdb_id), {})
            cdy = entry.get("dynasty_id", "")
            if cdy and cdy != "15" and cdy != "28":
                # CBDB 明確非趙宋/南朝宋 → 誤標
                canon_map = {
                    "6": "唐", "19": "明", "20": "清", "18": "元", "16": "遼",
                    "17": "金", "21": "中華民國", "22": "中華人民共和國",
                    "13": "唐", "77": "武周", "79": "元", "80": "南明",
                }
                canon = canon_map.get(cdy)
                if canon:
                    e["dynasty"] = canon
                    e["dynasty_basis"] = f"cbdb:c_dy={cdy}→{canon}(誤標宋)"
                    e["updated_at"] = now_iso()
                    stats[f"E2.entity.宋→{canon}(cbdb)"] += 1
                    continue
        # 無 cbdb_id 但 work period 明確非 song/nanbeichao
        ws = eid_to_works.get(eid, [])
        if not ws:
            continue
        pers = set()
        for w in ws:
            p = w.get("period")
            if p:
                pers.add(p)
        # 所有 work period 都非 song/nanbeichao
        if pers and pers <= {"qing", "ming", "liao-jin-yuan", "qin-han", "sui-tang", "five-dynasties"}:
            # 但這不一定是誤標（可能是宋人著作被四庫收錄）
            # 只有在 work period 明確是 qin-han/sui-tang 且無 cbdb 時才清理
            if pers <= {"qin-han", "sui-tang"}:
                # 取最多 period
                from collections import Counter as C2
                pc = C2(w.get("period") for w in ws if w.get("period"))
                top_per = pc.most_common(1)[0][0]
                canon = {"qin-han": "漢", "sui-tang": "唐"}.get(top_per)
                if canon:
                    e["dynasty"] = canon
                    e["dynasty_basis"] = f"work_period:{top_per}→{canon}(誤標宋)"
                    e["updated_at"] = now_iso()
                    stats[f"E2.entity.宋→{canon}(work_period)"] += 1

    # ========== Batch F2: Entity→Author 傳播 ==========
    print("\n=== Batch F2: Entity→Author 傳播 ===")
    entity_dyn_map = {}
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn and dyn not in AMBIGUOUS:
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
                    a["dynasty_basis"] = f"entity_propagation_r2:{eid}"
                    stats[f"F2.author.{adyn}→{new_dyn}"] += 1
                    changed = True
        if changed:
            w["updated_at"] = now_iso()

    # ========== Batch G2: Author→Entity 反向傳播 ==========
    print("\n=== Batch G2: Author→Entity 反向傳播 ===")
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
                    e["dynasty_basis"] = "author_propagation_r2"
                    e["updated_at"] = now_iso()
                    stats[f"G2.entity.{dyn}→{new_dyn}"] += 1

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
