# 交棒給 C 類（斷代）—— 來自 B1 併池

## 一、被併之條所帶的 period 一律未搬，請勿以為漏

`scripts/b1/merge.py` 不承接 `period`／`period_upper`／`dynasty`／`loss_status`
（C、D 車道之欄）。合併只承接卷數等作品身分欄。keeper 若無 period，仍待 C 車道補。

## 二、一個已知的誤判模式：清史稿「不著時代」→ period=qing

《毛詩義疏》被併之條 `1evc5pcnjvcow` 之 `period_basis` 作
「qing_round1:period=qing 且非通用作者 dynasty 唯一为「清」」，
而其著錄原文是清史稿「**不著時代**舒瑗《毛詩義疏》一卷，不著時代。」——
清史稿之「不著時代」條被當成清人之作。該條已隨合併消去（其正主是隋志舒援二十卷本），
但**同一模式極可能還有一批**：凡 `period=qing` 而其唯一著錄源為清史稿、
且著錄原文含「不著時代」者，宜整批復核。
