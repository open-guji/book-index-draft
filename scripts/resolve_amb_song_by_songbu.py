#!/usr/bin/env python3
"""A4：歧義「宋」之一路——見《宋史藝文志補》者判趙宋。

撰人 dynasty 作「宋」而歧（劉宋｜趙宋）者，庫中長期留 null：
2026-08-06〈period未決〉曾擬「無宋前志⇒非劉宋」之判，以庫中明標劉宋之
八十五條驗之而**不成立**（九成劉宋之書只見於晚出目錄），遂棄之。

本判準不同，是**雙重證據**且可自驗：

  撰人 dynasty 作「宋」（歧） ＋ 其書見於《宋史藝文志補》（斷代宋志）

《宋史藝文志補》乃清人補宋史藝文志，專收宋人著述——劉宋之書無由入之。
以庫中資料自驗（本腳本 --verify 可覆算）：

  該志所著錄 722 條，已定 period 555 條中 song 533（96.0%）；
  其撰人 dynasty 明標者：南宋 343、宋 170、北宋 30（趙宋合計 543），
  而「南朝宋」僅 2 條——且那 2 條本已明標，不在歧義之列。

**兼繫早志者不判**（隋志、兩唐志、漢志、崇文總目之屬）：一書既見宋志補
又見宋前之志，則其為劉宋之書尚有可能，此時雙重證據不成立。
實測本輪 119 條無一兼繫早志。

用法：python3 scripts/resolve_amb_song_by_songbu.py [--verify] [--apply]
"""
import json, glob, os, re, sys, datetime, collections

EARLY = {'隋書經籍志', '舊唐書經籍志', '新唐書經籍志', '新唐書藝文志', '漢書藝文志',
         '後漢藝文志', '三國藝文志', '補晋書藝文志', '崇文總目',
         '隋書經籍志考證', '漢藝文志考證'}
SRC = '宋史藝文志補'


def verify():
    pc, dyc, tot = collections.Counter(), collections.Counter(), 0
    for p in glob.glob('Work/*/*/*/*.json'):
        if not re.match(r'^1[a-z0-9]{12}-', os.path.basename(p)):
            continue
        d = json.load(open(p, encoding='utf-8'))
        if d.get('type') != 'work' or d.get('_promoted_to'):
            continue
        if SRC not in {e.get('source') for e in (d.get('indexed_by') or [])}:
            continue
        tot += 1
        if d.get('period'):
            pc[d['period']] += 1
        for a in (d.get('authors') or []):
            if a.get('dynasty'):
                dyc[a['dynasty']] += 1
    n = sum(pc.values())
    print(f'《{SRC}》所著錄 {tot} 條，已定 period {n}')
    for k, v in pc.most_common():
        print(f'  {k}: {v} ({v/n:.1%})')
    print(' 撰人 dynasty:', dyc.most_common(8))
    return pc.most_common(1)[0][1] / n if n else 0


def main():
    if '--verify' in sys.argv:
        r = verify()
        print(f'song 佔比 {r:.1%}　{"≥90%，斷代志成立" if r >= 0.9 else "未達 90%，判準不成立"}')
        if '--apply' not in sys.argv:
            return
    apply_ = '--apply' in sys.argv

    picks, skipped = [], []
    for p in glob.glob('Work/*/*/*/*.json'):
        if not re.match(r'^1[a-z0-9]{12}-', os.path.basename(p)):
            continue
        d = json.load(open(p, encoding='utf-8'))
        if d.get('type') != 'work' or d.get('_promoted_to') or d.get('period'):
            continue
        auth = [a for a in (d.get('authors') or [])
                if isinstance(a, dict) and a.get('role') not in
                {'舊題撰', '託名', '舊題', '偽託'}]
        dys = {a.get('dynasty') for a in auth if a.get('dynasty')}
        if dys != {'宋'}:
            continue
        srcs = {e.get('source') for e in (d.get('indexed_by') or []) if e.get('source')}
        if SRC not in srcs:
            continue
        if srcs & EARLY:
            skipped.append({'id': d['id'], 'title': d.get('title'),
                            '故': '兼繫宋前之志，雙重證據不成立',
                            '志': sorted(srcs & EARLY)})
            continue
        picks.append((p, d, sorted(srcs)))

    print(f'可判趙宋 {len(picks)}　兼繫早志而不判 {len(skipped)}')
    if not apply_:
        print('（dry-run，加 --apply 方寫入）')
        return

    IW = {}
    for s in '0123456789abcdef':
        IW[s] = json.load(open(f'index/works/{s}.json'))

    def shard(i):
        h = 0
        for c in i:
            h = ((h * 31) + ord(c)) & 0xFFFFFFFF
        return '%x' % (h % 16)

    for p, d, srcs in picks:
        d['period'] = 'song'
        d['period_basis'] = (
            f'撰人朝代作「宋」，歧（劉宋｜趙宋）；而其書見《{SRC}》——'
            f'清人補宋史藝文志，專收宋人著述，劉宋之書無由入之。'
            f'以庫中自驗：該志已定 period 者 96.0% 為 song，'
            f'其撰人明標「南朝宋」者僅 2 條而趙宋 543 條。'
            f'本條不兼繫宋前之志（所繫：{"、".join(srcs)}），雙重證據成立，故判趙宋。'
            f'（2026-08-24 A4）')
        d['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
        e = IW[shard(d['id'])].get(d['id'])
        if e is not None:
            e['period'] = 'song'
    for s, obj in IW.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    if skipped:
        with open('.claude/known-issues/A4-歧義宋-兼繫早志未判.json', 'w',
                  encoding='utf-8') as f:
            json.dump({'_說明': '撰人作「宋」而見宋史藝文志補，然兼繫宋前之志者——'
                                '劉宋之可能未除，不判。', '條目': skipped},
                      f, ensure_ascii=False, indent=2)
            f.write('\n')
    print(f'已寫入 {len(picks)}')


if __name__ == '__main__':
    main()
