#!/usr/bin/env python
"""把錯掛的早志著錄節自晚代 Work 摘出，改繫庫中對應之 Work。

由來：catalog_bound 覆驗查出一批 Work 之 period 逾其著錄志之上限，而該志之著錄語
與本條撰人全不相干——多是同題異書被併為一條。如司馬光《書儀》上掛著隋志「《書儀》
二卷蔡超撰」。

配對之判準（三者俱備方改）：
1. 題名相符（著錄之 title_info 或本條 title，去標點後比對）
2. 目標 Work 之 period（或 period_upper）≤ 該志之上限；二者皆空則不以此設限——
   period 空之薄條目往往正是待承接者（《書儀》蔡超 1ewywfxapuzno 即是），排之則漏
3. **著錄語中之撰人名見於目標 Work 之 authors**——只憑題名配會大量誤配，
   同題異書正是本專項所要拆的東西

逐節獨立處置：能配者改繫，不能配者留在原條並記於清單。

用法：python reattach_misplaced_catalog_nodes.py [--apply]
"""
import json, glob, re, sys, os, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from period_bounds import BOUND, I  # noqa: E402

APPLY = '--apply' in sys.argv
ROOTS = ('/workspace/book-index-draft', '/workspace/book-index')
DY_PREFIX = (r'^(後漢|東漢|西漢|漢|三國魏|北魏|後魏|魏|蜀|吳|西晉|東晉|晉|劉宋|南朝宋|北宋|'
             r'南宋|宋|南齊|北齊|齊|南朝梁|梁|南朝陳|陳|北周|後周|周|隋|後唐|南唐|唐|後晉|'
             r'五代|遼|金|元|明|國朝|清)')


def norm(s):
    return re.sub(r'[《》〈〉•·\s（）()「」、。]', '', s or '')


def persons(rec):
    """自著錄語抽撰人名。"""
    s = (str(rec.get('summary') or '') + ' ' + str(rec.get('author_info') or '')
         + ' ' + str(rec.get('title_info') or ''))
    out = set()
    for m in re.finditer(r'([一-鿿]{2,4})(?:撰|注|註|編|輯|解|傳|集解|章句|疏|音)(?:[。，、]|$|\s)', s):
        out.add(m.group(1))
    for m in re.finditer(r'^([一-鿿]{2,4})[《〈]', s.strip()):
        out.add(m.group(1))
    for m in re.finditer(r'[》〉]([一-鿿]{2,4})(?:[。，]|$)', s):
        out.add(m.group(1))
    both = set(out)
    for x in out:                       # 剝朝代前綴後再收一份
        y = re.sub(DY_PREFIX, '', x)
        if len(y) >= 2:
            both.add(y)
    return both


def load():
    W = {}
    for root in ROOTS:
        for f in glob.glob(f'{root}/Work/*/*/*/*.json'):
            try:
                d = json.load(open(f, encoding='utf-8'))
            except Exception:
                continue
            if d.get('_promoted_to'):
                continue
            d['__f'] = f
            W[d['id']] = d
    return W


def save(d):
    with open(d['__f'], 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(json.dumps({k: v for k, v in d.items() if k != '__f'},
                            ensure_ascii=False, indent=2))


def main():
    W = load()
    byt = collections.defaultdict(list)
    for d in W.values():
        for t in [d.get('title')] + (d.get('additional_titles') or []):
            if t:
                byt[norm(t)].append(d)

    moved = 0
    left = []
    touched = {}
    for d in list(W.values()):
        if not d.get('period') or not d.get('period_upper'):
            continue
        if I[d['period']] <= I[d['period_upper']]:
            continue
        nm = (d.get('authors') or [{}])[0].get('name')
        early = [r for r in d.get('indexed_by') or []
                 if r.get('source') in BOUND and I[BOUND[r['source']][0]] < I[d['period']]]
        if any(nm and nm in (str(r.get('summary') or '') + str(r.get('author_info') or ''))
               for r in early):
            continue                     # A 類：撰人朝代錯或志書誤收，不屬本專項
        for r in early:
            ps = persons(r)
            ub = BOUND[r['source']][0]
            tgt = None
            for key in {norm(r.get('title_info') or ''), norm(d.get('title'))}:
                if not key:
                    continue
                for x in byt.get(key, []):
                    if x['id'] == d['id']:
                        continue
                    xn = {a.get('name') for a in x.get('authors') or [] if a.get('name')}
                    if not (ps & xn):
                        continue          # 撰人名不合即非，題名相同不足為據
                    xp = x.get('period') or x.get('period_upper')
                    if xp and I[xp] > I[ub]:
                        continue          # 目標本身晚於該志，非承接者
                    tgt = x
                    break
                if tgt:
                    break
            if not tgt:
                left.append((d['id'], d.get('title'), r.get('source'),
                             str(r.get('summary') or '')[:80], sorted(ps)))
                continue
            d['indexed_by'].remove(r)
            tgt.setdefault('indexed_by', []).append(dict(
                r, note=(r.get('note', '') +
                         f'（2026-08-21 錯掛訂正：自《{d.get("title")}》{d["id"]} 移入——'
                         f'該條為 {d.get("period")} 之作，而本節出《{r.get("source")}》'
                         f'（上限 {ub}），著錄語之撰人與本條合）').strip()))
            d['ai_note'] = ((d.get('ai_note') or '') +
                            f'\n\n2026-08-21 錯掛訂正：《{r.get("source")}》一節'
                            f'（「{str(r.get("summary") or "")[:50]}」）與本條撰人全不相干，'
                            f'係同題異書誤併，今移繫《{tgt.get("title")}》{tgt["id"]}。').strip()
            tgt['ai_note'] = ((tgt.get('ai_note') or '') +
                              f'\n\n2026-08-21 錯掛訂正承接：《{r.get("source")}》一節原誤繫'
                              f'《{d.get("title")}》{d["id"]}（{d.get("period")}之作），'
                              f'其著錄語之撰人與本條合，今改繫。').strip()
            touched[d['id']] = d
            touched[tgt['id']] = tgt
            moved += 1

    print(f'改繫 {moved} 節，餘 {len(left)} 節無可承接者')
    if APPLY:
        for d in touched.values():
            save(d)
        json.dump(left, open('/workspace/book-index-draft/.claude/known-issues/'
                             '著錄錯掛待建.json', 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    else:
        for x in left[:10]:
            print('   餘:', x[0], x[1], x[2], x[3][:50])
    return moved


if __name__ == '__main__':
    main()
