#!/usr/bin/env python3
"""為本輪新繫之《玉函山房輯佚書》諸節補輯佚檔（著錄層）

`chk.py`「輯佚叢書整理本 待辦（已繫而無輯佚檔）」由 1 增為 7，是本輪新繫六節
所致——目錄既言馬氏輯之，該 work 當有輯佚檔。依《春秋傳駮》一輪之例補立，
`coverage.level: catalog`，`fragments_attested: null`（未知，非零），
`fragments: []`；所輯條數與佚文出處目錄不載，俟輯本正文。
"""
import json, glob, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import load_index

YH = '1evjr68pzxog0'
DIR = f'Work/1/e/v/{YH}/collated_edition'


def main():
    apply = '--apply' in sys.argv
    works = load_index('works')
    need = []
    for f in glob.glob(DIR + '/*.json'):
        if 'index' in f:
            continue
        cd = json.load(open(f))
        for i, s in enumerate(cd['sections']):
            w = s.get('work_id')
            if not isinstance(w, str) or w not in works:
                continue
            if glob.glob(f'Work/*/*/*/{w}/fragments/*.json'):
                continue
            need.append((f.split('/')[-1], i, s, works[w]))
    print('已繫而無輯佚檔者', len(need))
    for fn, i, s, w in need:
        print(f"  《{w['title']}》{w.get('author')} {w['id']}  ← {fn}#{i} {s.get('book_title')}")
    if not apply:
        print('（乾跑。加 --apply 方寫檔）')
        return
    for fn, i, s, w in need:
        wid = w['id']
        d = f'Work/{wid[0]}/{wid[1]}/{wid[2]}/{wid}/fragments'
        os.makedirs(d, exist_ok=True)
        rec = {
            'work_id': wid, 'title': w['title'], 'type': 'fragments',
            'schema_version': 2,
            'coverage': {'level': 'catalog',
                         'note': '本檔之據為《玉函山房輯佚書》之目錄，非其正文。'
                                 '馬氏輯得幾條、佚文見於何書，目錄不載，故 '
                                 'fragments_attested 為 null——是未知，不是零。',
                         'fragments_attested': None, 'fragments_recorded': 0,
                         'text_available': False},
            'loss_status': 'partially_extant',
            'statement': f'《玉函山房輯佚書》{s.get("lei") or ""}著錄'
                         f'「{s.get("book_title")}{s.get("measure") or ""}卷」'
                         + (f'，撰人{s["author"]}' if s.get('author') else '')
                         + '。馬氏既為之輯，則其書清時已佚。',
            'provenance': 'secondary',
            'provenance_note': '據目錄立，未覆核輯本正文。',
            'based_on': [{'source': '玉函山房輯佚書', 'source_bid': YH,
                          'field': 'collated_edition'}],
            'collectors': [{'collector': '馬國翰', 'work': '玉函山房輯佚書',
                            'work_id': YH,
                            'sections': [{'file': fn, 'index': i,
                                          'title': s.get('title'),
                                          'part': s.get('part'),
                                          'juan_no': s.get('juan_no'),
                                          'lei': s.get('lei')}],
                            'count': None, 'count_unit': None,
                            'basis': '玉函山房輯佚書目錄（光緒九年長沙嫏嬛館補校刊本）著錄本書',
                            'note': '所輯條數、佚文出處目錄不載，須俟輯本正文。'}],
            'fragments': [],
            'ai_note': '本檔據《玉函山房輯佚書》目錄補立——該叢書之整理本已繫本書，'
                       '而本書先前無輯佚檔。繫連之由見 collated_edition 該 section 之 '
                       'link_basis，覆核時當先驗其是否果為一書。',
            'schema_ref': 'SCHEMA.md#輯佚檔fragments'}
        with open(f'{d}/{w["title"]}.json', 'w', encoding='utf-8') as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
    print('已補', len(need))


if __name__ == '__main__':
    main()
