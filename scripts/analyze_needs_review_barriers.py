#!/usr/bin/env python3
"""分析 88 个 needs-review Work 的障碍类型"""
import json, os, re

no_entity = []      # 作者无 Entity
entity_not_ming = [] # 有 Entity 但 dynasty≠明
no_author = []       # 明史志條目作者为空
other = []

for root, _, files in os.walk("/workspace/Work"):
    for f in files:
        if not f.endswith(".json"): continue
        fp = os.path.join(root, f)
        if "/collated_edition/" in fp: continue
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                w = json.load(fh)
        except:
            continue
        note = w.get("ai_note", "")
        if "needs-review" not in note: continue
        
        m = re.search(r"條目作者：'([^']*)'", note)
        ming_author = m.group(1) if m else None
        
        if ming_author is None:
            other.append((w["id"], w.get("title",""), note[:100]))
            continue
        
        if not ming_author:
            no_author.append((w["id"], w.get("title","")))
            continue
        
        # 查找 Work 中的作者
        found = False
        for a in w.get("authors", []):
            if a.get("name") == ming_author:
                found = True
                eid = a.get("entity_id")
                if not eid:
                    no_entity.append((w["id"], w.get("title",""), ming_author))
                else:
                    # 查 Entity
                    efp = None
                    for r2, _, f2 in os.walk("/workspace/Entity"):
                        for ff in f2:
                            if ff.startswith(eid) and ff.endswith(".json"):
                                efp = os.path.join(r2, ff)
                                break
                        if efp: break
                    if efp:
                        with open(efp) as fh:
                            e = json.load(fh)
                        if e.get("dynasty") != "明":
                            entity_not_ming.append((w["id"], w.get("title",""), ming_author, eid, e.get("dynasty")))
                    else:
                        no_entity.append((w["id"], w.get("title",""), ming_author))
                break
        
        if not found:
            no_entity.append((w["id"], w.get("title",""), ming_author + "(Work中无此作者)"))

print(f"=== needs-review 障碍分析 ({88} 总计) ===")
print(f"\n1. 明史志條目作者為空: {len(no_author)} 个")
for wid, title in no_author[:10]:
    print(f"   {wid} 《{title}》")

print(f"\n2. 作者無 Entity / Work中無此作者: {len(no_entity)} 个")
for wid, title, author in no_entity[:10]:
    print(f"   {wid} 《{title}》 作者={author}")

print(f"\n3. 有 Entity 但 dynasty≠明: {len(entity_not_ming)} 个")
for wid, title, author, eid, dyn in entity_not_ming[:10]:
    print(f"   {wid} 《{title}》 作者={author} Entity={eid} dynasty={dyn}")

print(f"\n4. 其他 (非 gazetteer_propagation 模式): {len(other)} 个")
for wid, title, note in other[:5]:
    print(f"   {wid} 《{title}》")
    print(f"     {note}")
