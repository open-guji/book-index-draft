#!/usr/bin/env python3
"""西漢範圍探勘時發現之若干「漢」朝代誤標／實體分裂問題，逐條修正。

本庫對漢代著作絕大多數僅籠統標作「漢」（942條）或「東漢」（483條），
極少數才細分「西漢」（5條）——這本身即是西漢／東漢範圍界定工作的
結構性障礙。逐條核查時，另外查出五個獨立問題，與斷代粒度無關，逕行
修正：

  1. 賈逵三方分裂——東漢經學家賈逵（30-101，以《左傳》《國語》學名
     家）之著作，因 CBDB 自動比對錯誤，分裂繫連於三個 Entity：
     1j96h8rw7vhhj（賈逵，dynasty=漢，6作品，此前已自行卸除誤繫之
     「宋賈逵」CBDB配對）、1j96heyk37z7k（漢侍中賈逵，dynasty缺，1
     作品）、1j969m70q2eqt（賈逵，dynasty=三國魏，16作品——其自身
     cbdb_source 欄位明言比對候選為「东汉贾逵」，然 dynasty 卻誤填
     「三國魏」，自相矛盾）。核對三方 23 部作品書目（皆《左氏》
     《國語》《毛詩》《周禮》《尚書》經學撰著），確認同屬一人，逕予
     合併為 1j96h8rw7vhhj（dynasty 訂正為「東漢」，與絕大多數作品
     Work 層級之既有標記一致）。

  2. 漢高祖實録（1evgphixio45c，蘇逢吉撰）——蘇逢吉為五代後漢（劉知
     遠）宰相，非西漢高祖劉邦時人；《國史經籍志》著錄語「漢蘇逢吉」
     之「漢」指五代後漢，非秦漢之漢，逕予訂正 dynasty／period。

  3. 𣈆高祖實錄（1evgphisnjzeo，竇貞固撰）——竇貞固亦五代後漢／後周
     宰相，本書题即作「𣈆（晉）高祖實錄」（記後晉高祖石敬瑭事），與
     漢代無涉，dynasty「漢」純屬誤植，逕予訂正。

  4. 喪服經傳王氏注（1ewsa49t4pru0，王肅撰）——王肅（195-256）為三
     國曹魏經學家，非漢人，dynasty「漢」誤植，逕予訂正。

  5. 十一家注孫子（1evjr3jstkwzk）——原 authors 作「曹操唐杜牧」，
     將漢魏之際曹操與唐代杜牧二人姓名／朝代誤合為一條，且未反映
     「等」所示尚有多位未具名注家（十一家注實為宋吉天保所輯，凡
     曹操、李筌、杜牧、陳皥、賈林、孟氏、梅堯臣、王晳、何延錫、
     張預、杜佑十一家）。逕改 authors 為吉天保（宋，輯），並於
     ai_note 說明原始十一家名單。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, data, indent=2):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
        f.write("\n")


def shard_of(id_str, n=16):
    h = 0
    for c in id_str:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return h % n


def build_work_index():
    idx = {}
    for s in SHARDS:
        d = load(ROOT / "index" / "works" / f"{s}.json")
        for wid, entry in d.items():
            idx[wid] = ROOT / entry["path"]
    return idx


def fix_jiakui_entity_split(widx):
    BASE = "1j96h8rw7vhhj"
    DONORS = ["1j969m70q2eqt", "1j96heyk37z7k"]

    base_p = ROOT / "Entity/1/j/9/1j96h8rw7vhhj-賈逵.json"
    base = load(base_p)
    base_works = {w["work_id"]: w for w in base.get("works", [])}

    for did in DONORS:
        shard = shard_of(did)
        ent_files = list((ROOT / "Entity").rglob(f"{did}-*.json"))
        donor_p = ent_files[0]
        donor = load(donor_p)
        for w in donor.get("works", []):
            base_works.setdefault(w["work_id"], w)
        donor_p.unlink()
        idxp = ROOT / "index" / "entities" / f"{shard:x}.json"
        d = load(idxp)
        if did in d:
            del d[did]
            save(idxp, d, indent=1)

    base["works"] = list(base_works.values())
    base["dynasty"] = "東漢"
    base["period"] = "qin-han"
    base["period_basis"] = "據 dynasty「東漢」"
    base["ai_note"] = base.get("ai_note", "") + (
        " 2026-08-11：西漢範圍探勘時發現本人物於庫中另分裂為二 Entity——"
        "1j969m70q2eqt（賈逵，dynasty 誤填「三國魏」，然其自身 cbdb_source"
        "欄位明言比對候選為「东汉贾逵」，自相矛盾；16部作品書目《左氏》"
        "《國語》《毛詩》《周禮》《尚書》皆經學撰著，確與本條同屬一人）、"
        "1j96heyk37z7k（漢侍中賈逵，dynasty缺，1作品）。三方 23 部作品"
        "書目核對確認同屬東漢經學家賈逵（30-101），今併為一。dynasty 由"
        "「漢」訂正為「東漢」，與絕大多數作品 Work 層級之既有標記一致。"
    )
    save(base_p, base)

    for wid in base_works:
        p = widx[wid]
        d = load(p)
        changed = False
        for a in d.get("authors", []):
            if a.get("name") == "賈逵" and a.get("entity_id") in DONORS:
                a["entity_id"] = BASE
                changed = True
        if changed:
            save(p, d)


def fix_wudai_mislabeled_han(widx):
    fixes = [
        ("1evgphixio45c", "後漢", "後漢蘇逢吉，非西漢高祖劉邦時人"),
        ("1evgphisnjzeo", "後漢", "後晉／後漢竇貞固，本書記後晉高祖石敬瑭事，與漢代無涉"),
    ]
    for wid, dynasty, note in fixes:
        p = widx[wid]
        d = load(p)
        d["authors"][0]["dynasty"] = dynasty
        d["period"] = "five-dynasties"
        d["period_basis"] = f"據 authors[0].dynasty「{dynasty}」（原誤標「漢」，2026-08-11 訂正：{note}）"
        d["ai_note"] = d.get("ai_note", "") + (
            f" 2026-08-11：西漢範圍探勘時發現本條 dynasty 原誤標「漢」——{note}。"
            "已訂正 dynasty／period。"
        )
        save(p, d)


def fix_wangsu(widx):
    wid = "1ewsa49t4pru0"
    p = widx[wid]
    d = load(p)
    d["authors"][0]["dynasty"] = "三國魏"
    d["period"] = "three-kingdoms"
    d["period_basis"] = "據 authors[0].dynasty「三國魏」（原誤標「漢」，2026-08-11 訂正）"
    d["ai_note"] = d.get("ai_note", "") + (
        " 2026-08-11：西漢範圍探勘時發現本條 dynasty 原誤標「漢」——王肅"
        "（195-256）為三國曹魏經學家，非漢人。已訂正 dynasty／period。"
    )
    save(p, d)


def fix_shiyijia_sunzi(widx):
    wid = "1evjr3jstkwzk"
    p = widx[wid]
    d = load(p)
    d["authors"] = [
        {"name": "吉天保", "role": "輯", "dynasty": "宋"}
    ]
    d["period"] = "song"
    d["period_basis"] = "據 authors[0].dynasty「宋」（原誤標「漢」，2026-08-11 訂正）"
    d["ai_note"] = d.get("ai_note", "") + (
        " 2026-08-11：西漢範圍探勘時發現本條 authors 原作「曹操唐杜牧」"
        "（dynasty「漢」），將漢魏之際曹操與唐代杜牧二人姓名／朝代誤合為"
        "一條，且未反映原著錄「等」字所示尚有多位未具名注家。十一家注"
        "實為宋吉天保所輯，凡曹操、李筌、杜牧、陳皥、賈林、孟氏、梅堯"
        "臣、王晳、何延錫、張預、杜佑十一家（見本條 related_works 之"
        "1ev3bbesj0oow「孫子」條說明）。今改 authors 為吉天保（宋，輯），"
        "period 隨之訂正為 song。"
    )
    save(p, d)


def main():
    widx = build_work_index()
    fix_jiakui_entity_split(widx)
    fix_wudai_mislabeled_han(widx)
    fix_wangsu(widx)
    fix_shiyijia_sunzi(widx)
    print("done")


if __name__ == "__main__":
    main()
