# Collection 升格方案（2026-08-26 擬）

> 前置已竣：`chk_collection.py` 已立（甲乙丙三級），甲級十八條已清盡（見 70d91114dc）。
> 本檔定升格之步驟、閘、與尚待裁決之事。所有數字皆 2026-08-26 實測，非估算。

---

## 零、盤點

| | 數 |
|---|---|
| draft 活條 | **53** |
| draft 墓碑（2026-05 已升） | 10 |
| production | 10 |
| 索引 `index/collections.json` | 63（**不分片，單檔**） |

已升的 10 條全是四庫系（文淵閣、文津閣……四庫全書珍本初集）。

---

## 一、Collection 與 Work／Entity 之三處根本不同

### 一之一　引用面極廣，而**大半在 Book 上**

須改繫者 **39,141 處、涉 39,080 檔**：

| 倉 | 類 | 欄 | 處數 |
|---|---|---|---|
| draft | Book | `contained_in[].id` | 19,393 |
| prod | Book | `contained_in[].id` | 19,386 |
| prod | Work | `contained_in[].id` | 136 |
| prod | Work | `related_works[].id`（`collected_in`） | 82 |
| draft | Work | `contained_in[].id` | 81 |
| draft | Collection | `contained_in[]` | 19 |
| draft／prod | 整理本 `sections[].collection_id` | | 19＋19 |
| draft | Work | `related_works[].id` | 6 |

對照：entity 全量升格只改 `authors[].entity_id` **一種欄**、54,279 處。
Collection 是 **七種欄形**，逐一都要寫進改繫器，漏一種就是一批靜默積欠。

`prod Work.collections[]` 現有 7 處，所指已是 production id，不在改繫之列，
但改繫器仍須認得此欄——**他日若有指 draft 者，此欄是唯一的漏網處**。

### 一之二　`contained_in` 是**單向**的，不得以雙向論

兩倉 Book 以 `contained_in` 反指 Collection 者 38,779 處，
而 Collection 之 `books` 止 469＋25 條——大叢編**不逐一列其書**。
《國立故宮博物院善本舊籍》入引 35,114 而三種成員列表俱空，即其例。

這與人物↔作品之雙向**正相反**。`chk_collection.py` 特為此立戒；
改繫與校驗都不可「補全」這一側。

### 一之三　成員列表有三，語義不可互換

`books`（具體版本）／`contained_works`（作品，帶冊次）／`contains`（結構組成部分）。
2026-08-26 已清出十五處以 Collection id 混入 `books` 者——叢編相含當由
子條之 `contained_in` 指母條，母條不再列之。

---

## 二、巢狀：淺 DAG，無環，但**必須先鑄全部號再寫檔**

```
出土簡帛 ⊃ 長台關楚簡・上博楚竹書・郭店・清華・安大・荊州王家嘴・馬王堆・
          銀雀山・阜陽雙古堆・定州八角廊・北大西漢竹書・海昏侯・張家山   （13）
武英殿刻書 ⊃ 二十四史(殿本)・武英殿聚珍版叢書・武英殿十三經注疏          （3）
二十四史(work_collection) ⊃ 二十四史(殿本)・二十四史(百衲本)              （2）
十三經注疏 ⊃ 武英殿十三經注疏                                            （1）
```

深二層，無環（`chk_collection.py` 有環驗）。
`contained_in` 所指是**同批之兄弟**，故升格器不可像 `promote_entity.py` 那樣
邊鑄邊寫——**須先把 53 個 production id 全部鑄出、造成 D→P 全表，再寫檔**。
`promote_entity.py` 邊鑄邊寫無妨，是因 entity 之間本不相引。

## 三、索引：單檔、且**帶展示欄**

`index/collections.json` 不分片。production 之條帶
`author`／`year`／`holder`／`role`／`subtype`／`additional_titles`／`edition`／
`juan_count`／`has_text`／`has_image`——升格器須從記錄檔重新算出，
**且記錄檔用 `_has_text`／`_has_image`（帶底線），索引用不帶底線的**，勿混。

墓碑之索引條只留 `{id, title, type, path, promoted_to}`（比照 work／entity 之例）。

---

## 四、步驟

1. **前置**（已竣）
   - `chk_collection.py` 立驗；甲級清盡。
2. **決三事**（見〈五〉，**須使用者裁**）
3. **寫 `scripts/promote_collection.py`**，契約如下：
   - 閘一：`chk_collection.py` 甲級為零。
   - 閘二（逐條）：已升格者不升；id 之 status／type 位須為 draft／Collection(2)；
     無 `title`／無 `subtype` 者不升；`contained_works`／`books`／`contains`／
     `contained_in`／`related_collections`／`work_id` 有懸空者不升。
     **孤懸（三種成員列表俱空）不阻塞**——與 entity 之例不同，理由見〈五之一〉。
   - **先鑄全部號，再寫檔**（〈二〉）。
   - production 副本之出向改繫：`contained_works[].id`、`books[]` 過
     `promotions.json`（work／book 之 D→P）；`contained_in[]`、
     `related_collections[].collection_id`、`contains[].collection_id`
     過本批之 D→P 全表。
   - 兩倉之入向改繫：〈一之一〉七種欄形，一趟掃完，**不得分次**。
   - draft 留五欄墓碑（帶 `schema_version`，比照 work／entity 現制），
     索引條改為 5 欄＋`promoted_to`。
   - 預設只驗不寫，`--apply` 方動。
4. **試升三條**（取無巢狀、入引少者，如《怡園五種》《四大奇書》《漢代緯書》），
   跑 `chk.py`＋`chk_collection.py` 覈之。
5. **全量升 53 條**，再覈。
6. **升竣覆掃**：比照 entity 之例，遍掃兩倉一切 id 引用，看有無新的靜默積欠；
   於 `chk.py` production 節增驗：
   - `Collection.contained_works[].id`／`books[]` 指 draft 者（基線 0）
   - `Book／Work.contained_in[].id` 不指 production Collection 者（基線 0）
7. **SKILL／SCHEMA 補記**。

---

## 五、三件待裁之事

### 五之一　孤懸（三種成員列表俱空）十一條，升不升？

**建議：升。** 與 entity 之孤懸不同——此輩多是**入引極多而不列其書**者：

| Collection | 入引 | 成員列表 |
|---|---|---|
| 國立故宮博物院善本舊籍 | 35,114 | 俱空 |
| 中華再造善本 | 2,654 | 俱空（有 `sections` 三部） |

不升，則兩倉三萬七千餘 Book 永指一個 draft id。
另有六條入引為零（四庫未收書輯刊、四庫禁燬書叢刊、同補編、四庫全書存目叢書補編、
故宮珍本叢刊、四庫全書珍本臺灣商務再續本），是**已建而未及錄其書**者，
非殘條——其 `description`、`publication_info`、`authors` 俱全。一併升為宜。

### 五之二　《武英殿刻書》`books[]` 中二十五部尚在 draft 之 Book

若 Collection 先升而該二十五部 Book 後升，則 production Collection 之
`books[]` 留二十五個 draft id——**而 Book 之升格器未必掃 Collection.books**
（entity 全量升格時已見同型之坑：併條工具只掃 draft，production 靜默積欠）。

三途：
- **甲（建議）**：照升，並於 `chk.py` production 節立
  「`Collection.books[]` 指 draft」一驗（基線 0），升竣即見，見即補。
- 乙：等那二十五部 Book 升格之後再升《武英殿刻書》一條。
- 丙：現在就把那二十五部 Book 升了——**越界**，Book 是別的會話的車道。

### 五之三　與 Book 升格會話的**撞車**

本批要改兩倉各約一萬九千個 Book 檔（只動 `contained_in[].id` 一行）。
另一會話正在成批升格 Book（近日提交：四庫薈要 470 條、武英殿聚珍版……）。
同時動同一批 Book 檔，**merge 衝突面極大**。

三途：
- **甲（建議）**：先問過那邊，取一個窗口，一趟做完（39,141 處一次掃完，
  實測 entity 之同類操作 33 秒）。做完立刻 push，窗口極短。
- 乙：分兩段——先升入引少的 47 條（改繫不足 400 處），
  《國立故宮博物院善本舊籍》《中華再造善本》等六條大戶留待 Book 批次告一段落。
- 丙：不管，撞了再解。**不取**——一萬九千檔的衝突不是人能解的。

---

## 六、不在本方案之內（登記待議）

- 《四庫全書存目叢書》庫中現以 production **Work** `d59f2og4vke9` 記之，
  而 SCHEMA〈叢書之著錄〉明言「一部叢書不得因見於書目而別立一 Work」。
  改立為 Collection 牽動其下二百餘種之繫連，非本輪所及。
- 三條《二十四史》同題（work_collection 一、book_collection 二：殿本、百衲本），
  乃 SCHEMA 所明許之層級（「一个作品丛编下面可以挂多个书籍丛编」），**非重出**。
  惟三者 `title` 全同，於索引與檢索不便，或當於 `title` 加版本以別之——體例之事，待議。
