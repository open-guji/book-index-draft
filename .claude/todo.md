# 古籍書目索引擴展計劃

更新：2026-08-09（遼金元 Round 2：317 no_author 以斷代志規則補 dynasty=遼金元，11 棄權）

---

## 朝代規範化

### 遼金元未決深查 Round 2（✅ 本地完成，待推 main）

**腳本**：`scripts/fix_liao_jin_yuan_round2.py`

**對象**：Round 1 遺留的 328 個 no_author Work（period=liao-jin-yuan, dynasty=null, authors=[]）。

**規則**：`indexed_by` 來源集合 ⊆ {元史藝文志, 補遼金元藝文志, 遼史藝文志, 金史藝文志} ∧ 不為空
→ Work.dynasty = 遼金元，`dynasty_basis=gazetteer_propagation`（SCHEMA 自驗：元史+補遼金元 96% 遼金元）。
來源含國史經籍志（明焦竑通代志）或隋書經籍志等非斷代志 → 棄權。

**已修復**：

| 類型 | 數量 | 說明 |
|---|---:|---|
| Work.dynasty 補全 | 317 | dynasty=遼金元，dynasty_basis=gazetteer_propagation |
| 棄權（mixed_source） | 11 | indexed_by 含國史經籍志(10) / 隋書經籍志(1) |
| index 同步 | 16 shards | 317 dynasty_sync，works 全部 16 shard 有改動 |

**驗證**：
- Work 索引 dynasty 不符：0
- `period=liao-jin-yuan` 無 dynasty：11（= 全部棄權）
- 已補分布：元 3497 / 金 369 / 遼金元 317 / 遼 31 / 金元 1 → 合計 4215
- chk.py 基線全數不變（197 / 3 / 4 / 24 / 12 / 2）

**棄權 11 條清單（附非斷代志）**：
1. 國語孝經（+隋書經籍志）
2. 九經要覽 / 宋汴都宮室記 / 百戰奇法 / 至元心燈錄 / 四書詳說 / 四書釋要 / 大易忘筌 / 成憲綱要 / 金國官制 / 孟子衍義（+國史經籍志）

### 遼金元未決深查 Round 1（✅ 已上 main）

**腳本**：
- `scripts/investigate_liao_jin_yuan.py`：只讀深查，輸出 `.claude/known-issues/遼金元未決.json`
- `scripts/fix_liao_jin_yuan_round1.py`：高置信補全 Work.dynasty + Entity.period + 誤入遼金元之南宋 Work 移出

**深查結論**：
- `period=liao-jin-yuan` 之 4,227 Work 原全數 dynasty 為空。
- author.dynasty 分布：元 3501 / 金 369 / 遼 31 / null 5 / 三國魏 1。
- Entity 側 period=liao-jin-yuan 1588 條，dynasty 俱已補（元 1442、金 125、遼 18、金元 2、偽齊 1）。

**已修復**：

| 類型 | 數量 | 說明 |
|---|---:|---|
| Work.dynasty 補全 | 3,898 | 元 3497 + 金 369 + 遼 31 + 金元 1 + 南宋 1（誤入遼金元移出） |
| Work.period 變更 | 1 | liao-jin-yuan → song（王厚之南宋，經 CBDB c_dy=15 證） |
| Entity.period 補全 | 76 | 元 69、金 7 → period=liao-jin-yuan（period_basis=synonym） |
| Entity.period 補全 | 1 | 王厚之 → period=song（period_basis=cross_check，CBDB c_dy=15） |
| Work author.dynasty 覆蓋 | 2 | 桐江詩派 李康（三國魏→元）、王厚之（null→南宋） |
| 棄權（no_author） | 328 | 無 authors，無從據 author.dynasty 補全，留人工 |
| index 同步 | 33 shards | works 16+1 shards（3899 dynasty_sync + 1 period_sync），entities 16 shards（77 period_sync） |

**判準**：
- Work.dynasty_basis = `author_propagation`（據 author.dynasty；author.dynasty null 時 fallback 至 Entity.dynasty）。
- Work.period_basis = `cross_check`（CBDB c_dy=15 證為南宋北宋時，period 由 liao-jin-yuan 改 song）。
- Entity.period_basis = `synonym`（dynasty=遼/金/元…→period=liao-jin-yuan 派生），或 `cross_check`（CBDB 證改 song）。
- 含非遼金元 author.dynasty（如三國魏）時，優先以 Entity.dynasty 覆蓋（Entity 是主檔）；若 Entity.dynasty 亦屬非規範則棄權。

**驗證**：
- `period=liao-jin-yuan` 但 dynasty 仍空：328（= 全部 no_author）
- period=liao-jin-yuan 且 dynasty=南宋/北宋（誤入殘留）：0
- Work 索引 dynasty 不符：0；Work 索引 period 不符：23（預存，不變）
- Entity 索引 dynasty 不符：0；Entity 索引 period 不符：1189（-1，王厚之被正確同步）
- chk.py 基線全數不變（索引欄位不符 197、懸空關聯 3、B→W 4、人物→作品 24、整理本 12、輯佚檔 2）

**剩餘邊界**：
- 328 個 no_author：無法據 author 補 dynasty，需下輪人工或其他規則（如 indexed_by 之斷代志）推斷。
- 預存 23 Work / 1189 Entity period 索引/檔案不符（索引有 period 而檔案 None）為歷史批次遺留，待 index 重建輪。

---

### 隋唐未決深查（✅ 已上 main）

**腳本**：
- `scripts/investigate_sui_tang.py`：只讀深查，輸出 `.claude/known-issues/隋唐未決.json`
- `scripts/fix_sui_tang_round1.py`：高置信補全 Work.dynasty + Entity.period

**深查結論**：
- `period=sui-tang` 之 Work 原有 1,832 條，**全部 dynasty 為空**。
- author.dynasty 分布：唐 1783、隋 51、隋唐 2、null 1、北宋 1。
- 1,831 條可機械補全（author.dynasty 俱屬 {隋,唐,隋唐}）；1 條棄權。
- Entity 側 period=sui-tang 787 條，dynasty 俱已補；dynasty=隋/唐 而 period 空者 7 條。

**已修復**：
| 類型 | 數量 | 說明 |
|---|---:|---|
| Work.dynasty 補全 | 1,831 | 唐 1779、隋 50、隋唐 2（單值取該值；多值混合取隋唐） |
| Entity.period 補全 | 7 | dynasty=唐 6、dynasty=隋 1 → period=sui-tang |
| 棄權（manual_mixed） | 1 | 《孝經注疏》作者 唐玄宗(唐)+邢昺(北宋)，跨隋唐/宋，留人工判 |
| index 同步 | 20 shards | works 16 shards（1831 條 dynasty_sync），entities 4 shards（7 條 period_sync） |

**驗證**：
- `period=sui-tang` 但 dynasty 仍空：1（《孝經注疏》棄權）
- Work 索引 dynasty 不符：0
- Entity 索引 dynasty 不符：0；我改的 7 Entity period 已同步
- chk.py 基線全數不變（索引欄位不符 197、懸空關聯 3、B→W 4、人物→作品 24、整理本 12、輯佚檔 2）

**判準**：
- dynasty_basis=`author_propagation`（據 author.dynasty 補全）。
- Entity.period_basis=`synonym`（據 dynasty 派生 period：隋/唐→sui-tang）。
- 含非隋唐 author.dynasty（如北宋）者一律棄權，不入機械批次。

**剩餘邊界**：
- 《孝經注疏》（1ev7943so5beo）：唐玄宗御注 + 宋邢昺疏，period=sui-tang 是否該改 song 待人工判。
- 邢昺 Entity（1j967cp1zdr1b, dynasty=北宋, period=null）待補 period=song（非本輪隋唐範圍）。
- 五代 Round 2 移交之「dynasty=唐/漢 大批殘留」：經查實為 period=sui-tang 之 author.dynasty=唐（真唐，非後唐），無需再拆；後唐已在五代輪處理。
- 預存之 23 條 Work period 索引/檔案不符 + 1190 條 Entity period 索引/檔案不符（索引有 period 而檔案 None），為歷史批次遺留，非本輪所致，待另立 index 重建輪處理。

---

### 五代十國未決深查（✅ 本地完成，待推 PR）

**分支**：`fix/five-dynasties-unresolved-investigation`

**腳本**：
- `scripts/investigate_five_dynasties_unresolved.py`：只讀深查，輸出 `.claude/known-issues/五代十國未決_深查.json`
- `scripts/fix_five_dynasties_unresolved_round2.py`：深查後高置信修復

**深查結論**：
- 當前 `period=five-dynasties` 的 Work 原有 50 條，其中 45 條是真五代十國 Work，但 `dynasty` 未補。
- 5 條其實是誤入五代：`釋亡名《周易私記》`、`樊文深《五經大義》`、`盧辨《稱謂》`、`周沈重《禮記義疏》`、`周熊安生《禮記義疏》`。
- 樊文深即樊深，字文深，北周經學家；「周沈重」「周熊安生」中的「周」為北周朝代前綴；盧辨亦北周人；釋亡名見於隋書經籍志，不可作五代後周。

**已修復**：
| 類型 | 數量 | 說明 |
|---|---:|---|
| Work.dynasty 補全 | 45 | 南唐 14、五代 14、後蜀 8、後晉 3、後周 3、後唐 2、前蜀 1 |
| 誤入五代 Work 移出 | 5 | 北周 4、待考 1 |
| Entity 修正 | 5 | 4 條改北周/nanbeichao，1 條釋亡名清空 dynasty/period 待考 |
| index 同步 | 21 shards | works 16 shards，entities 5 shards |

**驗證**：
- `period=five-dynasties` Work：45
- 五代 Work 無 `dynasty`：0
- 目標 Work/Entity 與 index 分片不一致：0

**剩餘邊界**：
- `dynasty=唐/漢` 的大批殘留不在本輪處理，交由隋唐/秦漢進程，避免同名異人誤判。
- 本輪不做 Entity 合併（如樊文深、盧辨/盧辯、沈重/周沈重），只修正高置信 dynasty/period。

---

### 南北朝朝代拆分（✅ 已推 PR #21，待 review/合併）

**分支**：`fix/nanbeichao-dynasty`

**處理範圍**：entity 和 author 層的歧義 dynasty 值（宋/晉/梁/周/齊/魏/吳/蜀/陳等），
拆分為學界通用的無歧義規範名（北宋/南宋/南朝宋/西晉/東晉/南朝梁/北魏等）。

**Round 1**（fix_nanbeichao_round1.py）：
- Batch A: CBDB c_dy 判定（1381 個有 cbdb_id 的 entity）
- Batch B: 歷史人物詞典
- Batch C: 隋志上限信號
- Batch D: Work.period 信號
- Batch E/F: Entity↔Author 雙向傳播

**Round 2**（fix_nanbeichao_round2.py）：
- Batch A2: CBDB IndexYear 判定（補充查詢 1381 個 cbdb_id 的 IndexYear）
- Batch B2: Work.title 年號關鍵詞
- Batch C2: 歷史人物詞典擴充（晉代 135+ 人物）
- Batch D2: Work.indexed_by 信號補強
- Batch E2: 誤標清理
- Batch F2/G2: Entity↔Author 雙向傳播

**成果**：
| 歧義值 | Round 1 前 | Round 2 後 | 解決比例 |
|---|---|---|---|
| entity.宋 | 2349 | 536 | 77% |
| entity.晉 | 886 | 298 | 66% |
| author.宋 | 3962 | 1173 | 70% |
| author.晉 | 1043 | 380 | 64% |

**剩餘工作**：
- [ ] PR #21 review/合併後 close
- [ ] 剩餘 ~536 entity.宋（c_dy=15 無 IndexYear）+ ~298 entity.晉（無 cbdb_id 殘名）待 Round 3
- [ ] 詳見 `.claude/known-issues/南北朝未決.json`

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
| 直齋書錄解題 | 1ev3bb403quio | 3,208 | 49類 | 2026-05-01 |

---

## 數據清洗待辦

> **已查明成因與範圍、決定暫不修者，登記在 `.claude/known-issues/`。**
> 那裡的每一條都是一張「動手前的對照表」——尤其是**準備新建 work 之前**，
> 先對 `殘名撰人.md`：比對不合未必真是庫中沒有。


### 補晉書藝文志 13 條錄入錯誤（✅ 已修復）

**修復狀態**：✅ 完成（2026-05-01）

**修復成果**：
- ✅ 刪除 3 條純注文條目（1evfuv425q3gg、1evfuv7m9pdds、1evfuva6picjk）
- ✅ 完全修復 5 條人名確認條目（程咸、盧湛、孔潘、王濬、正）
- ⚠️ 部分修復 5 條人名待確認條目（謝[某]、蔡[某]、王[某]、范[某]、[某]）

**原問題描述**：以下 13 條 Work 在錄入時，書名與作者字段發生串位——官職+姓氏被誤放進 `title`，卷數「集N卷」被誤放進 `author.name`。部分條目的 title 甚至是書志注文（「謹按見《七録》」等）而非書名。

**來源**：`indexed_by.source = 補晉書藝文志`
**詳見**：/d/workspace/overview/補晉書藝文志_修復完成報告.md

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

### 殘名撰人 169 條（✅ 已推 PR #17，待 review/合併）

**修復狀態**：✅ 已推 PR #17（4df5a12137 + f22cc4c7dc + 998bc84e18）

**已知缺陷檔案**：`.claude/known-issues/殘名撰人.md` + `殘名撰人.json`

**修復進度**：
| 批次 | 修復項目 | Work數 | Entity數 | 關鍵修復 |
|------|---------|--------|---------|---------|
| batch1+2 | 甲類14條+乙類高置信47條 | 61 | 23 | 公孫弘/歐陽棐/諸葛恪（甲類）；干→干寶/徐→徐邈（乙類） |
| batch3 | 乙類中置信25條 | 37 | 25 | 范→范寧/崔→崔譔；肇→僧肇/影→曇影/遠→慧遠（佛教）；伏→伏滔/戴→戴祚；蔡→蔡謨/謝→謝沈/毓→氜毓/純→荀綽/護→晏謨 等 |
| batch4 | 乙類其餘60條（四庫總目/漢志/補晉/None/遼金元） | 59 | 23 | 四庫：潘咸/莊昶/李禴；漢志：湯→天乙（臣X保留加注）；補晉：庾袞/郭璞/荀綽/劉涓子/嵇喜/阮侃/程實/胡訥/臣瓚/陳勰/范宣/范寧/釋曇微/毋雅/王濛/王肅/趙𢾅；None：李隆基/胤禛/張豫章/弘曆/高恥傳/薛𨭉/韓坰/胡煒；遼金元：釋元海 |
| 二字殘名普查 | 釋字缺失/姓氏缺失/複姓截首 | 66 | 12 | 道安→釋道安(35)/慧遠→釋慧遠(8)/景元→陳景元/馬彪→司馬彪 等 |

**重要發現**：
- 23 個 Entity 為錯誤關聯（如蕭維禎→僧肇、崔志→慧遠、釋法成→潘咸、朱瞻垍→莊昶、劉逸→釋元海、釋慶暹→范寧、釋祖賢→饒[置null]、董葵→義[置null]、竇說→說[置null]、郭純→荀綽、奇玄表→晏謨、韋祥→戴祥、張秀→程實 等），已一併更正
- 2 條 Entity 置 null（甄異記=戴祚 vs Entity=戴逵；禮記音=謝模 vs Entity=謝沈；《方言》劉昞 vs 劉銑共用）
- 18 條保留單字名但加注：堯舜湯娷饒信吾彭義說（漢志古帝王/臣X失姓）；孫傳車氏續（補晉不可考）；原湘（無法確定）
- 甲類改 title 已同步更新 `index/works/*.json` 的 title 和 path
- 部分 Work 同步修正 `period`（如靖炎兩朝見聞錄：陳→宋；唐石經/高恥傳/古梅禪師：朝代字→真實朝代）

**剩餘工作**：
- [ ] PR #17 review/合併後 close
- [ ] 核查 18 條保留單字中是否仍有可補考者（如《通鄭》陳起東、《老子湘注》湘東王繹等）

---

### 秦漢同名異書核對（✅ 已推 PR #17，待 review/合併）

**已知缺陷檔案**：`.claude/known-issues/秦漢同名異書核對.md`

**修復進度**（271 組同名候選 + 全庫 Entity 分裂掃描）：
| 批次 | 處理內容 | 合併數 | 關鍵修復 |
|------|---------|--------|---------|
| batch1-4 | 個案逐組核對（揚雄/張仲景/說文等） | 16 Work | 楊/揚異寫、張機=張仲景、說文目標選錯修正 |
| batch2 | 別集連書省撰人（秦漢一區） | 63 組 118 Work | 陳琳集/班固集/蔡邕集等志書省撰人 |
| batch5-9 | 連續個案核對 | 14 組 | 准/準異體字、姓氏誤拆朝代（魏伯陽/陳伯宣） |
| batch10 | 50 組待核清單 | 44 Work | 7 組作者誤截修正 + 35 組經典常識匹配 |
| batch11-12 | 列女傳/孝子傳/皇覽等個案 | 18 Work | 綦毋邃殘名、祖珽=祖孝徵、樊文深質疑拆分 |
| batch13 | Entity 分裂合併 | 26 Entity | 郭璞/干寶/釋道安/范寧/謝沈/曹丕/嵇康 等 16 組 |
| batch14 | 同題同 Entity 掃描 | 20 Work | 張華/范咸/干寶/傅玄 等；5 組漢志同名異書跳過 |
| batch15 | 同作者名不同 Entity 掃描 | 10 Work + 3 Entity | 4 entity_id 修正（司馬彪/荀悅/庾亮/茅元儀） |
| batch16 | 徐邈 Entity 合併 + Pattern 3 全庫掃描 | 119 Work + 1 Entity | 73 組連書省撰人（殷褒集/王坦之集/嵇紹集等） |

**剩餘工作**：
- [ ] PR #17 review/合併後 close
- [ ] 約 38 組秦漢同名候選待覈（多屬「XX注」「XX傳」大型異撰人集合，推定多為真異書）
- [ ] 徐廣宋 entity（cbdb 96703）待 CBDB 覆核是否為劉宋
- [ ] 公孫尼子「吳定」疑混淆輯佚者與原作者，待覈

---

## 待整理（優先順序）

### 1. 崇文總目 ✅ 完成

- **Work ID**: GYL54TNYYa3
- **條目數**: 3,369，44類目
- **完成日期**: 2026-04-13
- **腳本**: `D:/tmp/process_cwzm.py`（可作為模板）

### 2. 直齋書錄解題 ✅ 完成

- **性質**：南宋陳振孫私家目錄（約1234年）
- **重要性**：現存最重要的宋代私家目錄，條目詳有解題，史料價值極高
- **原文**：Wikisource → https://zh.wikisource.org/wiki/直齋書錄解題
- **卷數**：22卷 ✅（卷21-22 發現需用「卷二十一」「卷二十二」格式，已全部下載）
- **條目數**：3,208 條 ✅ 100% 覆蓋（較原始估計 3,039 多因多書合記格式）
- **已生成 Work**：2,157 個新建 + 1,051 個匹配現有
- **已生成 CE 類目**：49 個（經部 10 類、史部 17 類、子部 18 類、集部 1 類、含各種雜部）
- **完成日期**：2026-05-01
- **狀態**：✅ 完全完成（3,208/3,208）

### 3. 郡齋讀書志

- **性質**：南宋晁公武私家目錄（約1151年，比直齋書錄解題早 83 年）
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
