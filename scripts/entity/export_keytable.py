#!/usr/bin/env python3
"""专名键表导出（GUJI-394，设计见 docs/entity-build/键表设计.md）。

用法：
  python3 -I export_keytable.py <book-index 路径> <输出目录> [--subtypes people,place,...]
        [--limit-people N] [--prev <旧键表.tsv>]

只读 <book-index>/Entity/**/*.json，写 <输出目录>/ 下：
  键表.tsv     key, entity_id, subtype, key_kind, dynasty, cand_n
  重定向表.tsv  old_id, status(merged|retired), final_id, old_name
  键表.meta.json  源 commit、行数、生成口径
  增量.tsv     （仅给 --prev 时）op(add|del|chg), key, entity_id, 新旧 key_kind／dynasty
只含 live 条目的名（primary_name＋alt_names）；merged_into 条走重定向表，retired 条不入键表。
输出按 (key, entity_id) 排序，同一输入逐字节可复现。
"""
import argparse
import csv
import glob
import json
import os
import subprocess
import sys
from collections import defaultdict


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
    for eid, e in live.items():
        for name, kind in rows_for(e):
            keys.append((name, eid, e.get("subtype"), kind, e.get("dynasty") or ""))
            owners[(e.get("subtype"), name)].add(eid)
    keys = sorted(set(keys), key=lambda r: (r[0], r[1], r[3]))

    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "键表.tsv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["key", "entity_id", "subtype", "key_kind", "dynasty", "cand_n"])
        for name, eid, st, kind, dyn in keys:
            w.writerow([name, eid, st, kind, dyn, len(owners[(st, name)])])

    redirects = []
    for eid, e in ents.items():
        if want and e.get("subtype") not in want:
            continue
        if e.get("merged_into"):
            redirects.append((eid, "merged", final_id(ents, eid), e.get("primary_name") or ""))
        elif e.get("retired"):
            redirects.append((eid, "retired", "", e.get("primary_name") or ""))
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
    meta = {"source_repo": "open-guji/book-index", "source_commit": sha,
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
                return {(x["key"], x["entity_id"]): (x["key_kind"], x["dynasty"]) for x in r}
        old = read(a.prev)
        new = {(k, e): (kd, d) for k, e, st, kd, d in keys}
        with open(os.path.join(a.out, "增量.tsv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t", lineterminator="\n")
            w.writerow(["op", "key", "entity_id", "key_kind", "dynasty"])
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
