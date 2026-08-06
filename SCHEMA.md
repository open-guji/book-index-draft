下面我们要把这个文件夹下面的每一个文件的Schema从markdown文件转成json文件 

所以我们现在要去设计一个多层的Schema 

你先看一下现在的不同的book collection和work 他们之间有哪些field 然后先照现在有的信息是帮我设计一个schema 注意现在我们的key的名字还是要用英文 方便以后转换成code  然后相关的设计都放到这个文件的后面 

---

## Proposed JSON Schema Design

Each entity (`Work`, `Collection`, `Book`) will have a corresponding JSON structure. 

### 1. Work Schema
Represents the abstract intellectual content.

```json
{
  "id": "string (e.g., GXyzYmA7iJb)",
  "type": "work",
  "subtype": "string (book | article | poem | chapter, default: book)",
  "title": "string (Chinese title)",
  "additional_titles": ["string (同書異名/別稱，如《左傳》=《春秋左氏傳》=《春秋左傳》)"],
  "description":  "Description (object)",
  "authors": [
    {
      "name": "string",
      "role": "string (e.g., author, annotator, editor)",
      "dynasty": "string (optional)",
      "source": "Source"
    }
  ],
  "books": ["string (List of Book IDs)"],
  "related_works": [
    {
      "id": "string (Work ID)",
      "title": "string (Work title, for display — 應與目標 Work 的 title 一致)",
      "relation": "string (見下文「關聯詞表」)",
      "note": "string (optional, 說明此關聯的性質或限度)"
    }
  ],
  "additional_works": [
    {
      "book_title": "string (sub-work title within this work)",
      "n_juan": "integer (number of juan)"
    }
  ],
  "measures": [
    {
      "unit": "string (計量單位：卷|回|集|編|篇|則|段|節|部|册 等)",
      "number": "integer (數量)",
      "note": "string (optional, 僅存計量相關信息，如「每集五回」)"
    }
  ],
  "measure_info": "string (optional, UI 直接展示文本，應與 measures 一致，例：「四集（每集五回）二十回」)",
  "juan_count": {
    "number": "integer (卷數)",
    "description": "string (optional, 如「存三卷」「原十卷今殘」)"
  },
  "original_title": "string (optional, 條目原題與規範題不同時記原題，如《毛詩義問劉楨撰》→「毛詩義問」)",
  "dynasty": "string (optional, 作品成書朝代；與 authors[].dynasty 不同，後者是作者所屬朝代)",
  "indexed_by": [] // type: IndexEntry，見下文
  "emendated_by": [] // type: IndexEntry，考證／校勘類著作對本書的校訂條目
  "contained_in": [
    {
      "id": "string (Collection ID)",
      "volume_index": "string | integer | array (optional, 在該叢編中的冊次／卷次)"
    }
  ],
  "publication_info": {
    "year": "string (年份或朝代)",
    "details": "string"
  },
  "version_graph": {
    "enabled": "boolean",
    "title": "string",
    "description": "string",
    "...": "版本傳承圖資料，供前端渲染"
  },
  "_has_text": "boolean (派生：resources[].types 含 text)",
  "_has_image": "boolean (派生：resources[].types 含 image)",
  "_has_collated": "boolean (派生：存在 collated_edition 整理本)",
  "loss_status": "string (optional, 存佚。枚舉見下「loss_status 枚舉」。欄位不存在 = 今存或未考，不必寫)",
  "promoted_to": "string (Production ID，本草稿記錄已升格；權威來源為 promotions.json)",
  "promoted_at": "string (ISO 8601 時間戳)",
  "ai_note": "string (optional, 建檔／整理過程的自注：資料來源、存疑、待辦。非面向讀者的正文)",
  "sources": [] // type: Source
}
```

**已刪之欄位**：`book_contained_in`、`parent_works`、`resource_groups`（Work 層）——見「記錄之共通欄位」節。
`book_contained_in` 的設計仍然有效（見下文說明），但實際錄入一律走 `contained_in`；
Work 層的 `parent_works` 已由 `related_works[].relation == "part_of"` 取代；
`resource_groups` 目前只在 Book 層使用。

#### 整理本 section 的三個指涉欄位

整理本置於 `Work/{c1}/{c2}/{c3}/{id}/collated_edition/`，每卷一檔，檔內 `sections` 為條目陣列。
條目指向別的記錄有三個欄位，義各不同，不可混用：

| 欄位 | 指向 | 義 |
|---|---|---|
| `work_id` / `work_ids` | Work | 本條所著錄的作品。一條著錄多書時用複數形。 |
| `book_id` | Book | 本條所著錄的是某一具體版本（如小說書目逐版著錄者）。 |
| `target_bid` | Work（書目本身） | **本志所考的那部書目**，如《隋書經籍志考證》各條的 `target_bid` 為《隋書經籍志》。與前二者無關。 |

`target_bid` 之名易生誤解——它不是「本條所指的 book」，而是考證的對象。
凡欲記「本條所指為某具體版本」，一律用 `book_id`。

#### 輯佚檔（`fragments`）

置於 `Work/{c1}/{c2}/{c3}/{id}/fragments/{title}.json`，`schema_version: 2`。
分層而共用一個結構：**著錄層**（`catalog`）記某書幾家輯過、各得幾條、見於哪些書哪些卷，
皆有據而不含佚文原文；**文本層**（`text`）逐條錄其佚文。得文本則就地填入 `fragments[].text`，
不另立檔，`coverage.level` 是唯一須隨之改動的欄位。

**受控詞彙一律英文**（2026-08 遷移）。此前輯佚檔作中文（著錄層／文本層）而整理本作
`toc`／`text`，同一概念兩套詞。專名（`collector`、`work`、`title`）與散文說明
（`statement`、`note`、`basis`、輯本序原文）仍中文——那是內容，不是詞彙。

| 欄位 | 枚舉 |
|---|---|
| `coverage.level` | `catalog` → `titles` → `text` ／ `text_partial` |
| `text_status` | `recorded`／`not_recorded` |
| `confidence` | `certain`／`uncertain` |
| `provenance` | `secondary`（轉錄自考證書或輯本）／`primary`（已覆核所引原書） |
| `count_unit` | `item`（條）`piece`（篇）`section`（節）`entry`（事）`poem`（首）`juan`（卷） |
| `verify_result` | `out_of_scope`（該輯家體例不收此類書）／`not_found`（遍檢其書而無之） |
| 整理本 section `part` | `main`（正編）／`supplement`（續編）／`appendix`（附） |
| 整理本 section `bian` | `classics`（經編）／`masters`（子編）／`history`（史編）／`supplement`／`appendix` |
| 整理本 section `type` | `reconstruction`（輯本） |

`schema_note` 已去（一千二百三十四份逐字相同，八萬七千餘字），改為指標 `schema_ref`
指向本節。schema 之說明是 schema 之事，不是每條資料之屬性。

主要欄位：

| 欄位 | 義 |
|---|---|
| `work_id` | 本書之 Work ID，須與所在路徑相符 |
| `loss_status` | 存佚，見下表 |
| `statement` | 存佚之敘述（何時著錄、何時亡佚、據何而知） |
| `provenance` | `primary`（已覆核輯本原書）／`secondary`（轉錄自考證書）。<br>現全為 `secondary`；此欄雖恆定而不可去——一旦覆核原書即當改 `primary`，去之則後人須重立。 |
| `based_on[]` | 所據之書：`{source, source_bid, field}` |
| `collectors[]` | 輯家：`{collector, work, work_id, sections, count, count_unit, statement, basis}`。<br>**`count` 是「該輯家輯得幾條」，不是「本庫已錄他幾條」**——二者常不等（《古文瑣語》馬國翰得十五條而本庫只錄一條），校驗時勿相比。本庫所錄之數在 `coverage.fragments_recorded`。<br>`count` 取自輯本序者須防序中之數非其本人所得，見 SKILL「從輯本序裡取條數」。<br>`sections[]` 記本書在該輯佚叢書整理本中的位置 `{file, index, title, part, juan_no, lei}`——一書而正編、續編兩見者，馬氏正編輯之而續編又補，非歧義，故用陣列。<br>**`collector` 不得為空**——一條即斷言「某人輯過此書」，無其人則此斷言落空。<br>`work_id` 繫本庫中該輯佚叢書之 Work。 |
| `collection_attested[]` | 確有輯本而未詳其輯家者：`{basis, work, statement, count, count_unit}`。<br>與 `collectors[]` 分立，因該陣列之一條即斷言「某人輯過此書」，輯家不可空；而「有輯本而不著其人」是另一件事，記於此欄，其據照錄於 `basis`。<br>得其人後當移入 `collectors[]`。校驗時本欄與 `collectors`、`fragments` 同為據，有其一即非空檔。 |
| `other_statements[]` | 與本書相關而**不是輯本序**者（本志篇序、舊注之序、校注序），自 `collectors` 移出者記 `moved_from` |
| `cited_in_summary[]` | 佚文所見之書與部類，尚未析出為逐條者 |
| `fragments[]` | 逐條佚文：`{seq, text, cited_in, collected_by, attested_by, confidence, note}`。<br>**`heading` 與 `piece_title` 不是同一件事，勿合併**：`piece_title` 是**這一條佚文自身之題**（嚴可均按撰人編次，一條即一篇，如〈上書諫伐匈奴〉）；`heading` 是**數條佚文共有之標目**（姚之駰按傳主編次，「光武皇帝」下繫四十七條）。一者標識自身，一者標識所屬。<br>`editor_note` 是輯家之案語（姚書原作【…】），是輯家之考，非本書之文，**不得與 `text` 相混**。<br>`text_from` 已去（八百條與 `attested_by` 逐字相同）。 |
| `coverage` | `{level, fragments_attested, fragments_recorded, text_available}`。<br>`level` 四級：`catalog`（僅知幾家輯過）→ `titles`（知輯本各篇之題）→ `text`（正文全錄）／`text_partial`（正文部分錄）。<br>`titles` 現無實例（嚴可均那批已升 `text`），定義保留待用。<br>`fragments_attested` 為 null 者是**未知**，非零——如據叢書目錄立檔，目錄不載條數。<br>**數家所得不同時，`fragments_attested` 取諸家所稱之最大數**，並以 `fragments_attested_note` 記其所以（《古文瑣語》嚴輯十九條、馬輯十五條、章宗源云十三事，取二十五）。 |
| `fragments[]` 之篇目條 | 有 `piece_title` 而 `text` 為 null，是「知其篇而未錄其文」，須並記 `text_status`，否則與「無文」無從分辨。 |

##### 輯佚叢書整理本（`type: fragment_collection`）

輯佚叢書（《玉函山房輯佚書》一類）之整理本，別於書目之 `catalog` 與考證之 `kaozhen`。
一類一檔，section 即一部輯本書，`work_id` 指其所輯之原書。
`coverage.level` 三級：`books_only`（僅知其書）→ `toc`（卷目已備）→ `text`（文本已錄）。
與輯佚檔之 `level` 同為英文而詞不同——彼記「這部書之佚文到了哪一層」，
此記「這部叢書之整理到了哪一層」，二事不同，故不強合。

**section 須自帶 `coverage`。** `fragments: []` 之義為「尚未錄入」而非「無佚文」，
無此欄則二者無從分辨。

雙向：整理本 `section.work_id` → 原書；原書輯佚檔 `collectors[].sections[]` → 整理本之條。

##### `loss_status` 枚舉

一軸而已：**本書之文今日尚存幾何**。欄位不存在 = 今存或未考，不必說明。

| 值 | 中文 | 界說與判準 |
|---|---|---|
| `lost` | 全佚 | 原書無一存。**類書所引之佚文、後人之輯本，皆不改其為全佚**——「今存者為清孫星衍校輯本」仍是 `lost` |
| `partially_extant` | 殘存 | 存其部分。須有原數今數之差（「《漢志》七十一篇，今存六十三篇」）；泛言「殘缺」不足 |
| `extant` | 今存 | 已覆核尚存。只在需要推翻既有推定時才明寫 |
| `undetermined` | 未詳 | 考過而不能定。與「欄位不存在」有別——後者是未考 |

**殘存不用 `fragmentary`。** 西方書目學之 fragmentary 多指「只靠他書徵引之斷片存世」，
那正是本庫的 `lost` 加輯佚檔，與 `partially_extant` 相反，用之則二者混為一詞。

**不入本枚舉的兩件事：**

- **出土**不是存佚狀態而是路徑。原書久佚而賴簡帛復見者，其狀態即 `extant` 或
  `partially_extant`；出土之事由該 Work 的 Book（簡帛實物）與「出土簡帛」Collection 承載。
  又：出土之書多數（本庫 257 部中 242 部）前所未聞，從無記載可失，本不需要此欄位。
- **有輯本**不是存佚狀態而是補救。由 `fragments` 檔之有無與 `collectors` 是否非空導出。
- **真偽**是另一軸。《古文尚書》今存而偽，《關尹子》今存而偽——併入本枚舉即無從表達。

#### IndexEntry object type（`indexed_by` / `emendated_by` 共用）

```json
{
  "source": "string (著錄該書的目錄／志書／考證書名稱，如「漢書藝文志」「直齋書錄解題」)",
  "source_bid": "string (該目錄書的 Work ID)",
  "title_info": "string (該目錄中的著錄標題原文，如「毛詩義問十卷魏太子文學劉楨撰」)",
  "summary": "string (該目錄中的著錄／解題全文)",
  "section": "string (optional, 該目錄中的分類，如「經部/易類」)",
  "juan_count": "string (optional, 該目錄著錄的卷數原文)"
}
```

- `indexed_by`：本書被目錄書／志書**著錄**（文獻學引證，記「某志收有此書」）。
- `emendated_by`：本書被**考證／校勘類著作**校訂（記「某考證書對此書有辨正」），如《漢藝文志考證》《隋書經籍志考證》。二者結構相同，語義不同：前者是登記，後者是校議。

Book 的 `indexed_by` 與 Work 的 `indexed_by` 同結構，記錄該具體版本被目錄書/志書/考證書著錄的條目。場景：通俗小說書目這類目錄書中按版本著錄的條目（如「乾隆甲戌本脂硯齋重評石頭記」「王希廉評紅樓夢一百二十回」）應掛在對應的 Book 上，而非新建 Work。

`book_contained_in`（**設計保留，庫中未使用**）原擬作 **Work → book_collection 的临时挂载点**，记录"某丛编中收有此作品的某具体本"而尚未拆分成独立 Book 条目。它与 `indexed_by` 的关键区别：
- `indexed_by`：作品被**目录书/志书/考证书**（也是 Work，描述性著作）著录，记录的是文献学引证。
- `book_contained_in`：作品被**藏品丛编/影印丛编**（Collection.subtype=book_collection）收录，记录的是某个具体藏本/版本，**应当**最终拆分为独立 Book + Book.contained_in 指向该 Collection。

實際錄入未走這條臨時通道：叢編收錄一律直接記在 `Work.contained_in`（作品層，指向 Collection ID），或升格為獨立 Book 後記 `Book.contained_in`。新資料請沿用 `contained_in`，勿再啟用 `book_contained_in`。

`measures` 用於補充 `juan_count`，適合通俗小說等需要多維計量（卷+回+集+篇）的作品。
- `juan_count` 側重傳統「卷」維度，前端已使用。
- `measures` 數組按原書順序排列，每項一個單位。
- `measure_info` 是人類可讀的拼接展示（供 UI 直接渲染），例如「四卷二十回」、「八集四十回（每集五回）」。

`additional_titles` 用於記錄同書的其他常用書名（別名/異稱）：
- 適用於有多個傳統名稱的經典：如《左傳》=《春秋左氏傳》=《左氏傳》=《春秋左傳》
- 適用於原書與通行名差異：如《春秋古經》=《古文春秋經》
- 與 `Entity.alt_names`（人物別名）平行設計，但 Work 級別僅存名稱字符串（無 type 區分）
- UI 應在搜索時匹配 `title` + `additional_titles` 全集

#### resources 的 group 字段（资源组）

`resources[]` 默认是扁平列表，每条独立。当多个 resource 描述**同一份内容**的不同存储/下载位置时（如：一份 PDF 同时挂在天一生水 / IA / 百度网盘），用 `group` 把它们关联起来。

**核心约定**：
- **同一 `group` 值**：表示是**同一份内容**的不同存储位置（镜像）。点开任意一个，下载下来内容字节完全等价（或仅水印/格式细微差别）。
- **不同 `group` 值**：表示是**不同变体**（如 人文社 1975 黑白本 vs 中華再造善本彩色本，或 完整本 vs 缺页本）。
- **无 `group`**：独立 resource，与现行行为完全一致（如识典/CText 这些独立整理本文本）。

**group_role**：
- `origin`：原始来源（如天一生水原本就有）
- `mirror`：我们做的备份镜像（如我们上传到 IA / 百度网盘）

**group_label / group_description**（推荐方式）：写在 Book/Work 顶层的 `resource_groups` 字典里，避免每条 resource 重复：

```json
{
  "resource_groups": {
    "<group_key>": {
      "label": "string (人类可读小标题，如「人民文学出版社 1975 年影印本」)",
      "description": "string (optional, 一段说明文字。可解释这一组为何独立成组，或它与其他组的区别)"
    }
  }
}
```

**向后兼容**：现有 resource 上的 `group_label` 字段仍读，但优先级低于 `Book.resource_groups[<gk>].label`。新数据写入 `resource_groups`；老数据按需迁移。

**示例**（庚辰本含两组同源资源 + 一条独立文本）：

```json
{
  "resource_groups": {
    "renmin-1975-bw": {
      "label": "人民文学出版社 1975 年影印本",
      "description": "人文社 1975 年首次影印庚辰本，黑白底本，含徐星署购书时附补 64/67 两回（据己卯本）。"
    },
    "zhsy100476-color": {
      "label": "中華再造善本 ZHSY100476 彩色高清",
      "description": "中华再造善本明清编据北大藏底本彩色精印，附胡适民国廿二年题记。"
    }
  },
  "resources": [
    { "id": "shidianguji", "name": "识典古籍", "url": "...", "types": ["text"] },

    { "id": "jiangyu-renmin1975", "group": "renmin-1975-bw", "group_role": "origin",
      "name": "天一生水", "url": "https://dropbox.jiangyu.org/...", "types": ["image"] },
    { "id": "ia-renmin1975", "group": "renmin-1975-bw", "group_role": "mirror",
      "name": "Internet Archive", "url": "https://archive.org/...", "types": ["image"] },
    { "id": "baidu-renmin1975", "group": "renmin-1975-bw", "group_role": "mirror",
      "name": "百度网盘", "url": "https://pan.baidu.com/s/...", "types": ["image"],
      "metadata": { "access_code": "abcd" } },

    { "id": "wikimedia-zhsy100476", "group": "zhsy100476-color", "group_role": "origin",
      "name": "Wikimedia Commons", "url": "...", "types": ["image"] }
  ]
}
```

**多群组同书示例**（己卯本：陶洙补抄本 vs 复原本）：

```json
{
  "resource_groups": {
    "taozhu-original": {
      "label": "陶洙補抄本（國圖藏，灰度膠片）",
      "description": "原稿入民國藏書家陶洙手後，添大量批註、補抄第 21-30 回闕葉等，現存國家圖書館。本組為國圖灰度膠片本，保留陶洙加工痕跡。"
    },
    "shanghai-1981-restored": {
      "label": "上海古籍出版社 1981 年復原影印本",
      "description": "上古社 1981 年影印時，盡可能剔除陶洙添加的批註與補抄痕跡，恢復清乾隆己卯（1759）抄本原貌。本組為現代學界引用最廣的版本。"
    }
  },
  "resources": [
    { "id": "shuge-jimao", "group": "taozhu-original", "group_role": "origin", ... },
    { "id": "nlc-17522", "group": "taozhu-original", "group_role": "origin", ... },
    { "id": "ia-taozhu-original", "group": "taozhu-original", "group_role": "mirror", ... },
    { "id": "baidu-taozhu-original", "group": "taozhu-original", "group_role": "mirror", ... },

    { "id": "jiangyu", "group": "shanghai-1981-restored", "group_role": "origin", ... },
    { "id": "ia-shanghai-1981-restored", "group": "shanghai-1981-restored", "group_role": "mirror", ... },
    { "id": "baidu-shanghai-1981-restored", "group": "shanghai-1981-restored", "group_role": "mirror", ... }
  ]
}
```

**UI 渲染逻辑**（前端实现指引）：
1. 把 `resources` 按 `group` 分桶；无 group 的每条单独成桶
2. 每桶头部：查 `Book.resource_groups[gk]`，渲染 `label`（小标题）+ `description`（小字说明）
3. 桶内列出 resource：站点名 + URL + 提取码（若有），origin 加角标
4. fallback：若 `Book.resource_groups` 未设，从组内某条 resource 读 `group_label`（兼容历史数据）

**向后兼容**：所有不带 `group` 的现有 resource 保持原扁平展示。

### 2. Collection Schema
Represents a collection or series that contains multiple books or other collections.

```json
{
  "id": "string (e.g., FCPFFgib9Pd)",
  "type": "collection",
  "subtype": "string (work_collection | book_collection)",
  "title": "string",
  "description":  "Description (object)",
  "contained_in": ["string (Parent Collection IDs)"],
  "authors": [
    {
      "name": "string",
      "role": "string",
      "dynasty": "string",
      "source": "Source"
    }
  ],
  "publication_info": {
    "year": "string",
    "details": "string",
    "source": "Source"
  },
  "current_location": "Location (object)",
  "books": ["string (List of Book IDs)"],
  "contained_works": [
    {
      "id": "string (Work ID)",
      "title": "string (for display)",
      "volume_index": "integer | array (optional, 在本叢編中的冊次；跨多冊時用陣列)"
    }
  ],
  "contains": [
    {
      "type": "string (preface | subwork | selected_from | ...)",
      "title": "string",
      "work_id": "string (optional)",
      "book_id": "string (optional)",
      "collection_id": "string (optional)",
      "scope": "string (該組成部分的範圍說明)",
      "position": "string (前置 | 後附 | ...)",
      "note": "string (optional)"
    }
  ],
  "work_id": "string (optional, 本叢編整體對應的傘狀作品，如《武英殿十三經注疏》→《十三經注疏》)",
  "editors": [],
  "publisher": "string",
  "publish_year": "string",
  "total_volumes": "integer",
  "total_works": "integer",
  "sections": [{ "name": "string (叢編分部，如「唐宋編」「經部」)" }],
  "additional_titles": ["string"],
  "edition": "string (版本名)",
  "juan_count": { "number": "integer", "description": "string" },
  "page_count": { "number": "integer", "description": "string" },
  "indexed_by": [] // type: IndexEntry
  "related_books": ["string (Book IDs)"],
  "related_collections": ["string (Collection IDs)"],
  "resources": [] // 與 Book.resources 同結構
  "promoted_to": "string", "promoted_at": "string",
  "ai_note": "string",
  "sources": [] // type: Source
}
```

**Collection 的三種成員列表，語義不同，不可互換**：
- `books`：成員是具體版本（Book ID 陣列）。
- `contained_works`：成員是作品（影印／彙編叢書按作品收錄時用，帶冊次）。
- `contains`：本叢編的**結構組成部分**（聖諭、進表、總目、選印來源等），不是平列成員。

**已刪之欄位**：`history`、`volume_count`（Collection 層）。叢編的實體規模記 `total_volumes`；沿革敘述併入 `description.text`。

### 3. Book Schema
Represents a physical or specific digital edition/copy of a work.

```json
{
  "id": "string (e.g., CX8nkEm1UAB)",
  "type": "book",
  "title": "string (Specific edition name)",
  "work_id": "string (ID of the parent Work)",
  "edition": "string (版本名，如「清乾隆間寫文淵閣四庫全書本」「武英殿聚珍版」)",
  "contained_in": [
    {
      "id": "string (Collection ID)",
      "volume_index": "integer | array (optional, 在該叢編中的冊次)",
      "details": "string (optional)"
    }
  ],
  "authors": [
    {
      "name": "string",
      "role": "string",
      "dynasty": "string",
      "source": "Source"
    }
  ],
  "publication_info": {
    "year": "string",
    "details": "string",
    "source": "Source"
  },
  "current_location": "Location (object)",
  "volume_count": {
    "number": "integer",
    "description": "string",
    "source": "Source"
  },
  "page_count": {
    "number": "integer",
    "description": "string",
    "source": "Source"
  },
  "description":  "Description (object)",
  "indexed_by": [
    {
      "source": "string (目錄/志書名稱，如「中國通俗小說書目」)",
      "source_bid": "string (目錄 Work ID)",
      "title_info": "string (該目錄中此版本的著錄標題)",
      "summary": "string (該目錄中對此版本的全文著錄)"
    }
  ],
  "resources": [
      {
        "id": "string (short identifier, extracted from url domain or custom)",
        "name": "string (source name)",
        "url": "string (resource link, optional for physical)",
        "type": "string (text | image | text+image | physical)",
        "root_type": "string (catalog | search, default: catalog)",
        "structure": ["string (level names, e.g. ['册', '卷'])"],
        "coverage": { "level": "integer", "ranges": "string (e.g. '2,3,5-8')" },
        "details": "string (supplementary notes)",
        "group": "string (optional, 资源组 ID。同一 group 内的 resources 是同一份内容的不同存储位置/镜像)",
        "group_label": "string (optional, 该组的人类可读描述，如「人民文学出版社1975 黑白影印」。在组内任一 resource 上写一次即可，推荐写在 group_role=origin 上)",
        "group_role": "string (optional, origin | mirror。origin=原始来源；mirror=我们做的备份镜像)",
        "metadata": {
            "access_code": "string (optional, 网盘提取码)",
            "edition": "string (optional, 版本说明)",
            "color": "string (optional, color | bw)",
            "completeness": "string (optional, complete | partial)"
        }
      }
  ],
  "location_history": [] // type: Location
  "related_books": ["string (IDs of related editions)"],
  "section": "string (該版本在所屬叢編中的分類，如「經部/易類」)",
  "additional_titles": ["string"],
  "attached_texts": [{ "title": "string", "...": "隨本附刻之序跋、附錄等" }],
  "lineage": { "...": "版本源流資料（承自何本、據何本翻刻）" },
  "sections": [{ "...": "本書內部分卷／分部結構" }],
  "measures": [], "measure_info": "string",  // 與 Work 同結構，記該版本自身的計量
  "juan_count": { "number": "integer", "description": "string" },
  "zhsy_id": "string (中華再造善本編號)",
  "metadata": { "...": "來源系統原始欄位的透傳，不作規範化" },
  "promoted_to": "string", "promoted_at": "string",
  "ai_note": "string",
  "sources": [] // type: Source
}
```

**`edition` 與 `sources[].version` 是兩回事**，勿混：
- `Book.edition`（頂層，22,842 條）＝**版本名**，文獻學意義上的「這是哪一個本子」。
- `sources[].version` / `sources[].processor_version`＝**處理程序版本號**（如 `"1.0"`），與書無關。

Book 頂層一律用 `edition`；曾有 276 條誤寫作 `version`，已於整理中歸併。

### Source object type:
```json
{
    "id": "string (e.g., CX8nkEm1UAB)",
    "name": "string",
    "type": "bookID, url, etc",
    "details": "string",
    "position": "string",
    "version": "string (e.g. v0.1)",
    "processor_version": "string (e.g. v0.1)"
}
```
### Location Object type
```json
{
    "name": "string",
    "start_date": "string (YYYY-MM-DD)",
    "end_date": "string (YYYY-MM-DD)",
    "description": "string",
    "source": "Source"
}
```

### Description object type
```json
{
    "text": "string (Overview of the work)",
    "sources": ["Source"]
  }
```

---

## Subtype 字段说明

`subtype` 在 `type` 基础上进一步细分实体类别，便于前端展示、筛选与统计。

### Work.subtype

| subtype | 含义 | 示例 |
|---|---|---|
| `book` (默认) | 独立成书的作品 | 《漢書》《論語》《紅樓夢》 |
| `article` | 单篇文章 | 《陳情表》《岳陽樓記》 |
| `poem` | 诗词 | 《春望》《水調歌頭·明月幾時有》 |
| `chapter` | 书中被单独拎出研究/索引的章节 | 《漢書·藝文志》《史記·太史公自序》 |

**判定规则**：
- 默认一律标 `book`，志书录入绝大多数都是书。
- 明确是书中一章且被单独索引（有 `related_works.relation == "part_of"`）→ `chapter`。
- 单位是"篇"且 number=1 或属于集部别集的单篇文章 → `article`。
- 单位是"首"或为诗词 → `poem`。

`chapter` 按需创建：不要把《漢書》的每一篇志都拆成 Work，只有被单独研究或作为目录书索引的才升格（例：《漢書·藝文志》需要被引用为 `source`，所以单独建 Work；《漢書·地理志》未被索引就不建）。

### Collection.subtype

| subtype | 含义 | 示例 |
|---|---|---|
| `work_collection` | 作品的丛编（抽象层，跨版本） | 《二十四史》《四書》《四大名著》《十三經》《十三經注疏》 |
| `book_collection` | 书籍的丛编（具体版本） | 《二十四史百衲本》《欽定四庫全書文渊阁本》《武英殿聚珍版叢書》 |

**判定规则**：
- 有具体 `publication_info.year`（年份而非朝代）、具体 `current_location`、image 类型资源（扫描件）→ `book_collection`。
- 只有作品列表、无具体版本信息 → `work_collection`。
- 一个作品丛编（如《二十四史》）下面可以挂多个书籍丛编（百衲本、武英殿本），后者 `contained_in` 指向前者。

---

### 4. Entity Schema

抽象概念（作者、地名、朝代等），与具体书目（Book/Work/Collection）平级存在。

```json
{
  "id": "string (e.g., 1j965dvig7c3k)",
  "type": "entity",
  "subtype": "string (people | place | dynasty | ...)",

  "primary_name": "string (最通行的名字，用于显示)",
  "alt_names": [
    { "name": "string", "type": "string (字|號|諡號|賜號|別名|常用名|簡體)" }
  ],

  "dynasty": "string (朝代标签，与 Work.authors.dynasty 对齐)",
  "birth_year": "integer | null (公历年)",
  "death_year": "integer | null",

  "works": [
    { "work_id": "string (Work ID)", "role": "string (撰|注|編|評...)" }
  ],

  "external_ids": {
    "cbdb_id": "integer | null",
    "cbdb_match": "string (auto | manual | none, optional)",
    "cbdb_source": "string (匹配凭据, optional)"
  },

  "description": "Description (object)",
  "ai_note": "string (optional, 建檔自注)",
  "sources": []
}
```

`sources` 已定義但庫中無資料；Entity 的出處一律記在 `description.sources`。

#### Entity.subtype

| subtype | 含义 | 示例 |
|---|---|---|
| `people` | 人物（作者、注家、编者等） | 蘇軾、王應麟、焦竑 |
| `place` | 地名（保留） | — |
| `dynasty` | 朝代（保留） | — |

#### alt_names.type 枚举

| type | 含义 | 对应 CBDB ALTNAME_CODES |
|---|---|---|
| `字` | 表字 | 4 |
| `號` | 号/室名别号 | 5 |
| `諡號` | 谥号 | 6 |
| `賜號` | 赐号 | 11 |
| `別名` | 其他别名 | 3 |
| `常用名` | 常用称谓（如「陽明先生」） | — |
| `簡體` | 简体写法 | — |

#### Work.authors.entity_id

每个 `Work.authors[i]` 通过 `entity_id` 引用对应的 people Entity：

```json
"authors": [
  {
    "name": "蘇軾",
    "role": "撰",
    "dynasty": "宋",
    "entity_id": "12xabc..."
  }
]
```

- `name` / `dynasty` / `role` 保留不变 —— 便于显示、搜索、兜底（entity_id 为空时仍可用）。
- CBDB 相关信息（`cbdb_id` / `cbdb_match` / `cbdb_source`）**不**存在 Work 里，而是归到 Entity 的 `external_ids`。Work 只需通过 `entity_id` 间接引用。

---

## ID 类型编码

ID 用 64-bit snowflake 结构，3 bits 标识 type：

| type 值 | 名称 | 含义 |
|:---:|---|---|
| 0 | Book | 具体书籍/版本 |
| 1 | Reserved1 | (保留) |
| 2 | Collection | 丛书 |
| 3 | Work | 作品 |
| 4 | Entity | 抽象实体（人物/地名/朝代...） |
| 5-7 | Reserved | (保留) |

**0-3 用于实体书目，4-7 用于抽象概念。** 见 `book_index_manager/id_generator.py`。

草稿庫的 ID 為 13 字元（status=1），升格後的 Production ID 為 12 字元（status=0）。
一條記錄升格後，草稿檔保留並記 `promoted_to` / `promoted_at`，
**權威對照表是根目錄的 `promotions.json`**，欄位只是冗餘副本。
校驗關聯是否懸空時，Production ID 不在草稿索引中屬正常，須併入白名單。

---

## 記錄之共通欄位（issue #10）

以下五欄凡 Work／Book／Collection／Entity 皆有，2026-08 立。

| 欄位 | 義 |
|---|---|
| `schema_version` | 主記錄自 `1` 起。**輯佚檔（`fragments`）別為一族，已在 `2`，二者不同源，勿混。**<br>無此欄則將來任一次結構調整都成考古。 |
| `updated_at` | 這條最後一次被人碰的時間（ISO 8601）。<br>現值自 git 該檔最後一次提交回填——**不一律填「現在」**，假時間比沒有更壞。<br>檔在 git 裡，diff 自有時間戳，然「這條何時被碰」須能直接查，不必翻歷史。 |
| `_` 起首者 | **派生欄位**：`_has_text`、`_has_image`、`_has_collated`、`_promoted_to`、`_promoted_at`。<br>校驗一律「重新生成後比對，不一致以生成值為準」，故**手寫無用**。 |
| `zhsy_retrieved_at` / `authors[].cbdb_retrieved_at` | 外部對齊之取得時間。現存皆 `null`——一千三百餘條 `zhsy_id` 是 v0.2／v0.3（2026-04-29、2026-05-14）批次匯入時帶入，其取得之時無記錄，填一個推導的時間即是假造。**新增對齊必填。**<br>`cbdb_id` 為 `null` 而 `cbdb_match: none` 者是**查而否決**，非未查，故亦有此欄——對方日後改指向，否決同樣會過期。 |

### 派生欄位為何要加底線

`has_text` 之現狀曾是「有的對、有的錯、大半沒有」：已有者五千九百八十七條中二條與重算不符，
而一萬零十八個 Work、七千七百四十九個 Book 有 `resources` 卻無此欄。
病根在於**它與手寫欄長得一模一樣**，遂無人知其該不該在、值對不對。
加底線之後，`chk.py` 對所有 `_` 起首之欄一律重算比對，基線 0。

**`index/` 之欄不加底線**——整個檔都是派生產物，檔級已說明此事，欄再加底線是重複。
但其值同須與記錄相符（`chk.py` 已驗）。

`related_works[].title` 未改名亦未刪：刪之則 git diff 與人工閱讀時看不出關聯的是什麼書，
排查要多查一步。改為每次重生成則與「保留可讀性」相衝。
今**保留原名而在校驗中報漂移**，基線 0。
（曾漂移九處，皆同一成因：work 之題名清掉了誤切進去的案語，而此處還留著舊題。）

### 已刪之欄位

`book_contained_in`、`parent_works`（Work）、`history`、`volume_count`（Collection）、
`resource_groups`（Work）——**庫中皆零**，今自本文件刪去。
留在 spec 裡的死欄位，三年內一定會被某個人重新啟用；需要時自 git 歷史取回。

**按**：`resource_groups` 與 `volume_count` 在 **Book** 各有一條在用
（`11q411jij5qm8`、`11q6q7v82w7pc`），不在此列，仍為有效欄位。

## 關聯詞表（`related_works[].relation`）

| relation | 反向 | 含義 |
|---|---|---|
| `text_carried_by` | `contains_text_of` | 本文承載於某實物／某書 |
| `studies` | `studied_by` | 本書研究、注解、考證某書 |
| `has_part` | `part_of` | 整體 ↔ 部分（篇卷、附錄、子編） |
| `followed_by` | `preceded_by` | 續作／前作 |
| `related` | `related`（自反） | 泛關聯，語義不明確時的兜底 |
| `collected_in` | —（單向） | 收入某彙編 |
| `derived_from` | —（單向） | 由某書輯出、改編而成 |
| `adapted_from` | — | 改編自 |

**成對關聯必須雙向寫入**：在 A 寫 `has_part → B` 的同時，須在 B 寫 `part_of → A`。
`collected_in` / `derived_from` **沒有反向詞**，只在來源側單寫一條；
若需要在對面留痕，用 `related`，不要臆造反向詞。

`related_works[].title` 應與目標 Work 的 `title` 保持一致；改題或合併作品後須同步更新所有指向它的 `title`。

---

## 索引檔（`index/`）

檔案本身是唯一真實來源，`index/` 是為檢索而生成的扁平副本。

| 路徑 | 內容 | 分片 |
|---|---|---|
| `index/works/{0-f}.json` | 全部 Work | 按 ID 分 16 片 |
| `index/books/{0-f}.json` | 全部 Book | 同上 |
| `index/entities/{0-f}.json` | 全部 Entity | 同上 |
| `index/collections.json` | 全部 Collection | 不分片 |

分片函數（對 ID 逐字元）：`h = 0; for c in id: h = ((h * 31) + ord(c)) & 0xFFFFFFFF` → 片號 `'%x' % (h % 16)`。

索引條目是**扁平的顯示用摘要**，非完整記錄：

```json
{
  "id": "string",
  "type": "string (Work | Book | Collection | Entity ——首字母大寫)",
  "title": "string",
  "path": "string (檔案相對路徑)",
  "author": "string", "role": "string", "dynasty": "string",
  "juan_count": "…", "measure_info": "string", "edition": "string",
  "additional_titles": [], "subtype": "string", "year": "string",
  "holder": "string", "has_text": "boolean", "has_image": "boolean",
  "has_collated": "boolean", "promoted_to": "string"   // index/ 之欄不加底線，全檔皆派生
}
```

注意 **`type` 在索引中首字母大寫（`"Work"`），在檔案中全小寫（`"work"`）** ——
這是既定約定，兩邊都不要「改齊」。

`authors` 是陣列，索引只取第一位攤平為 `author` / `role` / `dynasty`。
改動檔案的標題、作者、路徑後，**必須同步更新索引**，否則校驗會報「索引欄位不符」。

---

## ai_note 的用法

`ai_note` 出現在四類記錄的頂層，是**整理者寫給整理者的注**，不面向讀者：

- 記資料來源與可信度，例：「據網路檢索資料建檔，未核原書」。
- 記存疑與待辦，例：「卷數與通行所記三十一卷不合，待核」。
- 記整理決策，例：「原有非 schema 之頂層欄位 part_of，今改記為 related_works 之 part_of 關係」。

面向讀者的正文一律進 `description.text`，其出處進 `description.sources`。
前端不應渲染 `ai_note`。