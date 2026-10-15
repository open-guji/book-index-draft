#!/usr/bin/env python3
"""专名键表导出（GUJI-394，设计见 docs/entity-build/键表设计.md）。

用法：
  python3 -I export_keytable.py <book-index 路径> <输出目录> [--subtypes people,place,...]
        [--limit-people N] [--prev <旧键表.tsv>]

只读 <book-index>/Entity/**/*.json，写 <输出目录>/ 下：
  键表.tsv     key, entity_id, primary_name, subtype, key_kind, dynasty, cand_n, norm_key, norm_cand_n
  重定向表.tsv  old_id, status(merged|promoted|retired), final_id, old_name
  键表.meta.json  源 commit、脚本 sha256、行数、两表 sha256
  增量.tsv     （仅给 --prev 时）op(add|del|chg), key, entity_id, 新 key_kind／dynasty／cand_n
只含 live 条目的名（primary_name＋alt_names）；merged_into 条走重定向表，retired 条不入键表。
promoted：<book-index>/promotions/*.json 里 type=entity 的草稿 id → 正式 id 映射，
  final_id 会再跟随 merged_into，并校验落在 live（否则 status 记 promoted-dangling）。
norm_key：本脚本内置的异体字折叠（NFKC＋逐字表，不含繁简转换，不依赖 opencc，输出可复现）；
  norm_cand_n 为同 (subtype, norm_key) 下不同 entity 数，供查表方做异体宽松匹配。
输出按 (key, entity_id) 排序，同一输入逐字节可复现。
"""
import argparse
import csv
import glob
import hashlib
import json
import os
import subprocess
import unicodedata
import sys
from collections import defaultdict


# 逐字异体折叠表（与 scripts/dynasty-reign/guji_norm.py 的 NORMALIZE 同向，再补人名／官署常见异体）
_VARIANTS = {'尙': '尚', '郞': '郎', '戸': '戶', '叅': '參', '祕': '秘', '歴': '曆', '淸': '清',
             '彞': '彝', '啓': '啟', '裏': '裡', '羣': '群', '峯': '峰', '麤': '粗', '蹟': '跡',
             '爲': '為', '眞': '真',
             # GUJI-509 对 002/003 真实名单补：异体 → 通行字
             '𠮓': '變', '𫎇': '蒙', '鈎': '鉤', '温': '溫', '巖': '岩', '璇': '璿', '錄': '録',
             '决': '決', '藴': '蘊', '沈': '沉', '畧': '略', '復': '複', '冲': '沖', '頴': '穎',
             '註': '注', '内': '內'}
_VAR_TABLE = str.maketrans(_VARIANTS)


def norm_key(s):
    return unicodedata.normalize("NFKC", s).strip().translate(_VAR_TABLE)


def load_promotions(repo):
    """草稿 entity id → 正式 id。"""
    out = {}
    for p in sorted(glob.glob(os.path.join(repo, "promotions", "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        for old, v in (d.get("promotions") or {}).items() if isinstance(d, dict) else []:
            if isinstance(v, dict) and v.get("type") == "entity" and v.get("production_id"):
                out[old] = v["production_id"]
    return out


def load(repo):
    ents = {}
    for p in glob.glob(os.path.join(repo, "Entity", "**", "*.json"), recursive=True):
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        if isinstance(d, dict) and d.get("type") == "entity" and d.get("id"):
            ents[d["id"]] = d
    return ents


def final_id(ents, eid):
    seen = set()
    while eid in ents and ents[eid].get("merged_into") and eid not in seen:
        seen.add(eid)
        eid = ents[eid]["merged_into"]
    return eid


def rows_for(e):
    pn = e.get("primary_name")
    if pn:
        yield pn, "primary"
    for a in e.get("alt_names") or []:
        if isinstance(a, dict) and a.get("name"):
            yield a["name"], "alt:" + (a.get("type") or "")
        elif isinstance(a, str) and a:
            yield a, "alt:"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo")
    ap.add_argument("out")
    ap.add_argument("--subtypes", default="")
    ap.add_argument("--limit-people", type=int, default=0, help="仅样例用：人物只取 id 排序后前 N 条")
    ap.add_argument("--prev")
    a = ap.parse_args()

    want = set(filter(None, a.subtypes.split(",")))
    ents = load(a.repo)
    live = {k: e for k, e in ents.items()
            if not e.get("merged_into") and not e.get("retired")
            and (not want or e.get("subtype") in want)}
    if a.limit_people:
        ppl = sorted(k for k, e in live.items() if e.get("subtype") == "people")[: a.limit_people]
        keep = set(ppl)
        live = {k: e for k, e in live.items() if e.get("subtype") != "people" or k in keep}

    keys = []
    owners = defaultdict(set)
    nowners = defaultdict(set)
    for eid, e in live.items():
        st = e.get("subtype")
        # dynasty 只对 people 有意义；其余 subtype 留空
        dyn = (e.get("dynasty") or "") if st == "people" else ""
        for name, kind in rows_for(e):
            keys.append((name, eid, e.get("primary_name") or "", st, kind, dyn))
            owners[(st, name)].add(eid)
            nowners[(st, norm_key(name))].add(eid)
    keys = sorted(set(keys), key=lambda r: (r[0], r[1], r[4]))

    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "键表.tsv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["key", "entity_id", "primary_name", "subtype", "key_kind", "dynasty",
                    "cand_n", "norm_key", "norm_cand_n"])
        for name, eid, pn, st, kind, dyn in keys:
            nk = norm_key(name)
            w.writerow([name, eid, pn, st, kind, dyn, len(owners[(st, name)]),
                        nk, len(nowners[(st, nk)])])

    redirects = []
    for eid, e in ents.items():
        if want and e.get("subtype") not in want:
            continue
        if e.get("merged_into"):
            redirects.append((eid, "merged", final_id(ents, eid), e.get("primary_name") or ""))
        elif e.get("retired"):
            redirects.append((eid, "retired", "", e.get("primary_name") or ""))
    # promoted：草稿 id → 正式 id（再跟随 merged_into，须落在 live）
    seen_old = {r[0] for r in redirects}
    promo = load_promotions(a.repo)
    n_dangling = 0
    for old, new in promo.items():
        if old in seen_old:
            continue
        fin = final_id(ents, new)
        tgt = ents.get(fin)
        ok = bool(tgt) and not tgt.get("retired") and not tgt.get("merged_into")
        if want and tgt and tgt.get("subtype") not in want:
            continue
        if not tgt and want:
            continue
        n_dangling += 0 if ok else 1
        redirects.append((old, "promoted" if ok else "promoted-dangling", fin, ""))
    redirects.sort()
    with open(os.path.join(a.out, "重定向表.tsv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["old_id", "status", "final_id", "old_name"])
        w.writerows(redirects)

    try:
        sha = subprocess.run(["git", "-C", a.repo, "rev-parse", "HEAD"], capture_output=True,
                             text=True, check=True).stdout.strip()
    except Exception:
        sha = ""
    def sha256(name):
        with open(os.path.join(a.out, name), "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    with open(os.path.abspath(__file__), "rb") as f:
        script_sha = hashlib.sha256(f.read()).hexdigest()
    meta = {"keytable_sha256": sha256("键表.tsv"), "redirect_sha256": sha256("重定向表.tsv"),
            "script_sha256": script_sha, "promoted_rows": sum(1 for r in redirects if r[1].startswith("promoted")),
            "promoted_dangling": n_dangling, "source_repo": "open-guji/book-index", "source_commit": sha,
            "subtypes": sorted(want) or "all", "limit_people": a.limit_people,
            "key_rows": len(keys), "live_entities": len(live), "redirect_rows": len(redirects),
            "ambiguous_keys": sum(1 for v in owners.values() if len(v) > 1)}
    with open(os.path.join(a.out, "键表.meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    if a.prev:
        def read(p):
            with open(p, encoding="utf-8") as f:
                r = csv.DictReader(f, delimiter="\t")
                return {(x["key"], x["entity_id"]): (x["key_kind"], x["dynasty"], x.get("cand_n", ""))
                        for x in r}
        old = read(a.prev)
        new = {(k, e): (kd, d, str(len(owners[(st, k)]))) for k, e, pn, st, kd, d in keys}
        with open(os.path.join(a.out, "增量.tsv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t", lineterminator="\n")
            w.writerow(["op", "key", "entity_id", "key_kind", "dynasty", "cand_n"])
            for k in sorted(set(old) | set(new)):
                if k not in old:
                    w.writerow(["add", *k, *new[k]])
                elif k not in new:
                    w.writerow(["del", *k, *old[k]])
                elif old[k] != new[k]:
                    w.writerow(["chg", *k, *new[k]])
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
