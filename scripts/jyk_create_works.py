#!/usr/bin/env python3
"""乙1 建 work：《經義考》著錄而庫中無、且引前代志者

**建之範圍**：`tier == 乙1` 且過閘者。閘凡六，過不了的一律不建，出
`.claude/known-issues/經義考乙1待覈.json`：

  形訛近名   庫中有同題之書而撰人之名只差一字（徐孝充／徐孝克）。純字形
             之異已入 jyk_triage 之 EXTRA 表歸一；此處所餘是避諱之改
             （王元感／王玄感）與真異人（何晏／何休）雜居，非逐條裁不可。
  稱篇不稱卷 著錄止言「二篇」而不言卷——篇多是一書之一篇，非獨立之書。
  標目解析誤 `head_form` 為 dyn／zi／shih 者，撰人欄多不可用
             （「漢淮南王劉（安）道訓」解成撰人「王劉安」）。
  缺字碼     kanripo 私用區碼 `&KR2066;` 未還原，人名不可用。
  批內重出   同題同撰而《經義考》兩見——建一條，兩處著錄並記於 indexed_by[]。
  題名過短   歸一後不足二字者不建。

**所記止於朱彝尊所有**：題、撰人之名、所引之志、卷、頁。

  · `period` 不繫——分流所用之時代界是統計之物（準確率 0.9646），不是
    據。定代須依所引之志與撰人本傳逐條為之（庫規「朝代不推，只取有據
    者」）。
  · `loss_status` 不繫——朱氏之判入 `indexed_by[].attested_status`，非本
    庫之判（四庫御製題已駁其「未見」之不可信）。
  · `role` 不繫——實測 691 條，著錄之文無一明言其役（「馬氏（融）周易注」
    只是姓名＋題，不言馬融是撰是注）。以題末之「注」「傳」推役是推，非據。
  · `entity_id` 不繫——《經義考》只給人名，繫人須另考（依《玉函山房》建
    work 之例）。
"""
import json, os, sys, hashlib, collections, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import nz, load_index

DATA = '.claude/known-issues/經義考待裁.json'
HOLD = '.claude/known-issues/經義考乙1待覈.json'
SRC, SRC_BID = '經義考', '1ev3bb43bv4lc'
STATUS = {'佚': 'lost', '存': 'extant', '未見': 'not_seen', '闕': 'partial'}
NOTE = ('此是朱彝尊所判，非本庫之判，故不改本記錄之 loss_status。'
        '四庫御製題論此書曰「所注闕佚未見者，今四庫所録往往其書尚存」'
        '——其判是十七世紀一人之見聞。「未見」尤非亡佚，是朱氏未見其書。')
AI_NOTE = (
    '本 work 據《經義考》（朱彝尊撰，欽定四庫全書文淵閣本，kanripo KR2n0011）'
    '新建——該書{lei}類著錄「{head}」，所引{cit}，而本庫先前無同題之 work。\n\n'
    '所記止於朱氏所有：題、撰人之名、所引之志、卷、頁。以下諸欄一概不繫，'
    '非漏，是無據：\n'
    '· `period`：《經義考》各類之內雖以撰人時代為序，然此序只堪分流（實測'
    '準確率 0.9646），不堪定代。定代須依所引之志與撰人本傳逐條為之。\n'
    '· `loss_status`：朱氏判本書為「{status}」，其判入 indexed_by[].'
    'attested_status，不作本庫之判。\n'
    '· `authors[].role`：著錄之文不言其役——「某氏（某）某經注」只是姓名'
    '加題，不言其人是撰是注。以題末之字推役是推，非據。\n'
    '· `authors[].entity_id`：《經義考》只給人名，繫人須另考。')


def b36(n, w=13):
    d = '0123456789abcdefghijklmnopqrstuvwxyz'
    s = ''
    while n:
        s = d[n % 36] + s
        n //= 36
    return s.rjust(w, '0')[-w:]


def mkid(seed, taken):
    for salt in range(64):
        h = hashlib.sha1(f'jyk-yi1:{seed}:{salt}'.encode()).hexdigest()
        i = '1ex' + b36(int(h[:16], 16), 10)
        if i not in taken:
            taken.add(i)
            return i
    raise RuntimeError('id 生不出：' + seed)


def shard(i):
    h = 0
    for c in i:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return '%x' % (h % 16)


# 括中之語若非校語而是人名，即標目未解淨——「南平王蕭（偉）周易幾義」剔括
# 後成《南平王蕭周易幾義》，是造一部不存在的書。校語必起於「或」「一」「舊」
# 或某志之名，故以此反判：短而不起於校語之詞者，是漏解之人名。
_JIAOYU = re.compile(r'或|一|舊|今|亦|新|唐|宋|隋|漢|晉|梁|陳|齊|周|七|釋文|通考|'
                     r'崇文|中興|國史|館閣|讀書|書錄|書録|陸|馬|晁|陳氏|宋史|本傳')


def name_in_paren(t):
    """括中夾人名而未解出者，回傳其語；無則 None"""
    for m in re.findall(r'（([^）]*)）', t or ''):
        if len(m) <= 3 and not _JIAOYU.match(m):
            return m
    return None


def clean_title(t):
    """剔朱氏校語括號。括中之語是校語不是異題，不入 additional_titles，
    原標目已全文存於 ai_note，不另立欄。"""
    return re.sub(r'（[^）]*）', '', t or '').strip()


CIT = ['漢志', '七略', '七畧', '别録', '別錄', '隋志', '唐志', '宋志', '七録',
       '七錄', '通志', '崇文總目', '中興書目', '書録解題', '讀書志', '文獻通考',
       '國史志', '館閣書目']


def main():
    apply = '--apply' in sys.argv
    works = load_index('works')
    taken = set(works)
    by_title = collections.defaultdict(list)
    for v in works.values():
        by_title[nz(v.get('title'))].append(v)

    D = json.load(open(DATA))
    Y = [d for d in D if d['tier'] == '乙1']

    dupe = collections.defaultdict(list)
    for d in Y:
        dupe[(nz(d.get('title')), nz(d.get('author')))].append(d)

    make, hold = [], []
    for key, ds in dupe.items():
        d = ds[0]
        g = []
        if '&KR' in d['head']:
            g.append('缺字碼')
        if d['head_form'] in ('dyn', 'zi', 'shih'):
            g.append('標目解析待覈')
        at = '；'.join(d['attest'] or [])
        if '篇' in at and '卷' not in at:
            g.append('稱篇不稱卷')
        if len(nz(clean_title(d.get('title')))) < 2:
            g.append('題名過短')
        _p = name_in_paren(d.get('title'))
        if _p:
            g.append(f'標目解析待覈（括中「{_p}」疑是人名）')
        ja = nz(d.get('author'))
        if ja:
            for w in by_title.get(nz(d.get('title')), []):
                wa = nz(w.get('author'))
                if wa and wa != ja and len(wa) == len(ja) \
                        and sum(x != y for x, y in zip(wa, ja)) == 1:
                    g.append(f'形訛近名（庫作「{w.get("author")}」{w["id"]}）')
                    break
        if g:
            for x in ds:
                hold.append({'gates': g, **{k: x[k] for k in
                             ('head', 'author', 'title', 'lei', 'juan', 'page', 'status', 'attest')}})
        else:
            make.append(ds)

    print(f'乙1 {len(Y)} 條，歸併批內重出後 {len(dupe)} 種；建 {len(make)}，待覈 {len(hold)}')
    print(collections.Counter(h['gates'][0].split('（')[0] for h in hold))
    print('其中無撰人者', sum(1 for ds in make if not ds[0].get('author')))
    if not apply:
        print('（乾跑。加 --apply 方寫檔）')
        return

    shards = {s: json.load(open(f'index/works/{s}.json')) for s in '0123456789abcdef'}
    n = 0
    for ds in make:
        d = ds[0]
        title = clean_title(d['title'])
        wid = mkid(f"{d['juan']}|{d['page']}|{d['head']}", taken)
        path = f'Work/{wid[0]}/{wid[1]}/{wid[2]}/{wid}-{title}.json'
        cit = '、'.join(c for c in CIT if c in ''.join(d['attest'] or [])) or '無前代志'
        rec = {'schema_version': 1, 'type': 'work', 'title': title, 'id': wid}
        if d.get('author'):
            rec['authors'] = [{'name': d['author'], 'role': None}]
        rec['ai_note'] = AI_NOTE.format(lei=d['lei'], head=d['head'], cit=cit,
                                        status=d['status'])
        rec['indexed_by'] = [
            {'source': SRC, 'source_bid': SRC_BID,
             'title_info': f"《{x['title']}》" + (f"（{x['author']}）" if x.get('author') else ''),
             'summary': '；'.join(x['attest']) if x['attest'] else '',
             'section': x['lei'], 'juan': x['juan'], 'page': x['page'],
             'attested_status': STATUS[x['status']],
             'attested_status_raw': x['status'],
             'attested_status_note': NOTE}
            for x in ds]

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
            f.write('\n')

        e = {'id': wid, 'title': title, 'type': 'Work', 'path': path}
        if d.get('author'):
            e['author'] = d['author']
        shards[shard(wid)][wid] = e
        for x in ds:
            x['created_work'] = wid
        n += 1

    for s, obj in shards.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8') as f:
            json.dump(dict(sorted(obj.items())), f, ensure_ascii=False, indent=2)
            f.write('\n')
    json.dump(D, open(DATA, 'w'), ensure_ascii=False, indent=1)
    json.dump(hold, open(HOLD, 'w'), ensure_ascii=False, indent=1)
    print('已建', n)


if __name__ == '__main__':
    main()
