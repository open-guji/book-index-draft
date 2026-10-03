#!/usr/bin/env python3
"""重整《尚書》今古文架構。

背景：本庫原以 1evl7fct2ezgg（title「尚書」）作為跨今古文的抽象總綱，掛了 510 條
related_works（含後世注疏、辨偽考證、篇章 has_part）。使用者決定拆分為三部：

  1. 1evl7fct2ezgg「尚書」（別名「今文尚書」）——伏生所傳今文廿八篇，今存，
     總名稱「尚書」歸還給它，避免預設讀者看到的是偽書。
  2. 新建「古文尚書」（真，孔壁本，四十六卷五十七篇，魏晉之際亡佚，今僅存
     馬融、鄭玄等漢魏舊注佚文與清人輯本）。
  3. 1evd3dbcb0nb4「偽古文尚書」（東晉梅賾本，58篇，附偽孔傳，即通行《十三經
     注疏》本）——維持既有身份，吸收原掛在抽象總綱下、實為此本注疏的後世著作。

分類規則（title 字面判準，逐條可核）：
  BUCKET_A（留在「尚書」＝今文尚書）：題含「今文」字樣者；今文三家家法
    （歐陽／夏侯）章句；《尚書大傳》及其注疏定本（伏生一系附庸文獻）；
    《洪範五行傳》系（劉向今文一系）；「今古文」比較性著作（孫星衍、
    豐川等，重心在辨正今文/真古文，非以偽本為底本）。
  BUCKET_B（移至新建「古文尚書」）：漢魏（早於東晉梅賾獻書）諸家直接注
    古文經者（馬融、鄭玄、王肅）及其輯佚／箋釋；孔安國隸古定之屬；
    《尚書緯》《尚書中候》讖緯系（依附古文經學傳統，非通行本注疏）。
    其中與偽古文尚書已有既存關聯者不動舊關聯，僅另加一條指向新 work
    （雙重歸屬——真古文與偽孔傳源流兩皆有學理根據，見案語）。
  其餘（含「古文尚書」但性質為考辨偽孔傳真偽的清人著作、以及全部未標
  今古文字樣的宋元明清一般注疏）→ BUCKET_C，移至偽古文尚書（通行本）。
  collected_in「十三經」「十三經注疏」兩條移除（今文尚書本身未被收入
  叢編，被收入的是通行的偽古文本）。
  has_part（今存 58 篇之篇目，含真今文篇、清華簡篇、偽古文篇混雜）本輪
  不動——分類需要另一輪專項工作，先在 ai_note 存證待辦。

每一步都寫檔並記錄審計報告到 .claude/known-issues/。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

SHANGSHU_JINWEN = "1evl7fct2ezgg"  # 尚書／今文尚書（保留原 id，收窄語義）
WEI_GUWEN = "1evd3dbcb0nb4"        # 偽古文尚書（既有）
ZHEN_GUWEN = "1ewujzde8gxd6"       # 古文尚書（真，孔壁本，新建）
MAGU_JIYI = "1ewsa49z35t25"        # 古文尚書（玉函山房輯佚書著錄，既有）
SKIP_IDS = {WEI_GUWEN}              # 已正確互指，不動
COLLECTED_IN_REMOVE = {"1ahwtau87mm80", "1ahwtau9gw0zk"}  # 十三經／十三經注疏

BUCKET_A = {
    "1ev85dirqz37k",  # 尚書伏生傳
    "1evr5e3m76rr7",  # 今文尚書考證
    "1ev85ditaukg0",  # 尚書歐陽說義（原重出兩次，僅留一）
    "1ev85dise2neo",  # 尚書歐陽章句
    "1ev85dispxo1s",  # 尚書大小夏侯解故
    "1ev85gx88gjy8",  # 尚書大夏侯章句
    "1ev85gx8toow0",  # 尚書小夏侯章句
    "1evr5e3m76rrj",  # 漢夏侯建尚書章句
    "1evc5pcc4rta8",  # 今文尚書音顧彪撰
    "1evr5e3m6vjea",  # 今文尚書經說考
    "1evr5e3m6vjeb",  # 尚書歐陽夏侯遺說考
    "1ev3b9xx9dvy8",  # 今文尚書說
    "1evgops4fqp6o",  # 今文尚書音
    "1evc5pcc9rlz4",  # 尚書大傳鄭玄注
    "1evincdi95m9s",  # 尚書大傳定本
    "1evjqyl6is4qo",  # 尚書大傳補注
    "1evjqyl2d9gjk",  # 尚書大傳疏證
    "1evr5e3m76rr9",  # 尚書大傳考異補遺
    "1ev3b9y23vjls",  # 別本尚書大傳
    "1evr5e3meogtn",  # 別本尚書大傳補遺
    "1evr5e3m76rra",  # 尚書大傳注
    "1evr5e3m76rrb",  # 尚書大傳注（另一家）
    "1ev3b9xgd0d8g",  # 尚書大傳（原重出兩次，僅留一，取 studied_by）
    "1evkanst2nev4",  # 尚書古今文同異考
    "1evr5e3m6vjds",  # 尚書今古文集解
    "1evr5e3m6vjda",  # 尚書今古文疏證
    "1evjqyhvx86ps",  # 尚書今古文考證
    "1ev3b9xzf3z7k",  # 豐川今古文尚書質疑
    "1evr5wajutz40",  # 尚書今古文注疏（孫星衍）
    "1evcbl0m6ji80",  # 許商五行傳記
    "1evcpct1ve4g0",  # 尚書洪范五行傳
    "1evc5pccj4q9s",  # 尚書洪范五行傳論劉向注（偽古文尚書亦已掛此條，雙重歸屬保留）
    "1evr5e3m76rrr",  # 尚書五行傳注
    "1ev85dis3gkxs",  # 尚書五行傳記
}

BUCKET_B = {
    "1evc5pcb5hzwg",  # 尚書王肅注（偽古文尚書已掛，雙重歸屬）
    "1evr5e3m76rrk",  # 魏王肅尚書注
    "1evr5e3meogto",  # 尚書馬融傳
    "1evc5pcapw4qo",  # 尚書鄭玄注（偽古文尚書已掛，雙重歸屬）
    "1evincdjkagao",  # 尚書馬鄭注
    "1evr5e3m6vjde",  # 古文尚書馬鄭注
    "1evjqyjqgc2rk",  # 古文尚書鄭氏注箋釋
    "1evc5pcakwc1s",  # 今字尚書孔安國撰
    "1evc5penip1c0",  # 尚書緯鄭玄注（偽古文尚書已掛，雙重歸屬）
    "1evc5peno02kg",  # 尚書中候鄭玄注（偽古文尚書已掛，雙重歸屬）
    "1evincdovmxa8",  # 尚書中候鄭注
    "1evkpiqr9z08w",  # 尚書中侯
    "1evfteinvo35s",  # 尚書中候注
    "1evjqykz0gmbk",  # 尚書中候疏證
}

REVERSE = {"text_carried_by": "contains_text_of", "studied_by": "studies"}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def build_index():
    idx = {}
    for shard_type in ("works", "books"):
        for s in SHARDS:
            d = load(ROOT / "index" / shard_type / f"{s}.json")
            for wid, entry in d.items():
                idx[wid] = ROOT / entry["path"]
    return idx


def upsert_related(data, target_id, target_title, relation, note=None):
    rw = data.setdefault("related_works", [])
    for e in rw:
        if e.get("id") == target_id:
            return False  # already present, leave untouched
    entry = {"id": target_id, "title": target_title, "relation": relation}
    if note:
        entry["note"] = note
    rw.append(entry)
    return True


def retarget_related(data, old_id, new_id, new_title):
    """把 data['related_works'] 中指向 old_id 的條目改指 new_id；若無則不動（由呼叫端另行 upsert）。"""
    changed = False
    for e in data.get("related_works", []):
        if e.get("id") == old_id:
            e["id"] = new_id
            e["title"] = new_title
            changed = True
    return changed


def main():
    idx = build_index()
    report = {"bucket_a_kept": [], "bucket_b_moved": [], "bucket_c_moved": [],
              "collected_in_removed": [], "dedup_removed": [], "errors": []}

    jinwen = load(idx[SHANGSHU_JINWEN])
    weiguwen = load(idx[WEI_GUWEN])

    old_rw = jinwen.get("related_works", [])
    new_jinwen_rw = []
    seen_ids = set()

    zhenguwen_rw = []  # related_works to attach to new 古文尚書 work
    weiguwen_additions = []  # (target_id, title, relation) to upsert into 偽古文尚書

    for e in old_rw:
        wid = e["id"]
        title = e["title"]
        relation = e["relation"]

        if wid in SKIP_IDS:
            new_jinwen_rw.append(e)
            continue

        if relation == "has_part":
            new_jinwen_rw.append(e)
            continue

        if wid in COLLECTED_IN_REMOVE:
            report["collected_in_removed"].append([wid, title])
            continue

        if wid in BUCKET_A:
            if wid in seen_ids:
                report["dedup_removed"].append([wid, title, relation])
                continue
            seen_ids.add(wid)
            new_jinwen_rw.append(e)
            report["bucket_a_kept"].append([wid, title, relation])
            continue

        if wid in BUCKET_B:
            zhenguwen_rw.append({"id": wid, "title": title, "relation": relation})
            report["bucket_b_moved"].append([wid, title, relation])
            # retarget or add reverse link in target file
            try:
                tpath = idx[wid]
                tdata = load(tpath)
                if not retarget_related(tdata, SHANGSHU_JINWEN, ZHEN_GUWEN, "古文尚書"):
                    upsert_related(tdata, ZHEN_GUWEN, "古文尚書", REVERSE.get(relation, "related"))
                save(tpath, tdata)
            except Exception as ex:
                report["errors"].append([wid, title, str(ex)])
            continue

        # default -> bucket C (偽古文尚書)
        weiguwen_additions.append((wid, title, relation))
        report["bucket_c_moved"].append([wid, title, relation])
        try:
            tpath = idx[wid]
            tdata = load(tpath)
            if not retarget_related(tdata, SHANGSHU_JINWEN, WEI_GUWEN, "偽古文尚書"):
                upsert_related(tdata, WEI_GUWEN, "偽古文尚書", REVERSE.get(relation, "related"))
            save(tpath, tdata)
        except Exception as ex:
            report["errors"].append([wid, title, str(ex)])

    jinwen["related_works"] = new_jinwen_rw

    # --- 拆出漢志「尚書古文經四十六卷」相關著錄，另建「古文尚書」(真,孔壁本) ---
    guwen_indexed = [e for e in jinwen.get("indexed_by", []) if e.get("title_info") == "尚書古文經四十六卷"]
    jinwen["indexed_by"] = [e for e in jinwen.get("indexed_by", []) if e.get("title_info") != "尚書古文經四十六卷"]

    guwen_emendated = [e for e in jinwen.get("emendated_by", []) if e.get("title_info") == "尚書古文經四十六卷。"]
    jinwen["emendated_by"] = [e for e in jinwen.get("emendated_by", []) if e.get("title_info") != "尚書古文經四十六卷。"]

    jinwen["measures"] = [m for m in jinwen.get("measures", []) if m.get("number") != 46]
    jinwen["juan_count"] = {
        "number": 29,
        "description": "漢志著錄今文大、小夏侯本各二十九卷，歐陽本三十二卷；孔壁真古文經四十六卷另見獨立之「古文尚書」條"
    }
    at = jinwen.get("additional_titles", [])
    if "今文尚書" not in at:
        at.append("今文尚書")
    jinwen["additional_titles"] = at

    jinwen["description"] = {
        "text": "中國最古的政事文獻彙編，記載虞、夏、商、周諸代帝王政令誥誓。「尚」者上也，謂上古帝王之書。相傳孔子刪訂百篇，為《書序》。本條專指伏生所傳今文《尚書》一系——秦焚書後，伏生口傳28篇，漢文帝時晁錯往受，以漢隸寫定，立於學官，歐陽、大小夏侯三家分傳，此即今日仍存於通行本中的可信核心。孔壁所出之真古文經（46卷/57篇）魏晉之際亡佚，另見獨立之「古文尚書」條；東晉梅賾所獻、雜以偽造25篇並附偽孔傳的通行58篇本，見「偽古文尚書」條——本條之28篇今文即嵌於彼58篇本中之33篇（析篇後計）。总名稱「尚書」歸於本條，因其為信而有徵之原典核心，不宜使讀者預設看到的是東晉偽本。",
        "sources": [
            "《漢書·藝文志》",
            "《尚書正義》",
            "蔣善國《尚書綜述》"
        ]
    }
    jinwen["ai_note"] = jinwen.get("ai_note", "") + (
        " | 2026-08-10：應使用者要求，將原「跨今古文抽象總綱」拆分為三部：本條收窄為今文尚書專條（總名稱「尚書」仍歸本條，另加別名「今文尚書」）；"
        "孔壁真古文經另建獨立 work「古文尚書」（" + ZHEN_GUWEN + "，46卷/57篇，魏晉亡佚，僅存漢魏舊注佚文與清人輯本）；"
        "既有「偽古文尚書」（" + WEI_GUWEN + "，東晉梅賾58篇本，通行十三經注疏本）身份不變。"
        "原掛於本條之 510 條 related_works 依「後世所據何本」逐類重分：題含「今文」字樣、今文三家家法、"
        "《尚書大傳》系（伏生一脈附庸文獻）、《洪範五行傳》系（劉向今文一脈）、「今古文」比較性著作（孫星衍等）留本條；"
        "漢魏（早於東晉梅賾獻書）諸家直接注古文經者（馬融、鄭玄、王肅）及其輯佚箋釋、孔安國隸古定之屬、"
        "《尚書緯》《尚書中候》讖緯系移至新建「古文尚書」（部分與偽古文尚書已有既存關聯者，改為雙重歸屬，兩不移除）；"
        "其餘（含大量以「古文尚書」為名而實為考辨偽孔傳真偽之清人著作，以及全部未標今古文字樣的宋元明清一般注疏，如"
        "孔穎達《尚書正義》、蔡沈《書集傳》等）移至「偽古文尚書」——此為唐宋以下科舉及通行注疏傳統的真實底本。"
        "collected_in「十三經」「十三經注疏」兩條一併移除，因被收入叢編的是通行的偽古文58篇本，非今文28篇本身。"
        "詳細名單見 .claude/known-issues/尚書今古文重整_round1.json。"
        "⚠️ 遺留待辦：本條原有 has_part 子篇（堯典、舜典……含清華簡保訓等）本輪未動——其中混有真今文篇、"
        "清華簡出土篇、偽古文25篇三種性質不同的材料，掛在同一抽象總綱下已不再合本次拆分後之語義，"
        "留待下一輪按篇目性質分別歸屬。"
    )

    # apply bucket C additions to 偽古文尚書 (dedup against existing)
    existing_wg_ids = {e["id"] for e in weiguwen.get("related_works", [])}
    added_to_wg = 0
    for wid, title, relation in weiguwen_additions:
        if wid in existing_wg_ids:
            continue
        weiguwen.setdefault("related_works", []).append(
            {"id": wid, "title": title, "relation": relation}
        )
        existing_wg_ids.add(wid)
        added_to_wg += 1

    # 十三經注疏 collected_in -> 偽古文尚書 (not yet present)
    upsert_related(weiguwen, "1ahwtau9gw0zk", "十三經注疏", "collected_in")

    # --- 新建「古文尚書」(真,孔壁本,已佚) ---
    zhenguwen_rw.append({
        "id": SHANGSHU_JINWEN, "title": "尚書", "relation": "related",
        "note": "同錄於漢志六藝略書類，同屬《尚書》一經之不同傳本系統；今文28篇與古文多出16篇的關係見兩條 description"
    })
    zhenguwen_rw.append({
        "id": MAGU_JIYI, "title": "古文尚書", "relation": "text_carried_by",
        "note": "清馬國翰《玉函山房輯佚書》著錄「古文尚書三卷」，據目錄立，未見輯本正文"
    })
    zhenguwen = {
        "schema_version": 1,
        "id": ZHEN_GUWEN,
        "type": "work",
        "title": "古文尚書",
        "additional_titles": ["尚書古文經"],
        "loss_status": "lost",
        "description": {
            "text": "漢武帝時魯恭王壞孔子宅，於孔壁中得蝌蚪文（先秦古文字）寫本《尚書》，較伏生今文本多出16篇，孔安國以隸古定釋讀，然未列於學官。馬融、鄭玄、王肅等漢魏經師皆曾為之作注，其學一度與今文並行。永嘉之亂後原本散佚，鄭注等亦漸次亡佚，孔安國隸古定本亦未能完整流傳。東晉梅賾所獻並附偽孔傳之58篇本（見「偽古文尚書」條）雖沿用「古文尚書」之名及部分篇目名目，其文字內容實為後人偽造，非本條所指真本。今日所知本條篇目、卷數，皆賴《漢書·藝文志》等目錄轉述，馬融、鄭玄舊注僅存佚文，另有清馬國翰《玉函山房輯佚書》所輯殘本。",
            "sources": ["《漢書·藝文志》", "《隋書·經籍志》", "阎若璩《尚書古文疏證》"]
        },
        "indexed_by": guwen_indexed,
        "emendated_by": guwen_emendated,
        "measures": [{"unit": "卷", "number": 46}],
        "juan_count": {"number": 46, "description": "漢志著錄四十六卷，為五十七篇；原本魏晉之際亡佚，今卷數僅存目錄所載"},
        "related_works": zhenguwen_rw,
        "ai_note": "2026-08-10：應使用者要求，自「尚書」（今文尚書，1evl7fct2ezgg）拆出——原漢志「尚書古文經四十六卷」indexed_by/emendated_by 條目、以及一批漢魏（早於東晉梅賾獻偽書）諸家直接注古文經之著作（馬融、鄭玄、王肅注及其後世輯佚箋釋）、孔安國隸古定之屬、《尚書緯》《尚書中候》讖緯系，均自彼條移至本條。與「偽古文尚書」（1evd3dbcb0nb4）已有既存關聯之條目（尚書鄭玄注、尚書王肅注、尚書緯鄭玄注、尚書中候鄭玄注、尚書洪范五行傳論劉向注）採雙重歸屬，未移除其原有關聯——因這些漢魏舊注雖成於偽書出現之前，後世（尤其王肅注）確與偽孔傳源流有學術公案牽連，兩條關聯皆有文獻根據。詳細移動名單見 .claude/known-issues/尚書今古文重整_round1.json。",
        "updated_at": "2026-08-10T00:00:00+00:00",
        "period": "qin-han",
        "period_basis": "孔壁發現於漢武帝時，篇目本身溯源先秦"
    }
    save(idx.get(ZHEN_GUWEN, ROOT / "Work" / "1" / "e" / "w" / f"{ZHEN_GUWEN}-古文尚書.json"), zhenguwen)

    # 馬國翰輯本 (1ewsa49z35t25) 反向補上關聯
    magu_path = idx[MAGU_JIYI]
    magu_data = load(magu_path)
    upsert_related(magu_data, ZHEN_GUWEN, "古文尚書", "contains_text_of")
    save(magu_path, magu_data)

    save(idx[SHANGSHU_JINWEN], jinwen)
    save(idx[WEI_GUWEN], weiguwen)

    report["added_to_weiguwen"] = added_to_wg
    report["zhenguwen_related_works_count"] = len(zhenguwen_rw)
    out = ROOT / ".claude" / "known-issues" / "尚書今古文重整_round1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    save(out, report)
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in report.items()},
                      ensure_ascii=False, indent=2))
    print("zhenguwen_rw entries prepared:", len(zhenguwen_rw))
    print("report ->", out.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
