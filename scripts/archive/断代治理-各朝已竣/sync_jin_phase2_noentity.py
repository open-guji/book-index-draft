#!/usr/bin/env python3
"""晉朝探勘分期第二階段：期jin範圍內73條「dynasty籠統『晉』且無
entity_id」批次。

兩類處理：
  A. LINK_MAP——作者名與本輪／先前各階段已判定西晉／東晉之既有
     Entity同名同人（如徐邈六條「X氏音」皆與其東晉音義注疏之學術
     形象吻合），逕補entity_id並同步dynasty。
  B. DIRECT_CLASSIFICATIONS——尚無Entity，以史實直接訂正
     authors[0].dynasty，不建立/繫連entity_id。

存疑者（劉昞疑為北涼人、蘇蕙疑為前秦人、孔曄/顧微/伏琛/封懿等年代
或政權歸屬不確、殘名如「[某]」「王[某]」「謝[某]」「未詳」「氏」
等資料本身殘缺）一律不列，寧缺不錯。
"""
import json
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

LINK_MAP = {
    "徐邈": ("1j96hl473bf9c", "東晉"),
    "范甯": ("1j96ob0byktmo", "東晉"),
    "楊方": ("1j967cp1zdr2i", "東晉"),
    "劉智": ("1j96h8rw86q2s", "晉"),
    "范宣": ("1j96hfbg5o4cg", "東晉"),
}

DIRECT_CLASSIFICATIONS = {
    "李軌": ("東晉", "注莊子/法言之東晉學者"),
    "虞喜": ("東晉", "281-356，天文學家，發現歲差"),
    "嵇喜": ("西晉", "嵇康之兄，仕晉為秀才"),
    "嵇含": ("西晉", "263-306，嵇康之侄孫，撰南方草木狀"),
    "釋支遁": ("東晉", "314-366，高僧"),
    "郗鑒": ("東晉", "269-339"),
    "何琦": ("東晉", "撰三國評"),
    "司馬昱": ("東晉", "320-372，簡文帝"),
    "嵇紹": ("西晉", "253-304，嵇康之子，死於蕩陰之戰"),
    "顧凱之": ("東晉", "顧愷之，348-409，畫家"),
    "欒肇": ("西晉", "注論語"),
    "范堅": ("東晉", "范甯之兄"),
    "庾肅之": ("東晉", "庾亮家族"),
    "綦毋邃": ("東晉", "注列子"),
    "繆協": ("東晉", "注穆天子傳"),
    "釋道安": ("東晉", "312-385，高僧"),
    "袁喬": ("東晉", "?-347，桓溫伐蜀主要謀士"),
    "袁山崧": ("東晉", "?-401，撰後漢書"),
    "華譚": ("西晉", "?-322，廣陵人"),
    "王愆期": ("東晉", "注莊子"),
    "鄒湛": ("西晉", "?-297"),
    "釋慧遠": ("東晉", "334-416，高僧"),
    "郗超": ("東晉", "336-378"),
    "庾倩": ("東晉", "庾希之弟"),
    "江熙": ("東晉", "注論語"),
    "王廙": ("東晉", "276-322，王導從弟"),
}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, data, indent=2):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
        f.write("\n")


def get_indent(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    lines = raw.split("\n")
    if len(lines) > 1:
        cand = len(lines[1]) - len(lines[1].lstrip(" "))
        if cand > 0:
            return cand
    return 2


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

    for wid, path in widx.items():
        try:
            j = load(path)
        except Exception:
            continue
        if j.get("period") != "jin":
            continue
        a = j.get("authors")
        if not a or a[0].get("dynasty") != "晉" or a[0].get("entity_id"):
            continue
        name = a[0].get("name")

        if name in LINK_MAP:
            eid, dyn = LINK_MAP[name]
            a[0]["entity_id"] = eid
            a[0]["dynasty"] = dyn
            if j.get("dynasty") == "晉":
                j["dynasty"] = dyn
            j["period_basis"] = f"據 authors[0].dynasty「{dyn}」（原缺entity_id，2026-08-11 晉朝探勘分期第二階段補繫並訂正）"
            save(path, j, get_indent(path))
            linked += 1
        elif name in DIRECT_CLASSIFICATIONS:
            dyn, basis = DIRECT_CLASSIFICATIONS[name]
            a[0]["dynasty"] = dyn
            if j.get("dynasty") == "晉":
                j["dynasty"] = dyn
            j["period_basis"] = f"據 authors[0].dynasty「{dyn}」（原作籠統「晉」，2026-08-11 晉朝探勘分期第二階段訂正：{basis}）"
            save(path, j, get_indent(path))
            direct += 1

    print(f"linked: {linked}, direct: {direct}")


if __name__ == "__main__":
    main()
