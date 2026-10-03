#!/usr/bin/env python3
"""撤銷「清史稿輯佚條目」以斷代志誤判之 qing。

SCHEMA〈period〉判準三之例外：《清史稿·藝文志》各部類下之「輯佚」子目著錄
清人所輯之本，其原書可極古，故該子目不入斷代之列。判別之法：ai_note 載
「清史稿藝文志〈某部某類〉輯佚條目」者即是。

該例外 2026-08-21 增訂時撤了 105 條，然全庫尚有 121 條漏網（ai_note 明載
輯佚條目，period_basis 仍作「所著錄之志唯一且為斷代志……清史稿藝文志」）。
本腳本撤其 period 與 period_basis，留 null，出清單。

不動者：period=qing 而 basis 為 authors[0].dynasty「清」者（6 條）——
那是實有清人撰者，非本漏洞。

用法：python3 scripts/c1_revoke_qing_jiyi.py [--apply]
"""
import json, glob, sys, datetime

TODAY = '2026-08-22'


def main():
    apply_ = '--apply' in sys.argv
    hits = []
    for p in glob.glob('Work/*/*/*/*.json'):
        d = json.load(open(p, encoding='utf-8'))
        if d.get('_promoted_to') or d.get('period') != 'qing':
            continue
        if '輯佚條目' not in (d.get('ai_note') or ''):
            continue
        if '斷代志' not in (d.get('period_basis') or ''):
            continue
        hits.append((p, d))
    print('待撤', len(hits))
    if not apply_:
        for p, d in hits[:10]:
            print('  ', d['id'], d.get('title'))
        print('（dry-run，加 --apply 方寫入）')
        return

    IW = {s: json.load(open(f'index/works/{s}.json')) for s in '0123456789abcdef'}

    def shard(i):
        h = 0
        for c in i:
            h = ((h * 31) + ord(c)) & 0xFFFFFFFF
        return '%x' % (h % 16)

    listed = []
    for p, d in hits:
        listed.append({'id': d['id'], 'title': d.get('title'), 'path': p,
                       '原period': 'qing'})
        d.pop('period', None)
        d.pop('period_basis', None)
        d['ai_note'] = (d.get('ai_note') or '').rstrip() + (
            f'\n\n{TODAY} C1：原以「所著錄之志唯一且為斷代志」判 qing，'
            '然本條係清史稿藝文志之輯佚條目，該子目著錄清人所輯之本而原書可極古，'
            '依 SCHEMA〈period〉判準三之例外不入斷代之列，故撤此判，留 null。')
        d['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write('\n')
        e = IW[shard(d['id'])].get(d['id'])
        if e is not None:
            e.pop('period', None)
    for s, obj in IW.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write('\n')
    with open('.claude/known-issues/清史稿輯佚誤判qing_已撤.json', 'w', encoding='utf-8') as f:
        json.dump({'_說明': f'{TODAY} C1 撤銷之 {len(listed)} 條。皆清史稿藝文志輯佚條目，'
                            '原以斷代志判 qing 無據。其書多可由題名所含撰人定代'
                            '（王粲英雄記→東漢、張璠後漢記→西晉、王肅國語章句→三國魏），'
                            '然本庫 authors 欄闕，補撰人非 C 車道之權，交 A／B 車道。',
                   '條目': listed}, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('已撤', len(listed))


if __name__ == '__main__':
    main()
