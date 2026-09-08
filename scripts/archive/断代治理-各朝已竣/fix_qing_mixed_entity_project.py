#!/usr/bin/env python3
"""清朝探勘：處理47個「明」組混合Entity獨立立項之部分（4組）。

  A. 蕭吉：真正之朝代誤植（非姓名巧合）。經核對「書目答問」「清
     史稿藝文志」皆明確標示「隋蕭吉」，確為隋代人（蕭吉，?-614，
     隋朝太常博士，著五行大義），Entity原dynasty誤植為「明」，
     訂正為隋/sui-tang，並同步全部11作品（含9筆先前period=None
     者，一併訂正）。

  B. 姚夔《飲和堂集》：真正姓名巧合之不同人物。引文明載「國朝姚
     夔撰。夔字胄師，號成葊，山陰人。順治甲午舉人，官安化縣知縣」
     ——順治甲午（1654）為清代年號，與明代名臣姚夔（1414-1473）
     完全不同之人物，原entity_id誤繫，今拆分建立新Entity。

  C. 劉均《蕺山年譜》：Entity本身death_year=1427與此作品內容（為
     劉宗周〔号蕺山，卒於1645〕所作年譜）明顯不符，判斷為不同之
     劉均，證據不足以確立其真實身分，逕予解除entity_id繫連，
     dynasty/period依其自身著錄（清史稿藝文志代填之「清」，
     暫定合理，蕺山年譜當成書於劉宗周身故後）維持不變。

  D. 曹學佺：《蜀中名勝記》《宋詩選》二作品，引文皆確認為同一
     明末人物本人之著作（如「明曹學佺撰...學佺所著本無此書之名
     ...摘其蜀中廣記內名勝一門」），與其22件其餘作品同屬ming，
     period因啟發式或欄位同步問題誤植為qing，訂正。
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


def new_id_from(seed):
    import hashlib
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    return "1j99" + h[:9]


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


def create_entity(eid, name, dyn, period, works, note):
    ent = {
        "schema_version": 1,
        "id": eid,
        "type": "entity",
        "subtype": "people",
        "primary_name": name,
        "dynasty": dyn,
        "works": [{"work_id": w, "role": "撰"} for w in works],
        "external_ids": {},
        "ai_note": note,
        "period": period,
        "period_basis": f"據 dynasty「{dyn}」（2026-08-13 清朝探勘混合Entity獨立立項：{note}）",
    }
    c1, c2, c3 = eid[0], eid[1], eid[2]
    ent_dir = ROOT / "Entity" / c1 / c2 / c3
    ent_dir.mkdir(parents=True, exist_ok=True)
    ent_path = ent_dir / f"{eid}-{name}.json"
    save(ent_path, ent, indent=2)

    s = shard_of(eid)
    idx_path = ROOT / "index" / "entities" / f"{s:x}.json"
    idx = load(idx_path)
    idx[eid] = {
        "id": eid, "type": "entity", "subtype": "people",
        "primary_name": name, "path": str(ent_path.relative_to(ROOT)),
        "dynasty": dyn, "period": period,
    }
    save(idx_path, idx, get_indent(idx_path))


def main():
    widx = build_work_index()
    eidx_paths = build_entity_index()

    # A. 蕭吉：訂正為隋/sui-tang，同步全部作品
    xiao_ji_eid = "1j969m70q2eqz"
    ent_p = eidx_paths[xiao_ji_eid]
    ent = load(ent_p)
    ent["dynasty"] = "隋"
    ent["period"] = "sui-tang"
    note_a = "蕭吉（?-614，隋朝太常博士，著五行大義）：書目答問/清史稿藝文志皆明確標示「隋蕭吉」，Entity原dynasty誤植「明」，訂正"
    ent["period_basis"] = f"據 dynasty「隋」（2026-08-13 清朝探勘：{note_a}）"
    ent["ai_note"] = ent.get("ai_note", "") + f" 2026-08-13：{note_a}"
    ent["external_ids"] = {}
    save(ent_p, ent, get_indent(ent_p))
    for w in ent.get("works", []):
        wid = w.get("work_id")
        p = widx.get(wid)
        if not p:
            continue
        j = load(p)
        a = j.get("authors")
        if not a or not isinstance(a, list) or not isinstance(a[0], dict):
            continue
        if a[0].get("entity_id") != xiao_ji_eid:
            continue
        a[0]["dynasty"] = "隋"
        a[0].pop("dynasty_basis", None)
        if j.get("dynasty") is not None:
            j["dynasty"] = "隋"
        j["period"] = "sui-tang"
        j["period_basis"] = f"據 authors[0].dynasty「隋」（2026-08-13 清朝探勘：{note_a}）"
        save(p, j, get_indent(p))

    # B. 姚夔《飲和堂集》：拆分建立新Entity
    yao_kui_wid = "1ev3be7fv8d8g"
    new_eid = new_id_from("姚夔清胄師成葊山陰")
    create_entity(new_eid, "姚夔", "清", "qing", [yao_kui_wid],
                   "與明代名臣姚夔（1414-1473）同名異人：本條字胄師，號成葊，山陰人，順治甲午舉人，官安化縣知縣，原誤繫至明代同名人物之Entity，今拆分獨立")
    # detach from old entity
    old_eid = "1j967c148abkc"
    old_p = eidx_paths[old_eid]
    old_ent = load(old_p)
    old_ent["works"] = [w for w in old_ent.get("works", []) if w["work_id"] != yao_kui_wid]
    save(old_p, old_ent, get_indent(old_p))
    j = load(widx[yao_kui_wid])
    j["authors"][0]["entity_id"] = new_eid
    j["authors"][0]["dynasty"] = "清"
    save(widx[yao_kui_wid], j, get_indent(widx[yao_kui_wid]))

    # C. 劉均《蕺山年譜》：解除entity_id繫連
    liu_jun_wid = "1evr5e3m9274k"
    liu_jun_eid = "1j967cp20mp7f"
    old_p = eidx_paths[liu_jun_eid]
    old_ent = load(old_p)
    old_ent["works"] = [w for w in old_ent.get("works", []) if w["work_id"] != liu_jun_wid]
    save(old_p, old_ent, get_indent(old_p))
    j = load(widx[liu_jun_wid])
    j["authors"][0].pop("entity_id", None)
    j["ai_note"] = j.get("ai_note", "") + " 2026-08-13：清朝探勘：原entity_id所指劉均（明，death_year=1427）與本書內容（劉宗周身故〔1645〕後所作年譜）明顯不符，判斷為不同之劉均，解除entity_id繫連，真實身分待未來查核。"
    save(widx[liu_jun_wid], j, get_indent(widx[liu_jun_wid]))

    # D. 曹學佺：訂正2作品為ming
    cao_xueqian_eid = "1j967afjbhiz8"
    for wid in ["1evke2jdyucjk", "1evr5e3mdqrbc"]:
        p = widx[wid]
        j = load(p)
        j["authors"][0]["dynasty"] = "明"
        j["authors"][0].pop("dynasty_basis", None)
        if j.get("dynasty") is not None:
            j["dynasty"] = "明"
        j["period"] = "ming"
        j["period_basis"] = "據 authors[0].dynasty「明」（2026-08-13 清朝探勘：曹學佺，引文確認為同一明末人物本人著作，period因啟發式誤植為qing，訂正）"
        save(p, j, get_indent(p))

    print("done")


if __name__ == "__main__":
    main()
