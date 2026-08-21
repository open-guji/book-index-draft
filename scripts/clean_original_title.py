#!/usr/bin/env python3
"""`original_title` 清雜訊。

本欄之義：**本條所本之書題**——去撰人、去役字之後所餘者。
《呂氏春秋高誘注》→「呂氏春秋」，《周易論范氏撰》→「周易論」。

庫中三類非此義者：
1. 志書原文殘片——匯入時把著錄原文（「又十二卷王肅注。」「橘林集》十六卷、《後集」）
   落入本欄
2. 與 title 全同（或只多一對書名號）——無別識之用
3. 通名之尾——「文集」「詩集」「語錄」之屬，是撰人字首式剝除後所餘之通名，
   非書題，不能識別任何一書

用法：python scripts/clean_original_title.py [--apply]
"""
import json, glob, sys, collections

APPLY = '--apply' in sys.argv
GENERIC = {'文集', '詩集', '語錄', '别集', '別集', '詩鈔', '集', '奏議',
           '文鈔', '詩', '詞', '鈔', '文', '續集', '外集', '後集'}


def kind(t, o):
    if o.startswith('又') or o.endswith('。') or ('》' in o and '卷' in o):
        return '志書原文殘片'
    if o.strip('《》') == t or o == t:
        return '與 title 全同'
    if o in GENERIC:
        return '通名之尾'
    return None


def main():
    c = collections.Counter()
    for root in ('/workspace/book-index-draft', '/workspace/book-index'):
        for f in glob.glob(f'{root}/Work/*/*/*/*.json'):
            try:
                d = json.load(open(f, encoding='utf-8'))
            except Exception:
                continue
            if d.get('_promoted_to') or not d.get('original_title'):
                continue
            t, o = (d.get('title') or '').strip(), d['original_title'].strip()
            k = kind(t, o)
            if not k:
                continue
            c[k] += 1
            d.pop('original_title', None)
            d['ai_note'] = ((d.get('ai_note') or '') + ('\n\n' if d.get('ai_note') else '')
                            + f'2026-08-21 original_title 清雜訊：撤去「{o}」——{k}，'
                              f'非本條所本之書題。')
            if APPLY:
                with open(f, 'w', encoding='utf-8', newline='\n') as fh:
                    fh.write(json.dumps(d, ensure_ascii=False, indent=2))
    print('撤去 original_title：' + '，'.join(f'{k} {v}' for k, v in c.most_common())
          + f'　合計 {sum(c.values())}' + ('' if APPLY else '　(dry-run)'))


if __name__ == '__main__':
    main()
