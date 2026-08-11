#!/usr/bin/env python3
"""西漢探勘分期第三階段：264條「無 entity_id」批次中 191 條具名作品
（扣除 73 條佚名，留待第四階段）。

兩種處理方式：
  A. LINK_MAP——作者名於庫中已有唯一且明確之西漢／東漢 Entity（多為
     階段一、二或原始 90 組已核校者），逕補 entity_id 並同步 dynasty。
  B. DIRECT_CLASSIFICATIONS——作者名於庫中尚無 Entity（或有多個同名
     Entity 而未能唯一判定），僅以史實直接訂正 Work.authors[0].
     dynasty，不建立或繫連 entity_id（entity 繫連留待日後）。

異體題名（如「鄭康成」即「鄭玄」字、「楊雄」即「揚雄」異寫、「鼂錯」
即「晁錯」異體、「吾邱壽王」即「吾丘壽王」異寫、「趙歧」即「趙岐」
異體）一併納入 VARIANT_MAP 正規化後套用。
"""
import json
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

VARIANT_MAP = {
    "鄭康成": "鄭玄",
    "楊雄": "揚雄",
    "鼂錯": "晁錯",
    "吾邱壽王": "吾丘壽王",
    "趙歧": "趙岐",
    "許愼撰": "許慎",
}

LINK_MAP = {
    "鄭玄": ("1j9678njjg2rr", "東漢"),
    "劉向": ("1j9678njjg2rq", "西漢"),
    "何休": ("1j96a9e1uacqo", "東漢"),
    "賈逵": ("1j96h8rw7vhhj", "東漢"),
    "董仲舒": ("1j967a0kj9gyh", "西漢"),
    "許慎": ("1j967avzlcjyi", "東漢"),
    "班固": ("1j967afjb6ae0", "東漢"),
    "孔安國": ("1j967a0kj9gzv", "西漢"),
    "蔡邕": ("1j9678njjrbcf", "東漢"),
    "賈誼": ("1j967bgl5rlz6", "西漢"),
    "應劭": ("1j967bgl6pbns", "東漢"),
    "京房": ("1j9678gg70hta", "西漢"),
    "揚雄": ("1j968k0jdrlz6", "西漢"),
    "荀爽": ("1j967afjav1vx", "東漢"),
    "衛宏": ("1j96ad662wp34", "東漢"),
    "徐幹": ("1j96h8rw7k8xg", "東漢"),
    "眭弘": ("1j96hexw1mww0", "西漢"),
    "郭舍人": ("1j96heaw6ewao", "西漢"),
    "嚴彭祖": ("1j967a0kj9gyi", "西漢"),
    "王充": ("1j96kef6x6z9c", "東漢"),
    "戴聖": ("1j967cp1zdr1y", "西漢"),
    "韓嬰": ("1j96a9e52emtc", "西漢"),
    "宋衷": ("1j96a9e4508ow", "東漢"),
    "延篤": ("1j967cp1zdr2u", "東漢"),
    "毛萇": ("1j96ha6ne3myo", "西漢"),
    "崔寔": ("1j967cp1zdr2w", "東漢"),
    "荀悅": ("1j96ha5ms7pj4", "東漢"),
    "劉歆": ("1j967a0kj9gy0", "西漢"),
    "薛漢": ("1j9678njjg2sv", "東漢"),
    "王符": ("1j96hl9dzno5c", "東漢"),
    "公孫弘": ("1j967cp1zdr1i", "西漢"),
    "鄭興": ("1j9678njjrbbl", "東漢"),
    "劉熙": ("1j96hllpzsoao", "東漢"),
    "黃憲": ("1j96hjwlxny1c", "東漢"),
    "杜子春": ("1j96heahhbnk0", "東漢"),
    "孟喜": ("1j96hlegg6eww", "西漢"),
    "李巡": ("1j967cp1zozk1", "東漢"),
    "服虔": ("1j96a9e2atxj4", "東漢"),
    "河上公": ("1j96a9e6few3k", "西漢"),
    "趙岐": ("1j96hl7dua03k", "東漢"),
    "氾勝之": ("1j96hf14ieha8", "西漢"),
    "郗萌": ("1j96hfajqjta8", "東漢"),
    "施讎": ("1j9678gg70ht9", "西漢"),
    "費直": ("1j96afen00wlc", "西漢"),
    "趙曄": ("1j96hllm6g9a8", "東漢"),
    "戴德": ("1j96hl6izcetc", "西漢"),
    "王隆": ("1j96hhvcrjvhu", "東漢"),
    "王逸": ("1j96h8rw7k8wc", "東漢"),
    "程曾": ("1j96hf8xgalts", "東漢"),
    "梁丘賀": ("1j96ha470oykg", "西漢"),
    "盧植": ("1j9678njjrbcc", "東漢"),
    "嚴遵": ("1j967bgl7y9tc", "西漢"),
    "劉表": ("1j96hl3yk5wqo", "東漢"),
    "伏勝": ("1j967afjbsrjd", "西漢"),
}

DIRECT_CLASSIFICATIONS = {
    "鄭衆": ("東漢", "鄭眾，?-83，東漢經學家（與宦官鄭眾同名異人，然本庫著作皆經學著作）"),
    "趙君卿": ("東漢", "趙爽，字君卿，東漢末數學家，注周髀算經"),
    "包鹹": ("東漢", "6BC-65CE，東漢經學家，注論語"),
    "袁康": ("東漢", "撰越絕書，東漢人"),
    "魯恭": ("東漢", "32-112，東漢名臣"),
    "彭宣": ("西漢", "?-4CE，西漢成帝時丞相"),
    "嚴安": ("西漢", "武帝時人"),
    "侯苞": ("西漢", "撰韓詩翼要，西漢人"),
    "嚴助": ("西漢", "莊助，?-前122"),
    "犍為文學": ("西漢", "犍為郡文學掾，西漢爾雅注家（傳統託名）"),
    "貢禹": ("西漢", "前124-前44"),
    "許負": ("西漢", "高祖時相術家"),
}

SKIP_UNCERTAIN = {
    "崔篆",  # 新／東漢過渡，庫中既有記錄作「新」，不強行二分
    "張魯",  # 漢魏之際，個案已另行處理
    "趙溫",  # 東漢末人，待個別覈實
    "樊光",  # Entity 記錄疑誤（見前輪發現），不逕自訂正
    "孫氏", "鄭氏", "鄒氏",  # 泛稱姓氏，非確指
    "臣賢", "說", "義", "彭", "海鄭康成", "南以前所",  # 疑資料訛誤／殘缺
    "蔡景君", "劉蒼", "蔡葵", "趙壹", "麻達", "張升", "陽成子長",
    "夾氏", "許淑", "毛亨傳", "段肅", "宋哀", "甘容", "鄭玄，[唐]賈公彥",
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

    linked = 0
    direct = 0
    skipped_names = set()

    for wid, path in widx.items():
        try:
            j = load(path)
        except Exception:
            continue
        if j.get("period") != "qin-han":
            continue
        a = j.get("authors")
        if not a or a[0].get("dynasty") != "漢" or a[0].get("entity_id"):
            continue
        name = a[0].get("name")
        if name == "佚名":
            continue
        canon = VARIANT_MAP.get(name, name)

        if canon in LINK_MAP:
            eid, dyn = LINK_MAP[canon]
            a[0]["entity_id"] = eid
            a[0]["dynasty"] = dyn
            j["period_basis"] = f"據 authors[0].dynasty「{dyn}」（原作籠統「漢」且無 entity_id，2026-08-11 西漢探勘分期第三階段補繫並訂正）"
            save(path, j)
            linked += 1
        elif canon in DIRECT_CLASSIFICATIONS:
            dyn, basis = DIRECT_CLASSIFICATIONS[canon]
            a[0]["dynasty"] = dyn
            j["period_basis"] = f"據 authors[0].dynasty「{dyn}」（原作籠統「漢」，2026-08-11 西漢探勘分期第三階段訂正：{basis}）"
            save(path, j)
            direct += 1
        elif canon in SKIP_UNCERTAIN:
            continue
        else:
            skipped_names.add(name)

    print(f"linked (entity_id補繫+dynasty同步): {linked}")
    print(f"direct (僅dynasty訂正): {direct}")
    print(f"unclassified names encountered: {sorted(skipped_names)}")


if __name__ == "__main__":
    main()
