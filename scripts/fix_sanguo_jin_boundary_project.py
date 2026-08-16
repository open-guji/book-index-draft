#!/usr/bin/env python3
"""三國魏晉「period邊界個案」獨立立項：系統性核校period=jin範圍內
dynasty明確為三國魏／三國吳／三國蜀之記錄，逐一核實人物卒年是否
早於265年（晉代建立），決定period歸屬。

執行三國魏晉探勘輪原始建議：「先普查所有『dynasty明確為三國魏／
三國吳／三國蜀，而period=jin』之記錄全集，逐條核實人物卒年是否
早於265年，再決定是否整批移動period，而非逐條零星處理」。

普查結果：18組（35作品）。核實後發現多數對應Entity本身早已由
其他管道（或本session稍早批次）確立period=three-kingdoms，僅Work
記錄未同步——此類直接依Entity同步，非本輪之編輯判斷：
  嵇康（8）、薛瑩（3）、沈瑩（1）、韋昭（1）、譙周/1j96a9ecduxa8（1）。

另4組之Entity無entity_id或Entity尚屬period=jin，經逐一核實生平：

  A. 王弼（226-249）：庫中已有既有正確Entity（1j96kee48pc00，三國魏
     ／three-kingdoms，16作品），逕予補繫。
  B. 徐幹（170-217，建安七子）：dynasty_basis本身已標記
     「known_mislabel」，庫中已有正確Entity（1j96h8rw7k8xg，東漢／
     qin-han，3作品）——徐幹卒於217年，早於曹魏建國（220）與晉代
     建立（265）皆遠，正確歸屬應為東漢，非三國魏亦非晉，逕予訂正
     並補繫。
  C. 譙周（4作品之分裂Entity，1j96kegkid5vk，primary_name殘缺為
     單字「周」）：與既有正確之譙周Entity（1j96a9ecduxa8，
     three-kingdoms，13作品，201-270）為同一人，合併。
  D. 陳術：著錄本身載「陳術乃劉蜀時人」（見《華陽國志》），無晉代
     仕歷佐證，訂正為three-kingdoms。

其餘經逐一核實生平佐證後，確認**應維持period=jin不予變動**（此
決定本身即為本輪獨立立項之產出，非疏漏）：
  - 荀輝：著錄本身載「晉太子中庶子」，明確仕於晉朝。
  - 楊泉：史學界普遍歸類為西晉思想家（撰物理論於晉初），著錄稱
    「徵士」（晉朝徵召之隱士），逕予補繫其無entity_id之第三作品。
  - 郤正：263年隨劉禪降魏後仕於西晉，278年方卒，仕歷明確跨入晉代。

顏幼明：Entity（1j96keh0wmx34）之birth/death年份（785-866）為
CBDB錯誤比對之殘留（與唐代另一同名人物混淆），與dynasty_basis本身
所載「三國魏人」矛盾，卸除錯誤年份；然因生平記載過簡（僅知其
注《靈棋經》，見《郡齋讀書志》），無充分證據判定是否曾仕於晉代，
period暫不變動，留待未來查核。

劉徽、孫登、荀融：生平記載不足（無生卒年、亦無明確之晉代或
三國仕歷佐證），本輪不予處理，留待未來個案查核。
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


# entities already period=three-kingdoms, just sync mismatched works
SYNC_TO_SANGUO = ["1j967a0kj9gyf", "1j96hhvcrjvig", "1j967cp1zdr2m",
                  "1j96gmdzkugw0", "1j96a9ecduxa8"]

# 陳術：獨立訂正
CHEN_SHU_WID = "1evfuvkvro3y8"

# 顏幼明：僅清除錯誤生卒年
YAN_YOUMING_EID = "1j96keh0wmx34"

# 楊泉：補繫無entity_id之第三作品
YANG_QUAN_EID = "1j96kegqemj9c"
YANG_QUAN_ORPHAN_WID = "1ewsa4atbb2pa"

# 王弼：補繫至既有正確Entity
WANG_BI_WID = "1evkpy1pzn20w"
WANG_BI_EID = "1j96kee48pc00"

# 徐幹：訂正為東漢並補繫
XU_GAN_WID = "1ewsa4a57jclw"
XU_GAN_EID = "1j96h8rw7k8xg"

# 譙周：合併分裂Entity
QIAOZHOU_BASE = "1j96a9ecduxa8"
QIAOZHOU_DONOR = "1j96kegkid5vk"


def sync_work(wid, widx, dyn, period, eid, note):
    p = widx.get(wid)
    if not p:
        return False
    j = load(p)
    a0 = j["authors"][0]
    a0["dynasty"] = dyn
    a0.pop("dynasty_basis", None)
    if eid:
        a0["entity_id"] = eid
    if j.get("dynasty") is not None:
        j["dynasty"] = dyn
    j["period"] = period
    j["period_basis"] = f"據 authors[0].dynasty「{dyn}」（2026-08-13 三國魏晉period邊界獨立立項：{note}）"
    save(p, j, get_indent(p))
    return True


def main():
    widx = build_work_index()
    eidx_paths = build_entity_index()
    eidx = {eid: load(p) for eid, p in eidx_paths.items()}
    fixed = 0

    # 1. sync entities already three-kingdoms
    for eid in SYNC_TO_SANGUO:
        ent = eidx[eid]
        dyn = ent.get("dynasty")
        for w in ent.get("works", []):
            wid = w.get("work_id")
            p = widx.get(wid)
            if not p:
                continue
            j = load(p)
            a = j.get("authors")
            if not a or not isinstance(a, list) or not isinstance(a[0], dict):
                continue
            if a[0].get("entity_id") != eid or j.get("period") != "jin":
                continue
            note = f"{ent.get('primary_name')}：Entity早已確立period=three-kingdoms，Work記錄未同步"
            if sync_work(wid, widx, dyn, "three-kingdoms", eid, note):
                fixed += 1

    # 2. 陳術
    j = load(widx[CHEN_SHU_WID])
    dyn = j["authors"][0]["dynasty"]
    sync_work(CHEN_SHU_WID, widx, dyn, "three-kingdoms", j["authors"][0].get("entity_id"),
               "陳術：著錄本身載「陳術乃劉蜀時人」，無晉代仕歷佐證")
    fixed += 1

    # 3. 顏幼明：清除錯誤生卒年
    ent_p = eidx_paths[YAN_YOUMING_EID]
    ent = load(ent_p)
    ent.pop("birth_year", None)
    ent.pop("death_year", None)
    ent["ai_note"] = ent.get("ai_note", "") + " 2026-08-13：三國魏晉period邊界獨立立項查核：birth/death年份（785-866）與dynasty_basis所載「三國魏人」矛盾，係CBDB與唐代另一同名人物混淆之殘留，卸除；因生平記載過簡，period暫不變動。"
    ent["external_ids"] = {}
    save(ent_p, ent, get_indent(ent_p))

    # 4. 楊泉：補繫第三作品
    ent_p = eidx_paths[YANG_QUAN_EID]
    ent = load(ent_p)
    ent_works = {w["work_id"]: w for w in ent.get("works", [])}
    ent_works.setdefault(YANG_QUAN_ORPHAN_WID, {"work_id": YANG_QUAN_ORPHAN_WID, "role": "撰"})
    ent["works"] = list(ent_works.values())
    save(ent_p, ent, get_indent(ent_p))
    j = load(widx[YANG_QUAN_ORPHAN_WID])
    j["authors"][0]["entity_id"] = YANG_QUAN_EID
    save(widx[YANG_QUAN_ORPHAN_WID], j, get_indent(widx[YANG_QUAN_ORPHAN_WID]))

    # 5. 王弼：補繫至既有正確Entity
    ent_p = eidx_paths[WANG_BI_EID]
    ent = load(ent_p)
    ent_works = {w["work_id"]: w for w in ent.get("works", [])}
    ent_works.setdefault(WANG_BI_WID, {"work_id": WANG_BI_WID, "role": "注"})
    ent["works"] = list(ent_works.values())
    save(ent_p, ent, get_indent(ent_p))
    sync_work(WANG_BI_WID, widx, "三國魏", "three-kingdoms", WANG_BI_EID,
              "王弼（226-249）：卒於晉代建立(265)前16年，補繫既有正確Entity")
    fixed += 1

    # 6. 徐幹：訂正為東漢並補繫
    ent_p = eidx_paths[XU_GAN_EID]
    ent = load(ent_p)
    ent_works = {w["work_id"]: w for w in ent.get("works", [])}
    ent_works.setdefault(XU_GAN_WID, {"work_id": XU_GAN_WID, "role": "撰"})
    ent["works"] = list(ent_works.values())
    save(ent_p, ent, get_indent(ent_p))
    sync_work(XU_GAN_WID, widx, "東漢", "qin-han", XU_GAN_EID,
              "徐幹（170-217，建安七子）：dynasty_basis本身已標記known_mislabel，卒於曹魏建國(220)前，正確歸屬為東漢")
    fixed += 1

    # 7. 譙周：合併分裂Entity
    base_p = eidx_paths[QIAOZHOU_BASE]
    base = load(base_p)
    base_works = {w["work_id"]: w for w in base.get("works", [])}
    donor_p = eidx_paths[QIAOZHOU_DONOR]
    donor = load(donor_p)
    donor_wids = [w["work_id"] for w in donor.get("works", [])]
    for w in donor.get("works", []):
        base_works.setdefault(w["work_id"], w)
    base["works"] = list(base_works.values())
    base["ai_note"] = base.get("ai_note", "") + " 2026-08-13：三國魏晉period邊界獨立立項：併入primary_name殘缺為單字「周」之分裂Entity（1j96kegkid5vk）。"
    save(base_p, base, get_indent(base_p))
    delete_entity(QIAOZHOU_DONOR, donor_p)

    for wid in donor_wids:
        j = load(widx[wid])
        a = j.get("authors")
        if a and isinstance(a, list) and isinstance(a[0], dict) and a[0].get("entity_id") == QIAOZHOU_DONOR:
            sync_work(wid, widx, "三國蜀", "three-kingdoms", QIAOZHOU_BASE,
                      "譙周：Entity分裂合併，既有正確Entity（201-270）早已確立period=three-kingdoms")
            fixed += 1

    print(f"fixed_works={fixed}")


if __name__ == "__main__":
    main()
