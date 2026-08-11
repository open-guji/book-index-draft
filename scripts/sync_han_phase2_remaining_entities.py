#!/usr/bin/env python3
"""西漢探勘分期第二階段：382條批次中出現頻次較低（1-3條）之剩餘人物，
逐位以生卒年／仕歷核校後分類。僅收錄有把握者，存疑之孤僻人名一律
不列（寧缺不錯，留待日後個別考訂）。

另收錄二個斷代邊界之獨立修正（非西漢／東漢二分可涵蓋）：
  - 項籍（項羽，前232-前202）——楚漢相爭時西楚霸王，未曾為漢臣，
    卒於漢朝建立同年，dynasty「漢」不確，訂正為「秦」（比照孔鮒之
    處理原則：楚漢之際、未及正式仕漢者，歸秦漢之際的「秦」端）。
  - 陳餘（?-前204）——楚漢相爭時趙王，早於漢朝建立而卒，同上理由
    訂正為「秦」。
"""
import json
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

CLASSIFICATIONS = {
    "劉安": ("西漢", "淮南王，前179-前122"),
    "許慎": ("東漢", "58-147，說文解字作者"),
    "朱建": ("西漢", "?-前177，高祖時人"),
    "歐陽高": ("西漢", "今文尚書歐陽學傳人"),
    "路溫舒": ("西漢", "宣帝時人"),
    "毛萇": ("西漢", "毛詩傳承者"),
    "夏侯建": ("西漢", "今文尚書夏侯學，宣帝時人"),
    "劉敬": ("西漢", "婁敬，高祖時人"),
    "淮南王劉安": ("西漢", "前179-前122"),
    "劉奭": ("西漢", "漢元帝，前74-前33"),
    "孔臧": ("西漢", "武帝時人，孔子後裔"),
    "莊助": ("西漢", "嚴助，?-前122"),
    "終軍": ("西漢", "?-前112"),
    "戴德": ("西漢", "大戴，禮學家"),
    "李陵": ("西漢", "?-前74"),
    "公羊壽": ("西漢", "公羊學傳人"),
    "顏安樂": ("西漢", "宣帝時穀梁學者"),
    "申培": ("西漢", "魯詩傳人"),
    "焦延壽": ("西漢", "京房之師"),
    "桓寬": ("西漢", "鹽鐵論編者，宣帝時人"),
    "伏生": ("西漢", "秦博士，傳尚書於漢初"),
    "主父偃": ("西漢", "?-前126"),
    "歐陽生": ("西漢", "今文尚書歐陽學始祖"),
    "郭顯卿": ("東漢", "字書學者"),
    "唐蒙": ("西漢", "武帝時通西南夷使者"),
    "侯應": ("西漢", "元帝時匈奴事務官員"),
    "蔡癸": ("西漢", "武帝時農官"),
    "王符": ("東漢", "78-163，政論家"),
    "虞丘說": ("西漢", "武帝時人"),
    "司馬談": ("西漢", "?-前110，司馬遷之父"),
    "馮商": ("西漢", "元成間人"),
    "江翁": ("西漢", "今文尚書學者"),
    "京房": ("西漢", "前77-前37"),
    "黃憲": ("東漢", "109-156，名士"),
    "嚴君平": ("西漢", "嚴遵，著老子指歸"),
    "周王孫": ("西漢", "詩經注家"),
    "翼奉": ("西漢", "元帝時人"),
    "尹更始": ("西漢", "宣帝時人"),
    "張蒼": ("西漢", "前256-前152，丞相"),
    "申培公": ("西漢", "同申培"),
    "許商": ("西漢", "成帝時人"),
    "氾勝之": ("西漢", "前32-前7，農學家"),
    "楊何": ("西漢", "武帝時易學傳人"),
    "宋忠": ("東漢", "宋衷"),
    "賈讓": ("西漢", "前7年前後人"),
    "叔孫通": ("西漢", "高祖時人"),
    "郭舍人": ("西漢", "武帝時人，注爾雅"),
    "丁寬": ("西漢", "易學傳人"),
    "楊惲": ("西漢", "?-前54"),
    "史游": ("西漢", "前48-前33，急就篇作者"),
    "梁丘賀": ("西漢", "宣帝時易學傳人"),
    "公孫弘": ("西漢", "前200-前121"),
    "莊忌": ("西漢", "嚴忌，景帝時辭賦家"),
    "谷永": ("西漢", "?-前8"),
    "王商": ("西漢", "?-前25，丞相"),
    "五鹿充宗": ("西漢", "元帝時人"),
    "仲長": ("東漢", "仲長統，180-220"),
    "氾勝": ("西漢", "同氾勝之"),
    "徐樂": ("西漢", "前130年前後人"),
    "眭弘": ("西漢", "?-前78"),
    "魏朗": ("東漢", "?-158"),
    "賈捐之": ("西漢", "前47年前後人"),
    "班婕妤": ("西漢", "前48-前2"),
    "卜式": ("西漢", "前120年前後人"),
    "劉辟強": ("西漢", "楚元王後裔，劉向從兄"),
    "亰房": ("西漢", "京房異寫"),
    "阮瑀": ("東漢", "165-212"),
    "李息": ("西漢", "武帝時將領"),
    "枚皋": ("西漢", "枚乘之子"),
    "李巡": ("東漢", "爾雅注家"),
    "馬援": ("東漢", "前14-49，光武帝時名將"),
    "耿育": ("西漢", "成帝時人"),
    "王延壽": ("東漢", "163年前後人"),
}

# 需個別處理者：(id 或 name+entity_id, 訂正朝代, 理由)
SPECIAL_CASES_BY_NAME = {
    "項籍": ("秦", "項羽（前232-前202），楚漢相爭時西楚霸王，未曾仕漢，卒於漢朝建立同年"),
    "陳余": ("秦", "陳餘（?-前204），楚漢相爭時趙王，早於漢朝建立而卒"),
}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, data, indent=2):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
        f.write("\n")


def build_work_index():
    idx = {}
    for s in SHARDS:
        d = load(ROOT / "index" / "works" / f"{s}.json")
        for wid, entry in d.items():
            idx[wid] = ROOT / entry["path"]
    return idx


def main():
    widx = build_work_index()

    ent_by_id = {}
    for f in glob.glob(str(ROOT / "Entity" / "**" / "*.json"), recursive=True):
        try:
            j = load(Path(f))
        except Exception:
            continue
        eid = j.get("id")
        if eid:
            ent_by_id[eid] = Path(f)

    all_classifications = dict(CLASSIFICATIONS)
    all_classifications.update(SPECIAL_CASES_BY_NAME)

    fixed_entities = set()
    fixed_works = 0
    unmatched_names = set()

    for wid, path in widx.items():
        try:
            j = load(path)
        except Exception:
            continue
        if j.get("period") != "qin-han":
            continue
        a = j.get("authors")
        if not a or a[0].get("dynasty") != "漢":
            continue
        name = a[0].get("name")
        eid = a[0].get("entity_id")
        if not eid or name not in all_classifications:
            continue

        target_dyn, basis = all_classifications[name]
        a[0]["dynasty"] = target_dyn
        j["period_basis"] = f"據 authors[0].dynasty「{target_dyn}」（原作籠統「漢」，2026-08-11 西漢探勘分期第二階段訂正：{basis}）"
        save(path, j)
        fixed_works += 1

        if eid in ent_by_id and eid not in fixed_entities:
            ent = load(ent_by_id[eid])
            if ent.get("dynasty") in (None, "漢", "秦漢"):
                ent["dynasty"] = target_dyn
                ent["period"] = "qin-han"
                ent["period_basis"] = f"據 dynasty「{target_dyn}」（原作籠統，2026-08-11 西漢探勘分期第二階段訂正：{basis}）"
                save(ent_by_id[eid], ent)
                fixed_entities.add(eid)

    print(f"fixed works: {fixed_works}, fixed entities: {len(fixed_entities)}")


if __name__ == "__main__":
    main()
