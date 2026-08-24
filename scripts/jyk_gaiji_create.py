#!/usr/bin/env python3
"""經義考待覈「缺字碼未還原」14 條：立其書，記其人

此 14 條之閘是撰人之名含 kanripo 缺字碼（&KRnnnn;），未能還原，故不建。
然**同一批中已建之《錢氏古文易》（`1exjinuotxail`）正是同一人之書**——
該次以 `authors: []` 建之，缺字碼只留在逐字照錄的著錄語裡。閘之寬嚴不一。

且缺字雖未還原，**其人已可指實**：

  · `&KR2066;`（10 條）＝ **錢士□，字穉拙**（一作穉茁），**平湖縣人，國子監生**，
    朱彝尊之亡友。據《錢氏古文易》著錄語所引「平湖縣志錢士&KR2066;字穉拙
    國子監生」，及《續越絶書》論斷「按續越絶書二卷亡友錢穉茁避地白石樵林時
    所撰也」。其名是**二字**（士＋缺字），非一字——待覈之目作「錢氏（&KR2066;）」
    是標目解析漏了「士」。本庫已有其書二部：《錢氏古文易》`1exjinuotxail`、
    《周禮答疑》`1exuoffgxzlk1`。
  · `&KR2115;`（劉氏，1 條）＝ **劉□，字子有**。據論斷「董鼎曰&KR2115;字子有」。
  · `&KR2115;`（張氏，1 條）＝ 少城**進士張□**，倣呂氏所鏤本書丹刻《古文尚書》
    於石。據論斷所引晁公武語。（同一缺字碼而分屬劉、張二姓，非一人。）
  · `&KR0958;`（徐氏）、`&KR1220;`（張氏）：論斷無文，其人不可指。

**故改為建之**——書之存在有《經義考》為證，不因撰人一字不可讀而不錄；
`authors` 依《錢氏古文易》之例留空（缺字碼不入姓名欄，否則索引與併池皆受其累），
所知之人事記於 `ai_note`，缺字碼則逐字照錄於著錄語，可覆按。

用法：python3 scripts/jyk_gaiji_create.py [--apply]
"""
import json, os, sys, hashlib, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import nz, load_index

HOLD = '.claude/known-issues/經義考待覈.json'
SRC, SRC_BID = '經義考', '1ev3bb43bv4lc'
STATUS = {'佚': 'lost', '存': 'extant', '未見': 'not_seen', '闕': 'partial'}
NOTE = ('此是朱彝尊所判，非本庫之判，故不改本記錄之 loss_status。'
        '四庫御製題論此書曰「所注闕佚未見者，今四庫所録往往其書尚存」'
        '——其判是十七世紀一人之見聞。「未見」尤非亡佚，是朱氏未見其書。')

# 缺字碼 → 其人之考
WHO = {
 '&KR2066;': ('錢士□，字穉拙（一作穉茁），平湖縣人，國子監生，朱彝尊之亡友。'
   '據《錢氏古文易》（`1exjinuotxail`）著錄語所引「平湖縣志錢士&KR2066;字穉拙'
   '國子監生」，及《續越絶書》論斷「按續越絶書二卷亡友錢穉茁避地白石樵林時所撰也」。'
   '**其名是二字（士＋缺字）**，非一字——本條標目作「錢氏（&KR2066;）」是解析漏了「士」。'
   '本庫已有其書二部：《錢氏古文易》`1exjinuotxail`、《周禮答疑》`1exuoffgxzlk1`。'),
 '&KR2115;劉': '劉□，字子有。據本條論斷所引「董鼎曰&KR2115;字子有」。',
 '&KR2115;張': ('少城進士張□，倣呂氏所鏤本書丹刻《古文尚書》於石。'
   '據本條論斷所引晁公武語。按：`&KR2115;` 一碼於本庫分屬劉、張二姓，非一人。'),
}


def b36(n, w=13):
    d = '0123456789abcdefghijklmnopqrstuvwxyz'
    s = ''
    while n:
        s = d[n % 36] + s; n //= 36
    return s.rjust(w, '0')[-w:]


def shard(i):
    h = 0
    for c in i: h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return '0123456789abcdef'[h % 16]


def who(r):
    a = r.get('author') or ''
    if '&KR2066;' in a: return WHO['&KR2066;']
    if '&KR2115;' in a: return WHO['&KR2115;劉'] if a.startswith('劉') else WHO['&KR2115;張']
    return ('其名之一字為 kanripo 缺字碼 `%s`，未能還原；'
            '本條論斷無文，其人亦不可指。' % a.replace(r['author'][0], '', 1))


def main():
    apply = '--apply' in sys.argv
    works = load_index('works')
    taken = set(works)
    D = json.load(open(HOLD, encoding='utf-8'))
    sub = [r for r in D if '缺字' in r['why']]
    print(f'缺字碼待覈 {len(sub)} 條')

    # 先驗：庫中不得已有同題而撰人亦闕者（免生無名重出）
    bt = collections.defaultdict(list)
    for w, v in works.items(): bt[nz(v.get('title'))].append(v)
    risky = []
    for r in sub:
        same = [v for v in bt.get(nz(r['title']), []) if not v.get('author')]
        if same: risky.append((r['head'], [v['id'] for v in same]))
    if risky:
        print('！庫中已有同題而無撰人者，恐生重出：')
        for h, ids in risky: print('   ', h, ids)
        return
    print('驗過：庫中無同題而撰人亦闕者，不生無名重出')

    made = []
    for r in sub:
        for salt in range(64):
            h = hashlib.sha1(f"jyk-gaiji:{r['head']}:{r['page']}:{salt}".encode()).hexdigest()
            wid = '1ex' + b36(int(h[:16], 16), 10)
            if wid not in taken: break
        taken.add(wid)
        t = r['title']
        rec = {
            'schema_version': 1, 'type': 'work', 'title': t, 'id': wid,
            'ai_note':
                f'本 work 據《經義考》（朱彝尊撰，欽定四庫全書文淵閣本，kanripo '
                f'KR2n0011）新建——該書{r["lei"]}類著錄「{r["head"]}」。\n\n'
                f'**撰人之名含缺字碼，故 `authors` 留空**（缺字碼不入姓名欄，'
                f'否則索引與併池皆受其累），非謂其書無撰人。所知者記此：\n'
                f'{who(r)}\n\n'
                f'缺字碼逐字照錄於 `indexed_by[].title_info`／`summary`，可覆按。\n\n'
                f'以下諸欄不繫，非漏，是無據或不屬本道：\n'
                f'· `period`：屬 C 車道；論斷所引之年號是引者之年非撰人之年，'
                f'曾試而準確率只 0.81。\n'
                f'· `loss_status`：朱氏判本書為「{r["status"]}」，其判入 '
                f'`indexed_by[].attested_status`，不作本庫之判。\n'
                f'· `authors[].role`／`entity_id`：著錄之文不言其役；繫人須另考。',
            'indexed_by': [{
                'source': SRC, 'source_bid': SRC_BID,
                'title_info': f'《{t}》（{r["author"]}）',
                'summary': '；'.join(r['attest']) if r['attest'] else '',
                'section': r['lei'], 'juan': r['juan'], 'page': r['page'],
                'attested_status': STATUS[r['status']],
                'attested_status_raw': r['status'],
                'attested_status_note': NOTE}],
            'period_upper': 'qing',
            'period_upper_basis':
                'catalog_bound：所繫諸志中最緊者為《經義考》（清朱彝尊（1700）），'
                '故不晚於 qing',
        }
        made.append((wid, t, rec, r))
        print(f'  建 {wid} 《{t}》  ← {r["head"]}')
    if not apply:
        print('（乾跑。加 --apply 方寫檔）')
        return

    shards = {x: json.load(open(f'index/works/{x}.json', encoding='utf-8'))
              for x in '0123456789abcdef'}
    for wid, t, rec, r in made:
        p = f'Work/{wid[0]}/{wid[1]}/{wid[2]}/{wid}-{t}.json'
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(rec, ensure_ascii=False, indent=2) + '\n')
        shards[shard(wid)][wid] = {'id': wid, 'title': t, 'type': 'Work', 'path': p}
    for x, obj in shards.items():
        with open(f'index/works/{x}.json', 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps({k: obj[k] for k in sorted(obj)},
                               ensure_ascii=False, indent=2) + '\n')
    heads = {r['head'] for _, _, _, r in made}
    rest = [d for d in D if d['head'] not in heads]
    with open(HOLD, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(rest, ensure_ascii=False, indent=1) + '\n')
    # 待裁之目記其所建
    T = '.claude/known-issues/經義考待裁.json'
    TD = json.load(open(T, encoding='utf-8'))
    m = {r['head']: wid for wid, _, _, r in made}
    for d in TD:
        if d['head'] in m and not d.get('created_work'):
            d['created_work'] = m[d['head']]
    with open(T, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(TD, ensure_ascii=False, indent=1) + '\n')
    print(f'已寫檔：新建 {len(made)}，待覈 {len(D)} → {len(rest)}')


if __name__ == '__main__':
    main()
