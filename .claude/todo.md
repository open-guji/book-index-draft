# 古籍書目索引擴展計劃

更新：2026-04-13

---

## 已完成

| 志書 | Work ID | 條目數 | 類目數 | 完成日期 |
|------|---------|--------|--------|----------|
| 漢書藝文志 | GY2rqZp8Hvw | 621 | 6略 | 2026-04 |
| 隋書經籍志 | GYPvDKFFw83 | 3,230 | 40類 | 2026-04 |
| 舊唐書經籍志 | GYTWvzLCAo9 | 2,950 | 39類 | 2026-04 |
| 新唐書藝文志 | GYTaMxR7uV9 | 5,257 | 44類 | 2026-04 |
| 宋史藝文志 | GYTbVni8ptF | 9,984 | 44類 | 2026-04 |
| 明史藝文志 | GYPyKweoWhV | 3,874 | 35類 | 2026-04 |
| 欽定四庫全書總目（含存目） | GY4HvsY3w3u | 10,283 | 200卷 | 2026-04 |
| 清史稿藝文志 | GYUAfQHm7bu | 8,883 | 45類 | 2026-04-12 |
| 崇文總目 | GYL54TNYYa3 | 3,369 | 44類 | 2026-04-13 |

---

## 數據清洗待辦

### 補晉書藝文志 13 條錄入錯誤（待修）

**問題描述**：以下 13 條 Work 在錄入時，書名與作者字段發生串位——官職+姓氏被誤放進 `title`，卷數「集N卷」被誤放進 `author.name`。部分條目的 title 甚至是書志注文（「謹按見《七録》」等）而非書名。

**來源**：`indexed_by.source = 補晉書藝文志`

**受影響的 wid**：
| wid | 現 title（錯誤） | 現 author.name（錯誤） |
|---|---|---|
| 1evfuv2kzy51c | 輔國將軍王 | 集一卷 |
| 1evfuv2ncjg8w | 侍中程 | 集三卷 |
| 1evfuv2potiww | 巴西太守 | 正集一卷 |
| 1evfuv425q3gg | 一卷謹按見《七録》。 | 一卷 |
| 1evfuv5he7da8 | 司空從事中郎盧 | 集十卷 |
| 1evfuv611ucqo | 太常謝 | 集二卷 |
| 1evfuv7m9pdds | 一卷謹按見《七録》。兩《唐志》著録 | 一卷 |
| 1evfuv7wi1edc | 司徒蔡 | 集四十三卷 |
| 1evfuva6picjk | 一卷謹按見《七錄》。《隋志》四卷,云殘缺。 | 一卷 |
| 1evfuvarown40 | 太常王 | 集十五卷 |
| 1evfuvb97g0e8 | 豫章太守范 | 集十六卷 |
| 1evfuvc0tmuio | 右軍參軍孔 | 集二卷 |
| 1evfuvcxycm4g | 武帝左九 | 集四卷 |

**處理方向**：
1. 回源查「補晉書藝文志」原文，確認每條的真實書名與作者全名
2. 修正 `title`（應為「XXX集」形式）、`author.name`（應為人名）、`author.dynasty`（晉）
3. 對 `title` 含書志注文的條目（1evfuv425q3gg、1evfuv7m9pdds、1evfuva6picjk），確認是否應保留該 Work 或刪除

**補晉書藝文志**原文可從 `D:\workspace\book-index-draft\.claude\二十五史艺文经籍志考补萃编书目.md` 確認收錄情況。

---

## 待整理（優先順序）

### 1. 崇文總目 ✅ 完成

- **Work ID**: GYL54TNYYa3
- **條目數**: 3,369，44類目
- **完成日期**: 2026-04-13
- **腳本**: `D:/tmp/process_cwzm.py`（可作為模板）

### 2. 直齋書錄解題

- **性質**：南宋陳振孫私家目錄（約1234年）
- **重要性**：現存最重要的宋代私家目錄，條目詳有解題，史料價值極高
- **原文**：Wikisource → https://zh.wikisource.org/wiki/直齋書錄解題
- **卷數**：22卷
- **條目數**：約3,039條
- **格式**：類似崇文總目，有解題文字
- **狀態**：⬜ 待開始

### 3. 郡齋讀書志

- **性質**：南宋晁公武私家目錄（約1151年）
- **重要性**：現存最早的附有解題的私家目錄
- **原文**：Wikisource → https://zh.wikisource.org/wiki/郡齋讀書志
- **卷數**：20卷（衢本）/ 4卷（袁本）
- **條目數**：約1,472條
- **狀態**：⬜ 待開始

### 4. 經義考

- **性質**：清朱彝尊撰，專錄經學著作（1700年）
- **重要性**：最全面的經學書目，收錄歷代經學著作約6萬種
- **原文**：Wikisource → https://zh.wikisource.org/wiki/經義考
- **卷數**：300卷
- **條目數**：極多（估計15,000+條）
- **注意**：規模很大，可能需要分批處理
- **狀態**：⬜ 待開始

### 5. 書目答問

- **性質**：清張之洞撰（1875年），推薦讀書目錄
- **重要性**：影響深遠的入門書目，近代士人必讀
- **原文**：Wikisource → https://zh.wikisource.org/wiki/書目答問
- **卷數**：5卷（附補遺）
- **條目數**：約2,200條
- **狀態**：⬜ 待開始

### 6. 四庫禁毀書目

- **性質**：清乾隆時列為禁書的書目
- **重要性**：補充四庫體系，反映清代文化管制史料
- **版本**：
  - 四庫全書禁毀書目（官方）
  - 四庫禁毀書叢刊（北京出版社，1997，收488種）
- **原文**：Wikisource → https://zh.wikisource.org/wiki/四庫全書禁毀書目
- **狀態**：⬜ 待開始

### 7. 漢書藝文志深度校對（進行中）

- **性質**：對已完成的漢書藝文志做深度校對，補充description和ai_note
- **資料**：溫浚源《漢書藝文志講要》（四川師大）—— `D:/workspace/book-index-draft/tmp/汉书艺文志讲要/`
- **進度**：
  - [x] 六藝略·01-易 完成
  - [ ] 六藝略·02-書 進行中（本次session處理）
  - [ ] 六藝略·03-詩 待開始
  - [ ] ... 其餘各略待開始
- **Skill**：使用 `collate-catalog` skill，參數傳入對應章節MD文件
- **狀態**：🔄 進行中

---

## 資源清單

### 維基文庫

- 崇文總目：https://zh.wikisource.org/wiki/崇文總目
- 直齋書錄解題：https://zh.wikisource.org/wiki/直齋書錄解題
- 郡齋讀書志：https://zh.wikisource.org/wiki/郡齋讀書志
- 經義考：https://zh.wikisource.org/wiki/經義考
- 書目答問：https://zh.wikisource.org/wiki/書目答問
- 四庫全書禁毀書目：https://zh.wikisource.org/wiki/四庫全書禁毀書目

### 上海圖書館古籍書目

- 入口：https://gj.library.sh.cn/ancientBookCatalogue/search
- 各志書 dataType 參數需到網站確認

### CText（中國哲學書電子化計劃）

- 崇文總目：https://ctext.org/wiki.pl?if=gb&res=657047

---

## 腳本模板位置

已完成的志書腳本可複用：

- `D:/tmp/process_qingshigao.py` — 清史稿處理主腳本（最新，可作模板）
- `D:/tmp/build_qingshigao_ce.py` — CE構建腳本
- `D:/tmp/fix_qingshigao_duplicates.py` — 同名異書修復
- `D:/tmp/fix_qingshigao_all.py` — 综合質量修復

---

## 注意事項

1. **作者校驗必須在第一輪匹配時進行**——古籍同名異書極普遍（宋史錯誤率80%）
2. **注本一律獨立Work**——通過 `related_works.commentary_on` 關聯原典
3. **序文識別**——無書名號+長段散文(>100字)=序文，用 `type:"序"`
4. **崇文總目特殊情況**：今本多有缺卷，使用輯本時需注意標注
5. **工作流**：始終按 collate-bibliography.md skill 的5步流程執行
