# 先秦條目 D 類修復（2026-08-19）

draft → production 升級前的資料修復。全流程入口 `run_all.sh`，從乾淨 HEAD 出發可重跑。

| 腳本 | 作用 |
|---|---|
| `merge_works_v2.py <src> <tgt>` | 合併兩個 Work。基於 `overview/scripts/merge_works.py`，補了 `emendated_by` 合併、`books` 去重、路徑參數化 |
| `clean_selfref.py` | 合併後山海經出現的兩條自指 `related_works` |
| `fix_period_dynasty.py [--apply]` | P1 諸侯國「齊」誤判／P2 period 空值回填／P3 違反漢志上限／P4 作者朝代與 entity 串位 |
| `fill_descriptions.py [--apply]` | 補寫 5 條缺 description |
| `fix_orphan_refs.py [--apply]` | 補掉 merge 漏改的陣列形態引用（`sections[].work_ids`、`Entity.works`） |
| `undo_rename.py` | 撤銷 save_item 對《六韜六卷附逸文一卷》的量詞尾剝離改名 |
| `normalize_index.py` | 回填 index shard 的 `period`，並把寫入格式歸一化回 `indent=1` |
| `audit_period_bound.py` | 依 SCHEMA §period 規則2 核出 period 過晚者，產出 known-issues JSON |

## 兩個必須知道的 CLI 副作用

`normalize_index.py` 存在的理由，見 `.claude/known-issues/先秦promote待決.md` §六：

1. `build_index_entry` 不輸出 `period`，任一次 `save_item` 都會把該條的 period 從索引抹掉；
   **一次 `book-index reindex --target draft` 會抹光全庫七萬餘條的 period**。
2. 索引 shard 寫入用 `indent=2`，倉庫既有格式是 `indent=1`，改一條就整個 shard 重排。

這兩點修好之前，promote 流程第 4 步的 `book-index reindex` 不可直接跑。
