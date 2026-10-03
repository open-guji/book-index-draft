#!/usr/bin/env python3
"""隋志注亡書批次之 period_upper 收緊：sui-tang → nanbeichao。

此批 work 皆自《隋書經籍志》注中之亡書新建（ai_note 記其建檔之由）——
隋志之例，正文著隋時見存之書，其注記「梁有某書幾卷，某人撰，亡」：
**梁時尚存**（本阮孝緒《七錄》所錄），唐初已亡。故其時代上限不是隋志
成書之 sui-tang，而是梁之 nanbeichao——原標據隋志正文一律作 sui-tang，
白鬆了一檔，今收緊。

只動：無 period、period_upper 為 sui-tang、ai_note 明記「注中之亡書」
且含「梁有」者。已有 period 者（後判為 nanbeichao/jin 等）不動。

用法：python3 scripts/tighten_suizhi_note_upper.py [--apply]
"""
import json, glob, sys

APPLY = '--apply' in sys.argv


def main():
    n = 0
    skipped = []
    for f in glob.glob('Work/*/*/*/*.json'):
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        if d.get('_promoted_to') or d.get('promoted_to'):
            continue
        note = d.get('ai_note') or ''
        if '注中之亡書' not in note or '隋書經籍志' not in note:
            continue
        if d.get('period'):
            continue
        if d.get('period_upper') != 'sui-tang':
            if d.get('period_upper') not in ('nanbeichao', 'jin'):
                skipped.append((d['id'], d.get('title'), d.get('period_upper')))
            continue
        if '梁有' not in note:
            skipped.append((d['id'], d.get('title'), '注無「梁有」'))
            continue
        d['period_upper'] = 'nanbeichao'
        d['period_upper_basis'] = (
            'catalog_bound：本條出隋志注「梁有……亡」——梁時尚存'
            '（本阮孝緒《七錄》所錄），故不晚於 nanbeichao'
            '（2026-08-24 收緊；原據隋志成書之年作 sui-tang，鬆了一檔）')
        n += 1
        if APPLY:
            with open(f, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
    print(f'收緊 sui-tang → nanbeichao：{n} 條' + ('' if APPLY else '  (dry-run)'))
    if skipped:
        print(f'跳過（上限非 sui-tang/nanbeichao/jin 或注無「梁有」）：{len(skipped)}')
        for s in skipped[:10]:
            print('  ', s)


if __name__ == '__main__':
    main()
