# 並行會話認領

見 `.claude/plans/升格並行方案.md` §七。

- `claims/<branch>.json` —— 一會話一檔，開工前寫、收工刪。天然無衝突。
- `handoff/<branch>.md` —— 越出認領範圍而不自己動手的事，寫在這裡交棒。

開工前掃一遍 `claims/`，有重疊先協調。
