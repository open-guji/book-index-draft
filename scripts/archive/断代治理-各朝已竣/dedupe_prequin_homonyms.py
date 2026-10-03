#!/usr/bin/env python3
"""先秦組「重名的書」逐條裁決（使用者要求：查所有 pre-qin 題目在全庫的同名記錄，決定合併或改名）。

比對範圍：269 條 pre-qin Work 的題名，是否有全庫其他任何記錄（不限 period）共用
同一 title。共查得 14 個題名、24 條旁支記錄，逐條核讀原始 indexed_by／
collated_edition 內容（不僅看 Work 檔表層欄位）後裁決：

  真磁鐵，需合併：
    - 成相雜辭 1ev7xm2s9f56o → 併入 1evdsvononrwg（本條已有既存 note 明指
      「同書之重出」，僅需執行）。
    - 孫子 1evr5e3mj1skc → 併入 1ev3bbesj0oow（吳孫武本）。表層 juan_count
      標 10，然核對 collated_edition 實際內容為《直齋書錄解題》「孫子三卷
      ……吳孫武撰，魏武帝削其繁冗，定為十三篇」，即吳孫子本身，非另一書。
    - 孫子 1evr5e3mifbch → 併入 1evfuuxirjke8（孫綽本）。表層 juan_count
      標 3，然核對 collated_edition 實際內容為《直齋書錄解題》「孫子十卷
      ……題晉孫綽興公撰」，與孫綽本同書，非吳孫子。
      注意：兩條孫子stub 的表層 juan_count 與其自身 indexed_by／
      collated_edition 內容不符（3⇄10 顛倒），是本次核查揪出的另一項資料
      品質問題，隨合併一併訂正。

  真異書，僅需消歧（加 related 互指、補齊 period），不合併：
    - 莊子 1evfuuwz3wkxs（晉葛洪修機十七卷輯本）vs 1ev7xkgpbz7r4（原典）——
      已有 ai_note「留待覆核」，核實為異書，補雙向 related。
    - 楚辭／周易／燕丹子／筮法／管仲／魏公子／春秋(李氏) 諸叢——核讀後
      皆為前人已正確處理或明顯異書（撰人、朝代、性質皆不同），無需動作。

  發現的欄位缺漏，一併補上：
    - 五子胥(1ewp0r8yu05c4)／師曠(1ewp0r90ag0lh)／孫臏兵法(1evjr3k5q21a8)
      period 缺漏，補 pre-qin。
    - 楚辭朱熹注(1evkps5e8f0n4) period 缺漏，補 song。
    - 春秋李氏(1evr5e3mezpc2) period 缺漏，補 pre-qin。

  孝經傳（1evcsw8wfkgsg）三書合一——最先發現之磁鐵，另見
  scripts/split_xiaojingzhuan.py。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def save_index(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")


def shard_of(id_str, n=16):
    h = 0
    for c in id_str:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return h % n


def remove_index_entry(work_id):
    s = shard_of(work_id)
    p = ROOT / "index" / "works" / f"{s:x}.json"
    d = load(p)
    if work_id in d:
        del d[work_id]
        save_index(p, d)


def retarget_collated(path, old_id, new_id, note):
    data = load(path)
    changed = False
    for sec in data.get("sections", []):
        if sec.get("work_id") == old_id:
            sec["work_id"] = new_id
            sec["link_basis"] = note
            changed = True
    if changed:
        save(path, data)
    return changed


def build_index():
    idx = {}
    for s in SHARDS:
        d = load(ROOT / "index" / "works" / f"{s}.json")
        for wid, entry in d.items():
            idx[wid] = ROOT / entry["path"]
    return idx


def main():
    idx = build_index()

    # ---------- 1. 成相雜辭：併入 1evdsvononrwg ----------
    base_p = idx["1evdsvononrwg"]
    base = load(base_p)
    base["indexed_by"].append({
        "source": "漢書藝文志", "source_bid": "1euhm19a23jsw",
        "title_info": "成相雜辭十一篇", "summary": "《成相雜辭》十一篇。",
        "section": "詩賦略／雜賦"
    })
    base["related_works"] = [e for e in base["related_works"] if e["id"] != "1ev7xm2s9f56o"]
    base["ai_note"] = base.get("ai_note", "") + " | 2026-08-10：併入 1ev7xm2s9f56o（同一漢志著錄之重出零引用 stub）。"
    save(base_p, base)
    retarget_collated(ROOT / "Work/1/e/u/1euhm19a23jsw/collated_edition/詩賦略.json",
                       "1ev7xm2s9f56o", "1evdsvononrwg",
                       "原繫 1ev7xm2s9f56o，該條已併入 1evdsvononrwg（同一漢志著錄之重出，2026-08-10），今改繫。")
    (ROOT / "Work/1/e/v/1ev7xm2s9f56o-成相雜辭.json").unlink()
    remove_index_entry("1ev7xm2s9f56o")

    # ---------- 2. 孫子 1evr5e3mj1skc（吳孫武本）：併入 1ev3bbesj0oow ----------
    sunzi_p = idx["1ev3bbesj0oow"]
    sunzi = load(sunzi_p)
    sunzi["indexed_by"].append({
        "source": "直齋書錄解題", "source_bid": "1ev3bb403quio",
        "title_info": "《孫子》三卷",
        "summary": "《孫子》三卷。吳孫武撰。《漢志》八十一篇。魏武帝削其繁冗，定為十三篇。世之言兵者，祖孫氏。然孫武事吳闔盧而不見於《左氏傳》，未知其果何時人也。"
    })
    sunzi["related_works"] = [e for e in sunzi["related_works"] if e["id"] != "1evr5e3mj1skc"]
    sunzi["ai_note"] = sunzi.get("ai_note", "") + (
        " | 2026-08-10：併入 1evr5e3mj1skc——該條表層 juan_count 誤標十卷，核對其"
        "collated_edition 原始內容實為《直齋書錄解題》兵書類「孫子三卷……吳孫武撰」，"
        "即本書之著錄，非異書，故不採原有 related 存疑關聯，逕行合併。"
    )
    save(sunzi_p, sunzi)
    retarget_collated(ROOT / "Work/1/e/v/1ev3bb403quio/collated_edition/兵書類.json",
                       "1evr5e3mj1skc", "1ev3bbesj0oow",
                       "原繫 1evr5e3mj1skc，核對原文確為吳孫子兵法本身之著錄，已併入 1ev3bbesj0oow（2026-08-10），今改繫。")
    (ROOT / "Work/1/e/v/1evr5e3mj1skc-孫子.json").unlink()
    remove_index_entry("1evr5e3mj1skc")

    # ---------- 3. 孫子 1evr5e3mifbch（孫綽本）：併入 1evfuuxirjke8 ----------
    sunchuo_p = idx["1evfuuxirjke8"]
    sunchuo = load(sunchuo_p)
    sunchuo["indexed_by"].append({
        "source": "直齋書錄解題", "source_bid": "1ev3bb403quio",
        "title_info": "《孫子》十卷",
        "summary": "《孫子》十卷。題晉孫綽興公撰。恐依託。《唐志》及《中興書目》並無之。余從程文簡家借錄。"
    })
    sunchuo.setdefault("related_works", []).append({
        "id": "1ev3bbesj0oow", "title": "孫子", "relation": "related",
        "note": "同題異書——彼為漢志兵書略兵權謀類吳孫武兵法之傳世本，本書為晉孫綽所撰別一種"
    })
    sunchuo["ai_note"] = sunchuo.get("ai_note", "") + (
        " | 2026-08-10：原 ai_note 所列五條同題「孫子」記錄已逐條核實——"
        "1evr5e3mifbch 表層 juan_count 誤標三卷，核對其 collated_edition 原始內容實為"
        "《直齋書錄解題》雜家類「孫子十卷……題晉孫綽興公撰」，即本書之著錄，非異書，"
        "已合併於此；1evr5e3mj1skc 已確認為吳孫子本身之著錄，併入 1ev3bbesj0oow；"
        "1evr5e3mfxf2u（魏武帝注）、1evr5e3mfxf2v（蕭古注）為吳孫子之注本，與本書"
        "（孫綽別撰）無涉，仍各自獨立。"
    )
    save(sunchuo_p, sunchuo)
    retarget_collated(ROOT / "Work/1/e/v/1ev3bb403quio/collated_edition/雜家類.json",
                       "1evr5e3mifbch", "1evfuuxirjke8",
                       "原繫 1evr5e3mifbch，核對原文確為晉孫綽所撰《孫子》之著錄，已併入 1evfuuxirjke8（2026-08-10），今改繫。")
    (ROOT / "Work/1/e/v/1evr5e3mifbch-孫子.json").unlink()
    remove_index_entry("1evr5e3mifbch")

    # ---------- 4. 莊子：消歧，補雙向 related ----------
    ge_p = idx["1evfuuwz3wkxs"]
    ge = load(ge_p)
    if not any(e["id"] == "1ev7xkgpbz7r4" for e in ge.get("related_works", [])):
        ge.setdefault("related_works", []).append({
            "id": "1ev7xkgpbz7r4", "title": "莊子", "relation": "related",
            "note": "同題異書——彼為莊周原典，本書為晉葛洪修機所輯撰之別一種（十七卷，已佚）"
        })
    ge["ai_note"] = ge.get("ai_note", "") + " | 2026-08-10：核實為異書（葛洪修機另撰，非莊周原典之重出），已補雙向 related，非合併。"
    save(ge_p, ge)

    zhuangzi_p = idx["1ev7xkgpbz7r4"]
    zhuangzi = load(zhuangzi_p)
    if not any(e["id"] == "1evfuuwz3wkxs" for e in zhuangzi.get("related_works", [])):
        zhuangzi.setdefault("related_works", []).append({
            "id": "1evfuuwz3wkxs", "title": "莊子", "relation": "related",
            "note": "晉葛洪修機另撰之《莊子》十七卷輯本（已佚），與本書同題異書"
        })
    save(zhuangzi_p, zhuangzi)

    # ---------- 5. period 欄位缺漏補全 ----------
    period_fixes = [
        ("1ewp0r8yu05c4", "pre-qin", "先秦"),
        ("1ewp0r90ag0lh", "pre-qin", "先秦"),
        ("1evjr3k5q21a8", "pre-qin", "戰國（銀雀山漢簡整理本所整理者為戰國孫臏兵法原文）"),
        ("1evkps5e8f0n4", "song", "南宋（朱熹）"),
        ("1evr5e3mezpc2", "pre-qin", "周（清史稿藝文志「周李氏春秋一卷」）"),
    ]
    for wid, period, note in period_fixes:
        p = idx[wid]
        d = load(p)
        d["period"] = period
        d["period_basis"] = f"2026-08-10 補全：{note}"
        save(p, d)
        # sync index period field too
        s = shard_of(wid)
        ip = ROOT / "index" / "works" / f"{s:x}.json"
        idata = load(ip)
        idata[wid]["period"] = period
        save_index(ip, idata)

    print("done")


if __name__ == "__main__":
    main()
