# B1 併池：同名異書 size≥4（393 組 2,076 條）

車道定義見 `.claude/plans/並行作業總表.md`〈B 類〉。本目錄記 B1 之施行明細。

## 作業工具

| 檔 | 用 |
|---|---|
| `scripts/b1/scan.py` | 掃出 393 組並攤平其全部欄位（只讀） |
| `scripts/b1/triage.py` | 按「組內有無可疑重出對」排優先序（只讀） |
| `scripts/b1/show.py` | 印指定 work 之著錄／考證原文，逐組裁決時用 |
| `scripts/b1/merge.py` | 依裁決計畫施行合併（乾跑／`--apply`） |

`merge.py` 之作業：loser 之 `indexed_by`／`emendated_by` 併入 keeper 並蓋
`merged_from`；keeper 空缺之欄補之（**不搬 `period_upper`——C 車道之欄**）；
全庫單次掃描改繫（整理本 `work_id`、`entity.works`、`Book.work_id`、他 work 之
`related_works`）；異名之 entity **解連而非改繫**，其 `works` 空則刪檔；
刪 loser 檔並同步索引（**不跑 reindex**）。

## 分流（2026-08-21 掃描）

| 檔 | 組數 | 說明 |
|---|---:|---|
| 同撰人 | 7 | 信號最強 |
| 撰人一字之差 | 53 | 形訛／異寫，依「同題異撰人」既有判準 |
| 一方無撰人而卷數同 | 67 | 需讀原文 |
| 兩無撰人而卷數同 | 1 | |
| 無信號 | 265 | 多為真異書（《易說》31 條各出宋人之手） |

## 施行

| 批 | 計畫檔 | 合併 | 結果 |
|---|---|---:|---|
| 01 | `batch01_plan.json` | 7 | 已施行，`chk.py` 無回歸 |
