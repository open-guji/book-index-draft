#!/usr/bin/env python3
"""南北朝探勘第二輪：修復首輪遺漏之個案。

第一輪修復「陳」姓氏誤作朝代前綴bug時，遺漏三類問題：

  1. 王安石/歐陽修/司馬光/蕭楚/陳傅良（另一work）/陳耆卿（以字
     「壽老」著錄之孟子紀蒙）：Entity早已正確（dynasty/period皆
     已正確），僅Work自身之period欄位未同步，逕行訂正。
  2. 周顯/戴顯(戴顒)/王弘：首輪exploration已查出並記錄，但consolidate
     時漏未寫入修復腳本，今補做。三者皆為CBDB「pending_accept」
     誤配（entity_propagation_r2），著錄內證另有明確斷代線索。
  3. 顧野王/許亨：Work層本身之authors[0].dynasty原已正確（南朝陳），
     然二者之Entity卻分別遭CBDB誤配污染（顧野王→清、許亨→元），
     且皆為pending_accept未確認狀態，今卸除污染並回復正確值。
  4. 陳汝元：首輪exploration已核實其著錄「皇明浙士登科考」明載
     為明代人，然consolidate時漏未列入修復腳本，今補做（其CBDB
     配對之dynasty「明」恰好正確，僅需訂正name/period）。
  5. 陳耀文：外部查證確認為明代學者（1524-1605，著天中記／學圃
     萱蘇），其Entity遭CBDB誤配至一位完全不相干之清代人物「鄂哲
     忒奎成」，primary_name/dynasty皆遭覆蓋，今卸除污染並訂正。
  6. 謝喬/申之/七子/宗望/鳳羽/得一/儀之：七者之Entity同樣遭CBDB
     誤配污染，primary_name遭覆蓋為完全不相干之他代人物（如「鄂哲
     忒奎成」「諸重光」「朱瞻墺」「陸黃鉞」「馮氏」「周天鳳」等），
     然外部查證未能確認其真實朝代，僅能卸除CBDB污染、回復姓氏
     「陳」+原有給名，dynasty回復著錄原值「南朝陳」（即Work層
     synonym:陳->南朝陳之原始基準值），此非斷定其確為南朝陳人，
     僅係在缺乏更佳證據下之保守回復，仍留供未來個案核實。
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


# (work_id, note) — 僅period需同步為song，dynasty/entity已正確
PERIOD_ONLY_SONG = [
    ("1ev3bcwz7sc8w", "王安石《臨川集》：Entity/dynasty已正確（北宋），僅period未同步"),
    ("1evcs0boa9ce8", "歐陽修《唐書》：同上"),
    ("1ev3b9zs0ly4g", "司馬光《書儀》：同上"),
    ("1ev3ba2muoglc", "蕭楚《春秋辨疑》：同上"),
    ("1ev3ba2q33z7k", "陳傅良《春秋後傳》：同上"),
    ("1evgor30i6o00", "陳耆卿（字壽老）《孟子紀蒙》：同上，「壽老」為陳耆卿本人字號，非另一人"),
]

# (work_id, entity_id, correct_name, correct_dynasty, correct_period, note)
ENTITY_CBDB_FIXES = [
    ("1evdmn7y6d0cg", "1j96hjwlxz6mi", "周顯", "南朝齊", "nanbeichao",
     "著錄載「齊中書郎周顯」，Entity遭CBDB誤配「明」（pending_accept），卸除並訂正"),
    ("1evcpctiecfsw", "1j96hjwlxny4f", "戴顒", "南朝宋", "nanbeichao",
     "著錄載「宋散騎常侍戴顒撰」，name原作「戴顯」疑為「顒」之形近之誤，Entity遭CBDB誤配「明」（pending_accept），卸除並訂正"),
    ("1evcpjzolwzk0", "1j96hjwlxny4g", "王弘", "南朝宋", "nanbeichao",
     "王弘（379-432，琅邪王氏，南朝宋名臣，嫻於禮儀故實，與書儀之著述相符），Entity遭CBDB誤配「明」（pending_accept），卸除並訂正"),
    ("1evgpjke4ak8w", "1j968si3dt6v5", "顧野王", "南朝陳", "nanbeichao",
     "顧野王（519-581，玉篇作者）：Work層dynasty本已正確（南朝陳），然Entity遭CBDB誤配「清」（curated:玉篇某清刻本），卸除並回復"),
    ("1evgpgtotx4ao", "1j96hjwlylnpb", "許亨", "南朝陳", "nanbeichao",
     "許亨（南朝陳史家，撰梁史）：Work層dynasty本已正確（南朝陳），然Entity遭CBDB誤配「元」（pending_accept），卸除並回復"),
    ("1evgpjftgas5c", "1j96hjwlylnpm", "陳汝元", "明", "ming",
     "陳汝元：著錄「皇明浙士登科考」明載為明代人，name原缺姓氏「陳」，dynasty經CBDB配對恰為「明」（正確），今補姓氏並訂正period"),
    ("1evgq0yit9zi8", "1j96hjwlylnq0", "陳耀文", "明", "ming",
     "陳耀文（1524-1605，天中記／學圃萱蘇作者，確為明代學者）：Entity遭CBDB誤配至完全不相干之清代人物「鄂哲忒奎成」（primary_name/dynasty皆遭覆蓋），今卸除污染並訂正為正確身分"),
]

# 缺乏足夠外部佐證斷定真實朝代者：僅卸除CBDB污染，回復姓氏「陳」+
# 原有給名，dynasty回復著錄原值「南朝陳」（保守回復，非斷定）
UNCERTAIN_REVERT = [
    ("1evgoqa11q51c", "1j96hjwlylnp3", "陳謝喬",
     "Entity遭CBDB誤配（pending_accept），primary_name遭覆蓋，卸除污染並保守回復姓氏，真實朝代仍待查"),
    ("1evgpjscs7bb4", "1j96hjwlylnpq", "陳申之",
     "同上（primary_name原覆蓋為「諸重光」，清代人物）"),
    ("1evgpohwg3cao", "1j96hjwlylnpw", "陳七子",
     "同上（primary_name原覆蓋為「朱瞻墺」，明宗室）"),
    ("1evgq5i7atam8", "1j96hjwlylnqc", "陳宗望",
     "同上（primary_name原覆蓋為「陸黃鉞」，清代人物）"),
    ("1evgq9yjg1yio", "1j96hjwlylnqi", "陳鳳羽",
     "同上（primary_name未遭覆蓋，僅dynasty遭誤配）"),
    ("1evgq1rixrsao", "1j96hjwlylnq5", "陳得一",
     "同上（primary_name原覆蓋為「馮氏(馮紹烈女)」，唐代人物）"),
    ("1evgoqyqk07b4", "1j96hjwlylnp6", "陳儀之",
     "同上（primary_name原覆蓋為「周天鳳」，元代人物）"),
]


def fix_work_and_entity(wid, eid, name, dyn, period, note, widx, eidx, clear_cbdb=True):
    p = widx[wid]
    j = load(p)
    a0 = j["authors"][0]
    a0["name"] = name
    a0["dynasty"] = dyn
    a0.pop("dynasty_basis", None)
    if j.get("dynasty") is not None:
        j["dynasty"] = dyn
    j["period"] = period
    j["period_basis"] = f"據 authors[0].dynasty「{dyn}」（2026-08-13 南北朝探勘第二輪：{note}）"
    save(p, j, get_indent(p))

    ent_p = eidx[eid]
    ent = load(ent_p)
    ent["primary_name"] = name
    ent["dynasty"] = dyn
    ent["period"] = period
    ent["period_basis"] = f"據 dynasty「{dyn}」（2026-08-13 南北朝探勘第二輪：{note}）"
    if clear_cbdb and "external_ids" in ent:
        ent["ai_note"] = ent.get("ai_note", "") + f" 2026-08-13：CBDB配對卸除（原cbdb_source: {ent['external_ids'].get('cbdb_source','')}），{note}。"
        ent["external_ids"] = {}
    ent.pop("dynasty_basis", None)
    ent.pop("birth_year", None)
    ent.pop("death_year", None)
    save(ent_p, ent, get_indent(ent_p))


def main():
    widx = build_work_index()
    eidx = build_entity_index()
    fixed = 0

    for wid, note in PERIOD_ONLY_SONG:
        p = widx[wid]
        j = load(p)
        j["period"] = "song"
        j["period_basis"] = f"據 authors[0].dynasty（2026-08-13 南北朝探勘第二輪：{note}）"
        save(p, j, get_indent(p))
        fixed += 1

    for wid, eid, name, dyn, period, note in ENTITY_CBDB_FIXES:
        fix_work_and_entity(wid, eid, name, dyn, period, note, widx, eidx)
        fixed += 1

    for wid, eid, name, note in UNCERTAIN_REVERT:
        fix_work_and_entity(wid, eid, name, "南朝陳", "nanbeichao", note, widx, eidx)
        fixed += 1

    print(f"fixed={fixed}")


if __name__ == "__main__":
    main()
