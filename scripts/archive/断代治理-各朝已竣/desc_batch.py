#!/usr/bin/env python3
"""缺描述之條：出料（dump）與回填（apply）。

出料：python scripts/desc_batch.py dump <period> <批號> [每批數]
回填：python scripts/desc_batch.py apply <料檔.json>
    料檔為 {work_id: {"text": "...", "sources": [...]}}
"""
import json, glob, sys

SIZE = 50


def collect(period):
    rows = []
    for root in ('/workspace/book-index-draft', '/workspace/book-index'):
        for f in glob.glob(f'{root}/Work/*/*/*/*.json'):
            try:
                d = json.load(open(f, encoding='utf-8'))
            except Exception:
                continue
            if d.get('_promoted_to') or d.get('period') != period:
                continue
            x = d.get('description')
            if (x or {}).get('text') if isinstance(x, dict) else x:
                continue
            ns = [r for r in (d.get('indexed_by') or [])
                  if not r.get('misattached') and len(r.get('summary') or '') >= 60]
            if ns:
                rows.append((d, f, ns))
    rows.sort(key=lambda r: r[0]['id'])
    return rows


def dump(period, batch, size=SIZE):
    rows = collect(period)
    lo, hi = batch * size, (batch + 1) * size
    print(f'# {period} 缺描述而有實文者 {len(rows)} 條；本批 [{lo}:{hi}]')
    for d, f, ns in rows[lo:hi]:
        au = '、'.join(f"{a.get('name')}（{a.get('role') or ''}）"
                       for a in d.get('authors') or []) or '未著'
        print(f"\n=== {d['id']}｜《{d.get('title')}》｜撰人：{au}"
              f"｜卷：{d.get('measure_info') or ''}｜存佚：{d.get('loss_status') or ''}")
        for r in ns[:3]:
            print(f"[{r.get('source')}] {(r.get('summary') or '')[:600]}")


def apply(path):
    data = json.load(open(path, encoding='utf-8'))
    idx = {}
    for root in ('/workspace/book-index-draft', '/workspace/book-index'):
        for f in glob.glob(f'{root}/Work/*/*/*/*.json'):
            try:
                d = json.load(open(f, encoding='utf-8'))
            except Exception:
                continue
            if d['id'] in data:
                idx[d['id']] = (d, f)
    n = 0
    for wid, v in data.items():
        if wid not in idx:
            print('  ！查無此條：', wid)
            continue
        d, f = idx[wid]
        d['description'] = {'text': v['text'], 'sources': v.get('sources') or []}
        d['ai_note'] = ((d.get('ai_note') or '') + ('\n\n' if d.get('ai_note') else '')
                        + '2026-08-21 秦漢段補描述：據本條所繫著錄之考證文撮述，'
                          '所出之志已記於 description.sources。')
        with open(f, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(json.dumps(d, ensure_ascii=False, indent=2))
        n += 1
    print(f'回填 {n} 條')


if __name__ == '__main__':
    if sys.argv[1] == 'dump':
        dump(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else SIZE)
    else:
        apply(sys.argv[2])
