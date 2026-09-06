# book-index-draft

草稿元数据仓。结构与 [book-index](https://github.com/open-guji/book-index)（生产仓）相同：
`Work/ Book/ Collection/ Entity/` 条目 JSON + `index/` 分片索引；条目经 `book-index promote` 升格进生产仓并换新 ID，
本仓留 tombstone，映射记在 `promotions.json`。

**规范在本仓的 [`SCHEMA.md`](SCHEMA.md)**（字段定义、索引檔结构、已删字段、判重十条）。
文本资产（整理本、辑佚、全文）不在这里，在 [book-text](https://github.com/open-guji/book-text)。

数据工具：`open-guji/book-index-manager`（`pip install -e .` 后有 `book-index` 命令；`--root` 指 `D:/workspace` 这个父目录）。
网站与部署全貌见 overview 仓的 `项目进展/古籍索引网站/2026-09-网站交接手册.html`
（[线上版](https://claude.ai/code/artifact/0b4a9456-eaf9-4f4c-9e2d-72bba9f4e5c8)）。
