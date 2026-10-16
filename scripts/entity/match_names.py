#!/usr/bin/env python3
"""文本侧专名匹配（GUJI-509 草案，接口说明见 docs/entity-build/文本侧匹配接口.md）。

只依赖 export_keytable.py 的输出目录（键表.tsv／重定向表.tsv），标准库即可。

用法：
  python3 -I match_names.py <键表目录> --name 蘇軾 [--dynasty 宋] [--subtype people]
  python3 -I match_names.py <键表目录> --id <旧id或草稿id>
  python3 -I match_names.py <键表目录> --batch 查询.tsv [--out 结果.jsonl]
      查询.tsv 表头：name[, dynasty, subtype]（制表符分隔，UTF-8）
输出 JSONL，每个查询一行：
  {query:{...}, status, via, candidates:[{entity_id, primary_name, subtype, dynasty, key_kind, via}], reason}
status：unique 唯一候选可直接挂（朝代不一致时 reason 提示抽检）｜likely 多候选仅一条朝代吻合｜ambiguous 多候选无法定，必须人判｜
        redirected 经重定向表落到 live｜tombstone_name 名字只命中墓碑旧名，已跟到 final（较弱，建议抽检）｜
        retired 命中退役条｜none 未命中（走缺实体入口 GUJI-395）
朝代只是软信号（候选带 dynasty_signal：match|partial|mismatch|unknown），只降权不排除。绝不在 ambiguous 时自动取第一条。
"""
import argparse
import csv
import json
import sys
import unicodedata
from collections import defaultdict

# 与 export_keytable.py 的 _VARIANTS 保持一致（键表里已有 norm_key 列，查询侧须用同一张表）
_VARIANTS = {'尙': '尚', '郞': '郎', '戸': '戶', '叅': '參', '祕': '秘', '歴': '曆', '淸': '清',
             '彞': '彝', '啓': '啟', '裏': '裡', '羣': '群', '峯': '峰', '麤': '粗', '蹟': '跡',
             '爲': '為', '眞': '真',
             # GUJI-509 对 002/003 真实名单补：异体 → 通行字
             '𠮓': '變', '𫎇': '蒙', '鈎': '鉤', '温': '溫', '巖': '岩', '璇': '璿', '錄': '録',
             '决': '決', '藴': '蘊', '沈': '沉', '畧': '略', '復': '複', '冲': '沖', '頴': '穎',
             '註': '注', '内': '內',
             # GUJI-509 对 002/003 真实名单补（愼→慎 起）：异体 → 通行字
             '愼': '慎', '峩': '峨', '衞': '衛', '綫': '線', '糺': '糾', '秌': '秋', '敍': '敘',
             '邨': '村', '躰': '體', '剏': '創', '剙': '創', '辤': '辭', '辞': '辭', '嵗': '歲',
             '歳': '歲', '隂': '陰', '夘': '卯', '凢': '凡', '荅': '答', '觧': '解', '髙': '高',
             '蘓': '蘇', '欵': '款', '槩': '概', '絶': '絕', '蠧': '蠹', '寳': '寶', '珤': '寶',
             '圎': '圓', '靑': '青', '氷': '冰', '屛': '屏', '巿': '市', '恠': '怪', '嶋': '島',
             '嶌': '島', '鬭': '鬥', '鬪': '鬥', '鬬': '鬥', '蔵': '藏', '搨': '拓', '厯': '曆',
             '筭': '算', '祘': '算', '緖': '緒', '鷄': '雞', '恆': '恒', '墻': '牆', '灋': '法'}
_TABLE = str.maketrans(_VARIANTS)


def norm_key(s):
    return unicodedata.normalize("NFKC", s).strip().translate(_TABLE)


def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


class Matcher:
    def __init__(self, d):
        self.by_key = defaultdict(list)
        self.by_norm = defaultdict(list)
        self.by_id = {}
        for r in _read(f"{d}/键表.tsv"):
            self.by_key[r["key"]].append(r)
            self.by_norm[r["norm_key"]].append(r)
            self.by_id.setdefault(r["entity_id"], r)
        self.redirect = {}
        self.tomb_names = defaultdict(list)
        for r in _read(f"{d}/重定向表.tsv"):
            self.redirect[r["old_id"]] = r
            if r["old_name"] and r["status"] in ("merged", "retired"):
                self.tomb_names[norm_key(r["old_name"])].append(r)

    @staticmethod
    def _cand(r, via):
        return {"entity_id": r["entity_id"], "primary_name": r["primary_name"], "subtype": r["subtype"],
                "dynasty": r["dynasty"], "key_kind": r["key_kind"], "via": via}

    def resolve_id(self, eid):
        """旧 id／草稿 id → live。"""
        if eid in self.by_id:
            return {"status": "unique", "via": "live_id",
                    "candidates": [self._cand(self.by_id[eid], "live_id")], "reason": ""}
        r = self.redirect.get(eid)
        if not r:
            return {"status": "none", "via": "", "candidates": [], "reason": "id 不在键表也不在重定向表"}
        if r["status"] == "retired":
            return {"status": "retired", "via": "retired", "candidates": [], "reason": "该 id 已退役，不得取用，报缺"}
        row = self.by_id.get(r["final_id"])
        if r["status"].startswith("promoted-dangling") or not row:
            return {"status": "none", "via": r["status"], "candidates": [],
                    "reason": "重定向目标不在 live：" + r["final_id"]}
        return {"status": "redirected", "via": r["status"],
                "candidates": [self._cand(row, r["status"])], "reason": ""}

    def match(self, name, dynasty="", subtype=""):
        q = name.strip()
        rows, via = self.by_key.get(q, []), "exact"
        if not rows:
            rows, via = self.by_norm.get(norm_key(q), []), "norm"
        if subtype:
            # 官署名常同时作为 collective（机构／群体）入库：查 office 时一并查 collective（GUJI-509 对稿）
            ok = {subtype, "collective"} if subtype == "office" else {subtype}
            rows = [r for r in rows if r["subtype"] in ok]
        if not rows:
            tomb = [t for t in self.tomb_names.get(norm_key(q), [])
                    if not subtype or (self.by_id.get(t["final_id"]) or {}).get("subtype", subtype) == subtype]
            live = [(t, self.by_id.get(t["final_id"])) for t in tomb if t["status"] == "merged"]
            live = [(t, r) for t, r in live if r]
            if live:
                ids = {r["entity_id"] for _, r in live}
                cands = [self._cand(r, "tombstone_name") for _, r in live]
                return {"status": "tombstone_name" if len(ids) == 1 else "ambiguous", "via": "tombstone_name",
                        "candidates": _dedup(cands), "reason": "名字只命中已合并墓碑的旧名"}
            if any(t["status"] == "retired" for t in tomb):
                return {"status": "retired", "via": "retired_name", "candidates": [],
                        "reason": "名字只命中退役条"}
            if tomb:
                return {"status": "none", "via": "tombstone_name", "candidates": [],
                        "reason": "名字命中墓碑旧名，但 final 不在本键表（样例截断或 final 已非 live）"}
            return {"status": "none", "via": "", "candidates": [], "reason": "键表无此名，走缺实体入口"}
        cands = _dedup([self._cand(r, via) for r in rows])
        for c in cands:
            c["dynasty_signal"] = _dyn_signal(dynasty, c["dynasty"])
        # 朝代只是软信号：只降权排序，绝不排除（帝王等朝代标注与年号表不一致，见设计文档 §三）
        order = {"match": 0, "partial": 1, "unknown": 2, "mismatch": 3}
        cands.sort(key=lambda c: (order[c["dynasty_signal"]], c["key_kind"] != "primary", c["entity_id"]))
        reason = ""
        if len(cands) == 1:
            status = "unique"
            if cands[0]["dynasty_signal"] == "mismatch":
                reason = "唯一候选但朝代不一致（%s≠%s），建议抽检" % (dynasty, cands[0]["dynasty"])
        else:
            top = [c for c in cands if c["dynasty_signal"] in ("match", "partial")]
            if len(top) == 1 and top[0]["dynasty_signal"] == "match":
                status, reason = "likely", "多候选，仅一条朝代吻合，其余降权保留；建议抽检"
            else:
                status, reason = "ambiguous", "同名多候选，需上下文（朝代／作品／作者）消歧"
        return {"status": status, "via": via, "candidates": cands, "reason": reason}


def _dyn_signal(q, d):
    if not q:
        return "unknown"
    if not d:
        return "unknown"
    nq, nd = norm_key(q), norm_key(d)
    if nq == nd:
        return "match"
    if nq in nd or nd in nq:  # 宋／北宋、南宋；清／清末
        return "partial"
    return "mismatch"


def _dedup(cands):
    seen, out = set(), []
    for c in cands:
        k = c["entity_id"]
        if k not in seen:
            seen.add(k)
            out.append(c)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("--name")
    ap.add_argument("--dynasty", default="")
    ap.add_argument("--subtype", default="")
    ap.add_argument("--id")
    ap.add_argument("--batch")
    ap.add_argument("--out")
    a = ap.parse_args()
    m = Matcher(a.dir)
    out = open(a.out, "w", encoding="utf-8") if a.out else sys.stdout
    if a.id:
        res = [({"id": a.id}, m.resolve_id(a.id))]
    elif a.name:
        res = [({"name": a.name, "dynasty": a.dynasty, "subtype": a.subtype},
                m.match(a.name, a.dynasty, a.subtype))]
    elif a.batch:
        res = []
        for r in _read(a.batch):
            res.append((r, m.match(r["name"], r.get("dynasty") or "", r.get("subtype") or "")))
    else:
        ap.error("需要 --name／--id／--batch 之一")
    for q, r in res:
        out.write(json.dumps({"query": q, **r}, ensure_ascii=False) + "\n")
    if a.batch:
        from collections import Counter
        print(json.dumps(Counter(r["status"] for _, r in res), ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    main()
