#!/usr/bin/env python3
"""注本條補 `original_title`——本條所本之書題。

法：自題名末剝去役字（注／疏／章句／集解…）與撰人之名，所餘即所本之題。
**須庫中實有同題之 Work 方採**——剝出之題若庫中無主，多是剝錯，寧缺勿誤。

用法：python scripts/backfill_original_title.py [period ...] [--apply]
"""
import json, glob, re, sys, os, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from magnet_lib import norm  # noqa: E402

# 倉根自本檔位置推得，不寫死容器路徑——舊值 /workspace/... 在別的容器
# 佈局下寫成，移倉之後 glob 掃不到任何檔而**靜默地什麼都不做**。
# 2026-08-24 已為此漏掉 4,121 條 period_upper，見 plans/全庫普查 附二。
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROD = os.path.join(os.path.dirname(_ROOT), 'book-index')

APPLY = '--apply' in sys.argv
PERIODS = [a for a in sys.argv[1:] if not a.startswith('--')] or ['qin-han']

# 役字：附於題名之末者。長者先試，免「集解」被「解」截斷
ROLE = ['詁訓傳', '訓詁傳', '章句', '集解', '解詁', '義疏', '正義', '注疏',
        '音義', '集注', '集釋', '釋義', '訓詁', '詁訓', '講疏', '口義',
        '注解', '傳注',
        '注', '疏', '箋', '解', '音', '訓', '釋', '傳', '說', '義', '考', '評']


# 「某氏」之尾：短者先試。正則之最左匹配會把「傳徐氏」當一姓，故不用 search
def shi_tails(s):
    return [s[-k:] for k in (2, 3) if len(s) > k and s.endswith('氏')]


def strip_tail(title, names, titles):
    """自題末剝役字與撰人，返所餘之題。

    役字只剝**一層**——《水經注箋》是箋《水經注》，非箋《水經》，
    層層剝盡則所本之書錯認一代。撰人與「某氏」則可續剝，
    且每剝一步須庫中實有同題者方進，免剝出無主之殘題。
    """
    s = title
    for r in ROLE:                       # 長者先試，「集解」不被「解」截
        if s.endswith(r) and len(s) > len(r) + 1:
            s = s[:-len(r)]
            break
    changed = True
    while changed:
        changed = False
        for n in list(names) + shi_tails(s):
            if n and s.endswith(n) and len(s) > len(n) + 1:
                cut = s[:-len(n)]
                if norm(cut) in titles:  # 剝到有主者方止，否則不剝
                    s, changed = cut, True
                    break
    return s


def main():
    W = []
    titles = set()
    for root in (_ROOT, _PROD):
        for f in glob.glob(f'{root}/Work/*/*/*/*.json'):
            try:
                d = json.load(open(f, encoding='utf-8'))
            except Exception:
                continue
            if d.get('_promoted_to'):
                continue
            titles.add(norm((d.get('title') or '').strip()))
            W.append((d, f))

    n = 0
    skipped = collections.Counter()
    for d, f in W:
        if d.get('original_title') or d.get('period') not in PERIODS:
            continue
        t = (d.get('title') or '').strip()
        names = [a.get('name') for a in (d.get('authors') or []) if a.get('name')]
        base = strip_tail(t, names, titles).strip()
        if base == t or len(base) < 2:
            skipped['剝不出'] += 1
            continue
        if norm(base) not in titles:
            skipped['所剝之題庫中無主'] += 1
            continue
        d['original_title'] = base
        d['ai_note'] = ((d.get('ai_note') or '') + ('\n\n' if d.get('ai_note') else '')
                        + f'2026-08-21 補 original_title「{base}」——自題名末剝去役字'
                          f'與撰人所得，庫中實有同題之 Work，非臆造。')
        n += 1
        if n <= 25:
            print(f'  {t!r} → {base!r}')
        if APPLY:
            with open(f, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(json.dumps(d, ensure_ascii=False, indent=2))
    print(f'補 original_title {n} 條；未採：'
          + '，'.join(f'{k} {v}' for k, v in skipped.most_common())
          + ('' if APPLY else '　(dry-run)'))


if __name__ == '__main__':
    main()
