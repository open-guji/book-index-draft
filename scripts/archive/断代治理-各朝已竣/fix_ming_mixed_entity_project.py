#!/usr/bin/env python3
"""明朝探勘：處理14組混合Entity獨立立項（部分）。

逐一核對indexed_by/description引文後，區分三類：

  A. 真正姓名巧合之不同人物（需拆分，建立新Entity）：
     - 張廷玉：《新傳理性元雅》《畢公生祠記》二作品，引文明載
       「明張廷玉撰。廷玉字汝光，號石初，延安人。萬曆庚戌進士，
       官至工部郎中」，與清雍正名臣張廷玉（1672-1755，桐城人）
       完全不同之人物，二作品原entity_id誤繫至清雍正名臣，今拆分
       建立新Entity。
     - 張汝霖：《易經澹窩因指》《周易因指》二作品，作者名本為
       「張汝霖」而非「張廷濟」，引文明載「明張汝霖撰。汝霖字明若，
       山陰人。萬曆乙未進士」，原entity_id誤繫至清代金石學家張廷濟
       （1768-1848），今拆分建立新Entity。

  B. 同一人物，僅Work.period因「回溯型志書代填」啟發式或欄位同步
     問題誤植（訂正為與Entity一致之song）：
     - 馮時行《周禮別說》、李衡《春秋釋例集說》、胡宏《周易黃金尺》：
       引文僅見於「明史藝文志」，無其他佐證顯示為不同人物，且三人
       皆為著名南宋學者，其餘作品已確立為song，判斷為明史藝文志
       誤植/代填之個別殘留，訂正。

  C. 存疑不處理：
     - 趙佑《地理紫囊》：引文作「趙祐」（示字，非趙佑），字形有異，
       疑為不同人物，證據不足，不予處理。
     - 董說（5作品）、謝文洊（1作品）、彭孫貽（1作品）、賀貽孫
       （2作品）：引文皆明確為同一明末清初人物本人之著作（如董說
       「說有《易發》，已著錄」互見文字），為真正跨代人物之著作
       依寫作時期標記為ming，Entity依其身故年代標記為qing，二者
       並不矛盾，不予變動。
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
    # 簡易衍生新id：與既有id同為13字元（1j99+9碼），確保格式一致且不衝突
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


def create_entity(eid, name, dyn, works, note):
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
        "period": "ming",
        "period_basis": f"據 dynasty「{dyn}」（2026-08-13 明朝探勘混合Entity獨立立項：{note}）",
    }
    s = shard_of(eid)
    c1, c2, c3 = eid[0], eid[1], eid[2]
    ent_dir = ROOT / "Entity" / c1 / c2 / c3
    ent_dir.mkdir(parents=True, exist_ok=True)
    ent_path = ent_dir / f"{eid}-{name}.json"
    save(ent_path, ent, indent=2)

    idx_path = ROOT / "index" / "entities" / f"{s:x}.json"
    idx = load(idx_path)
    idx[eid] = {
        "id": eid, "type": "entity", "subtype": "people",
        "primary_name": name, "path": str(ent_path.relative_to(ROOT)),
        "dynasty": dyn, "period": "ming",
    }
    save(idx_path, idx, get_indent(idx_path))
    return ent_path


def detach_from_entity(old_eid, wids):
    for f in Path(ROOT / "Entity").rglob("*.json"):
        try:
            j = load(f)
        except Exception:
            continue
        if isinstance(j, dict) and j.get("id") == old_eid:
            j["works"] = [w for w in j.get("works", []) if w["work_id"] not in wids]
            save(f, j, get_indent(f))
            return


def main():
    widx = build_work_index()

    # A1. 張廷玉（明，字汝光，延安人）
    zhang_tingyu_ming_wids = ["1ev3bbqtd416o", "1evkagedqeoe8"]
    new_eid1 = new_id_from("張廷玉明汝光延安")
    create_entity(new_eid1, "張廷玉", "明", zhang_tingyu_ming_wids,
                   "與清雍正名臣張廷玉（1672-1755，桐城人）同名異人：本條字汝光，號石初，延安人，萬曆庚戌進士，官至工部郎中，原誤繫至清代同名人物之Entity，今拆分獨立")
    detach_from_entity("1j967a0kj9gxu", zhang_tingyu_ming_wids)
    for wid in zhang_tingyu_ming_wids:
        p = widx[wid]
        j = load(p)
        j["authors"][0]["entity_id"] = new_eid1
        j["authors"][0]["dynasty"] = "明"
        save(p, j, get_indent(p))

    # A2. 張汝霖（明，字明若，山陰人）
    zhang_rulin_wids = ["1ev0r92ugiqrk", "1evdibiy4uo00"]
    new_eid2 = new_id_from("張汝霖明明若山陰")
    create_entity(new_eid2, "張汝霖", "明", zhang_rulin_wids,
                   "作者本名「張汝霖」而非「張廷濟」，與清代金石學家張廷濟（1768-1848）非同一人：本條字明若，山陰人，萬曆乙未進士，官至江西布政司參議，原誤繫entity_id至張廷濟之Entity，今拆分獨立")
    detach_from_entity("1j967a0kl4w98", zhang_rulin_wids)
    for wid in zhang_rulin_wids:
        p = widx[wid]
        j = load(p)
        j["authors"][0]["entity_id"] = new_eid2
        j["authors"][0]["dynasty"] = "明"
        save(p, j, get_indent(p))

    # B. 馮時行/李衡/胡宏：訂正period為song
    b_fixes = [
        ("1evdiboruga2o", "馮時行", "南宋"),
        ("1evdibrnaon40", "李衡", "南宋"),
        ("1evdid3jd5xc0", "胡宏", "南宋"),
    ]
    for wid, name, dyn in b_fixes:
        p = widx[wid]
        j = load(p)
        j["authors"][0]["dynasty"] = dyn
        j["authors"][0].pop("dynasty_basis", None)
        if j.get("dynasty") is not None:
            j["dynasty"] = dyn
        j["period"] = "song"
        j["period_basis"] = f"據 authors[0].dynasty「{dyn}」（2026-08-13 明朝探勘混合Entity獨立立項：{name}為著名南宋學者，引文僅見明史藝文志代填，無其他佐證顯示為不同人物，訂正為song）"
        save(p, j, get_indent(p))

    print("done")


if __name__ == "__main__":
    main()
