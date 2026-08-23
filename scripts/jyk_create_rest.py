#!/usr/bin/env python3
"""建乙2、丙之 work（《經義考》著錄而庫中無者）

與乙1 之法同（見 `jyk_create_works.py`），四事有異：

**一、標目先正**。乙1 只把解析不淨者擋在閘外，此輪逐條正之——表見
`jyk_head_fix.py`：姓氏知而名失傳者記其姓為撰人（庫中已有《周易服氏》之
例），姓名連書者分之，帝王從庫中舊例記其廟號，括中是校語者只剔括號。

**二、論斷入 summary**。著錄語＋換行＋論斷，逾 500 字截之並指其全文所在。
此是本輪重取原文之所得——朱彝尊於每條下所輯諸家論斷，前次解析只存二三十
字。撰人之里貫、師承、登第之年多在其中。

**三、閘多一道**：撰人相同而其名嵌於庫題之中者（《周易董遇注》對《周易
注》）不建——此是乙1 之失，三十一條建為重出而後刪，今立為閘。

**四、`period` 仍不繫**。曾試以論斷所引之年號定代——取撰人名後百二十字內
之首見年號——以庫中 Entity 為驗，準確率只 0.81：論斷屢引後人之語（漢人之
書而王應麟曰、范仲淹序），其年號是引者之年非撰人之年。不足以充一欄之據。
撰人在庫中 Entity 唯一者可定代，然 `period` 是 C 車道所擁，本道不越界——
論斷既已入 summary，C 道取之即得。
"""
import json, os, re, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import nz, load_index, embedded_author
from jyk_attach_source import SRC, SRC_BID, STATUS, NOTE
from jyk_create_works import shard, mkid, CIT
import jyk_head_fix as HF

DATA = '.claude/known-issues/經義考待裁.json'
LUN = '.claude/known-issues/經義考論斷.json'
LIMIT = 500
TAIL = '……（下略。全文見《經義考》整理本 collated_edition/{lei}.json，頁 {page}）'

AI_NOTE = (
    '本 work 據《經義考》（朱彝尊撰，欽定四庫全書文淵閣本，kanripo KR2n0011）'
    '新建——該書{lei}類著錄「{head}」，{cit}，而本庫先前無同題之 work。\n\n'
    '所記止於朱氏所有：題、撰人之名、所引之志（如有）、卷、頁，及其所輯諸家'
    '論斷（入 indexed_by[].summary，逾五百字者截之，全文在《經義考》整理本）。'
    '以下諸欄不繫，非漏，是無據或不屬本道：\n'
    '· `period`：曾試以論斷所引之年號定代，以庫中 Entity 為驗，準確率只 0.81'
    '——論斷屢引後人之語，其年號是引者之年非撰人之年。且 period 屬 C 車道。'
    '論斷既已在此，定代所須之據不待外求。\n'
    '· `loss_status`：朱氏判本書為「{status}」，其判入 indexed_by[].'
    'attested_status，不作本庫之判。\n'
    '· `authors[].role`：著錄之文不言其役。以題末之字推役是推，非據。\n'
    '· `authors[].entity_id`：《經義考》只給人名，繫人須另考。')


def main():
    apply = '--apply' in sys.argv
    tiers = {a for a in sys.argv[1:] if not a.startswith('-')} or {'乙2', '丙1', '丙2'}
    works = load_index('works')
    taken = set(works)
    by_title, by_author = collections.defaultdict(list), collections.defaultdict(list)
    for v in works.values():
        by_title[nz(v.get('title'))].append(v)
        if v.get('author'):
            by_author[nz(v['author'])].append(v)
    lun = {(x['page'], x['head']): x for x in json.load(open(LUN))}
    D = json.load(open(DATA))
    J = [d for d in D if d['tier'] in tiers
         and not (d.get('attached_to') or d.get('created_work'))]

    def fixed(d):
        """回傳（撰人, 正題, 標目正誤之由）"""
        if d['head'] in HF.FIX:
            return HF.FIX[d['head']]
        t = re.sub(r'（[^）]*）', '', d.get('title') or '').strip()
        return d.get('author'), t, None

    dupe = collections.defaultdict(list)
    for d in J:
        a, t, _ = fixed(d)
        dupe[(nz(t), nz(a))].append(d)

    make, hold = [], []
    for (kt, ka), ds in dupe.items():
        d = ds[0]
        a, t, why = fixed(d)
        g = []
        if '&KR' in (a or '') or '&KR' in t:
            g.append('缺字碼未還原')
        if len(kt) < 2:
            g.append('題名過短')
        if d['head'] not in HF.FIX and d['head'] not in HF.STRIP_ONLY:
            if d['head_form'] in ('dyn', 'zi', 'shih'):
                g.append('標目解析待覈（head_form 非常式）')
            p = [m for m in re.findall(r'（([^）]*)）', d.get('title') or '')
                 if len(m) <= 3 and not re.match(
                     r'或|一|舊|今|亦|新|唐|宋|隋|漢|晉|梁|陳|齊|周|七|釋文|通考|崇文|'
                     r'中興|國史|館閣|讀書|書錄|書録|陸|馬|晁|陳氏|宋史|本傳|闕', m)]
            if p:
                g.append(f'標目解析待覈（括中「{p[0]}」疑是人名）')
        if ka:
            for w in by_title.get(kt, []):
                wa = nz(w.get('author'))
                if wa == ka:
                    g.append(f'庫中已有同題同撰（{w["id"]}）')
                    break
                if wa and len(wa) == len(ka) and sum(x != y for x, y in zip(wa, ka)) == 1:
                    g.append(f'形訛近名（庫作「{w.get("author")}」{w["id"]}）')
                    break
            em = embedded_author(kt, ka, by_author)
            if em:
                g.append(f'撰人之名嵌於庫題之中（{em[0]["id"]}《{em[0]["title"]}》）')
        if g:
            for x in ds:
                hold.append({'gates': g, 'fixed_author': a, 'fixed_title': t,
                             **{k: x[k] for k in ('head', 'author', 'title', 'lei',
                                                  'juan', 'page', 'status', 'attest', 'tier')}})
        else:
            make.append((ds, a, t, why))

    print(f'{"／".join(sorted(tiers))} 未辦 {len(J)}；歸併同題同撰後 {len(dupe)} 種；'
          f'建 {len(make)}，待覈 {len(hold)}')
    print(collections.Counter(h['gates'][0].split('（')[0] for h in hold))
    print('其中無撰人者', sum(1 for m in make if not m[1]))
    if not apply:
        print('（乾跑。加 --apply 方寫檔）')
        return make, hold

    shards = {s: json.load(open(f'index/works/{s}.json')) for s in '0123456789abcdef'}
    n = 0
    for ds, a, t, why in make:
        d = ds[0]
        wid = mkid(f"{d['juan']}|{d['page']}|{d['head']}", taken)
        path = f'Work/{wid[0]}/{wid[1]}/{wid[2]}/{wid}-{t}.json'
        cit = '所引' + '、'.join(c for c in CIT if c in ''.join(d['attest'] or [])) \
            if any(c in ''.join(d['attest'] or []) for c in CIT) else '不引前代志'
        note = AI_NOTE.format(lei=d['lei'], head=d['head'], cit=cit, status=d['status'])
        if why:
            note += '\n\n標目之正：' + why + '。'
        rec = {'schema_version': 1, 'type': 'work', 'title': t, 'id': wid}
        if a:
            rec['authors'] = [{'name': a, 'role': None}]
        rec['ai_note'] = note
        rec['indexed_by'] = []
        for x in ds:
            k = lun.get((x['page'], x['head']))
            zhu = (k['zhu'] if k else '') or '；'.join(x['attest'] or [])
            lu = k['lun'] if k else ''
            if len(lu) > LIMIT:
                lu = lu[:LIMIT] + TAIL.format(lei=(k['lei'] if k else x['lei']), page=x['page'])
            summary = ((zhu + '\n' + lu) if zhu else lu).strip()
            rec['indexed_by'].append({
                'source': SRC, 'source_bid': SRC_BID,
                'title_info': f"《{t}》" + (f"（{a}）" if a else ''),
                'summary': summary, 'section': x['lei'], 'juan': x['juan'],
                'page': x['page'], 'attested_status': STATUS[x['status']],
                'attested_status_raw': x['status'], 'attested_status_note': NOTE})
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
            f.write('\n')
        e = {'id': wid, 'title': t, 'type': 'Work', 'path': path}
        if a:
            e['author'] = a
        shards[shard(wid)][wid] = e
        for x in ds:
            x['created_work'] = wid
        n += 1
    for s, obj in shards.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8') as f:
            json.dump(dict(sorted(obj.items())), f, ensure_ascii=False, indent=2)
            f.write('\n')
    json.dump(D, open(DATA, 'w'), ensure_ascii=False, indent=1)
    tag = '乙2' if tiers == {'乙2'} else ('丙' if tiers <= {'丙1', '丙2'} else '乙丙')
    json.dump(hold, open(f'.claude/known-issues/經義考{tag}待覈.json', 'w'),
              ensure_ascii=False, indent=1)
    print('已建', n)


if __name__ == '__main__':
    main()
