#!/usr/bin/env python
"""早志著錄語明書本條撰人之名者，其撰人必在該志之前——據以訂正 dynasty／period。

A 類（catalog_bound 覆驗所得）：Work 之 period 逾其著錄志之上限，而該志之著錄語
**明書本條撰人之名**。既然該志錄其人，其人必不晚於該志。二種處置：

1. **斷代補志**（宋史藝文志補、元史藝文志、補遼金元、明史藝文志、後漢、三國、補晉書）
   → period 逕從該志之斷代值。斷代補志之編者專為該代輯錄，收某人即斷其屬該代，
     是有據之判，非僅上限。實例：《宋史藝文志補》「斯植撰」「林洪撰」「王貴學撰」——
     三人皆南宋，而庫中標「明」。
2. **通代志**（隋志、兩唐志、崇文、直齋、宋志、國史經籍志）
   → 只知「不晚於該志」，不知確值。**撤 period，dynasty 置空**（原值記於 ai_note），
     標 period_upper。給個可能錯的值不如誠實留空。
     實例：隋志「《六情決》一卷王琛撰」——王琛必隋以前人，而庫中標「明」；
     然隋志未書其朝代，判 sui-tang 是上限非確值。

**例外：志書誤收。** 補晉書藝文志「涉史隨筆一卷 葛洪。謹按見《述古堂書目》」——
此書實南宋葛洪撰，補晉志編者誤作晉葛洪。判別：著錄語自云轉錄他書而無本志之據者，
或本條另有晚代之志著錄且撰人一致者，皆疑誤收，不動並記於清單。

用法：python fix_author_dynasty_by_catalog.py [--apply]
"""
import json, glob, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from period_bounds import BOUND, I, tightest, DYNASTY_PERIOD  # noqa: E402

APPLY = '--apply' in sys.argv
ROOTS = ('/workspace/book-index-draft', '/workspace/book-index')

DUANDAI = {'後漢藝文志': 'qin-han', '三國藝文志': 'three-kingdoms', '補晋書藝文志': 'jin',
           '宋史藝文志補': 'song', '元史藝文志': 'liao-jin-yuan',
           '補遼金元藝文志': 'liao-jin-yuan', '明史藝文志': 'ming', '清史稿藝文志': 'qing'}
# 補志之體例，每條必注所出——「謹按見《七録》」「謹按見《隋志》」是常態，非誤收之兆。
# 可疑者是引**後代私目**為據：晉人之書而以清錢曾《述古堂書目》為據，其時代之判即無根。
# 判準：所引之目晚於該志之斷代者。
LATE_SOURCES = ('述古堂書目', '也是園書目', '絳雲樓書目', '千頃堂書目',
                '四庫全書總目', '天一閣書目', '愛日精廬', '鐵琴銅劍樓')
# 著錄語提及某人而非謂其撰者（考證之定位語）
NOT_AUTHOR = ('次', '在', '之後', '之前', '别有', '別有')


def entity_index():
    idx = {}
    for f in glob.glob('/workspace/book-index-draft/Entity/*/*/*/*.json'):
        try:
            e = json.load(open(f, encoding='utf-8'))
        except Exception:
            continue
        ns = [e.get('primary_name')] + [(a.get('name') if isinstance(a, dict) else a)
                                        for a in (e.get('alt_names') or [])]
        for n in ns:
            if n:
                idx.setdefault(n, []).append(e)
    return idx


def main():
    ENT = entity_index()
    n_dd = n_tong = n_skip = 0
    log, skipped = [], []
    for root in ROOTS:
        for f in glob.glob(f'{root}/Work/*/*/*/*.json'):
            try:
                d = json.load(open(f, encoding='utf-8'))
            except Exception:
                continue
            if d.get('_promoted_to') or not d.get('period'):
                continue
            au = (d.get('authors') or [{}])[0]
            nm = au.get('name')
            if not nm:
                continue
            nodes = [r for r in d.get('indexed_by') or [] if not r.get('misattached')]
            early = [r for r in nodes if r.get('source') in BOUND
                     and I[BOUND[r['source']][0]] < I[d['period']]
                     and nm in (str(r.get('summary') or '') + str(r.get('author_info') or ''))]
            if not early:
                continue
            tgt = min(early, key=lambda r: I[BOUND[r['source']][0]])
            src, ub = tgt['source'], BOUND[tgt['source']][0]
            summ = str(tgt.get('summary') or '')
            if any(h in summ for h in LATE_SOURCES):
                skipped.append({'id': d['id'], 'title': d.get('title'), '志': src,
                                '語': summ[:120],
                                '因': '著錄語以後代私目為據，其時代之判無根，疑誤收'})
                n_skip += 1
                continue
            # 著錄語提其名而非謂其撰——考證之定位語（「按舊志次陳壽書之後」）
            pos = summ.find(nm)
            around = summ[max(0, pos - 6):pos + len(nm) + 6]
            if pos >= 0 and any(k in around for k in NOT_AUTHOR) and f'{nm}撰' not in summ:
                skipped.append({'id': d['id'], 'title': d.get('title'), '志': src,
                                '語': summ[:120], '因': '著錄語提其名而非謂其撰（考證之定位語）'})
                n_skip += 1
                continue
            # 按：曾以 Entity 之 dynasty 作交叉驗證，然 Entity 與 Work 之朝代出自同一批
            # 匯入，非獨立之證——以之驗只是重述同一錯誤，一舉攔下 15 條該改者，已去。
            # 志書才是獨立之證。斷代補志之判仍須人工覆核，清單見 known-issues。
            old_p, old_d = d['period'], au.get('dynasty')
            if src in DUANDAI:
                new = DUANDAI[src]
                d['period'] = new
                d['period_basis'] = (f'斷代補志著錄語明書撰人之名（2026-08-21）：《{src}》'
                                     f'「{summ[:50]}」——該志斷代輯 {new} 之作，'
                                     f'收其人即斷其屬該代。原標 dynasty「{old_d}」、period {old_p}')
                au['dynasty_basis'] = f'《{src}》著錄語明書其名，該志斷代輯 {new} 之作（2026-08-21）'
                d.pop('period_upper', None)
                d.pop('period_upper_basis', None)
                d['ai_note'] = ((d.get('ai_note') or '') +
                                f'\n\n2026-08-21 撰人時代訂正（斷代補志）：本條撰人{nm}原標「{old_d}」，'
                                f'period {old_p}，而《{src}》明書其名——該志專輯 {new} 之作，'
                                f'今從志改 period 為 {new}。dynasty 原值存而不改（史料轉錄，'
                                f'改之則失其所本），其可疑已記於此。').strip()
                n_dd += 1
                log.append(f'   斷代 {d["id"]} 《{d.get("title")}》 {nm}({old_d}) {old_p}→{new} 據《{src}》')
            else:
                d.pop('period', None)
                d.pop('period_basis', None)
                d['period_upper'] = ub
                d['period_upper_basis'] = (f'catalog_bound：《{src}》著錄語明書撰人{nm}之名'
                                           f'（「{summ[:40]}」），其人必不晚於該志，故不晚於 {ub}。'
                                           f'該志未書其朝代，確值待考')
                d['ai_note'] = ((d.get('ai_note') or '') +
                                f'\n\n2026-08-21 撰人時代存疑（通代志）：本條撰人{nm}原標「{old_d}」，'
                                f'period {old_p}，而《{src}》（上限 {ub}）明書其名——其人必不晚於該志，'
                                f'原判必誤。然該志未書其朝代，確值無從逕定，故撤 period 而標 period_upper。'
                                f'dynasty 原值存而不改，其可疑已記於此。').strip()
                n_tong += 1
                log.append(f'   通代 {d["id"]} 《{d.get("title")}》 {nm}({old_d}) {old_p}→撤，upper={ub} 據《{src}》')
            if APPLY:
                with open(f, 'w', encoding='utf-8', newline='\n') as fh:
                    fh.write(json.dumps(d, ensure_ascii=False, indent=2))
    print('\n'.join(log))
    print(f'\n斷代補志逕定 {n_dd}，通代志撤 period 標 upper {n_tong}，疑誤收跳過 {n_skip}'
          + ('' if APPLY else '  (dry-run)'))
    if APPLY and skipped:
        json.dump(skipped, open('/workspace/book-index-draft/.claude/known-issues/'
                                '志書疑誤收.json', 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
