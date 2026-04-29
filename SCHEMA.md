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
  "sources": [] // type: Source
}
```

`measures` 用於補充 `juan_count`，適合通俗小說等需要多維計量（卷+回+集+篇）的作品。
- `juan_count` 側重傳統「卷」維度，前端已使用。
- `measures` 數組按原書順序排列，每項一個單位。
- `measure_info` 是人類可讀的拼接展示（供 UI 直接渲染），例如「四卷二十回」、「八集四十回（每集五回）」。

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
  "resources": [
      {
        "id": "string (short identifier, extracted from url domain or custom)",
        "name": "string (source name)",
        "url": "string (resource link, optional for physical)",
        "type": "string (text | image | text+image | physical)",
        "root_type": "string (catalog | search, default: catalog)",
        "structure": ["string (level names, e.g. ['册', '卷'])"],
        "coverage": { "level": "integer", "ranges": "string (e.g. '2,3,5-8')" },
        "details": "string (supplementary notes)"
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