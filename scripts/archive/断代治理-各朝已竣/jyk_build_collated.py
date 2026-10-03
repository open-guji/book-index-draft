#!/usr/bin/env python3
"""立《經義考》整理本：全文入 collated_edition，並繫其所著錄之 work

原文重取與解析見 `jyk_fetch_source.py`，此處只管落地。

**分檔以類**——《經義考》三百卷分二十六類（御注、易、書、詩、周禮、儀禮、
禮記、禮、通禮、樂、春秋、論語、孝經、孟子、爾雅、羣經、四書、逸經、毖緯、
擬經、承師、宣講、刋石、書壁、鏤板、著錄、通說、家學、自述），類目取自各卷
卷首縮排三格之行，是原書自標，非本輪所擬。

**書與非書之界**依原書體例：有存佚之判者為書（`type: 书`），無者為論（
`type: 论`）——承師記傳授之事、著錄記官修之緣起、通說錄諸家之言，皆非書目。
此判準出自書之體例，可自驗。

**`work_id` 之繫**有二路：一是本輪逐條所裁（`經義考待裁.json` 之
`attached_to`／`created_work`），二是自庫中回推——凡 work 之 `indexed_by[]`
已有經義考一源者，以其 `page` 與 `title_info` 之題比對原文標目，一頁一中者
取之，一頁數中者不取（頁次不足以定條）。
"""
import json, glob, os, re, sys, collections
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import nz

SRC = json.load(open('.claude/known-issues/經義考論斷.json'))
WID = '1ev3bb43bv4lc'
DIR = f'Work/{WID[0]}/{WID[1]}/{WID[2]}/{WID}/collated_edition'
STAMP = datetime.now().astimezone().replace(microsecond=0).isoformat()


def build_link():
    by_page = collections.defaultdict(list)
    for x in SRC:
        by_page[x['page']].append(x)
    link = {}
    for d in json.load(open('.claude/known-issues/經義考待裁.json')):
        w = d.get('attached_to') or d.get('created_work')
        if w:
            link[(d['page'], d['head'])] = w
    n0 = len(link)
    amb = 0
    for p in glob.glob('Work/*/*/*/*.json'):
        d = json.load(open(p))
        for e in (d.get('indexed_by') or []):
            if e.get('source') != '經義考' or not e.get('page'):
                continue
            m = re.match(r'《(.+?)》', e.get('title_info') or '')
            if not m:
                continue
            t = nz(m.group(1))
            cand = [x for x in by_page.get(e['page'], []) if t and t in nz(x['head'])]
            if len(cand) == 1:
                k = (e['page'], cand[0]['head'])
                if k not in link:
                    link[k] = d['id']
                elif link[k] != d['id']:
                    amb += 1
            elif len(cand) > 1:
                amb += 1
    print(f'繫連：本輪所裁 {n0}，自庫回推再得 {len(link) - n0}，歧義不取 {amb}')
    return link


def main():
    apply = '--apply' in sys.argv
    link = build_link()
    idx = json.load(open('index/works/' + '0123456789abcdef'[0] + '.json'))  # 佔位，下面重讀
    allw = set()
    for s in '0123456789abcdef':
        allw |= set(json.load(open(f'index/works/{s}.json')))

    groups = collections.OrderedDict()
    n_book = n_link = n_dang = 0
    for x in SRC:
        lei = x['lei'] or '未分'
        g = groups.setdefault(lei, [])
        is_book = bool(x['cun'])
        parts = [x['head']]
        if x['zhu']:
            parts.append(x['zhu'])
        if x['cun']:
            parts.append(x['cun'])
        if x['lun']:
            parts.append(x['lun'])
        sec = {'title': x['head'], 'level': 3 if is_book else 4,
               'type': 'book' if is_book else 'comment',   # 舊值 '书'／'论'
               'content': '\n'.join(parts), 'juan': x['juan'], 'page': x['page']}
        if is_book:
            n_book += 1
            w = link.get((x['page'], x['head']))
            if w:
                if w in allw:
                    sec['work_id'] = w
                    n_link += 1
                else:
                    n_dang += 1
        g.append(sec)

    print(f'類 {len(groups)}；條 {len(SRC)}（書 {n_book}，論 {len(SRC) - n_book}）；'
          f'繫 work {n_link}，標的已不在庫而不繫 {n_dang}')
    for k, v in groups.items():
        print(f'   {k:5s} {len(v):5d}')
    if not apply:
        print('（乾跑。加 --apply 方寫檔）')
        return

    os.makedirs(DIR + '/text', exist_ok=True)
    files = []
    for lei, secs in groups.items():
        fn = f'{lei}.json'
        files.append(fn)
        with open(f'{DIR}/{fn}', 'w', encoding='utf-8') as f:
            json.dump({'title': lei, 'sections': secs, 'updated_at': STAMP},
                      f, ensure_ascii=False, indent=2)
            f.write('\n')
        with open(f'{DIR}/text/{lei}.md', 'w', encoding='utf-8') as f:
            f.write(f'# {lei}\n\n')
            for s in secs:
                f.write(f'## {s["title"]}\n\n<{s["page"]}>\n\n{s["content"]}\n\n')
    with open(f'{DIR}/collated_edition_index.json', 'w', encoding='utf-8') as f:
        json.dump({'work_id': WID, 'total_entries': len(SRC),
                   'matched_entries': n_link,
                   'juan_files': files,
                   'juan_groups': [{'label': k, 'files': [f'{k}.json']} for k in groups],
                   'text_quality': {
                       'grade': 'source',
                       'source_note': 'kanripo KR2n0011（文淵閣四庫全書本），原文照錄未加標點。'
                                      '縮排即層：0 條目首行／2 著錄／3 存佚／1 論斷／4 按語；'
                                      '卷首縮排三格者是本卷之類。重取見 scripts/jyk_fetch_source.py，'
                                      '落地見 scripts/jyk_build_collated.py。'}},
                  f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('已寫', DIR)


if __name__ == '__main__':
    main()
