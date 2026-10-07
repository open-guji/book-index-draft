# book-index Schema

字段级 Schema 定义已迁移到 `book-index` 仓根目录的 `SCHEMA.md`，请前往那里查阅。

schema-v2（2026-10-07 起，`schema-v2` 分支）：草稿库与正式库同一套格式——源档只存一侧关系、不写 `Work.books` 与 `_` 起首字段、`authors[].role` 必填、分类走 `classification/<分类法>/` 类档。
新格式残留检查用正式库的脚本，`--root` 指向本仓：`python3 ../book-index/.claude/qa/check_v2.py --root . --summary`（只查 PR 改动的文件加 `--paths`）。
