#!/usr/bin/env python3
"""《戰國策》同名叢集去重（獨立問題，逐條裁決）。

使用者原始指出的 5 條同題「戰國策」，經核查牽出一個更大的既有磁鐵叢集
（部分條目已見於 .claude/known-issues/秦漢同名異書核對_42組待核.json 第
50 組，先前因撰人存疑而擱置）。逐條核實後裁決如下：

  刘向原典（33卷）：1ev7vo5ltthxc 保留為總集原典。
    併入 1evr5e3mi42um（直齋書錄解題，30卷，無撰人——僅一條著錄，本即
    刘向原典之異卷數著錄，非異書）。

  高誘注（33/32/21卷因殘卷分卷各異）：1ev3bad3a93i8 保留。
    併入 1evcs0ce8im80（新唐書藝文志，32卷）。
    并自 1evcpk0a1jmdc 中拆出 3 條原本錯配的高誘系著錄（隋書經籍志、
    宋史藝文志、書目答問雅雨堂本一則）移入本條——1evcpk0a1jmdc 因與
    「戰國策譚棷」（鮑彪注一支之異名刻本）題名形近而誤合入這批高誘
    系著錄，今分離。

  鮑彪注（十卷，南宋紹興丁卯成書）：1evcpk0a1jmdc 保留但改題「戰國策
    鮑彪注」（原題「戰國策譚諏」承四庫存目叢書之「戰國策譚棷」異名
    刻本題，移入 additional_titles）；連帶修正 entity 鮑彪之朝代——
    原機讀誤綁「隋書經籍志→南朝宋」，據本條四庫全書總目案語「宋鮑彪
    撰……成於紹興丁卯」改正為「南宋」。
    併入 1evjy50nku48w（鮑氏國策，中華再造善本，十卷，3 個 Book）。
    併入 1evr5e3mkaqlx（鮑氏校定戰國策，直齋書錄解題，十卷）。
    1evgq0bkwwu80（國史經籍志，十卷，撰人題「飭斬三」）**不併入**——
    此四字明顯非真實姓名，然已核對整理本原始 content 逐字為「（飭斬
    三）」，非本輪轉錄之訛，前次核查已標記「待人核原始文本」。循環境
    比對（同出國史經籍志、同十卷、緊鄰吳師道補正條）高度疑為鮑彪之
    訛，但無法排除為另一佚名注家，故僅加 related 存疑關聯，不逕行合
    併，待覆核原書解決。

  吳師道校注（十卷，補正鮑注）：1ev3bad43wn40 保留。
    併入 1evgq0bnnjtvk（國史經籍志，十卷）。

  穆文熙纂注（明，14冊）：1evka8kw1yl8g 改題「戰國策纂注」以消歧於
    刘向原典之裸標題「戰國策」，並補 related_works 連回原典。

所有 collated_edition 段落的 work_id 一併改繫，並依既有慣例補
link_basis 說明；Book/Collection 對被併記錄的引用一併改繫；相關
entity（鮑彪、吳師道）works 清單同步。
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


def save_index(p, data):
    save(p, data, indent=1)


def shard_of(id_str, n=16):
    h = 0
    for c in id_str:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return h % n


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


def remove_index_entry(work_id):
    s = shard_of(work_id)
    p = ROOT / "index" / "works" / f"{s:x}.json"
    d = load(p)
    if work_id in d:
        del d[work_id]
        save_index(p, d)


def update_index_title(work_id, new_title, new_path=None):
    s = shard_of(work_id)
    p = ROOT / "index" / "works" / f"{s:x}.json"
    d = load(p)
    d[work_id]["title"] = new_title
    if new_path:
        d[work_id]["path"] = new_path
    save_index(p, d)


def main():
    # ---------- 1. 刘向原典：併入 1evr5e3mi42um ----------
    liuxiang_p = ROOT / "Work/1/e/v/1ev7vo5ltthxc-戰國策.json"
    liuxiang = load(liuxiang_p)
    liuxiang["indexed_by"].append({
        "source": "直齋書錄解題", "source_bid": "1ev3bb403quio",
        "title_info": "戰國策三十卷",
        "summary": "《戰國策》三十卷。司馬遷《史記》所本，劉向所校者也。但無撰人名氏。後漢高誘注。自東周至中山十二國，凡三十三篇。"
    })
    liuxiang["ai_note"] = liuxiang.get("ai_note", "") + (
        " | 2026-08-10：併入 1evr5e3mi42um（直齋書錄解題著錄，三十卷，無撰人）——僅一條孤立著錄，"
        "即本典之異卷數著錄，非異書，已轉為 indexed_by 條目。"
    )
    save(liuxiang_p, liuxiang)
    retarget_collated(ROOT / "Work/1/e/v/1ev3bb403quio/collated_edition/雜史類.json",
                       "1evr5e3mi42um", "1ev7vo5ltthxc",
                       "原繫 1evr5e3mi42um，該條已併入 1ev7vo5ltthxc（同書異卷數著錄，2026-08-10），今改繫。")
    (ROOT / "Work/1/e/v/1evr5e3mi42um-戰國策.json").unlink()
    remove_index_entry("1evr5e3mi42um")

    # ---------- 2. 高誘注：併入 1evcs0ce8im80，並自 1evcpk0a1jmdc 拆出 3 條 ----------
    gaoyou_p = ROOT / "Work/1/e/v/1ev3bad3a93i8-戰國策注.json"
    gaoyou = load(gaoyou_p)
    gaoyou["indexed_by"].append({
        "source": "新唐書藝文志", "source_bid": "1evcs059gkvls",
        "title_info": "高誘注戰國策", "summary": "高誘注戰國策三十二卷"
    })
    tanzou_p = ROOT / "Work/1/e/v/1evcpk0a1jmdc-戰國策譚諏.json"
    tanzou = load(tanzou_p)
    move_titles = {"《戰國策》二十一卷", "高誘注《戰國策》三十三卷", "戰國策"}
    kept_indexed = []
    for e in tanzou["indexed_by"]:
        if e.get("title_info") in move_titles:
            gaoyou["indexed_by"].append(e)
        else:
            kept_indexed.append(e)
    tanzou["indexed_by"] = kept_indexed
    # emendated_by 亦屬高誘系，一併移出
    if tanzou.get("emendated_by"):
        gaoyou.setdefault("emendated_by", []).extend(tanzou["emendated_by"])
        tanzou["emendated_by"] = []
    gaoyou["ai_note"] = gaoyou.get("ai_note", "") + (
        " | 2026-08-10：併入 1evcs0ce8im80（新唐書藝文志，三十二卷）；並自 1evcpk0a1jmdc"
        "（因與鮑彪一支之異名刻本「戰國策譚棷」題名形近而誤合入的高誘系著錄）拆回 3 條"
        "indexed_by 及其 emendated_by。"
    )
    save(gaoyou_p, gaoyou)
    retarget_collated(ROOT / "Work/1/e/v/1evcs059gkvls/collated_edition/雜史類.json",
                       "1evcs0ce8im80", "1ev3bad3a93i8",
                       "原繫 1evcs0ce8im80，該條已併入 1ev3bad3a93i8（高誘注戰國策同書異卷數著錄，2026-08-10），今改繫。")
    (ROOT / "Work/1/e/v/1evcs0ce8im80-戰國策高誘注.json").unlink()
    remove_index_entry("1evcs0ce8im80")

    # ---------- 3. 鮑彪注：1evcpk0a1jmdc 改題，併入 1evjy50nku48w、1evr5e3mkaqlx ----------
    tanzou["title"] = "戰國策鮑彪注"
    tanzou["additional_titles"] = ["戰國策譚諏", "戰國策譚棷"]
    for a in tanzou.get("authors", []):
        if a.get("name") == "鮑彪":
            a["dynasty"] = "南宋"
            a["dynasty_basis"] = "四庫全書總目本條案語「宋鮑彪撰……成於紹興丁卯」；原entity_propagation誤綁『隋書經籍志→南朝宋』（因indexed_by混入高誘系著錄所致），2026-08-10已更正並拆分著錄。"

    jiuzhou_book = load(ROOT / "Work/1/e/v/1evjy50nku48w-鮑氏國策.json")
    tanzou.setdefault("books", []).extend(jiuzhou_book.get("books", []))
    tanzou.setdefault("description", {}).setdefault("sources", []).append("中華再造善本")

    jiaoding_p = ROOT / "Work/1/e/v/1evr5e3mkaqlx-鮑氏校定戰國策.json"
    jiaoding = load(jiaoding_p)
    tanzou["indexed_by"].extend(jiaoding.get("indexed_by", []))

    tanzou["period"] = "song"
    tanzou["period_basis"] = "據修正後 authors[0].dynasty「南宋」"
    tanzou["ai_note"] = tanzou.get("ai_note", "") + (
        " | 2026-08-10：改題「戰國策鮑彪注」（原題「戰國策譚諏」，四庫存目叢書作「戰國策譚棷」，"
        "皆鮑彪注之異名刻本題，移入 additional_titles）。併入 1evjy50nku48w（鮑氏國策，中華再造善本，"
        "十卷，3 個 Book 隨併）與 1evr5e3mkaqlx（鮑氏校定戰國策，直齋書錄解題，十卷）。修正 entity"
        "「鮑彪」朝代錯誤（見上）。另有 1evgq0bkwwu80（國史經籍志，十卷，撰人題「飭斬三」）循環境高度"
        "疑為鮑彪之訛書，然撰人字樣本身即整理本逐字轉錄、非本輪之訛，無法排除為另一佚名注家，"
        "故不併入，僅加 related 存疑關聯——見該條 ai_note。"
    )
    save(tanzou_p, tanzou)

    for bid in jiuzhou_book.get("books", []):
        bp = None
        for cand in ROOT.glob(f"Book/*/*/*/{bid}-*.json"):
            bp = cand
            break
        if bp:
            bdata = load(bp)
            bdata["work_id"] = "1evcpk0a1jmdc"
            save(bp, bdata)

    zhsy_p = ROOT / "Collection/1/a/h/1ahw9i7q2ih34/zhsy_book_mappings.json"
    zhsy = load(zhsy_p)
    for entry in zhsy.get("mappings", []):
        if entry.get("work_id") == "1evjy50nku48w":
            entry["work_id"] = "1evcpk0a1jmdc"
    save(zhsy_p, zhsy)

    (ROOT / "Work/1/e/v/1evjy50nku48w-鮑氏國策.json").unlink()
    remove_index_entry("1evjy50nku48w")
    (ROOT / "Work/1/e/v/1evr5e3mkaqlx-鮑氏校定戰國策.json").unlink()
    remove_index_entry("1evr5e3mkaqlx")

    baopiao_entity_p = ROOT / "Entity/1/j/9/1j967avzlnsi9-鮑彪.json"
    baopiao_entity = load(baopiao_entity_p)
    baopiao_entity["works"] = [w for w in baopiao_entity["works"] if w["work_id"] != "1evjy50nku48w"]
    baopiao_entity["dynasty"] = "南宋"
    baopiao_entity["dynasty_basis"] = "四庫全書總目本傳案語「宋鮑彪撰……成於紹興丁卯」；原誤綁『隋書經籍志→南朝宋』，2026-08-10更正"
    save(baopiao_entity_p, baopiao_entity)

    update_index_title("1evcpk0a1jmdc", "戰國策鮑彪注")

    # ---------- 4. 1evgq0bkwwu80：不併入，僅加存疑關聯 ----------
    weijue_p = ROOT / "Work/1/e/v/1evgq0bkwwu80-戰國策.json"
    weijue = load(weijue_p)
    weijue.setdefault("related_works", []).append({
        "id": "1evcpk0a1jmdc", "title": "戰國策鮑彪注", "relation": "related",
        "note": "同出《國史經籍志》、同十卷、緊鄰吳師道補正條，撰人題「飭斬三」疑為「鮑彪」之訛，"
                "然無法排除為另一佚名注家，不逕行合併，待覆核原書"
    })
    weijue["ai_note"] = weijue.get("ai_note", "") + (
        " | 2026-08-10：覆核《戰國策》同題叢集時重新檢視——「飭斬三」非真實姓名字樣，"
        "整理本 collated_edition 逐字轉錄亦作「（飭斬三）」，非本輪轉錄之訛。circumstantial "
        "evidence（同出國史經籍志、同十卷、緊鄰吳師道補正十卷條，而吳師道注即補正鮑彪注）"
        "高度指向「鮑彪」，然無直接證據，未逕行合併或改名，僅加 related 存疑關聯"
        "指向「戰國策鮑彪注」(1evcpk0a1jmdc)。仍待人核《國史經籍志》原始文本裁定。"
    )
    save(weijue_p, weijue)

    # ---------- 5. 吳師道校注：併入 1evgq0bnnjtvk ----------
    wushidao_p = ROOT / "Work/1/e/v/1ev3bad43wn40-戰國策校注.json"
    wushidao = load(wushidao_p)
    wushidao["indexed_by"].append({
        "source": "國史經籍志", "source_bid": "1ev3bb4qxubr4",
        "title_info": "《戰國策》十卷", "summary": "《戰國策》十卷（元吳師道注生）",
        "author_info": "元吳師道注生"
    })
    wushidao["ai_note"] = wushidao.get("ai_note", "") + (
        " | 2026-08-10：併入 1evgq0bnnjtvk（國史經籍志，十卷，同題「戰國策」，元吳師道撰，同人同卷數）。"
    )
    save(wushidao_p, wushidao)
    retarget_collated(ROOT / "Work/1/e/v/1ev3bb4qxubr4/collated_edition/子類下.json",
                       "1evgq0bnnjtvk", "1ev3bad43wn40",
                       "原繫 1evgq0bnnjtvk，該條已併入 1ev3bad43wn40（元吳師道戰國策校注同書異著錄，2026-08-10），今改繫。")
    (ROOT / "Work/1/e/v/1evgq0bnnjtvk-戰國策.json").unlink()
    remove_index_entry("1evgq0bnnjtvk")

    wushidao_entity_p = ROOT / "Entity/1/j/9/1j967avzlnsia-吳師道.json"
    wushidao_entity = load(wushidao_entity_p)
    wushidao_entity["works"] = [w for w in wushidao_entity["works"] if w["work_id"] != "1evgq0bnnjtvk"]
    save(wushidao_entity_p, wushidao_entity)

    # ---------- 6. 穆文熙纂注：改題消歧 ----------
    muwenxi_p = ROOT / "Work/1/e/v/1evka8kw1yl8g-戰國策.json"
    muwenxi = load(muwenxi_p)
    muwenxi["title"] = "戰國策纂注"
    muwenxi.setdefault("additional_titles", []).append("戰國策")
    muwenxi.setdefault("related_works", []).append({
        "id": "1ev7vo5ltthxc", "title": "戰國策", "relation": "text_carried_by"
    })
    muwenxi["ai_note"] = muwenxi.get("ai_note", "") + (
        " | 2026-08-10：改題「戰國策纂注」（原裸題「戰國策」與劉向原典 1ev7vo5ltthxc 撞題，"
        "本條實為明穆文熙纂注之specific刻本，非異書，今改題消歧，原題移入 additional_titles，"
        "並補 related_works 連回原典。"
    )
    save(muwenxi_p, muwenxi)
    liuxiang2 = load(liuxiang_p)
    liuxiang2.setdefault("related_works", []).append({
        "id": "1evka8kw1yl8g", "title": "戰國策纂注", "relation": "contains_text_of"
    })
    save(liuxiang_p, liuxiang2)
    update_index_title("1evka8kw1yl8g", "戰國策纂注")

    print("done")


if __name__ == "__main__":
    main()
