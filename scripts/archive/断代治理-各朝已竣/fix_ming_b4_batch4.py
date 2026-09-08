#!/usr/bin/env python3
"""
B4 二組 batch4-1：解除 8 個 Work needs-review（查作者 Entity 確認屬明）
- 武宗實錄 / 憲宗實錄 / 神宗實錄 / 孝宗實錄 / 光宗實錄（明官方實錄，修者均明人）
- 說林（張時徹 1500-1577）、玄覽（朱謀㙔 明宗室）、桂林志（陳璉 1370-1454）
"""
import json, os, re

WORKS = [
    ("1evcs0dz9tngg", "武宗實錄", "費宏", "明史官方實錄，費宏(1468-1535)等修"),
    ("1evcs0dyeaolc", "憲宗實錄", "劉吉", "明史官方實錄，劉吉(1427-1493)等修"),
    ("1evcsx8m3k1s0", "神宗實錄", "溫體仁", "明史官方實錄，溫體仁(1573-1638)等修"),
    ("1evcsx8nuaqyo", "孝宗實錄", "謝遷", "明史官方實錄，劉健、謝遷(1449-1531)等修"),
    ("1evcsx8o3nv9c", "光宗實錄", "葉向高", "明史官方實錄，葉向高(1559-1627)等修"),
    ("1evcpd1r9ni80", "說林", "張時徹", "張時徹(1500-1577)明人"),
    ("1evcpd3lzmm80", "玄覽", "朱謀㙔", "朱謀㙔明宗室，金石學家"),
    ("1evcsxm2498u8", "桂林志", "陳璉", "陳璉(1370-1454)明人"),
]

work_dir = "/workspace/Work"

def find_work_path(wid):
    for root, _, files in os.walk(work_dir):
        for f in files:
            if f.startswith(wid) and f.endswith(".json") and "/collated_edition/" not in os.path.join(root, f):
                return os.path.join(root, f)
    return None

for wid, title, author, note in WORKS:
    fpath = find_work_path(wid)
    if not fpath:
        print(f"[MISS] {wid} {title}")
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        w = json.load(f)
    old_note = w["ai_note"]
    # 移除 needs-review (gazetteer_propagation)，同時補充作者驗證 + 同名異書合併說明
    # 找 ming-round2 區段
    start = old_note.find("[ming-round2:")
    if start >= 0:
        # 找 needs-review 起始
        nr_idx = old_note.find("needs-review (gazetteer_propagation)", start)
        if nr_idx >= 0:
            # 構造新註解：移除 needs-review 標記，替換為驗證通過說明
            before = old_note[:start]
            bracket_content = old_note[start:]
            # 移除 needs-review (gazetteer_propagation)
            bracket_content = bracket_content.replace(" needs-review (gazetteer_propagation)", "")
            # 替換開頭的作者未驗證描述
            prefix_old = f"明史藝文志匹配：標題精確匹配但未能驗證作者（條目作者：'{author}'）。"
            prefix_new = f"明史藝文志匹配：標題精確匹配，作者 {author} Entity 查證屬明（{note}），gazetteer_propagation 確認正確。 indexed_by 含前朝同名異書條目，係不同朝代同名書合併記錄，待拆分 Work。"
            if old_note.startswith(prefix_old):
                bracket_content = prefix_new + " " + bracket_content
                # old_note 是 prefix_old + " " + [...]，现在需要把 prefix_old 替换，然后用新的 bracket 拼接
                new_note = prefix_new + " " + bracket_content[len(prefix_old)+1:]
                # 但上面 bracket_content 是 old_note[start:]，所以实际做法：
                new_note = old_note.replace(prefix_old, prefix_new)
                new_note = new_note.replace(" needs-review (gazetteer_propagation)", "")
            else:
                # fallback
                new_note = old_note.replace(" needs-review (gazetteer_propagation)", "")
                new_note = new_note.replace("未能驗證作者", f"作者{author}已驗證屬明（{note}）")
            w["ai_note"] = new_note
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(w, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"[OK] {wid} {title}")

# --- 同步 index ---
import hashlib, glob

def shard(wid):
    h = hashlib.sha256(wid.encode()).hexdigest()
    return h[:2]

changed_ids = [w[0] for w in WORKS]

index_dir = "/workspace/index/works"
for sh in sorted(set(shard(x) for x in changed_ids)):
    idx_path = os.path.join(index_dir, f"{sh}.json")
    if not os.path.exists(idx_path):
        continue
    with open(idx_path, "r", encoding="utf-8") as f:
        idx = json.load(f)
    dirty = False
    for i, entry in enumerate(idx):
        if entry.get("id") in changed_ids:
            wid = entry["id"]
            fpath = find_work_path(wid)
            with open(fpath, "r", encoding="utf-8") as f2:
                w = json.load(f2)
            # dynasty, period, dynasty_basis, period_basis 不變，只有 ai_note 變化
            # index 分片只有 dynasty/period/authors，沒有 ai_note，所以實際無需改動
            # 但仍確認 dynasty/period 一致
            for k in ["dynasty", "period", "dynasty_basis", "period_basis"]:
                if entry.get(k) != w.get(k):
                    entry[k] = w.get(k)
                    dirty = True
            if w.get("authors"):
                entry_authors = [a.get("name") for a in entry.get("authors", [])]
                w_authors = [a.get("name") for a in w.get("authors", [])]
                if entry_authors != w_authors:
                    entry["authors"] = w.get("authors", [])
                    dirty = True
    if dirty:
        with open(idx_path, "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"[SYNC] works/{sh}.json")
    else:
        print(f"[SKIP] works/{sh}.json (no field change, only ai_note)")

print("DONE batch4-1: 解除8個 needs-review")
