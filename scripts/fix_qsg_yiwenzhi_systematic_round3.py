#!/usr/bin/env python3
"""清史稿藝文志系統性排查 Round 3：ambiguous桶（真歧義朝代字：梁/宋/
魏/周，sub-variant分屬不同period值）之逐條核實與訂正。

34條citation之朝代字首雖屬SCHEMA.md「需拆分之歧義朝代」，然逐條核
對後發現，皆為極清晰、可憑姓名逕定之著名歷史人物，無一存在真正
disambiguation困難：

  - 「梁」（12條）：皆為南朝梁人物（嚴植之/皇侃/阮孝緒/庾儼默/
    樊恭/賀述/劉杳/太史叔明/褚仲都/梁武帝/梁元帝×2），無一為
    後梁（五代）人物 → nanbeichao。
  - 「宋」（10條）：分兩類——顏延之、僧慧琳為南朝宋（劉宋）人物
    → nanbeichao；趙善譽/馮椅/蔡淵/李杞/俞琰/袁燮/丁易東/傅寅
    皆為南宋易學/經學名家 → song。此組印證SCHEMA「宋」確實需
    逐條判，機械批次會誤判。
  - 「魏」（9條）：皆為三國魏（曹魏）人物（王肅×2/何晏/蔣濟/
    三字石經/王朗/周生烈/王弼），無一為北魏人物 → three-kingdoms。
  - 「周」（3條）：皆為先秦周人物（孔穿/辛甲/宋鈃），依SCHEMA
    「東周/春秋戰國」歸入 → pre-qin。

另查得「帝金樓子」「帝古今同姓名錄」二條原誤連結至朝鮮李朝儒者
崔永慶（字「孝元」，CBDB courtesy-name低信度誤配），實應為梁元帝
蕭繹本人著作，一併訂正並改連正確entity。

「慧琳」條刻意不連結entity——庫中僅有唐代釋慧琳（一切經音義作者）
entity，與本條南朝宋慧琳（均善論作者）為同名異代之不同僧人，不可
誤連，逕留空。
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


def sync_entity_index_fields(eid, fields):
    s = shard_of(eid)
    p = ROOT / "index" / "entities" / f"{s:x}.json"
    idx = load(p)
    if eid in idx:
        idx[eid].update(fields)
        save(p, idx, get_indent(p))


def detach_entity_work(eid, wid):
    p = find_entity(eid)
    e = load(p)
    e["works"] = [w for w in e.get("works", []) if w.get("work_id") != wid]
    save(p, e, get_indent(p))


def link_and_fix(wid, name, dyn, period, eid, note, fix_entity_dynasty=None):
    """訂正Work.period/dynasty/authors，並視情況連結/訂正entity。"""
    p = find_work(wid)
    j = load(p)
    if eid:
        j["authors"] = [{"name": name, "role": "撰", "dynasty": dyn, "entity_id": eid}]
    else:
        a = j.get("authors")
        if a and isinstance(a, list) and isinstance(a[0], dict):
            a[0]["dynasty"] = dyn
            a[0].pop("dynasty_basis", None)
        elif not a:
            pass  # no authors array; leave as top-level-only fix
    if j.get("dynasty") is not None or eid or not j.get("authors"):
        j["dynasty"] = dyn
    j["dynasty_basis"] = f"2026-08-18 清史稿藝文志系統性排查Round3：{note}"
    j["period"] = period
    j["period_basis"] = f"據 authors[0].dynasty「{dyn}」或citation朝代字首 訂正（Round3）"
    save(p, j, get_indent(p))
    sync_work_index_fields(wid, {"dynasty": dyn, "period": period, "author": name})

    if eid:
        ep = find_entity(eid)
        e = load(ep)
        if not any(w.get("work_id") == wid for w in e.get("works", [])):
            e.setdefault("works", []).append({"work_id": wid, "role": "撰"})
        if fix_entity_dynasty:
            e["dynasty"] = fix_entity_dynasty[0]
            if len(fix_entity_dynasty) > 1 and fix_entity_dynasty[1]:
                e["period"] = fix_entity_dynasty[1]
            e["ai_note"] = e.get("ai_note", "") + f" 2026-08-18 清史稿藝文志系統性排查Round3：{note}"
        save(ep, e, get_indent(ep))
        sync_entity_index_fields(eid, {"dynasty": e.get("dynasty"), "period": e.get("period")})


def detach_and_relink(wid, name, eid_new, eid_old, dyn, period, note):
    detach_entity_work(eid_old, wid)
    link_and_fix(wid, name, dyn, period, eid_new, note)


def main():
    # === 梁組（12條）：南朝梁 -> nanbeichao ===
    link_and_fix("1evr5e3m7t8v5", "嚴植之", "梁", "nanbeichao", "1j96hfs6cxvcw",
                 "嚴植之（南朝梁經學家），citation「梁嚴植之孝經注」明載")
    link_and_fix("1evr5e3m7t8v6", "皇侃", "梁", "nanbeichao", "1j96a9e5iy7ls",
                 "皇侃（南朝梁著名經學家，已有多部著作正確歸類，本條為漏修之另一著作）")
    link_and_fix("1evr5e3m8fpy2", "阮孝緒", "梁", "nanbeichao", "1j96ad6h4w9og",
                 "阮孝緒（南朝梁著名目錄學家，七錄作者）")
    link_and_fix("1evr5e3m8fpy3", "庾儼默", "梁", "nanbeichao", None,
                 "庾儼默，citation「梁庾儼默演說文」明載，庫中無既有entity可連")
    link_and_fix("1evr5e3m8fpy4", "樊恭", "梁", "nanbeichao", "1j96hllgt8d1c",
                 "樊恭（南朝梁人，廣蒼一書之撰者）")
    link_and_fix("1evr5e3m7i0d4", "賀述", "梁", "nanbeichao", "1j96heal0d8n4",
                 "賀述（南朝梁人，賀氏經學世家）")
    link_and_fix("1evr5e3mbvbyl", "劉杳", "南朝梁", "nanbeichao", "1j969m70q2eps",
                 "劉杳（字士深，南朝梁人，撰要雅），原entity誤植南朝宋，訂正",
                 fix_entity_dynasty=("南朝梁", "nanbeichao"))
    link_and_fix("1evr5e3m7t8yq", "太史叔明", "梁", "nanbeichao", "1j96ha708pc00",
                 "太史叔明（南朝梁經學家）")
    link_and_fix("1evr5e3m7t8yr", "褚仲都", "梁", "nanbeichao", "1j96ha56mdczk",
                 "褚仲都（南朝梁經學家，通易、周禮）")
    link_and_fix("1evr5e3m7t8v4", "梁武帝", "梁", "nanbeichao", "1j967afjav1vw",
                 "梁武帝蕭衍，citation「梁武帝孝經義疏」明載")
    detach_and_relink("1evr5e3mc6kj6", "梁元帝", "1j96hf83t28lc", "1j96h8rw6xrtr",
                       "梁", "nanbeichao",
                       "梁元帝蕭繹《古今同姓名錄》，原entity_id所指崔永慶（朝鮮李朝儒者，字孝元，"
                       "CBDB courtesy-name低信度誤配）與此書全然無涉，改連正確entity（梁元帝）")
    detach_and_relink("1evr5e3mbvbyb", "梁元帝", "1j96hf83t28lc", "1j96h8rw6xrtr",
                       "梁", "nanbeichao",
                       "梁元帝蕭繹《金樓子》，同上，原entity誤配至崔永慶，改連正確entity")

    # === 宋組（10條）：2南朝宋(nanbeichao) + 8宋代(song) ===
    link_and_fix("1evr5e3m7t8yl", "顏延之", "南朝宋", "nanbeichao", "1j968k0jdrlz5",
                 "顏延之（384-456，南朝宋著名文學家，與謝靈運齊名），citation「宋顏延之論語說」明載")
    link_and_fix("1evr5e3m7t8ym", "慧琳", "南朝宋", "nanbeichao", None,
                 "南朝宋僧慧琳（撰均善論等，宋文帝時人），庫中僅有唐代釋慧琳〔一切經音義作者〕"
                 "entity，二者為同名異代之不同僧人，不可誤連，逕留空")
    link_and_fix("1evr5e3m6vjbh", "趙善譽", "宋", "song", "1j967afjb6af1",
                 "趙善譽（南宋宗室，字靜之），citation「宋趙善譽易說」明載")
    link_and_fix("1evr5e3m6vjbi", "馮椅", "宋", "song", "1j96hl6touhog",
                 "馮椅（1140-1231，字奇之，南宋易學家，號厚齋）")
    link_and_fix("1evr5e3m6vjbj", "蔡淵", "宋", "song", "1j967afjb6afb",
                 "蔡淵（蔡元定長子，南宋朱熹門人）")
    link_and_fix("1evr5e3m6vjbk", "李杞", "宋", "song", "1j96h8rw6xruu",
                 "李杞，citation「宋李杞周易詳解」明載")
    link_and_fix("1evr5e3m6vjbl", "俞琰", "宋", "song", "1j96a9e6vbzsw",
                 "俞琰（字玉吾，著名易學家），entity本身標「宋末元初」跨代人物，"
                 "本作citation明載「宋」，Work層依citation訂正為song")
    link_and_fix("1evr5e3m76ruf", "袁燮", "宋", "song", "1j967afjbsrix",
                 "袁燮（字和叔，號絜齋，南宋心學家）")
    link_and_fix("1evr5e3m6vjbm", "丁易東", "宋", "song", "1j967cp21keum",
                 "丁易東，citation「宋丁易東周易象義」明載")
    link_and_fix("1evr5e3m76rrf", "傅寅", "宋", "song", "1j967afjbsriv",
                 "傅寅（南宋學者，撰禹貢說斷）")

    # === 魏組（9條）：三國魏 -> three-kingdoms ===
    link_and_fix("1evr5e3m76rrk", "王肅", "魏", "three-kingdoms", "1j96glo90rdhd",
                 "王肅（曹魏經學家，注群經），citation「魏王肅尚書註」明載")
    link_and_fix("1evr5e3m6vjc8", "何晏", "魏", "three-kingdoms", "1j96ad6aoyy2o",
                 "何晏（曹魏玄學家，注論語），citation「魏何晏周易解」明載")
    link_and_fix("1evcmncp2msqo", "蔣濟", "魏", "three-kingdoms", "1j96keesd3j7k",
                 "蔣濟（曹魏重臣），citation「魏蔣濟蔣子萬機論」明載")
    link_and_fix("1evr5e3m84hez", "三字石經", "魏", "three-kingdoms", None,
                 "曹魏正始年間所立三體（三字）石經，非人名，citation「魏三字石經尚書」明載")
    link_and_fix("1evr5e3m7t8y3", "王朗", "魏", "three-kingdoms", "1j96kee2c14hs",
                 "王朗（曹魏司徒，王肅之父），citation「魏王朗論語說」明載")
    link_and_fix("1evr5e3m7t8y4", "王肅", "魏", "three-kingdoms", "1j96glo90rdhd",
                 "王肅另一著作，citation「魏王肅論語義說」明載")
    link_and_fix("1evr5e3m7t8y5", "周生烈", "魏", "three-kingdoms", "1j96ha89l8gzk",
                 "周生烈（曹魏博士，注論語）")
    link_and_fix("1evr5e3m84hep", "王肅", "魏", "three-kingdoms", "1j96glo90rdhd",
                 "王肅另一著作，citation「魏王肅聖證論」明載")
    link_and_fix("1evr5e3m7t8y6", "王弼", "魏", "three-kingdoms", "1j96kee48pc00",
                 "王弼（曹魏玄學家，注老子、周易），citation「魏王弼論語釋疑」明載")

    # === 周組（3條）：先秦周 -> pre-qin ===
    link_and_fix("1ev7xkhnxg35s", "孔穿", "周", "pre-qin", "1j96hehf4obnk",
                 "孔穿（字子高，孔子六世孫，戰國時人），citation「周孔穿讕言」明載")
    link_and_fix("1evr5e3mchszk", "辛甲", "周", "pre-qin", "1j96hex71ei9s",
                 "辛甲（商末周初人，周太史），citation「周辛甲書」明載")
    link_and_fix("1ev7xki0hfpq8", "宋鈃", "周", "pre-qin", "1j96hex3ghhxc",
                 "宋鈃（戰國宋國思想家，宋尹學派），citation「周宋鈃宋子」明載，"
                 "原entity無dynasty/period記錄，一併補全",
                 fix_entity_dynasty=("周", "pre-qin"))

    print("round3 done")


if __name__ == "__main__":
    main()
