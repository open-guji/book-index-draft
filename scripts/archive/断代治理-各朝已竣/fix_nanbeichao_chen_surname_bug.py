#!/usr/bin/env python3
"""南北朝探勘：修復「陳」姓氏與朝代同形碰撞之系統性bug。

根源：多筆記錄之著錄格式為「（陳XX）」，其中「陳」在絕大多數情況下
其實是作者本人之姓氏（如「陳彭年」「陳士元」），而非朝代標記；但
歸戶/正規化流程一律將其當作朝代前綴處理（synonym:陳->南朝陳），
剝除「陳」字，僅留給名（如「彭年」「士元」）作為name欄，並將
dynasty/period錯誤地訂為南朝陳/nanbeichao。此問題僅發生於「陳」字
（南朝陳之簡稱恰與極常見漢姓「陳」同形），其他斷代同形字
（劉宋/南齊/姚秦/後魏等皆為雙字全稱，不受影響）皆未見此問題。

已透過本庫既有之正確Entity（多數此類人物本有另一條屬其真實朝代之
正確Entity，因本bug而衍生出重複的「南朝陳」分裂Entity）逐一核實
真實身分，區分兩類處理：

  A. 目標人物之正確Entity已存在庫中（見TARGET_MERGES）：將bug產生
     之重複Entity所繫Work改繫至正確Entity，訂正name/dynasty/period，
     刪除重複Entity。
  B. 目標人物之正確Entity不存在，僅原地訂正（見INPLACE_FIXES）：
     直接修正該Entity自身之dynasty/period，並視需要補回被剝除之
     「陳」姓。
  C. entity_id為None者（見DIRECT_WORK_FIXES）：無Entity可改，逕行
     訂正Work自身authors[0]欄位。

陳傅良／陳傳良（六作品）另案處理為Entity合併（併入既有之南宋
陳傅良Entity 1j967avzkq2v7）。

尚有部分人物（得一/儀之/顯敎/申之/七子/宗望/鳳羽/謀道/之方/混掌/
謝喬/承韜/樂產/臧兢/從運）因缺乏足夠外部佐證斷定真實朝代，暫不
處理，留待未來個案核實。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

# (buggy_entity_id, correct_entity_id, correct_name, correct_dynasty, correct_period, note)
TARGET_MERGES = [
    ("1j967c148wsnm_PARTIAL", "1j967avzmli53", "陳彭年", "北宋", "song",
     "陳彭年（961-1017，北宋《廣韻》重修者）：5條著錄因姓氏「陳」誤作朝代前綴而誤繫入同名之明代彭年（孔嘉，1j967c148wsnm）Entity，今改繫正確之北宋陳彭年Entity"),
    ("1j96hfsldkw74", "1j967avzmli53", "陳彭年", "北宋", "song",
     "陳彭年（與法官合編《大中祥符編勑》）：同上，改繫北宋陳彭年Entity"),
    ("1j96h8rw6xrug", "1j967avzmli5p", "陳耆卿", "南宋", "song",
     "陳耆卿：南宋學者，著錄誤植朝代「南朝陳」，改繫既有正確之南宋陳耆卿Entity"),
    ("1j96hhvcrv40b", "1j967afjbhix6", "陳士元", "明", "ming",
     "陳士元：明代學者（字心叔），著錄誤植朝代「南朝陳」，改繫既有正確之明代陳士元Entity"),
    ("1j96hjwlxny3k", "1j96hjwlxny21", "陳日華", "宋", "song",
     "陳日華：宋人，著錄誤植朝代「南朝陳」，改繫既有之陳日華Entity（其CBDB誤配已於先前清除，本次一併補period）"),
    ("1j96hg94sftvk", "1j967bgl6e32i", "陳仕賢", "明", "ming",
     "陳仕賢：明人，著錄誤植朝代「南朝陳」，改繫既有正確之明代陳仕賢Entity"),
    ("1j96hjwlylnoz", "1j967afjbsrj2", "陳大猷", "南宋", "song",
     "陳大猷：南宋末學者（書集傳或問等），著錄誤植朝代「南朝陳」，改繫既有正確Entity"),
    ("1j96hfx0g8lxc", "1j96hesijr2m8", "陳顯微", "南宋", "song",
     "陳顯微：南宋道士（抱一子），著錄誤植朝代「南朝陳」，改繫既有正確Entity"),
    ("1j96hfsgjppmo", "1j967da97jm09", "陳致雍", "唐", "sui-tang",
     "陳致雍：唐代禮學家，著錄誤植朝代「南朝陳」，改繫既有正確Entity"),
    ("1j96hei0t1log", "1j96hei092eww", "陳康士", "唐", "sui-tang",
     "陳康士：晚唐琴家（著錄引皮日休為之作序，皮日休834-883），著錄誤植朝代「南朝陳」，改繫既有正確Entity"),
    ("1j96hei1ew7pc", "1j96hei092eww", "陳康士", "唐", "sui-tang",
     "陳康士（同上，另一分裂Entity）"),
    ("1j96hg31kevwg", "1j967bgl7n1ac", "陳無己", "北宋", "song",
     "陳無己（即陳師道，字無己/無巳，北宋詩人）：著錄誤植朝代「南朝陳」，改繫既有正確之陳師道Entity"),
    ("1j96kenesaio0", "1j96ha8re2o74", "陳長壽", "西晉", "jin",
     "陳長壽：《魏名臣奏》撰者，著錄誤植朝代「南朝陳」；本條題名「魏笙仁臣奏」疑為「魏名臣奏」之OCR異文，與既有西晉陳長壽Entity所繫之1evfuvf9ke0ao《魏名臣奏》極可能為同書異錄，暫先改繫既有Entity並於work層註記待未來查核是否為重出"),
    ("1j96hhvcrv408", "1j967avzkeuc1", "陳祥道", "北宋", "song",
     "陳祥道：北宋禮學家，著錄誤植朝代「南朝陳」，改繫既有正確Entity"),
    ("1j96hjwlylnpi", "1j967bgl7bspd", "陳全之", "明", "ming",
     "陳全之：明人，著錄誤植朝代「南朝陳」，改繫既有正確Entity"),
]

# (entity_id, correct_name, correct_dynasty, correct_period, note)
INPLACE_FIXES = [
    ("1j96hhvcrv405", "陳希亮", "北宋", "song",
     "陳希亮：北宋官員（蘇軾為撰神道碑），著錄誤植朝代「南朝陳」，原地訂正"),
    ("1j96hjwlylnp0", "陳鵬飛", "南宋", "song",
     "陳鵬飛：南宋經學家（詩解不解商魯二頌），著錄誤植朝代「南朝陳」，原地訂正"),
    ("1j967da97uuiy", "陳孔碩", "南宋", "song",
     "陳孔碩：南宋學者，著錄誤植朝代「南朝陳」，原地訂正"),
    ("1j96heq8m9pts", "陳槱", "南宋", "song",
     "陳槱：南宋人（負暄野錄，書中稱聞諸老先生議論），著錄誤植朝代「南朝陳」，原地訂正"),
    ("1j96hg1axrsao", "陳嗣古", "宋", "song",
     "陳嗣古：宋人（公孫龍子注），著錄誤植朝代「南朝陳」，原地訂正（南北未能確判，暫用籠統「宋」）"),
]

# (work_id, correct_name, correct_dynasty, correct_period, note)
DIRECT_WORK_FIXES = [
    ("1evjr9q5svchs", "陳作霖", "中華民國", "modern",
     "陳作霖：清末民初南京地方史家，既有正確Entity（1j96h8rw6xrtt）已作「中華民國」，本work原缺entity_id且誤植「南朝陳」，逕行訂正並補繫"),
    ("1evjr9u6nlvcw", "陳夔龍", "清", "qing",
     "陳夔龍：清末官員（1857-1948），著錄誤植朝代「南朝陳」，逕行訂正（庫中無既有Entity可繫）"),
    ("1evjr9sof4hkw", "陳衍", "清", "qing",
     "陳衍：清末民初詩論家（1856-1937），name欄本已保留全名，僅dynasty/period誤植，逕行訂正"),
    ("1evjrail630u8", "陳衍", "清", "qing",
     "陳衍（同上，另一work）"),
    ("1evjr9sgg9edc", "陳三立", "清", "qing",
     "陳三立：清末詩人（1853-1937，陳寅恪之父），著錄誤植朝代「南朝陳」，逕行訂正"),
    ("1evjraippc4xs", "陳田", "清", "qing",
     "陳田：清代學者（明詩紀事輯者，1849-1921），name欄本已保留全名，僅dynasty/period誤植，逕行訂正"),
]

# 陳傅良/陳傳良：Entity合併，併入既有正確Entity
CHUAN_LIANG_DONOR = "1j96gmtkzgo3k"
CHUAN_LIANG_TARGET = "1j967avzkq2v7"


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


def build_entity_index():
    idx = {}
    for f in Path(ROOT / "Entity").rglob("*.json"):
        try:
            j = load(f)
        except Exception:
            continue
        if isinstance(j, dict) and j.get("id"):
            idx[j["id"]] = f
    return idx


def delete_entity(eid, ent_path):
    ent_path.unlink()
    s = shard_of(eid)
    p = ROOT / "index" / "entities" / f"{s:x}.json"
    d = load(p)
    if eid in d:
        del d[eid]
        save(p, d, indent=get_indent(p))


def fix_work_record(j, path, name, dyn, period, note, eid=None):
    a0 = j["authors"][0]
    a0["name"] = name
    a0["dynasty"] = dyn
    if eid:
        a0["entity_id"] = eid
    a0.pop("dynasty_basis", None)
    if j.get("dynasty") is not None:
        j["dynasty"] = dyn
    j["period"] = period
    j["period_basis"] = f"據 authors[0].dynasty「{dyn}」（2026-08-13 南北朝探勘查出「陳」姓氏誤作朝代前綴之bug：{note}）"
    save(path, j, get_indent(path))


def main():
    widx = build_work_index()
    eidx = build_entity_index()

    fixed_works = 0
    deleted_entities = 0

    # TARGET_MERGES
    for buggy_eid_tag, correct_eid, name, dyn, period, note in TARGET_MERGES:
        correct_p = eidx[correct_eid]
        correct = load(correct_p)
        correct_works = {w["work_id"]: w for w in correct.get("works", [])}

        if buggy_eid_tag == "1j967c148wsnm_PARTIAL":
            # 部分work改繫：直接找出這些work，從舊entity的works[]中移除，
            # 加入新entity
            partial_wids = ["1evgph79mm2o0", "1evgpii6d3bb4", "1evgpiuh4lds0",
                             "1evgorh333chs", "1evf1nhfz3lz4"]
            wrong_p = eidx["1j967c148wsnm"]
            wrong = load(wrong_p)
            wrong["works"] = [w for w in wrong.get("works", []) if w["work_id"] not in partial_wids]
            save(wrong_p, wrong, get_indent(wrong_p))
            for wid in partial_wids:
                correct_works.setdefault(wid, {"work_id": wid, "role": "撰"})
                p = widx[wid]
                j = load(p)
                fix_work_record(j, p, name, dyn, period, note, eid=correct_eid)
                fixed_works += 1
        else:
            buggy_p = eidx[buggy_eid_tag]
            buggy = load(buggy_p)
            for w in buggy.get("works", []):
                correct_works.setdefault(w["work_id"], w)
                p = widx.get(w["work_id"])
                if p:
                    j = load(p)
                    fix_work_record(j, p, name, dyn, period, note, eid=correct_eid)
                    fixed_works += 1
            delete_entity(buggy_eid_tag, buggy_p)
            deleted_entities += 1

        correct["works"] = list(correct_works.values())
        save(correct_p, correct, get_indent(correct_p))

    # INPLACE_FIXES
    for eid, name, dyn, period, note in INPLACE_FIXES:
        ent_p = eidx[eid]
        ent = load(ent_p)
        ent["primary_name"] = name
        ent["dynasty"] = dyn
        ent["period"] = period
        ent["period_basis"] = f"據 dynasty「{dyn}」（2026-08-13 南北朝探勘：{note}）"
        ent["ai_note"] = ent.get("ai_note", "") + f" 2026-08-13：{note}"
        save(ent_p, ent, get_indent(ent_p))
        for w in ent.get("works", []):
            p = widx.get(w["work_id"])
            if p:
                j = load(p)
                fix_work_record(j, p, name, dyn, period, note, eid=eid)
                fixed_works += 1

    # DIRECT_WORK_FIXES
    for wid, name, dyn, period, note in DIRECT_WORK_FIXES:
        p = widx[wid]
        j = load(p)
        a0 = j["authors"][0]
        eid = a0.get("entity_id")
        fix_work_record(j, p, name, dyn, period, note, eid=eid)
        fixed_works += 1

    # 陳傅良/陳傳良 Entity合併
    target_p = eidx[CHUAN_LIANG_TARGET]
    target = load(target_p)
    target_works = {w["work_id"]: w for w in target.get("works", [])}
    donor_p = eidx[CHUAN_LIANG_DONOR]
    donor = load(donor_p)
    note = "陳傅良（南宋，1137-1203）：另一分裂Entity「傅良」/「傳良」（姓氏「陳」誤作朝代前綴）併入既有正確之南宋陳傅良Entity"
    for w in donor.get("works", []):
        target_works.setdefault(w["work_id"], w)
        p = widx.get(w["work_id"])
        if p:
            j = load(p)
            fix_work_record(j, p, "陳傅良", "南宋", "song", note, eid=CHUAN_LIANG_TARGET)
            fixed_works += 1
    target["works"] = list(target_works.values())
    save(target_p, target, get_indent(target_p))
    delete_entity(CHUAN_LIANG_DONOR, donor_p)
    deleted_entities += 1

    print(f"fixed_works={fixed_works}, deleted_entities={deleted_entities}")


if __name__ == "__main__":
    main()
