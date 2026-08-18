#!/usr/bin/env python3
"""遼金元／明「元末明初、宋末元初」大規模邊界人口獨立立項：系統性
分類處理。

背景：遼金元探勘、明朝探勘兩輪皆發現period=liao-jin-yuan與
period=ming之間存在約250筆Work.period與Entity.period不一致之
現象，經抽查發現規模過大、性質複雜，不宜個案零星處理，兩輪文件
皆建議獨立立項，以系統性方法（比對人物生卒年與1271年〔元建國〕、
1368年〔明建國〕兩條斷代線之相對位置）分批處理。

本腳本執行此獨立立項：

1. 蒐集全部Work.period=liao-jin-yuan而其entity_id所指Entity.period
   不同（或反向）之record，共244筆、涉162個相異Entity。
2. 其中85個Entity具明確之death_year，可據以分類：
   - death_year < 1271（元建國前）：entity不可能為元人，其現有
     dynasty多已為「南宋/北宋」且period已正確為song（27個），僅
     Work.period需訂正為song。
   - death_year > 1368（明建國後）：entity多已為「明」且period已
     正確為ming（39個），僅Work.period需訂正為ming。
   - 例外6個Entity（趙謙/王珣/趙汸/高遜志/張以寧/謝應芳）：其
     dynasty欄位本身標「元」，然death_year與此矛盾（趙謙/王珣死於
     元建國前；趙汸/張以寧死於明建國僅1-2年後；高遜志/謝應芳死於
     明建國後甚久但無/有明確元代仕歷佐證）——此類為真正邊界人物
     或證據本身自相矛盾，排除於本次批次訂正之外，維持現狀，留待
     未來以更精細之判準（如仕歷紀錄而非僅生卒年）逐一核實。
3. 其餘77個Entity（無death_year可查）與6個排除案例，本輪不予處理，
   留待未來以indexed_by引文之紀年關鍵字（比照清朝探勘輪之判準）
   或其他外部查證方式逐一核實。

本輪僅處理death_year明確、且entity.dynasty與死亡年份不衝突之
66個Entity（27+39），共104筆work記錄之period訂正。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

EXCLUDE_ENTITIES = {
    "1j96h8rw7vhho",  # 趙謙：dynasty「元」但死於1261（元建國前），自相矛盾
    "1j96hjwlxcpka",  # 王珣：同上，死於1224
    "1j967afjbhiwy",  # 趙汸：死於1369，明建國僅1年後，真正邊界人物
    "1j96hjwlxz6lz",  # 高遜志：死於1402，無生年可查，證據不足
    "1j96gxo52xf5v",  # 張以寧：死於1370，明建國僅2年後，真正邊界人物
    "1j967avzlz143",  # 謝應芳：死於1392（96歲高壽），主要仕歷仍屬元代，真正邊界人物
}


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


def main():
    widx = build_work_index()
    eidx = build_entity_index()

    fwd = []
    for wid, path in widx.items():
        try:
            j = load(path)
        except Exception:
            continue
        if j.get("period") != "liao-jin-yuan":
            continue
        a = j.get("authors")
        if not a or not isinstance(a, list) or not isinstance(a[0], dict):
            continue
        eid = a[0].get("entity_id")
        if not eid or eid not in eidx:
            continue
        ep = eidx[eid].get("period")
        if ep and ep != "liao-jin-yuan":
            fwd.append((wid, eid))

    rev = []
    for eid, e in eidx.items():
        if e.get("period") != "liao-jin-yuan":
            continue
        for w in e.get("works", []) or []:
            wid = w.get("work_id")
            p = widx.get(wid)
            if not p:
                continue
            j = load(p)
            a = j.get("authors")
            if not a or not isinstance(a, list) or not isinstance(a[0], dict):
                continue
            if a[0].get("entity_id") != eid:
                continue
            wp = j.get("period")
            if wp and wp != "liao-jin-yuan":
                rev.append((wid, eid))

    all_pairs = {}
    for wid, eid in fwd + rev:
        all_pairs.setdefault(eid, []).append(wid)

    fixed = 0
    for eid, wids in all_pairs.items():
        if eid in EXCLUDE_ENTITIES:
            continue
        e = eidx[eid]
        death = e.get("death_year")
        dyn = e.get("dynasty")
        if not death:
            continue
        if death < 1271:
            target_period = "song"
        elif death > 1368:
            target_period = "ming"
        else:
            continue  # genuinely Yuan-era death, entity is already liao-jin-yuan, no fix needed here

        note = (f"{e.get('primary_name')}（生卒{e.get('birth_year')}-{death}）："
                f"死於{'元建國(1271)前' if target_period == 'song' else '明建國(1368)後'}，"
                f"Entity既有分類（{dyn}／{target_period}）已正確，"
                f"Work.period因啟發式或欄位同步遺漏誤植為liao-jin-yuan，訂正")
        for wid in wids:
            p = widx.get(wid)
            if not p:
                continue
            j = load(p)
            a = j.get("authors")
            if not a or not isinstance(a, list) or not isinstance(a[0], dict):
                continue
            if a[0].get("entity_id") != eid or j.get("period") == target_period:
                continue
            a[0]["dynasty"] = dyn
            a[0].pop("dynasty_basis", None)
            if j.get("dynasty") is not None:
                j["dynasty"] = dyn
            j["period"] = target_period
            j["period_basis"] = f"據 authors[0].dynasty「{dyn}」（2026-08-13 遼金元/明邊界人口獨立立項：{note}）"
            save(p, j, get_indent(p))
            fixed += 1

    print(f"fixed_works={fixed}")


if __name__ == "__main__":
    main()
