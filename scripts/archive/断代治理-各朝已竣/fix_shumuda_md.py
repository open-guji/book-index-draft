#!/usr/bin/env python3
"""从 json 重新生成 書目答問 md 文件的标题层级"""

import json
import os

BASE = r"D:\workspace\book-index-draft\Work\3\1\h\31hyr4yqu8xk9\collated_edition"

JUANS = ["卷一經部", "卷二史部", "卷三子部", "卷四集部", "卷五叢書目"]


def render_md(sections):
    # 收集所有类节的 level 值，排序后建立映射（最小的 level → #, 次小 → ##, ...）
    class_levels = sorted(set(
        s.get("level", 3)
        for s in sections
        if s.get("type") in ("类", "序", "结语") or s.get("type") is None
    ))
    level_map = {lv: "#" * (i + 1) for i, lv in enumerate(class_levels)}

    lines = []
    for sec in sections:
        title = sec["title"]
        level = sec.get("level", 3)
        stype = sec.get("type", "书")
        content = sec.get("content", "")

        if stype in ("类", "序", "结语"):
            hashes = level_map.get(level, "#" * (level - 1))
            lines.append(f"{hashes} {title}")
            lines.append("")
            if content:
                lines.append(content)
                lines.append("")
        elif stype == "书":
            lines.append(f"**{title}**")
            lines.append("")
            if content:
                lines.append(content)
                lines.append("")
        else:
            hashes = level_map.get(level, "#" * (level - 1))
            lines.append(f"{hashes} {title}")
            lines.append("")
            if content:
                lines.append(content)
                lines.append("")

    # 去掉末尾多余空行
    while lines and lines[-1] == "":
        lines.pop()
    lines.append("")  # 文件末尾保留一个换行

    return "\n".join(lines)


for juan in JUANS:
    json_path = os.path.join(BASE, f"{juan}.json")
    md_path = os.path.join(BASE, "text", f"{juan}.md")

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    sections = data["sections"]
    md_content = render_md(sections)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"已生成 {juan}.md ({len(sections)} 节)")
