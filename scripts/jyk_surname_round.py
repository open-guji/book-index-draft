#!/usr/bin/env python3
"""經義考待覈「不著撰人」之標目有姓者：掛四、建三、扣一

承 `jyk_lun_attach.py`。該輪以「庫中恰有一條同姓」決三條，餘者判為
「庫中無同姓，依 SCHEMA〈同題異撰是二書〉當建」。**然逕建則誤**——
先以夾撰人之法（甲4）覆掃，三條實已在庫，只是撰人夾在題中：

  鄒氏《春秋傳》→《春秋鄒氏傳》`1ev7w0exbxt6o`（漢志十一卷，數合）
  夾氏《春秋傳》→《春秋夾氏傳》`1ev7w0exxsf7k`（漢志十一卷，數合）
  虞氏《尚書釋問》→《尚書釋問虞氏撰》`1evc5pcerz6yo`（隋志一卷，數合）
  孔氏《毛詩音》→《孔氏毛詩音》`1evfuvjrk8p34`

**若不覆掃而逕建，即為《春秋》五傳中那兩部（鄒氏、夾氏）各添一重出。**
甲4 之閘在本輪三處奏效（經義考「庫中二條以上」、玉函山房、此處），
可立為常法：**凡以題名比而不得者，須再以「剝去庫題所夾之撰人」比一次。**

餘三條庫中確無（含夾撰人者亦無），依 SCHEMA 別建：
何氏《周易講疏》、蔡氏《毛詩音》、周氏《論語解》。
撰人依《經義考》標目作「何氏」「蔡氏」「周氏」——**此是著錄之形，非缺文**，
本庫素有其例（趙氏、姜氏、伏氏、鄒氏、夾氏、虞氏皆然）。

扣一：李氏《春秋》。庫中《春秋》五條唯 `1ev7xkhqvkruo` 撰人作「李氏」，
二篇合著錄「漢志二篇」，本可掛；**惟其 period 為 pre-qin，屬先秦域，
他會話所主，本輪一律不動**。（鄒氏、夾氏二條 period 為 qin-han，不在其域，故掛。）

用法：python3 scripts/jyk_surname_round.py [--apply]
"""
import json, os, sys, hashlib, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import load_index

HOLD = '.claude/known-issues/經義考待覈.json'
SRC, SRC_BID = '經義考', '1ev3bb43bv4lc'
STATUS = {'佚': 'lost', '存': 'extant', '未見': 'not_seen', '闕': 'partial'}
NOTE = ('此是朱彝尊所判，非本庫之判，故不改本記錄之 loss_status。'
        '四庫御製題論此書曰「所注闕佚未見者，今四庫所録往往其書尚存」'
        '——其判是十七世紀一人之見聞。「未見」尤非亡佚，是朱氏未見其書。')

ATTACH = {
 'KR2n0011_WYG_170-11a|鄒氏（失名）春秋傳': ('1ev7w0exbxt6o',
   '庫題《春秋鄒氏傳》夾撰人於題中，剝之即本條之題；撰人欄正作「鄒氏」，'
   '十一卷合本條著錄「漢志十一巻」。論斷「漢初公羊榖梁鄒氏夾氏四家竝行，'
   '王莽之亂鄒氏無師」亦與之合。**若以題名相比則不得，逕建即為《春秋》'
   '五傳之鄒氏一傳添一重出。**'),
 'KR2n0011_WYG_170-11b|夾氏（失名）春秋傳': ('1ev7w0exxsf7k',
   '庫題《春秋夾氏傳》，同上。撰人欄正作「夾氏」，十一卷合本條著錄「漢志十一卷」。'
   '論斷「班固曰夾氏未有書……漢志注云有録無書」與之合。'),
 'KR2n0011_WYG_078-8b|虞氏（失名）尚書釋問': ('1evc5pcerz6yo',
   '庫題《尚書釋問虞氏撰》，剝其所綴之「虞氏撰」即本條之題；'
   '撰人欄正作「虞氏」，一卷合本條著錄「隋志一巻」。'),
 'KR2n0011_WYG_102-6b|孔氏（失名）毛詩音': ('1evfuvjrk8p34',
   '庫題《孔氏毛詩音》夾撰人於題首，剝之即本條之題。'
   '論斷「陸德明曰蔡氏孔氏不詳何人」正解本條標目之「失名」。'),
}

CREATE = {
 'KR2n0011_WYG_040-28b|何氏（失名）周易講疏':
   '庫中《周易講疏》四條（賀瑒、張譏、蕭衍、褚仲都），無一姓何；'
   '以夾撰人之法覆掃亦無。依 SCHEMA〈同題異撰是二書〉別建。',
 'KR2n0011_WYG_102-6b|蔡氏（失名）毛詩音':
   '庫中《毛詩音》八條（阮侃、王肅、徐爰、于寳、江惇、江淳、徐邈、李軌），'
   '無一姓蔡；以夾撰人之法覆掃亦無（孔氏一條有而蔡氏無）。'
   '同卷論斷「陸德明曰爲詩音者九人鄭康成徐邈蔡氏孔氏阮侃王肅江惇于寳李軌」'
   '——蔡氏本在九人之列，其書自為一部。依 SCHEMA 別建。',
 'KR2n0011_WYG_220-1a|周氏（失名）論語解':
   '庫中《論語解》四十六條無一姓周；以夾撰人之法覆掃亦無。'
   '論斷「朱子曰周教授論語解篤實似尹公謹嚴過之而純熟不及」，'
   '是朱子及見其書而稱之為「周教授」，其人有官而失其名。依 SCHEMA 別建。',
}

HOLD_WHY = {
 'KR2n0011_WYG_277-3b|李氏（失名）春秋':
   '庫中《春秋》五條唯 `1ev7xkhqvkruo` 撰人作「李氏」，二篇合本條著錄'
   '「漢志二篇」，本可掛；**惟其 period 為 pre-qin，屬先秦域，他會話所主，'
   '本輪一律不動**。（同批之鄒氏、夾氏二條 period 為 qin-han，不在其域，故掛。）'
   '所需之據已備，先秦域一路可逕掛。',
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


def main():
    apply = '--apply' in sys.argv
    works = load_index('works')
    bad = [w for w, _ in ATTACH.values() if w not in works]
    if bad:
        print('！id 不在庫：', bad); return
    D = json.load(open(HOLD, encoding='utf-8'))
    sub = [r for r in D if r['why'].startswith('庫中同題二條以上而本條不著撰人')]
    by = {f"{r['page']}|{r['head']}": r for r in sub}
    if len(by) != len(sub):
        print('！鍵不唯一'); return
    miss = (set(ATTACH) | set(CREATE) | set(HOLD_WHY)) - set(by)
    if miss:
        print('！表列不在待覈之目：', miss); return
    print(f'驗過：不著撰人 {len(sub)} 條；掛 {len(ATTACH)}、建 {len(CREATE)}、'
          f'明記其扣 {len(HOLD_WHY)}')

    def node(r, why, kind):
        return {'source': SRC, 'source_bid': SRC_BID,
                'title_info': f"《{r['title']}》",
                'summary': '；'.join(r['attest']) if r['attest'] else '',
                'section': r['lei'], 'juan': r['juan'], 'page': r['page'],
                'attested_status': STATUS[r['status']],
                'attested_status_raw': r['status'],
                'attested_status_note': NOTE,
                'link_basis': f'2026-08-24 待覈「不著撰人」標目有姓者逐條裁（{kind}）：' + why}

    n_add = 0
    for k, (wid, why) in ATTACH.items():
        r = by[k]; path = works[wid]['path']
        w = json.load(open(path, encoding='utf-8'))
        idx = w.setdefault('indexed_by', [])
        if (SRC, r['page']) in {(e.get('source'), e.get('page')) for e in idx}:
            continue
        idx.append(node(r, why, '掛既有'))
        n_add += 1
        print(f"  掛 {wid} 《{works[wid]['title']}》{works[wid].get('author')} ← {r['head']}")
        if apply:
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(json.dumps(w, ensure_ascii=False, indent=2) + '\n')

    taken = set(works); made = []
    for k, why in CREATE.items():
        r = by[k]
        sur = r['head'][0] + '氏'
        for salt in range(64):
            h = hashlib.sha1(f"jyk-surname:{k}:{salt}".encode()).hexdigest()
            wid = '1ex' + b36(int(h[:16], 16), 10)
            if wid not in taken: break
        taken.add(wid)
        rec = {'schema_version': 1, 'type': 'work', 'title': r['title'], 'id': wid,
               'authors': [{'name': sur, 'role': None,
                            'name_basis': f'《經義考》標目作「{r["head"]}」——'
                                          f'「{sur}」是著錄之形，非缺文；'
                                          f'「失名」謂其名不傳，本庫素有其例'
                                          f'（趙氏、姜氏、伏氏、鄒氏、夾氏、虞氏）。'}],
               'indexed_by': [node(r, why, '別建')],
               'ai_note':
                   f'本 work 據《經義考》（朱彝尊撰，欽定四庫全書文淵閣本，kanripo '
                   f'KR2n0011）新建——該書{r["lei"]}類著錄「{r["head"]}」。\n\n'
                   f'{why}\n\n'
                   f'**建前已以二法覆掃庫中同題諸條**：一以撰人之姓比，'
                   f'二以「剝去庫題所夾之撰人」比（甲4）。同批之鄒氏《春秋傳》、'
                   f'夾氏《春秋傳》、虞氏《尚書釋問》、孔氏《毛詩音》四條正由第二法'
                   f'查出庫中已有，改掛不建；本條二法俱不得，乃建。\n\n'
                   f'以下諸欄不繫，非漏，是無據或不屬本道：\n'
                   f'· `period`：屬 C 車道。\n'
                   f'· `loss_status`：朱氏判本書為「{r["status"]}」，其判入 '
                   f'`indexed_by[].attested_status`，不作本庫之判。\n'
                   f'· `authors[].role`／`entity_id`：著錄之文不言其役；'
                   f'其名既失，繫人無從措手。',
               'period_upper': 'qing',
               'period_upper_basis':
                   'catalog_bound：所繫諸志中最緊者為《經義考》（清朱彝尊（1700）），'
                   '故不晚於 qing'}
        made.append((wid, r, rec))
        print(f"  建 {wid} 《{r['title']}》{sur} ← {r['head']}")

    if not apply:
        print(f'待覈 {len(D)} → {len(D) - len(ATTACH) - len(CREATE)}（乾跑）')
        return

    shards = {x: json.load(open(f'index/works/{x}.json', encoding='utf-8'))
              for x in '0123456789abcdef'}
    for wid, r, rec in made:
        p = f"Work/{wid[0]}/{wid[1]}/{wid[2]}/{wid}-{r['title']}.json"
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(rec, ensure_ascii=False, indent=2) + '\n')
        shards[shard(wid)][wid] = {'id': wid, 'title': r['title'], 'type': 'Work',
                                   'path': p, 'author': rec['authors'][0]['name']}
    for x, obj in shards.items():
        with open(f'index/works/{x}.json', 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps({q: obj[q] for q in sorted(obj)},
                               ensure_ascii=False, indent=2) + '\n')
    done = set(ATTACH) | set(CREATE)
    rest = []
    for d in D:
        k = f"{d['page']}|{d['head']}"
        if k in done and d in sub: continue
        if k in HOLD_WHY and d in sub:
            d = dict(d); d['hold_basis'] = HOLD_WHY[k]
        rest.append(d)
    with open(HOLD, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(rest, ensure_ascii=False, indent=1) + '\n')
    T = '.claude/known-issues/經義考待裁.json'
    TD = json.load(open(T, encoding='utf-8'))
    m = {by[k]['head']: wid for (k, _), (wid, r, _) in zip(CREATE.items(), made)}
    for d in TD:
        if d['head'] in m and not d.get('created_work'):
            d['created_work'] = m[d['head']]
    with open(T, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(TD, ensure_ascii=False, indent=1) + '\n')
    print(f'掛 {n_add}、建 {len(made)}；待覈 {len(D)} → {len(rest)}　已寫檔')


if __name__ == '__main__':
    main()
