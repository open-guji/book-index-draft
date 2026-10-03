#!/usr/bin/env python3
"""清朝探勘 Round 8：33個剩餘「明」組混合Entity獨立立項之深查與訂正
（第一批，經WebSearch外部查證）。

發現：本組多數案例並非單純之period/dynasty邊界問題，而是更底層的
entity誤連結——清史稿藝文志之著錄原文常將「書名」「撰人」「朝代」
三者連寫（如「陳謝嶠爾雅音一卷」中「陳」為朝代非姓氏），批次匯入
時偶有切分錯誤，導致title/author攔錯位，再經CBDB以殘缺人名（如
courtesy name）之低信度（pending_accept altname）比對，誤連結至
完全無關之另一朝代同名人物。

本批處理：
  A. 爾雅音·施乾／爾雅音·謝嶠：清史稿原文「陳施乾爾雅音」「陳謝
     嶠爾雅音」之「陳」實指南朝陳（非姓氏），與已修正之「陳顧野王
     爾雅音」（見commit 97164e7a6f等歷輪）同一著錄叢集，此二條先前
     漏修。施乾又混入title；謝嶠另有喪服義work（隋書經籍志考證引
     《陳書·謝峤傳》確證其人）。訂正dynasty/period為南朝陳/
     nanbeichao，並清理施乾title。
  B. 南陽集（原題「陽集」，作者誤植「湘南」）：查明原书目「趙湘
     《南陽集》六卷」被切分為書名「陽集」＋作者「湘南」，「湘南」
     恰為文元發（明）之別名而誤連。庫中已有正確之趙湘《南陽集》
     （北宋，1ev3bcvuikef4）記錄，逕併入，不新建。
  C. 陳子性藏書（原題「藏書」，作者誤植「子性」）：查明「陳子性
     藏書」為清陳應選（字子性，廣州人，康熙中諸生）之書全稱本身，
     「子性」被誤判為劉三樂（明）之字而誤連。庫中已有正確記錄
     （1ev3bboclyww0），逕併入。
  D. 愛日齋叢鈔（原題「齋叢鈔」，作者誤植「愛日」）：清史稿原文
     「不著撰人愛日齋叢鈔五卷」，「愛日」實為書名前兩字，且原文
     明言「不著撰人」，卻誤連至「吳國華」（明）。庫中已有兩筆正確
     記錄（傳為宋葉寘/葉㟧撰），逕併入資料較完整者。
  E. 曾唯／汪本／沈志言／吳崧：Entity生年分別為1415/1477/1523/
     1516，若活至清（1644年建立）需逾160-230歲，絕無可能，
     Work.period因回溯型志書啟發式誤植為qing，逕訂正為ming
     （不受citation關鍵字判準之限——此四條citation本身無明清紀年
     關鍵字，但生年本身已是決定性證據，無需外部查證）。
  F. 繼生堂集·張賓：同書另三位撰人（張淇/張灝/張椿年）皆為高信度
     （auto/manual pid）清代人物，張賓卻連結至明代兵部尚書馬昂式
     之低信度（pending_accept altname）明代同名人物，與同書其餘
     三人明顯不類。解除誤連結，author.dynasty維持既有「清」（家集
     體例合理），entity_id留空待考。
  G. 芝厓詩集·超凡：Entity「胡尚英」之字「超凡」與此低信度
     （pending_accept altname）比對相符，然WebSearch未能找到任何
     獨立佐證顯示胡尚英（明）撰有此書；本輪同類「altname」比對
     （湘南/子性）驗證結果皆為誤連，基於此pattern高度懷疑同屬誤連，
     解除entity_id繫連，真實身分待未來查核。
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


def get_indent(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    lines = raw.split("\n")
    if len(lines) > 1:
        cand = len(lines[1]) - len(lines[1].lstrip(" "))
        if cand > 0:
            return cand
    return 2


def find_work(wid):
    return next(ROOT.glob(f"Work/?/?/?/{wid}-*.json"))


def find_work_maybe(wid):
    m = list(ROOT.glob(f"Work/?/?/?/{wid}-*.json"))
    return m[0] if m else None


def find_entity(eid):
    return next(ROOT.glob(f"Entity/?/?/?/{eid}-*.json"))


def shard_of(id_str, n=16):
    h = 0
    for c in id_str:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return h % n


def sync_work_index_fields(wid, fields):
    s = shard_of(wid)
    p = ROOT / "index" / "works" / f"{s:x}.json"
    idx = load(p)
    if wid in idx:
        idx[wid].update(fields)
        save(p, idx, get_indent(p))


def remove_from_work_index(wid):
    s = shard_of(wid)
    p = ROOT / "index" / "works" / f"{s:x}.json"
    idx = load(p)
    if wid in idx:
        del idx[wid]
        save(p, idx, get_indent(p))


def detach_entity_work(eid, wid):
    p = find_entity(eid)
    e = load(p)
    e["works"] = [w for w in e.get("works", []) if w.get("work_id") != wid]
    save(p, e, get_indent(p))


def sync_entity_index_fields(eid, fields):
    s = shard_of(eid)
    p = ROOT / "index" / "entities" / f"{s:x}.json"
    idx = load(p)
    if eid in idx:
        idx[eid].update(fields)
        save(p, idx, get_indent(p))


def main():
    log = []

    # A1. 爾雅音·謝嶠：dynasty/period 訂正
    xie_eid = "1j96hf210bx8g"
    ep = find_entity(xie_eid)
    e = load(ep)
    e["dynasty"] = "南朝陳"
    e["period"] = "nanbeichao"
    e["period_basis"] = "據 dynasty「南朝陳」（2026-08-17 清朝探勘round8：謝嶠，隋書經籍志考證引《陳書·謝峤傳》確證為陳國子祭酒，清史稿藝文志原文「陳謝嶠爾雅音」之「陳」實指朝代而非姓氏，Work.period因回溯型志書啟發式誤植為qing，訂正）"
    e["ai_note"] = e.get("ai_note", "") + " 2026-08-17：南朝陳人（國子祭酒），與已修正之陳顧野王《爾雅音》同一著錄叢集，此前漏修，本輪補正。"
    save(ep, e, get_indent(ep))
    sync_entity_index_fields(xie_eid, {"dynasty": "南朝陳", "period": "nanbeichao"})

    xie_wid = "1evcpcuy9m1a8"
    wp = find_work(xie_wid)
    w = load(wp)
    w["authors"][0]["dynasty"] = "南朝陳"
    w.pop("dynasty", None)
    w["dynasty"] = "南朝陳"
    w["dynasty_basis"] = "2026-08-17 清朝探勘round8：清史稿藝文志原文「陳謝嶠爾雅音」，陳為朝代非姓氏；隋書經籍志考證確證謝嶠為陳國子祭酒"
    w["period"] = "nanbeichao"
    w["period_basis"] = "據 authors[0].dynasty「南朝陳」訂正"
    save(wp, w, get_indent(wp))
    sync_work_index_fields(xie_wid, {"dynasty": "南朝陳", "period": "nanbeichao"})
    log.append(f"A1 謝嶠 {xie_eid}/{xie_wid} -> nanbeichao")

    # A2. 爾雅音·施乾：title 清理 + dynasty/period 訂正
    shi_eid = "1j96h8rw6xrsz"
    ep = find_entity(shi_eid)
    e = load(ep)
    e["dynasty"] = "南朝陳"
    e["period"] = "nanbeichao"
    e["external_ids"] = {}
    e["period_basis"] = "據 dynasty「南朝陳」（2026-08-17 清朝探勘round8：施乾，隋書經籍志/清史稿藝文志皆載「陳施乾爾雅音」，陳為朝代非姓氏，與謝嶠/顧野王同一著錄叢集之南朝陳爾雅學者，原CBDB「pending_accept」誤配至明代同名人，訂正）"
    e["ai_note"] = e.get("ai_note", "") + " 2026-08-17：南朝陳爾雅學者（與謝嶠、顧野王同時著錄），原title誤含朝代字「陳」而生「陳施乾」偽三字名，已清理title；原CBDB比對（pending_accept: auto_unique）誤配至明代同名人，解除。"
    save(ep, e, get_indent(ep))
    sync_entity_index_fields(shi_eid, {"dynasty": "南朝陳", "period": "nanbeichao"})

    shi_wid = "1evr5e3m84hgn"
    wp = find_work(shi_wid)
    w = load(wp)
    w["title"] = "爾雅音"
    w["authors"][0]["dynasty"] = "南朝陳"
    w["dynasty"] = "南朝陳"
    w["dynasty_basis"] = "2026-08-17 清朝探勘round8：原title「陳施乾爾雅音」之「陳」為朝代非姓氏，清理為「爾雅音」；隋書經籍志/清史稿藝文志皆載施乾為南朝陳人"
    w["period"] = "nanbeichao"
    w["period_basis"] = "據 authors[0].dynasty「南朝陳」訂正"
    save(wp, w, get_indent(wp))
    sync_work_index_fields(shi_wid, {"title": "爾雅音", "dynasty": "南朝陳", "period": "nanbeichao"})
    log.append(f"A2 施乾 {shi_eid}/{shi_wid} -> nanbeichao, title cleaned")

    # B. 陽集/湘南 -> 併入既有 南陽集/趙湘(北宋)
    yangji_wid = "1evr5e3mdfirr"
    keeper_wid = "1ev3bcvuikef4"
    wenyuanfa_eid = "1j96h8rw6xruf"
    zhaoxiang_eid = "1j967bgl89icb"

    yp = find_work(yangji_wid)
    yj = load(yp)
    kp = find_work(keeper_wid)
    kj = load(kp)
    kj.setdefault("indexed_by", [])
    for ib in yj.get("indexed_by", []) or []:
        if ib not in kj["indexed_by"]:
            kj["indexed_by"].append(ib)
    kj["ai_note"] = kj.get("ai_note", "") + (
        " 2026-08-17 清朝探勘round8：併入 1evr5e3mdfirr（原題「陽集」）。"
        "查明清史稿藝文志原文「趙湘南陽集六卷」被誤切為書名「陽集」＋作者「湘南」，"
        "「湘南」適為文元發（明）之別名而誤連CBDB，實為本條（趙湘《南陽集》北宋）之重出著錄。"
    )
    save(kp, kj, get_indent(kp))
    sync_work_index_fields(keeper_wid, {})

    # detach wrong entity, remove old work file+index, redirect collated section
    detach_entity_work(wenyuanfa_eid, yangji_wid)
    # ensure correct entity has keeper linked (should already)
    ep = find_entity(zhaoxiang_eid)
    e = load(ep)
    if not any(w.get("work_id") == keeper_wid for w in e.get("works", [])):
        e.setdefault("works", []).append({"work_id": keeper_wid, "role": "撰"})
        save(ep, e, get_indent(ep))

    section_fp = ROOT / "Work/1/e/v/1evdiulq07rwg/collated_edition/別集類.json"
    sec = load(section_fp)
    items = sec.get("sections") if isinstance(sec, dict) else sec
    sec_changed = False
    for item in items or []:
        if isinstance(item, dict) and item.get("work_id") == yangji_wid:
            item["work_id"] = keeper_wid
            sec_changed = True
    if sec_changed:
        save(section_fp, sec, get_indent(section_fp))

    yp.unlink()
    remove_from_work_index(yangji_wid)
    log.append(f"B 陽集{yangji_wid} 併入 南陽集{keeper_wid}, section_redirect={sec_changed}")

    # C. 藏書/子性 -> 併入既有 陳子性藏書/陳應選(清)
    zangshu_wid = "1evr5e3mezpd0"
    keeper2_wid = "1ev3bboclyww0"
    liusanle_eid = "1j96h8rw6xruo"

    zp = find_work(zangshu_wid)
    zj = load(zp)
    kp2 = find_work(keeper2_wid)
    kj2 = load(kp2)
    kj2.setdefault("indexed_by", [])
    for ib in zj.get("indexed_by", []) or []:
        if ib not in kj2["indexed_by"]:
            kj2["indexed_by"].append(ib)
    kj2["ai_note"] = kj2.get("ai_note", "") + (
        " 2026-08-17 清朝探勘round8：併入 1evr5e3mezpd0（原題「藏書」）。"
        "查明清史稿藝文志原文「陳子性藏書十二卷」（「陳子性」即陳應選之字「子性」冠姓，為本書慣稱全名，非「陳氏之《藏書》」）"
        "被誤切為書名「藏書」＋作者「子性」，「子性」適為劉三樂（明）之字而誤連CBDB，實為本條之重出著錄。"
    )
    save(kp2, kj2, get_indent(kp2))

    detach_entity_work(liusanle_eid, zangshu_wid)
    zp.unlink()
    remove_from_work_index(zangshu_wid)
    log.append(f"C 藏書{zangshu_wid} 併入 陳子性藏書{keeper2_wid}")

    # D. 齋叢鈔/愛日 -> 併入既有 愛日齋叢鈔（葉㟧，1ev794aa5nmyo）
    aizhang_wid = "1evr5e3mbvc2d"
    keeper3_wid = "1ev794aa5nmyo"
    wuguohua_eid = "1j96h8rw6xrts"

    ap = find_work(aizhang_wid)
    aj = load(ap)
    kp3 = find_work(keeper3_wid)
    kj3 = load(kp3)
    kj3.setdefault("indexed_by", [])
    for ib in aj.get("indexed_by", []) or []:
        if ib not in kj3["indexed_by"]:
            kj3["indexed_by"].append(ib)
    kj3["ai_note"] = kj3.get("ai_note", "") + (
        " 2026-08-17 清朝探勘round8：併入 1evr5e3mbvc2d（原題「齋叢鈔」，五卷本）。"
        "查明清史稿藝文志原文「不著撰人愛日齋叢鈔五卷」被誤切為書名「齋叢鈔」＋作者「愛日」，"
        "「愛日」實為書名前二字，原文明言「不著撰人」，卻誤連至吳國華（明）。"
        "卷數（五卷／宋史藝文志補作十卷）有異，然同題無他證顯示為異書，暫依既有先例視為同書之異本著錄，"
        "傳為宋葉寘/葉㟧撰。"
    )
    save(kp3, kj3, get_indent(kp3))

    detach_entity_work(wuguohua_eid, aizhang_wid)
    ap.unlink()
    remove_from_work_index(aizhang_wid)
    log.append(f"D 齋叢鈔{aizhang_wid} 併入 愛日齋叢鈔{keeper3_wid}")

    # E. 曾唯/汪本/沈志言/吳崧：生年機械判定訂正period
    mechanical = [
        ("1evr5e3m9dfmw", "曾唯", 1415),
        ("1evr5e3m9zwny", "汪本", 1477),
        ("1evr5e3mbk3et", "沈志言", 1523),
        ("1evr5e3mbvbxb", "吳崧", 1516),
    ]
    for wid, name, byear in mechanical:
        wp = find_work(wid)
        w = load(wp)
        w["authors"][0]["dynasty"] = "明"
        w["authors"][0].pop("dynasty_basis", None)
        if w.get("dynasty") is not None:
            w["dynasty"] = "明"
        w["period"] = "ming"
        w["period_basis"] = (
            f"據 authors[0].dynasty「明」（2026-08-17 清朝探勘round8：{name}生年{byear}，"
            f"若活至清建國（1644）需逾{1644-byear}歲，絕無可能，"
            "Work.period因回溯型志書啟發式誤植為qing，逕訂正，不受citation紀年關鍵字判準限制）"
        )
        save(wp, w, get_indent(wp))
        sync_work_index_fields(wid, {"dynasty": "明", "period": "ming"})
        log.append(f"E {name} {wid} -> ming (生年{byear}機械判定)")

    # F. 繼生堂集·張賓：解除誤連結
    jishen_wid = "1evr5e3me1zsx"
    zhangbin_eid = "1j96h8rw94fm3"
    wp = find_work(jishen_wid)
    w = load(wp)
    w["authors"][0].pop("entity_id", None)
    w["ai_note"] = w.get("ai_note", "") + (
        " 2026-08-17 清朝探勘round8：原entity_id所指張賓為明代人（1439-1517，pending_accept低信度比對），"
        "與同書其餘三位撰人（張淇/張灝/張椿年，皆高信度清代人物CBDB比對）明顯不類，"
        "本條張賓應為與此三人同時之清代家族成員，解除誤連結，真實身分待未來查核。"
    )
    save(wp, w, get_indent(wp))
    detach_entity_work(zhangbin_eid, jishen_wid)
    log.append(f"F 繼生堂集·張賓 解除誤連結")

    # G. 芝厓詩集·超凡：解除誤連結
    zhiya_wid = "1evr5e3mdfirb"
    huqingying_eid = "1j96hjwlxcpi9"
    wp = find_work(zhiya_wid)
    w = load(wp)
    w["authors"][0].pop("entity_id", None)
    w["ai_note"] = w.get("ai_note", "") + (
        " 2026-08-17 清朝探勘round8：原entity_id所指胡尚英（明，字超凡，pending_accept低信度altname比對），"
        "WebSearch未能找到任何獨立佐證顯示胡尚英撰有此書；本輪同類「altname」比對（湘南／子性）驗證結果皆為"
        "誤連（實為他人書名之殘餘字被拆分為姓名），基於此pattern高度懷疑同屬誤連，解除entity_id繫連，"
        "真實身分待未來查核。"
    )
    save(wp, w, get_indent(wp))
    detach_entity_work(huqingying_eid, zhiya_wid)
    log.append(f"G 芝厓詩集·超凡 解除誤連結")

    for line in log:
        print(line)


if __name__ == "__main__":
    main()
