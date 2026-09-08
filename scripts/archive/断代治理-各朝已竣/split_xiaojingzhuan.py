#!/usr/bin/env python3
"""拆分《孝經傳》磁鐵（1evcsw8wfkgsg）為三部獨立著作。

發現於先秦組（period=pre-qin）普查：本條 authors 只記「魏文侯」一人，
period 因此判為 pre-qin，但 indexed_by 實際掛了三條著錄，指向三個不同朝代
的三個不同人：

  清史稿藝文志：周魏文侯《孝經傳》一卷
  三國藝文志：  嚴畯孝經傳
  宋史藝文志：  《孝經傳》一卷任奉古

三書僅因同名《孝經傳》被匯入時誤合為一條，且本條原無 description（先秦
組 269 條中唯一一條 no_description），是資料單薄、未經覆核之旁證。

又查得庫中另有兩條已正確獨立之「孝經傳」——王朗（1evftehe0py4g，三國魏）、
白責（1evgbs6dwtqtc，元）——白責條之 ai_note 明載「同名異書：已有 Work
作者為 [('', ''), ('王朗', '三國魏'), ('魏文侯', '周'), ('', '')]……另建」，
可知前人已注意到「孝經傳」多人共題之磁鐵風險，唯彼時本條（原始三書合一者）
尚未拆分。今補完此一整理，令五部「孝經傳」互相 related 可尋。

Book 11qki0tl86m0w（清康熙十九年通志堂刊本；清嘉慶三年金溪王氏刊《漢魏
遺書鈔》之一）依其「漢魏遺書鈔」（專收漢魏佚書）之編選範圍，改繫於王朗
（三國魏）條，而非戰國魏文侯條——後者年代與「漢魏」編選範圍不符。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARDS = "0123456789abcdef"

WEIWENHOU = "1evcsw8wfkgsg"
YANJUN_NEW = "1ewhu66go9095"
RENFENGGU_NEW = "1ew2pafhsg2a5"
WANGLANG = "1evftehe0py4g"
BAIZE = "1evgbs6dwtqtc"

FAMILY = [WEIWENHOU, YANJUN_NEW, RENFENGGU_NEW, WANGLANG, BAIZE]
TITLES = {
    WEIWENHOU: "孝經傳", YANJUN_NEW: "孝經傳", RENFENGGU_NEW: "孝經傳",
    WANGLANG: "孝經傳", BAIZE: "孝經傳",
}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def save_index(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")


def shard_of(id_str, n=16):
    h = 0
    for c in id_str:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return h % n


def build_index():
    idx = {}
    for s in SHARDS:
        d = load(ROOT / "index" / "works" / f"{s}.json")
        for wid, entry in d.items():
            idx[wid] = ROOT / entry["path"]
    return idx


def main():
    idx = build_index()

    # ---------- 魏文侯：留原 id，收窄為單一著錄 ----------
    weiwenhou_p = idx[WEIWENHOU]
    wwh = load(weiwenhou_p)
    wwh["indexed_by"] = [e for e in wwh["indexed_by"] if e.get("source") == "清史稿藝文志"]
    wwh["books"] = []  # 原掛之漢魏遺書鈔本改繫王朗條，見下
    wwh["description"] = {
        "text": "《漢書·藝文志》未著錄。魏文侯（戰國魏開國君主，前445-前396年在位）注《孝經》之說，僅見於《清史稿藝文志》「周魏文侯《孝經傳》一卷」一條孤證，早期史志（隋志、唐志）皆無記載，其說可信度存疑，姑仍其舊題存目。與同題之嚴畯本（三國吳）、任奉古本（宋）、王朗本（三國魏）、白責本（元）皆為同名異書，非一書之異本。",
        "sources": ["清史稿藝文志"]
    }
    wwh["related_works"] = [
        e for e in wwh.get("related_works", []) if e.get("id") != "1evl1xugdoikg"
    ] + [{"id": "1evl1xugdoikg", "title": "孝經", "relation": "contains_text_of"}]
    for other in [YANJUN_NEW, RENFENGGU_NEW, WANGLANG, BAIZE]:
        wwh["related_works"].append({
            "id": other, "title": "孝經傳", "relation": "related",
            "note": "同題異書，撰人朝代各異，詳見各自 description"
        })
    wwh["ai_note"] = wwh.get("ai_note", "") + (
        " | 2026-08-10：本條原三書合一（魏文侯／嚴畯／任奉古），係典型同題磁鐵，"
        "今拆分——嚴畯本另建 " + YANJUN_NEW + "，任奉古本另建 " + RENFENGGU_NEW +
        "，本條僅留魏文侯一書。原掛之 Book（11qki0tl86m0w，漢魏遺書鈔本）依其"
        "「漢魏」編選範圍改繫王朗（三國魏）條，非戰國魏文侯條。五部「孝經傳」"
        "（本條、嚴畯、任奉古、王朗、白責）已互相補 related 關聯。"
    )
    save(weiwenhou_p, wwh)

    # ---------- 嚴畯：新建 ----------
    yanjun = {
        "schema_version": 1,
        "id": YANJUN_NEW,
        "type": "work",
        "title": "孝經傳",
        "authors": [
            {"name": "嚴畯", "role": "撰", "dynasty": "三國吳",
             "note": "字曼才，三國吳彭城人，官至衛尉，與張昭、諸葛瑾等友善"}
        ],
        "description": {
            "text": "《三國藝文志》著錄「嚴畯孝經傳」，未載卷數。嚴畯，字曼才，彭城人，三國吳臣，官至衛尉，通《詩》《書》《三禮》，與張昭友善，見《三國志·吳志》本傳。書已佚。與同題之魏文侯本（先秦）、任奉古本（宋）、王朗本（三國魏）、白責本（元）皆為同名異書。",
            "sources": ["三國藝文志"]
        },
        "indexed_by": [
            {"source": "三國藝文志", "source_bid": "1eve1eig5jn5s",
             "title_info": "嚴畯孝經傳。", "summary": "嚴畯孝經傳。"}
        ],
        "related_works": [
            {"id": "1evl1xugdoikg", "title": "孝經", "relation": "contains_text_of"},
            {"id": WEIWENHOU, "title": "孝經傳", "relation": "related", "note": "同題異書，戰國魏文侯本"},
            {"id": RENFENGGU_NEW, "title": "孝經傳", "relation": "related", "note": "同題異書，宋任奉古本"},
            {"id": WANGLANG, "title": "孝經傳", "relation": "related", "note": "同題異書，三國魏王朗本"},
            {"id": BAIZE, "title": "孝經傳", "relation": "related", "note": "同題異書，元白責本"},
        ],
        "loss_status": "lost",
        "ai_note": "2026-08-10：自 1evcsw8wfkgsg（原「孝經傳」三書合一之磁鐵）拆出，見該條 ai_note。",
        "updated_at": "2026-08-10T00:00:00+00:00",
        "period": "three-kingdoms",
        "period_basis": "據 authors[0].dynasty「三國吳」"
    }
    save(ROOT / "Work/1/e/w" / f"{YANJUN_NEW}-孝經傳.json", yanjun)

    # ---------- 任奉古：新建 ----------
    renfenggu = {
        "schema_version": 1,
        "id": RENFENGGU_NEW,
        "type": "work",
        "title": "孝經傳",
        "authors": [{"name": "任奉古", "role": "撰", "dynasty": "宋"}],
        "description": {
            "text": "《宋史·藝文志》著錄「《孝經傳》一卷任奉古」。任奉古生平未詳。書已佚。與同題之魏文侯本（先秦）、嚴畯本（三國吳）、王朗本（三國魏）、白責本（元）皆為同名異書。",
            "sources": ["宋史藝文志"]
        },
        "indexed_by": [
            {"source": "宋史藝文志", "source_bid": "1evcsw4kt579c",
             "title_info": "《孝經傳》", "summary": "《孝經傳》一卷任奉古"}
        ],
        "juan_count": {"number": 1},
        "measures": [{"unit": "卷", "number": 1}],
        "measure_info": "一卷",
        "related_works": [
            {"id": "1evl1xugdoikg", "title": "孝經", "relation": "contains_text_of"},
            {"id": WEIWENHOU, "title": "孝經傳", "relation": "related", "note": "同題異書，戰國魏文侯本"},
            {"id": YANJUN_NEW, "title": "孝經傳", "relation": "related", "note": "同題異書，三國吳嚴畯本"},
            {"id": WANGLANG, "title": "孝經傳", "relation": "related", "note": "同題異書，三國魏王朗本"},
            {"id": BAIZE, "title": "孝經傳", "relation": "related", "note": "同題異書，元白責本"},
        ],
        "loss_status": "lost",
        "ai_note": "2026-08-10：自 1evcsw8wfkgsg（原「孝經傳」三書合一之磁鐵）拆出，見該條 ai_note。",
        "updated_at": "2026-08-10T00:00:00+00:00",
        "period": "song",
        "period_basis": "據 authors[0].dynasty「宋」"
    }
    save(ROOT / "Work/1/e/v" / f"{RENFENGGU_NEW}-孝經傳.json", renfenggu)

    # ---------- 王朗：接收 Book，補 related ----------
    wanglang_p = idx[WANGLANG]
    wl = load(wanglang_p)
    wl.setdefault("books", []).append("11qki0tl86m0w")
    for other in [WEIWENHOU, YANJUN_NEW, RENFENGGU_NEW, BAIZE]:
        wl.setdefault("related_works", []).append({
            "id": other, "title": "孝經傳", "relation": "related", "note": "同題異書"
        })
    wl["ai_note"] = wl.get("ai_note", "") + (
        " | 2026-08-10：接收 Book 11qki0tl86m0w（清康熙十九年通志堂刊本；清嘉慶三年"
        "金溪王氏刊《漢魏遺書鈔》之一）——原繫於 1evcsw8wfkgsg（先秦魏文侯條），"
        "然「漢魏遺書鈔」專收漢魏佚書，不當收戰國文獻，改繫於本條（三國魏王朗）。"
        "並與另外四部同題「孝經傳」互補 related 關聯。"
    )
    save(wanglang_p, wl)

    # ---------- 白責：補 related ----------
    baize_p = idx[BAIZE]
    bz = load(baize_p)
    for other in [WEIWENHOU, YANJUN_NEW, RENFENGGU_NEW, WANGLANG]:
        bz.setdefault("related_works", []).append({
            "id": other, "title": "孝經傳", "relation": "related", "note": "同題異書"
        })
    save(baize_p, bz)

    # ---------- Book 改繫 ----------
    book_p = None
    for cand in ROOT.glob("Book/*/*/*/11qki0tl86m0w-*.json"):
        book_p = cand
        break
    bdata = load(book_p)
    bdata["work_id"] = WANGLANG
    save(book_p, bdata)

    # ---------- 新建兩條之索引項 ----------
    for wid, title, path in [
        (YANJUN_NEW, "孝經傳", f"Work/1/e/w/{YANJUN_NEW}-孝經傳.json"),
        (RENFENGGU_NEW, "孝經傳", f"Work/1/e/v/{RENFENGGU_NEW}-孝經傳.json"),
    ]:
        s = shard_of(wid)
        p = ROOT / "index" / "works" / f"{s:x}.json"
        d = load(p)
        d[wid] = {
            "id": wid, "title": title, "type": "Work", "path": path,
            "author": "嚴畯" if wid == YANJUN_NEW else "任奉古",
            "dynasty": "三國吳" if wid == YANJUN_NEW else "宋",
            "role": "撰",
            "period": "three-kingdoms" if wid == YANJUN_NEW else "song",
        }
        save_index(p, d)
        print("indexed", wid, "-> shard", f"{s:x}.json")

    # ---------- 原索引項之 dynasty/period 校正（原誤標周/pre-qin 因三書合一） ----------
    s = shard_of(WEIWENHOU)
    p = ROOT / "index" / "works" / f"{s:x}.json"
    d = load(p)
    d[WEIWENHOU]["dynasty"] = "先秦"
    save_index(p, d)

    print("done")


if __name__ == "__main__":
    main()
