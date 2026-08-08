#!/usr/bin/env python3
"""
fix_three_kingdoms_jin_round3.py — 三國·兩晉朝代拆分 第三輪

處理第一、二輪還未解的 ~1180 條：

  Batch F: Work.title 關鍵詞規則（更廣的信號）
    - 書名體裁暗示：起居注年代 / 中興 → 東晉 / 晉紀作者 / 十六國起居注→不屬西東晉
    - 作者名+書名：王沈魏書→三國魏，韋昭吳書→三國吳，習鑿齒漢晉春秋→東晉
    - 別傳/家傳按傳主時代（王濛別傳→東晉人王濛，王薈別傳→東晉人王薈）

  Batch G: 魏/吳誤標清理（關鍵發現：未解的 84 魏 + 35 吳 全沒有被《三國藝文志》著錄）
    分兩子批：
    G1 已知誤標詞典：昌碩(清)、朱晦翁(宋)、朱熹(宋)、吳均(梁)、
        阮籍(三國魏)、曹操(三國魏)、劉楨(三國魏)、鄭小同(三國魏)、
        崔浩(北魏/南北朝)、崔鴻(北魏)、沈瑩(三國吳)、唐固(三國吳)、
        姚信(三國吳)、王蕃(三國吳)、顧譚(三國吳)、周昭(三國吳)等
    G2 來源反向排除：只被明清志(清史稿/續修四庫/國史經籍志)著錄
        → 標 dynasty=null, dynasty_basis=garbage_clean

  Batch H: 別傳體裁 → 傳主時代詞典（查王濛/王薈/范汪等人 → 西晉/東晉）
           把這些人加入歷史人物詞典（利用前兩輪已分類的 entity/author 反向推）

  Batch I: 再一輪 Entity↔Author 傳播（第 3 次）
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def iter_work_files():
    return sorted(ROOT.glob("Work/?/?/?/*.json"))


def iter_entity_files():
    return sorted(ROOT.glob("Entity/?/?/?/*.json"))


# ========== Batch F: Work.title 關鍵詞規則 ==========
# 西晉年號（更全，包含可能在起居注中出現的）
XJ_NIANHAO_SET = {
    "泰始", "咸寧", "太康", "太熙", "永熙", "永平", "元康", "永康",
    "永寧", "太安", "永安", "建武", "永興", "光熙", "永嘉", "建興",
}
DJ_NIANHAO_SET = {
    "大興", "永昌", "太寧", "咸和", "咸康", "建元", "永和", "升平",
    "隆和", "興寧", "太和", "咸安", "寧康", "太元", "隆安", "元興",
    "大亨", "義熙", "元熙",
}
SGW_NIANHAO_SET = {
    "黃初", "太和", "青龍", "景初", "正始", "嘉平", "正元", "甘露",
    "景元", "咸熙",
}
SGWU_NIANHAO_SET = {
    "黃武", "黃龍", "嘉禾", "赤烏", "太元", "神鳳", "建興", "五鳳",
    "太平", "永安", "元興", "寶鼎", "建衡", "鳳皇", "天冊", "天璽", "天紀",
}
SGS_NIANHAO_SET = {"章武", "延熙", "景耀", "炎興"}

# 十六國/南北朝/隋唐 年號出現在起居注中 → 這些不是西晉/東晉
EXCLUDE_NIANHAO = {
    "南燕", "前燕", "後燕", "西燕", "北燕", "前秦", "後秦", "西秦",
    "前涼", "後涼", "南涼", "北涼", "西涼", "夏", "成漢",
    "劉宋", "北魏", "北齊", "北周", "梁", "陳", "隋", "唐", "宋",
}


def dynasty_from_work_title(title: str) -> tuple[str | None, str | None]:
    """從 Work.title 推斷該 Work 自身朝代（作者朝代僅弱推斷）"""
    # 1. 起居注年號
    if "起居注" in title:
        # 先看是否十六國 → 排除
        for ex in EXCLUDE_NIANHAO:
            if ex in title and "起居注" in title:
                return None, None  # 不屬西晉東晉，不動
        # 西晉年號起居注
        for nh in XJ_NIANHAO_SET:
            if nh in title and "起居注" in title:
                return "西晉", f"title_nianhao_qjz:{nh}→西晉"
        for nh in DJ_NIANHAO_SET:
            if nh in title and "起居注" in title:
                return "東晉", f"title_nianhao_qjz:{nh}→東晉"

    # 2. 中興書系列（只有東晉講"中興"：元帝南渡中興）
    if "中興" in title:
        return "東晉", "title_keyword:中興→東晉"

    # 3. 書名暗示時代
    # 漢晉春秋 → 東晉 (習鑿齒撰)
    if "漢晉春秋" in title:
        return "東晉", "title_book:漢晉春秋→東晉"
    # 晉陽秋 / 續晉陽秋 → 東晉
    if "晉陽秋" in title:
        return "東晉", "title_book:晉陽秋→東晉"
    # 魏武本紀 / 魏文帝士品錄 → 三國魏
    if "魏武" in title or "魏文帝" in title:
        return "三國魏", "title_keyword:魏武/魏文帝→三國魏"
    if "王沈魏書" in title:
        return "三國魏", "title_book:王沈魏書→三國魏"
    if "魏氏春秋" in title:
        return "三國魏", "title_book:魏氏春秋→三國魏"
    if "魏略" in title:
        return "三國魏", "title_book:魏略→三國魏"
    if "蜀本紀" in title:
        return "三國蜀", "title_book:蜀本紀→三國蜀"

    # 4. 傳/別傳：根據傳主是否在已知人物詞典中
    # 由後面 Batch H 處理

    # 5. 三國/兩晉的專有名詞
    if "華陽國志" in title:
        return "東晉", "title_book:華陽國志→東晉"  # 常璩東晉人

    return None, None


# ========== Batch G1: 魏/吳已知誤標詞典 ==========
# 依據前面抽樣 + 常識
WEI_WU_CORRECTIONS = {
    # --- 作者名 → (正確朝代, 依據) ---
    # 魏 → 三國魏 確定者
    "阮籍": ("三國魏", "阮籍(210-263)，字嗣宗，竹林七賢之一，三國魏"),
    "曹操": ("三國魏", "曹操(155-220)，字孟德，魏武帝，三國魏"),
    "劉楨": ("三國魏", "劉楨(?-217)，字公幹，建安七子之一，三國魏"),
    "鄭小同": ("三國魏", "鄭小同(約195-258)，鄭玄孫，三國魏高貴鄉公時"),
    "鄭小": ("三國魏", "鄭小即鄭小同(約195-258)，三國魏"),
    "劉楨": ("三國魏", "劉楨毛詩義問作者"),
    "曹丕": ("三國魏", "曹丕(187-226)，魏文帝"),
    "曹植": ("三國魏", "曹植(192-232)，陳思王"),
    "王粲": ("三國魏", "王粲(177-217)，建安七子"),
    "陳琳": ("三國魏", "陳琳(?-217)，建安七子"),
    "應瑒": ("三國魏", "應瑒(?-217)，建安七子"),
    "徐幹": ("三國魏", "徐幹(170-217)，建安七子"),
    "孔融": ("三國魏", "孔融(153-208)，建安七子，活動時代三國魏前身"),
    "繆襲": ("三國魏", "繆襲(186-245)，三國魏"),
    "應璩": ("三國魏", "應璩(190-252)，三國魏"),
    "李康": ("三國魏", "李康(約196-265)，三國魏，撰運命論"),
    "曹冏": ("三國魏", "曹冏，字符首，三國魏，撰六代論"),
    "桓範": ("三國魏", "桓範(?-249)，三國魏"),
    "蔣濟": ("三國魏", "蔣濟(?-249)，三國魏"),
    "傅嘏": ("三國魏", "傅嘏(209-255)，三國魏"),
    "鍾會": ("三國魏", "鍾會(225-264)，三國魏"),
    "鄧艾": ("三國魏", "鄧艾(197-264)，三國魏"),

    # 吳 → 三國吳 確定者（第二輪抽樣中有沈瑩、唐固、姚信、王蕃、顧譚、周昭）
    "沈瑩": ("三國吳", "沈瑩(?-280)，三國吳丹陽太守，撰臨海異物志"),
    "唐固": ("三國吳", "唐固(生卒不詳)，三國吳經學家，注國語公羊"),
    "姚信": ("三國吳", "姚信，字元直，三國吳吳興人，吳陸遜外甥"),
    "王蕃": ("三國吳", "王蕃(228-266)，字永元，三國吳天文學家"),
    "顧譚": ("三國吳", "顧譚(205-246)，字子默，三國吳顧雍之孫"),
    "周昭": ("三國吳", "周昭(?-261)，字恭遠，三國吳，撰周子"),
    "朱育": ("三國吳", "朱育，三國吳會稽人，撰毛詩答雜問"),
    "張儼": ("三國吳", "張儼，三國吳，撰默記"),
    "謝承": ("三國吳", "謝承(182-254)，字偉平，三國吳，撰後漢書"),
    "項竣": ("三國吳", "項竣，三國吳太史令"),
    "丁孚": ("三國吳", "丁孚，三國吳太史令，與項竣共撰吳書"),
    "韋昭": ("三國吳", "韋昭(204-273)，吳書撰者"),
    "薛瑩": ("三國吳", "薛瑩(?-282)，三國吳，吳書撰者"),
    "華覈": ("三國吳", "華覈(?-278)，三國吳，吳書撰者"),
    "周處": ("西晉", "周處(240-297)，字子隱，除三害，西晉人"),
    "陸機": ("西晉", "陸機(261-303)，吳亡入洛，西晉"),
    "陸雲": ("西晉", "陸雲(262-303)，西晉"),

    # 北魏/北朝人物（不屬三國魏）→ nanbeichao，但 nanbeichao/dynasty 用北魏/北朝
    # 本 SCHEMA 规範名裡沒有"北魏"只有 period=nanbeichao。先改 dynasty 為暫定值
    # 但這不在三國兩晉任務範圍。暫時標 null，待南北朝拆分處理
    "崔浩": ("北魏", "崔浩(381-450)，字伯淵，北魏太武帝時，非三國魏，待南北朝拆分"),
    "崔鴻": ("北魏", "崔鴻(?-525前)，字彥鸞，北魏，撰十六國春秋，非三國魏"),

    # 明確誤標（明清/宋人）→ dynasty=null，依據 garbage_clean
    "昌碩": (None, "garbage_clean:昌碩即吳昌碩(1844-1927)，清末民初人，誤標吳"),
    "朱晦翁": (None, "garbage_clean:朱晦翁即朱熹(1130-1200)，南宋理學家，誤標吳"),
    "朱熹": (None, "garbage_clean:朱熹(1130-1200)，南宋，誤標"),
    "慶坻": (None, "garbage_clean:慶坻即汪康年/袁昶等晚清人物字，清末民初，誤標吳"),
    "桂芳": (None, "garbage_clean:桂芳，督撫兩廣奏議作者，明清時人，誤標吳"),
    "重憙": (None, "garbage_clean:重憙=王闓運? 石蓮闇詩作者，清末民初，誤標吳"),
    "榮光": (None, "garbage_clean:石雲山人詩集作者，晚清，誤標吳"),
    "吳均": (None, "garbage_clean:吳均(469-520)，南朝梁文學家，非三國吳，誤標吳，待南北朝拆分"),
    "沈顏": (None, "garbage_clean:沈顏，五代十國吳? 隋唐? 不在三國吳時段"),
    "悼濟": (None, "garbage_clean:悼濟撰萬機論，真實作者不詳，明顯非三國魏"),
    "伯陽": (None, "garbage_clean:伯陽=老子字? 太丹記/還丹歌，顯非三國魏"),
    "了翁": (None, "garbage_clean:了翁即陳瓘(1057-1124?)，北宋人，撰九經要義，非三國魏"),
    "鄭公": (None, "garbage_clean:鄭公=鄭玄? 類儀作者，鄭玄已是秦漢，此鄭公不清，但必非三國魏"),
    "武帝": (None, "garbage_clean:武帝=司馬炎? 太公隂謀作者，太公隂謀託太公，真實作者非魏"),
    "任毅": (None, "garbage_clean:任毅撰任子道論，不知何人，不在三國魏"),
    "賈思同": (None, "garbage_clean:賈思同(?-535)，北魏/東魏人，春秋傳駁，非三國魏，待北朝拆分"),
    "劉之": (None, "garbage_clean:人物志作者為劉邵(三國魏)，此劉之顯係錯錄"),
    "希言": (None, "garbage_clean:希言撰風論山兆經，不知名氏，不在三國吳"),
    "天尋": (None, "garbage_clean:天尋撰啓霸集，不知名氏，不在三國吳"),
    "之英": (None, "garbage_clean:之英撰儀禮奭固，晚清或託名，不在三國吳"),
    "忌十弓": (None, "garbage_clean:忌十弓撰瑞像歷年記，不知名氏"),
    "無滂": (None, "garbage_clean:無滂撰唐子，不知名氏，不在三國吳"),
    "張嚴": (None, "garbage_clean:張嚴撰制嘿記，不知名氏"),
    "昭素": (None, "garbage_clean:昭素撰太平乾元歷，太平興國為宋年號，不在三國吳"),
    "興莫君謨": (None, "garbage_clean:興莫君謨撰月河所聞，不知名氏"),
    "可幾": (None, "garbage_clean:可幾撰千姓編，不在三國吳"),
    "張翼": (None, "garbage_clean:張翼撰宰輔明鑑，明/清人，不在三國吳"),
    "良輔": (None, "garbage_clean:良輔撰方言釋音/樂書/詩樂說，非三國吳同名良輔"),
    "郡歸有光": (None, "garbage_clean:郡歸有光=歸有光(1506-1571)，明人，誤標吳"),
    "懋談": (None, "garbage_clean:懋談撰小學纂釋，不知名氏"),
    "䖏厚": (None, "garbage_clean:䖏厚撰靑箱雜記，不知名氏"),
    "越范贊時": (None, "garbage_clean:越范贊時撰資談，不知名氏"),
    "林鼎": (None, "garbage_clean:林鼎撰吳江應用集，五代/宋? 不在三國吳"),
    "楊氏": (None, "garbage_clean:楊氏撰唐吳英雋賦集，唐朝/五代，不在三國吳"),
}


# ========== Batch H: 別傳體裁的傳主詞典 ==========
# 利用前兩輪已分類的 Entity 名，對付 title=X別傳/X家傳/X傳 形式
# 直接用第二輪 EXTRA_HISTORICAL_FIGURES 加上已分類的 entity primary_name 做
BIO_DYNASTY_HINTS = {
    # 直接寫死一批（補晉志常見的別傳）
    "王濛": "東晉",  # 王濛(309-347)，字仲祖，東晉
    "王薈": "東晉",  # 王薈，東晉王導之子
    "范汪": "東晉",
    "范寧": "東晉",
    "王羲之": "東晉",
    "王獻之": "東晉",
    "庾亮": "東晉",
    "謝安": "東晉",
    "桓溫": "東晉",
    "顧愷之": "東晉",
    "戴逵": "東晉",
    "陶淵明": "東晉",
    "孫盛": "東晉",
    "干寶": "東晉",
    "習鑿齒": "東晉",
    "袁宏": "東晉",
    "郭璞": "東晉",
    "葛洪": "東晉",
    "謝玄": "東晉",
    "王導": "東晉",
    "王敦": "東晉",
    "卞壼": "東晉",
    "賀循": "東晉",
    "蔡謨": "東晉",
    "劉超": "東晉",
    "劉惔": "東晉",
    "王濛": "東晉",
    "王坦之": "東晉",
    "王彪之": "東晉",
    "王述": "東晉",
    "溫嶠": "東晉",
    "司馬道子": "東晉",
    "劉牢之": "東晉",
    "王蘊": "東晉",
    "王恭": "東晉",
    "謝萬": "東晉",
    "謝石": "東晉",
    "桓沖": "東晉",
    "庾冰": "東晉",
    "庾翼": "東晉",
    "謝混": "東晉",
    "桓玄": "東晉",
    "殷仲文": "東晉",
    "殷仲堪": "東晉",
    "劉毅": "東晉",
    "何無忌": "東晉",
    "劉穆之": "東晉",
    "王韶之": "東晉",
    "劉裕": "東晉",
    "傅亮": "東晉",  # 跨東晉末到宋，按主要活動
    # 西晉
    "羊祜": "西晉",
    "杜預": "西晉",
    "王濬": "西晉",
    "衛瓘": "西晉",
    "張華": "西晉",
    "陳壽": "西晉",
    "左思": "西晉",
    "潘岳": "西晉",
    "陸機": "西晉",
    "陸雲": "西晉",
    "裴秀": "西晉",
    "何劭": "西晉",
    "山濤": "西晉",
    "王戎": "西晉",
    "王衍": "西晉",
    "王濟": "西晉",
    "王渾": "西晉",
    "石崇": "西晉",
    "歐陽建": "西晉",
    "摯虞": "西晉",
    "司馬彪": "西晉",
    "傅玄": "西晉",
    "傅鹹": "西晉",
    "夏侯湛": "西晉",
    "孫楚": "西晉",
    "成公綏": "西晉",
    "皇甫謐": "西晉",
    "劉琨": "西晉",
    "盧諶": "西晉",
    "郭象": "西晉",
    "向秀": "西晉",
    "鄭沖": "西晉",
    "束皙": "西晉",
    "虞溥": "西晉",
    "胡奮": "西晉",
    "牽秀": "西晉",
    "曹攄": "西晉",
    "張載": "西晉",
    "張協": "西晉",
    "張亢": "西晉",
    "索靖": "西晉",
    "衛恆": "西晉",
    "杜錫": "西晉",
    "卞粹": "西晉",
    "劉頌": "西晉",
    "李重": "西晉",
    "劉實": "西晉",
    "劉宏": "西晉",
    "閻纘": "西晉",
    "董巴": "西晉",
    "虞聳": "西晉",
    "陳卓": "西晉",
    "魯勝": "西晉",
    "繆徵": "西晉",
    "李熹": "西晉",
    "庾峻": "西晉",
    "庾珉": "西晉",
    "庾敳": "西晉",
    "杜育": "西晉",
    "王接": "西晉",
    "張輔": "西晉",
    "崔豹": "西晉",
    "王愷": "西晉",
    "賈充": "西晉",
    "荀勗": "西晉",
    "華嶠": "西晉",
    "王沈": "西晉",  # 王沈(?-266)，魏末晉初，撰魏書
    "羊琇": "西晉",
    "楊駿": "西晉",
    "衛瓘": "西晉",
    # 三國
    "曹操": "三國魏",
    "曹丕": "三國魏",
    "曹植": "三國魏",
    "阮籍": "三國魏",
    "嵇康": "三國魏",
    "鍾會": "三國魏",
    "鄧艾": "三國魏",
    "王弼": "三國魏",
    "何晏": "三國魏",
    "夏侯玄": "三國魏",
    "司馬懿": "三國魏",
    "司馬師": "三國魏",
    "司馬昭": "三國魏",
    "諸葛亮": "三國蜀",
    "關羽": "三國蜀",
    "張飛": "三國蜀",
    "劉備": "三國蜀",
    "譙周": "三國蜀",
    "孫權": "三國吳",
    "孫策": "三國吳",
    "周瑜": "三國吳",
    "魯肅": "三國吳",
    "陸遜": "三國吳",
    "韋昭": "三國吳",
    "陸績": "三國吳",
}


def dynasty_from_biography_title(title: str) -> tuple[str | None, str | None]:
    """X別傳 / X家傳 / X傳 → 查 BIO_DYNASTY_HINTS"""
    for name, dyn in BIO_DYNASTY_HINTS.items():
        # 比對 "X別傳" "X家傳" "X傳"
        if title.endswith(f"{name}別傳") or title.endswith(f"{name}家傳") or title.endswith(f"{name}傳"):
            return dyn, f"biography_subject:{name}→{dyn}"
        # 偶爾是 "X别傳" 简体
        if title.endswith(f"{name}别傳"):
            return dyn, f"biography_subject:{name}→{dyn}"
    return None, None


def has_sanguo_zhiyuan(indexed_by):
    for item in indexed_by:
        if isinstance(item, dict):
            src = str(item.get("source", ""))
            if "三國" in src and "藝文" in src:
                return True
    return False


def only_mingqing_sources(indexed_by):
    """只被明/清志著錄（未被隋志/唐志/宋志/三國志著錄）"""
    MQ = {"清史稿藝文志", "續修四庫全書", "國史經籍志", "書目答問",
          "欽定四庫全書總目", "四庫全書總目", "經義考", "續文獻通考"}
    if not indexed_by:
        return False  # 沒來源 -> 不確定
    all_sources = set()
    for item in indexed_by:
        if isinstance(item, dict):
            all_sources.add(item.get("source", ""))
    # 若有非明清志的來源，不清理
    NON_MQ = {"隋書經籍志", "舊唐書經籍志", "新唐書藝文志", "宋史藝文志",
              "崇文總目", "直齋書錄解題", "三國藝文志", "後漢藝文志",
              "漢書藝文志", "補晋書藝文志", "補三國藝文志",
              "文獻通考", "玉海"}
    if any(s in all_sources for s in NON_MQ):
        return False
    # 全部來源都在 MQ 裡
    return bool(all_sources) and all(s in MQ for s in all_sources)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    commit = args.commit or not args.dry_run

    stats = Counter()

    print("載入 Work / Entity ...")
    works = {}
    work_paths = {}
    for fp in iter_work_files():
        d = json.loads(fp.read_text(encoding="utf-8"))
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
    print(f"  Work: {len(works)}, Entity: {len(entities)}")

    # ========== Batch F: Work.title 關鍵詞 ==========
    print("\n=== Batch F: Work.title 關鍵詞 ===")
    for wid, w in works.items():
        title = w.get("title", "") or ""
        per = w.get("period")
        if per not in ("jin", "three-kingdoms"):
            continue

        dyn1, basis1 = dynasty_from_work_title(title)
        dyn2, basis2 = dynasty_from_biography_title(title)
        new_dyn = dyn1 or dyn2
        basis = basis1 or basis2
        if not new_dyn:
            continue

        changed = False
        # work.top
        if w.get("dynasty") in ("晉", "三國", None) and w.get("dynasty") != new_dyn:
            old = w.get("dynasty")
            w["dynasty"] = new_dyn
            w["dynasty_basis"] = basis
            w["updated_at"] = now_iso()
            stats[f"F.work.top.{old}→{new_dyn}"] += 1
            changed = True
        # authors（僅西晉/東晉/三國魏 推斷作者朝代，因 title 是作品朝代）
        for a in w.get("authors", []) or []:
            if not isinstance(a, dict):
                continue
            adyn = a.get("dynasty")
            if adyn in ("晉", "魏", "三國") and adyn != new_dyn:
                # 如果是"魏"只有推到三國魏才合理
                if adyn == "魏" and new_dyn == "三國魏":
                    a["dynasty"] = new_dyn
                    a["dynasty_basis"] = basis
                    stats[f"F.author.魏→三國魏"] += 1
                    changed = True
                elif adyn == "晉" and new_dyn in ("西晉", "東晉"):
                    a["dynasty"] = new_dyn
                    a["dynasty_basis"] = basis
                    stats[f"F.author.晉→{new_dyn}"] += 1
                    changed = True
        if changed and "updated_at" not in w:
            w["updated_at"] = now_iso()

    # ========== Batch G1: 魏/吳作者已知誤標詞典 ==========
    # 僅處理：原本 dynasty 就在 {魏,吳,None,晉,三國,北宋,南宋,宋,元,明,清,梁,金,北魏,東漢,漢} 中的
    # 但 漢/東漢 跳過（那是秦漢進程的領域，三國人物不必都改）
    # 宋/元/明/清/梁/金/北魏 → None 是垃圾清理，可以改
    # None/魏/吳 → 具體朝代 是糾正，可以改
    # 西晉 → 三國魏 是更精細，可以改（阮籍歸三國魏更精準但有爭議，保留此改）
    SKIP_G1_ORIGIN = {"漢", "東漢"}
    print("\n=== Batch G1: 魏/吳作者誤標詞典 ===")
    for wid, w in works.items():
        changed = False
        for a in w.get("authors", []) or []:
            if not isinstance(a, dict):
                continue
            name = a.get("name", "")
            if name not in WEI_WU_CORRECTIONS:
                continue
            old_dyn = a.get("dynasty")
            if old_dyn in SKIP_G1_ORIGIN:
                continue
            new_dyn, note = WEI_WU_CORRECTIONS[name]
            if old_dyn == new_dyn:
                continue
            a["dynasty"] = new_dyn
            a["dynasty_basis"] = f"known_mislabel:round3({note})"
            stats[f"G1.author.{old_dyn}→{new_dyn}"] += 1
            changed = True
        if changed:
            w["updated_at"] = now_iso()

    # 同樣處理 Entity（魏/吳 未解的 entity 也掃一遍）
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn not in ("魏", "吳"):
            continue
        name = e.get("primary_name", "")
        if name in WEI_WU_CORRECTIONS:
            new_dyn, note = WEI_WU_CORRECTIONS[name]
            if new_dyn != dyn:
                e["dynasty"] = new_dyn
                e["dynasty_basis"] = f"known_mislabel:round3({note})"
                e["updated_at"] = now_iso()
                stats[f"G1.entity.{dyn}→{new_dyn}"] += 1

    # ========== Batch G2: 魏/吳作者只被明清志著錄 → null ==========
    print("\n=== Batch G2: 魏/吳作者只被明清志著錄 → null ===")
    for wid, w in works.items():
        changed = False
        ib = w.get("indexed_by", []) or []
        only_mq = only_mingqing_sources(ib)
        for a in w.get("authors", []) or []:
            if not isinstance(a, dict):
                continue
            if a.get("dynasty") not in ("魏", "吳"):
                continue
            name = a.get("name", "")
            # 詞典已處理的跳過
            if name in WEI_WU_CORRECTIONS:
                continue
            # 被三國志著錄的不能清
            if has_sanguo_zhiyuan(ib):
                continue
            # 只被明清志/完全無來源 → 清理
            if only_mq or not ib:
                # 再保護：如果 work.period=three-kingdoms，不能清
                if w.get("period") == "three-kingdoms":
                    continue
                old = a.get("dynasty")
                a["dynasty"] = None
                a["dynasty_basis"] = f"garbage_clean:only_mingqing_sources_or_none"
                stats[f"G2.author.{old}→null"] += 1
                changed = True
        if changed:
            w["updated_at"] = now_iso()

    # ========== Batch H: 傳主詞典 → 傳播到 Entity (primary_name) ==========
    print("\n=== Batch H: 別傳傳主詞典 → Entity 傳播 ===")
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn not in ("晉", "魏", "吳", "三國"):
            continue
        name = e.get("primary_name", "")
        if name in BIO_DYNASTY_HINTS:
            new_dyn = BIO_DYNASTY_HINTS[name]
            if new_dyn != dyn:
                e["dynasty"] = new_dyn
                e["dynasty_basis"] = f"biography_dict:round3:{name}→{new_dyn}"
                e["updated_at"] = now_iso()
                stats[f"H.entity.{dyn}→{new_dyn}"] += 1

    # ========== Batch I: 再一輪 Entity↔Author 傳播 ==========
    print("\n=== Batch I: Entity↔Author 雙向傳播 v3 ===")
    # Ia: Entity→Author
    entity_dyn_map = {}
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn in ("三國魏", "三國蜀", "三國吳", "西晉", "東晉"):
            entity_dyn_map[eid] = dyn
    for wid, w in works.items():
        changed = False
        for a in w.get("authors", []) or []:
            if not isinstance(a, dict):
                continue
            dyn = a.get("dynasty")
            if dyn not in ("晉", "魏", "吳", "三國"):
                continue
            eid = a.get("entity_id")
            if eid and eid in entity_dyn_map:
                new_dyn = entity_dyn_map[eid]
                if new_dyn != dyn:
                    a["dynasty"] = new_dyn
                    a["dynasty_basis"] = f"entity_propagation:round3:{eid}"
                    stats[f"Ia.author.{dyn}→{new_dyn}"] += 1
                    changed = True
        if changed:
            w["updated_at"] = now_iso()
    # Ib: Author→Entity
    author_name_dyn = defaultdict(set)
    for wid, w in works.items():
        for a in w.get("authors", []) or []:
            if isinstance(a, dict):
                dyn = a.get("dynasty")
                if dyn in ("三國魏", "三國蜀", "三國吳", "西晉", "東晉"):
                    author_name_dyn[a.get("name", "")].add(dyn)
    for eid, e in entities.items():
        dyn = e.get("dynasty")
        if dyn not in ("晉", "魏", "吳", "三國"):
            continue
        name = e.get("primary_name", "")
        if name in author_name_dyn:
            c = author_name_dyn[name]
            if len(c) == 1:
                new_dyn = c.pop()
                if new_dyn != dyn:
                    e["dynasty"] = new_dyn
                    e["dynasty_basis"] = "author_propagation:round3"
                    e["updated_at"] = now_iso()
                    stats[f"Ib.entity.{dyn}→{new_dyn}"] += 1

    # ========== 寫入 ==========
    if commit:
        print("\n寫入 Work ...")
        for wid, w in works.items():
            fp = work_paths[wid]
            fp.write_text(json.dumps(w, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("寫入 Entity ...")
        for eid, e in entities.items():
            fp = entity_paths[eid]
            fp.write_text(json.dumps(e, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # ========== 報告 ==========
    print("\n=== 統計 ===")
    for k, v in sorted(stats.items()):
        print(f"  {k:60s} {v:>6}")

    remaining = Counter()
    for e in entities.values():
        dyn = e.get("dynasty")
        if dyn in ("晉", "魏", "吳", "三國"):
            remaining[f"entity.{dyn}"] += 1
    for w in works.values():
        for a in w.get("authors", []) or []:
            if isinstance(a, dict):
                dyn = a.get("dynasty")
                if dyn in ("晉", "魏", "吳", "三國"):
                    remaining[f"author.{dyn}"] += 1
    print(f"\n=== 剩餘未解 ===")
    for k, v in sorted(remaining.items()):
        print(f"  {k:30s} {v:>6}")


if __name__ == "__main__":
    main()
