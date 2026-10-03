#!/usr/bin/env python3
"""清史稿藝文志系統性排查 Round 2：collision桶（姓名撞庫疑點）之
逐條核實與訂正。

「姓名撞庫」檢驗發現10條citation以「吳/梁/周/唐/元」開頭而與既有
entity姓名產生2-3字重疊。逐一核實後分兩類：

A. 真collision（5組）——citation之「朝代字」實為撰人姓氏之一部，
   非朝代標記：
   - 吳則禮《北湘集》（citation「湘」為「湖」之OCR異寫）→ 併入既有
     《北湖集》（1ev3bcxqnqfi8，北宋吳則禮）
   - 吳皋《吾類稿》（citation疊字「吾吾」非誤，即其書原題）→ 併入
     既有《吾吾類稿》（1ev3bd7kk1am8，元吳皋）
   - 吳泳《林集》（citation脫「鶴」字）→ 併入既有《鶴林集》
     （1ev3bd2kb42dc，南宋吳泳）
   - 吳芾《山集》（citation脫「湖」字）→ 併入既有《湖山集》
     （1ev3bd0ex7280，南宋吳芾）
   - 吳可《海居士集》——與吳可既有之《藏海詩話》非同書（詩話與
     居士集屬不同體裁），非重出，逕訂正本條title/author/period，
     連結既有entity。

B. False alarm（5組）——姓名撞庫檢驗之誤警，「朝代字」讀法本身
   正確，2-3字重疊純屬巧合：
   - 梁元帝《纂要》：「梁」為朝代（南朝梁），citation本身完整未
     見garbled，逕補authors並連結既有「梁元帝」entity（1j96hf83t28lc）。
   - 元魯明善《農桑衣食撮要》：WebSearch/清朝探勘輪已確證魯明善
     為元代畏兀兒人農學家，「元魯」2字重疊命中之entity與此無關，
     逕訂正。
   - 唐元行沖《御注孝經疏》：元行沖為唐代經學家，「唐元」2字重疊
     命中之entity（primary_name本身即為可疑之殘缺記法「唐元」）
     與此無關，逕訂正。
   - 周卜氏《易傳》：「周」實為朝代（先秦周），「卜氏」為卜子夏
     （孔子弟子）之傳統書目稱法，「周卜」2字重疊純屬巧合，逕訂正
     為pre-qin。
   - 周易分野：此條實無撞庫關係——citation僅「《周易分野》一卷」
     並無撰人姓名，「周」乃書名「周易」（易之尊稱）首字而非朝代
     字首，本條不屬本bug模式，不予變動，另記錄存證。
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


def redirect_collated_section(wid_old, wid_new):
    section_fp = ROOT / "Work/1/e/v/1evdiulq07rwg/collated_edition/別集類.json"
    sec = load(section_fp)
    items = sec.get("sections") if isinstance(sec, dict) else sec
    changed = False
    for item in items or []:
        if isinstance(item, dict) and item.get("work_id") == wid_old:
            item["work_id"] = wid_new
            changed = True
    if changed:
        save(section_fp, sec, get_indent(section_fp))
    return changed


def merge_work(dup_wid, keeper_wid, wrong_eid, note):
    dp = find_work(dup_wid)
    dup = load(dp)
    kp = find_work(keeper_wid)
    keeper = load(kp)
    keeper.setdefault("indexed_by", [])
    for ib in dup.get("indexed_by", []) or []:
        if ib not in keeper["indexed_by"]:
            keeper["indexed_by"].append(ib)
    keeper["ai_note"] = keeper.get("ai_note", "") + f" 2026-08-18 清史稿藝文志系統性排查Round2：{note}"
    save(kp, keeper, get_indent(kp))

    detach_entity_work(wrong_eid, dup_wid)
    redirected = redirect_collated_section(dup_wid, keeper_wid)
    dp.unlink()
    remove_from_work_index(dup_wid)
    return redirected


def main():
    # A. 4組重出併入
    merge_work("1evr5e3mdfis9", "1ev3bcxqnqfi8", "1j96heg2dgx6o",
               "併入 1evr5e3mdfis9（原題「北湘集」，「湘」為「湖」之著錄異寫，"
               "作者誤析為「則禮」而誤連無關entity，實為吳則禮《北湖集》之重出著錄）。")
    merge_work("1evr5e3mdqr80", "1ev3bd7kk1am8", "1j96heg6zj668",
               "併入 1evr5e3mdqr80（原題「吾類稿」，作者誤析為「皋吾」而誤連無關entity，"
               "實為吳皋《吾吾類稿》之重出著錄，疊字「吾吾」為原書題，非OCR衍）。")
    merge_work("1evr5e3mdqr6r", "1ev3bd2kb42dc", "1j96heg5lwfsw",
               "併入 1evr5e3mdqr6r（原題「林集」，脫「鶴」字，作者誤析為「泳鶴」而誤連"
               "無關entity，實為吳泳《鶴林集》之重出著錄）。")
    merge_work("1evr5e3mdfitb", "1ev3bd0ex7280", "1j96heg3r3nk0",
               "併入 1evr5e3mdfitb（原題「山集」，脫「湖」字，作者誤析為「芾湖」而誤連"
               "無關entity，實為吳芾《湖山集》之重出著錄）。")

    # A5. 吳可《海居士集》：非重出，逕訂正
    wid = "1evr5e3mdfit6"
    eid = "1j96hldqqnsao"
    wrong_eid = "1j96heg3a8u80"
    detach_entity_work(wrong_eid, wid)
    p = find_work(wid)
    j = load(p)
    j["title"] = "藏海居士集"
    j["authors"] = [{"name": "吳可", "role": "撰", "dynasty": "宋", "entity_id": eid}]
    j["dynasty"] = "宋"
    j["dynasty_basis"] = "2026-08-18 清史稿藝文志系統性排查Round2：citation「吳可藏海居士集二卷」，吳可（宋，字思道，號藏海居士）另有《藏海詩話》已著錄於庫，此為其居士集，非同書，逕訂正"
    j["period"] = "song"
    j["period_basis"] = "據 authors[0].dynasty「宋」訂正"
    j["ai_note"] = j.get("ai_note", "") + " 2026-08-18 清史稿藝文志系統性排查Round2：原title「海居士集」脫「藏」字，作者誤析為「可藏」而誤連無關entity，今訂正為吳可本人之《藏海居士集》，與其《藏海詩話》為兩部不同著作，非重出。"
    save(p, j, get_indent(p))
    sync_work_index_fields(wid, {"title": "藏海居士集", "dynasty": "宋", "period": "song", "author": "吳可"})
    ep = find_entity(eid)
    e = load(ep)
    if not any(w.get("work_id") == wid for w in e.get("works", [])):
        e.setdefault("works", []).append({"work_id": wid, "role": "撰"})
        save(ep, e, get_indent(ep))

    # B1. 梁元帝《纂要》
    wid = "1evr5e3m8fpy1"
    eid = "1j96hf83t28lc"
    p = find_work(wid)
    j = load(p)
    j["authors"] = [{"name": "梁元帝", "role": "撰", "dynasty": "梁", "entity_id": eid}]
    j["dynasty"] = "梁"
    j["dynasty_basis"] = "2026-08-18 清史稿藝文志系統性排查Round2：citation「梁元帝纂要」，梁元帝（蕭繹，南朝梁）纂要為著名已佚類書，馬國翰有輯本"
    j["period"] = "nanbeichao"
    j["period_basis"] = "據 authors[0].dynasty「梁」訂正"
    save(p, j, get_indent(p))
    sync_work_index_fields(wid, {"dynasty": "梁", "period": "nanbeichao", "author": "梁元帝"})
    ep = find_entity(eid)
    e = load(ep)
    if not any(w.get("work_id") == wid for w in e.get("works", [])):
        e.setdefault("works", []).append({"work_id": wid, "role": "撰"})
        save(ep, e, get_indent(ep))

    # B2/B3. 元魯明善、唐元行沖：姓名撞庫為誤警，逕訂正period/dynasty
    for wid, dyn, period, note in [
        ("1evr5e3maxm9u", "元", "liao-jin-yuan",
         "citation「元魯明善農桑衣食撮要」，魯明善（畏兀兒人，元代農學家）確證為元人，"
         "「元魯」2字姓名撞庫檢驗為誤警（命中之南宋entity與此無關）"),
        ("1evr5e3m7t8v9", "唐", "sui-tang",
         "citation「唐元行沖御注孝經疏」，元行沖（唐代經學家，奉玄宗敕注孝經）確證為唐人，"
         "「唐元」2字姓名撞庫檢驗為誤警（命中之entity「唐元」primary_name本身即可疑之殘缺記法，與此無關）"),
    ]:
        p = find_work(wid)
        j = load(p)
        a = j.get("authors")
        if a and isinstance(a, list) and isinstance(a[0], dict):
            a[0]["dynasty"] = dyn
            a[0].pop("dynasty_basis", None)
        if j.get("dynasty") is not None or not a:
            j["dynasty"] = dyn
        j["period"] = period
        j["period_basis"] = f"據 清史稿藝文志citation朝代字首「{dyn}」（2026-08-18 清史稿藝文志系統性排查Round2：{note}）"
        save(p, j, get_indent(p))
        sync_work_index_fields(wid, {"dynasty": dyn, "period": period})

    # B4. 周卜氏《易傳》
    wid = "1evr5e3m6vjbq"
    p = find_work(wid)
    j = load(p)
    j["dynasty"] = "周"
    j["dynasty_basis"] = "2026-08-18 清史稿藝文志系統性排查Round2：citation「周卜氏易傳」，卜氏為孔子弟子卜商（子夏）之傳統書目稱法（子夏易傳），周為先秦周（孔子時代），非北周/後周；「周卜」2字姓名撞庫檢驗為誤警"
    j["period"] = "pre-qin"
    j["period_basis"] = "據 dynasty「周」（先秦）訂正"
    save(p, j, get_indent(p))
    sync_work_index_fields(wid, {"dynasty": "周", "period": "pre-qin"})

    # B5. 周易分野：不屬本bug模式，記錄存證，不動
    print("B5 周易分野（1evr5e3m6vjc5）：無撰人姓名，「周」為書名「周易」首字非朝代，"
          "不屬本bug模式，不予變動，記入known-issues。")

    print("round2 done")


if __name__ == "__main__":
    main()
