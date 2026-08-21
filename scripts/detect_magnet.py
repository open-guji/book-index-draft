#!/usr/bin/env python3
"""磁鐵偵測：著錄節所點明之撰人與本條 authors 相牴者。

「一條挂多節而題名寫法多」不是磁鐵之證——志書各記其題本是常態
（《論衡》十節十題，皆是一書）。真磁鐵之證是**撰人相牴**。
"""
import json, glob, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from magnet_lib import node_conflicts, is_commentary


def run(period):
    rows = []
    for root in ('/workspace/book-index-draft', '/workspace/book-index'):
        for f in glob.glob(f'{root}/Work/*/*/*/*.json'):
            try:
                d = json.load(open(f, encoding='utf-8'))
            except Exception:
                continue
            if d.get('_promoted_to') or d.get('period') != period:
                continue
            auth = {a.get('name') for a in (d.get('authors') or []) if a.get('name')}
            if not auth:
                continue
            title = d.get('title') or ''
            alts = [x.get('title') if isinstance(x, dict) else x
                    for x in (d.get('additional_titles') or [])]
            alts = [a for a in alts if a]
            if d.get('original_title'):
                alts.append(d['original_title'])
            comm = is_commentary(title, d.get('original_title'))
            nodes = [r for r in (d.get('indexed_by') or []) if not r.get('misattached')]
            if len(nodes) < 2:
                continue
            bad = []
            for i, r in enumerate(nodes):
                # 著錄語或在 title_info，或在 summary（「《吳越春秋》十卷」＋
                # 「…皇甫遵撰」）。summary 過長者是考證之文，其中人名多為旁徵，
                # 不可作本條撰人論，故限四十字。
                texts = [r.get('title_info') or '']
                sm = (r.get('summary') or '').strip()
                if sm and sm != texts[0] and len(sm) <= 40:
                    texts.append(sm)
                ns = None
                for tx in texts:
                    ns = node_conflicts(tx, title, auth, alts, comm)
                    if ns:
                        break
                if not ns:
                    continue
                bad.append({'i': i, 'names': sorted(ns), 'source': r.get('source'),
                            'title_info': r.get('title_info'),
                            'summary': (r.get('summary') or '')[:80]})
            if bad:
                rows.append({'id': d['id'], 'title': title, 'authors': sorted(auth),
                             'n_nodes': len(nodes), 'n_bad': len(bad), 'conflicts': bad,
                             'repo': 'production' if '/book-index/' in f else 'draft',
                             'file': f})
    rows.sort(key=lambda r: -r['n_bad'])
    return rows


if __name__ == '__main__':
    p = sys.argv[1] if len(sys.argv) > 1 else 'qin-han'
    rows = run(p)
    print(f'{p}：撰人相牴之條 {len(rows)}，涉節 {sum(r["n_bad"] for r in rows)}')
    json.dump(rows, open(f'.claude/known-issues/磁鐵撰人相牴_{p}.json', 'w'),
              ensure_ascii=False, indent=2)
    for r in rows[:30]:
        print(f"\n◆ {r['title']}　{r['id']}　authors={r['authors']}　{r['n_bad']}/{r['n_nodes']}")
        for c in r['conflicts'][:4]:
            print(f"    {c['source']}：{c['title_info']}　→ {c['names']}")
