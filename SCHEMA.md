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
  "parent_works": "Array of Book IDs", 
  "books": ["string (List of Book IDs)"],
  "related_works": [
    {
      "id": "string (Work ID)",
      "title": "string (Work title, for display)",
      "relation": "string (optional: part_of | has_part)"
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
  "book_contained_in": [
    {
      "collection_id": "string (book_collection ID)",
      "title_info": "string (该丛编中此本的标题，如《史記》一百三十卷)",
      "author_info": "string (该丛编中记录的作者署名)",
      "edition": "string (版本，如「清乾隆間寫文淵閣四庫全書本」)",
      "volume": "string (馆藏号/册次，如「故庫000153-000155」)",
      "section": "string (分类，如「經部/易類」)",
      "summary": "string (该丛编中的摘要原文)",
      "source_bid": "string (源系统记录ID，可空)"
    }
  ],
  "sources": [] // type: Source
}
```

Book 的 `indexed_by` 與 Work 的 `indexed_by` 同結構，記錄該具體版本被目錄書/志書/考證書著錄的條目。場景：通俗小說書目這類目錄書中按版本著錄的條目（如「乾隆甲戌本脂硯齋重評石頭記」「王希廉評紅樓夢一百二十回」）應掛在對應的 Book 上，而非新建 Work。

`book_contained_in` 是 **Work → book_collection 的临时挂载点**，记录"某丛编中收有此作品的某具体本"，但尚未拆分成独立 Book 条目。它与 `indexed_by` 的关键区别：
- `indexed_by`：作品被**目录书/志书/考证书**（也是 Work，描述性著作）著录，记录的是文献学引证。
- `book_contained_in`：作品被**藏品丛编/影印丛编**（Collection.subtype=book_collection）收录，记录的是某个具体藏本/版本，**应当**最终拆分为独立 Book + Book.contained_in 指向该 Collection。
- 录入流程：先临时挂在 Work.book_contained_in，后续按 collate-cong-bian 流程逐条升格为 Book。

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
  "volume_count": {
    "number": "integer",
    "description": "string",
    "source": "Source"
  },
  "history": ["string (Timeline of historical events/provenance)"],
  "books": ["string (List of Book IDs)"],
  "sources": [] // type: Source
}
```

### 3. Book Schema
Represents a physical or specific digital edition/copy of a work.

```json
{
  "id": "string (e.g., CX8nkEm1UAB)",
  "type": "book",
  "title": "string (Specific edition name)",
  "work_id": "string (ID of the parent Work)",
  "contained_in": ["string (Collection IDs)"],
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
  "sources": [] // type: Source
}
```

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
  "sources": []
}
```

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