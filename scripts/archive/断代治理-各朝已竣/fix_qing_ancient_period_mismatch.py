#!/usr/bin/env python3
"""清朝探勘：修復period=qing範圍內，因「回溯型志書（清史稿藝文志等）
代填period」啟發式失效，導致本屬先秦/秦漢/三國/南北朝之古代著作
被誤植為period=qing之案例。

此bug模式已於隋唐、五代十國、遼金元三輪探勘中重複發現，本輪為
第四度出現，且規模較大（26條）。判定依據：Entity本身已有明確、
無可置疑之古代朝代分類（如皇侃/南朝梁、董仲舒/西漢、王肅/三國魏
等，皆為極著名之古代人物，與period=qing間隔千年以上，不存在
「朝代邊界過渡人物」之可能性），而其indexed_by引文之「清史稿
藝文志」來源本身即明載古代朝代（如「梁皇侃」「漢董仲舒」「吳朱
育」），period卻誤填為「清」。

與明朝探勘輪之「大規模CBDB姓名巧合誤配」性質不同——此類案例並非
姓名巧合之誤配（entity本身即為正確之人物），而是單純之period欄位
代填規則錯誤，逕依Entity既有正確分類同步Work.period/dynasty。
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
            idx[j["id"]] = j
    return idx


TARGET_PERIODS = {"nanbeichao", "three-kingdoms", "qin-han", "pre-qin"}


def main():
    widx = build_work_index()
    eidx = build_entity_index()
    fixed = 0

    for wid, path in widx.items():
        try:
            j = load(path)
        except Exception:
            continue
        if j.get("period") != "qing":
            continue
        a = j.get("authors")
        if not a or not isinstance(a, list) or not isinstance(a[0], dict):
            continue
        eid = a[0].get("entity_id")
        if not eid or eid not in eidx:
            continue
        ent = eidx[eid]
        ep = ent.get("period")
        if ep not in TARGET_PERIODS:
            continue
        dyn = ent.get("dynasty")
        note = f"{ent.get('primary_name')}：來源「清史稿藝文志」等回溯型志書之著錄原文本身已明載古代朝代（{dyn}），period僅因來源志書本身之朝代「清」被誤代填，以Entity既有正確分類為準訂正"
        a[0]["dynasty"] = dyn
        a[0].pop("dynasty_basis", None)
        if j.get("dynasty") is not None:
            j["dynasty"] = dyn
        j["period"] = ep
        j["period_basis"] = f"據 authors[0].dynasty「{dyn}」（2026-08-13 清朝探勘：{note}）"
        save(path, j, get_indent(path))
        fixed += 1
        print("fixed:", wid, j.get("title"), "->", ep, dyn)

    print(f"total fixed={fixed}")


if __name__ == "__main__":
    main()
