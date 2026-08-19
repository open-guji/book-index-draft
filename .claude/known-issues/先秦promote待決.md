# 先秦條目 promote 前待決事項

2026-08-19。承 [先秦諸子總覽_分析與待辦.md](先秦諸子總覽_分析與待辦.md)（2026-08-10 初篩），
本輪為 draft → production 升級做的 D 類修復已完成（見同日 commit），以下是**刻意未動、留待決策**者。

## 一、《老子》／《道德經》：兩條皆非乾淨原典，不宜機械合併

| id | 題名 | 撰人 | Book | related_works | 實際扮演 |
|---|---|---|---|---:|---|
| `1evcmnccovx1c` | 老子 | 梁曠（隋志著錄） | 0 | **54**（全為 `text_carried_by` → 河上公注／鐘會注／羊祜注…） | 隋志注本群之**原典磁鐵** |
| `1evkaeh09axhc` | 道德經 | 李耳 | **7** | 5 | 故宮善本目錄錄入，description 講的是元趙孟頫寫本這個**版本** |

往任一方向合併都會丟結構：併入前者則 7 個 Book 掛到一條無 Book 的著錄條上；
併入後者則 54 條注本關係掛到一個版本條目上。
**處置**：走 `/collate-classic`，另立乾淨的《老子》原典 Work（「無作者經文 Work」模式，
比照 `1evl7l48e27ls` 周易、`1evl7fct2ezgg` 尚書），再把兩條分別歸位為著錄與版本。
在此之前兩條都不 promote。

庫中相關同題條目另有：`1evcmncbkb2f4`（鐘會）、`1evgpn7mcbhfk`（戰國河上丈人）、
`1evjr364pnb40`（馬王堆帛書本）、`1evr5e3mifbg9`、`1evkpy1pzn20w`（王弼）、
`1evkpxj94h98g`（河上公）及《老子注》十六條，一併在該輪釐清。

## 二、`period` 派生自「傳」「注」者，index.dynasty 顯示失真

`index/works/*.json` 的 `dynasty` 取 `authors[0].dynasty`。當一條原典 Work 的 authors 只有
傳經者或注者時，原典就顯示成傳／注者的朝代：

| id | 題名 | index 顯示 | 實情 |
|---|---|---|---|
| `1evl7nl9gl88w` | 儀禮 | 漢 | authors[0] 是「高堂生・傳」，高堂生確為漢人；`period` 已正確作 pre-qin |

**這不是條目資料錯，是索引派生規則的問題**——`_extract_first_author` 不區分 role。
記於此以免下次又被當成錯誤「修」掉。若要治本，宜在 `build_index_entry` 取首位 role 為
撰／編／輯／纂／作者之 dynasty，無則留空，而非逕取 authors[0]。

## 三、偽託先秦之作，`dynasty` 尚未依錄入規範改標成書時代

錄入規範〈偽托作品〉條：**dynasty 標實際成書時代，role 用「託名」**，並舉《關尹子》（宋）、
《列子》（魏晉）、《古三墳》（宋）為例。但庫中此三條仍標先秦：

| id | 題名 | 現 dynasty | 規範應標 | 影響 |
|---|---|---|---|---|
| `1ev3bcqgb33ls` | 關尹子 | 先秦（尹喜・撰） | 宋 | 改後移出先秦 promote A 批 |
| `1ev3bcqgzflz4` | 列子 | 先秦（列御寇・撰） | 魏晉 | 同上 |
| `1ev3bbtcalpts` | 禽經 | 春秋晉（師曠・撰） | 宋（舊題師曠撰張華注） | 本不在 A 批 |
| `1ev3bblr2isqo` | 李虛中命書 | 周（鬼谷子・撰） | 唐（李虛中）或宋 | 本不在 A 批 |
| `1ev3bbyca5ts0` | 於陵子 | 戰國齊（陳仲子・撰） | 明（四庫提要謂明人偽撰） | 本輪只修了 period 派生 bug |

**未動的理由**：這一改動會把 5 條移出先秦選集，屬編目判斷而非資料錯誤修復，
且規範所說的 `authenticity` / `attributed_dynasty` 欄位（D 階段）尚未擴充——
在只有一個 `dynasty` 欄的情況下，標成書時代就丟了「舊題某某」這一層信息。
建議與 schema 擴欄一併處理。

## 四、原典／注本層級未分，title 與 authors 不合錄入規範

| id | 題名 | 問題 |
|---|---|---|
| `1evinckalh1xc` | 難經集注 | authors 作「秦越人・撰」，然秦越人是《難經》原典舊題撰人，非集注輯者（呂廣以下五家注，明王九思等校刊）。`period` 因此懸空 |
| `1evcsw6n98r9c` | 大學 | authors[0].role 為「注」（鄭玄）。依錄入規範「role 為注／傳／疏者 title 含注者名」，title 宜作《大學鄭玄注》，今題《大學》與原典層易混 |
| `1ev794a8n13wg` | 纂圖互注老子道德經 | 刻本名建成 Work 且 dynasty 標先秦 |
| `1evka7taq0ykg` | 纂圖互注荀子 | 同上 |
| `1evkapdgetc74` | 王翰林集注黃帝八十一難經 | 同上；且與 `1evinckalh1xc` 難經集注實為一書異名 |
| `1evkaaiv2fthc` | 南華真經旁注 | 同上 |
| `1evcs0sj05qf4` | 孫子魏武帝注 | 注本命名已合規，惟 dynasty 標先秦（應為三國魏） |
| `1evkeavqxv4e8` | 春秋公羊傳注疏 | 同上 |

處置見〈原典注疏關係設計〉與〈06-注本命名重構方案〉。

## 五、`period` 與著錄志上限相牴觸（全庫 175 條，非先秦專有）

依 SCHEMA §period 規則2「著錄之志為時代上限」自動核出，明細見
[period-著錄志上限衝突.json](period-著錄志上限衝突.json)。

- 先秦範圍內的 4 條（論語、周禮、青史子、論語齊）本輪已修。
- 另 21 條是**注本假陽性**：注本 `period` 取注者朝代，卻繼承了原典的漢志著錄，
  如 `1ev3bacepxslc` 逸周書孔晁注（period=jin，孔晁西晉人，正確）。已在 JSON 裡以
  `derived_from_annotator` 標出。
- 其餘 175 條多為 `ming`/`qing` 而見於宋元以前之志，疑為同題異書合併過度（磁鐵條目），
  需另立一輪處理。

## 六、book-index-manager 兩處副作用（本輪繞開，未治本）

1. **`build_index_entry` 不輸出 `period`**（`book_index_manager/entry_extractor.py:154`）。
   但 SCHEMA §period 明言「`period` 亦入 `index/works/*.json`」，且現有 shard 確實有此欄。
   後果：任一次 `save_item` 都會把該條的 `period` 從索引抹掉；
   **一次 `book-index reindex --target draft` 會把全庫七萬餘條的 `period` 一次抹光**。
   本輪以 `scripts/promote-work/` 下的回填腳本繞開，未跑 reindex。
2. **索引 shard 寫入用 `indent=2`，倉庫既有格式是 `indent=1`**。
   後果：改一條就整個 shard 重排，5 條改動產生四十四萬行 diff。本輪寫回 `indent=1`。

兩者都在 `book-index-manager` 倉，需另發版修。**修好之前，promote 流程第 4 步的
`book-index reindex` 不可直接跑。**
