#!/usr/bin/env python
"""據《清史稿·藝文志》著錄語之朝代前綴訂正撰人 dynasty。

《清史稿·藝文志》之著錄式為「朝代＋撰人＋書名＋卷數」——「漢蔡邕《月令章句》一卷。」
導入時有一批誤以志書名《清史稿》之「清」為撰人朝代，致漢晉南北朝之人皆標作清。

**只在新值與舊值映射到不同 period 時才改。** 清史稿所書之朝代名簡略（「漢」「梁」「魏」），
庫中既有者往往更精（「東漢」「南朝梁」「三國魏」），同 period 而改之則失其精、且「梁」「魏」
「宋」有歧義，是把好資料改壞。

用法：python fix_qingshigao_dynasty_prefix.py [--apply]
"""
import json, glob, re, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from period_bounds import I, tightest, DYNASTY_PERIOD, AMBIGUOUS  # noqa: E402

APPLY = '--apply' in sys.argv
ROOTS = ('/workspace/book-index-draft', '/workspace/book-index')

DY = ('(後漢|東漢|西漢|漢|三國魏|曹魏|北魏|後魏|東魏|西魏|魏|蜀漢|前蜀|後蜀|蜀|孫吳|吳|'
      '西晉|東晉|晉|劉宋|南朝宋|北宋|南宋|南齊|北齊|齊|後梁|南朝梁|梁|南朝陳|陳|北周|後周|'
      '隋|後唐|南唐|唐|後晉|五代|遼|金|元|明|國朝|清)')
PAT = re.compile(r'^' + DY + r'([一-鿿]{2,4})[《〈]')

MAP = {
    '漢': 'qin-han', '東漢': 'qin-han', '西漢': 'qin-han', '後漢': 'qin-han',
    '魏': 'three-kingdoms', '三國魏': 'three-kingdoms', '曹魏': 'three-kingdoms',
    '蜀': 'three-kingdoms', '蜀漢': 'three-kingdoms', '吳': 'three-kingdoms', '孫吳': 'three-kingdoms',
    '晉': 'jin', '西晉': 'jin', '東晉': 'jin',
    '劉宋': 'nanbeichao', '南朝宋': 'nanbeichao', '北宋': 'song', '南宋': 'song',
    '齊': 'nanbeichao', '南齊': 'nanbeichao', '北齊': 'nanbeichao',
    '梁': 'nanbeichao', '南朝梁': 'nanbeichao', '陳': 'nanbeichao', '南朝陳': 'nanbeichao',
    '北魏': 'nanbeichao', '後魏': 'nanbeichao', '東魏': 'nanbeichao', '西魏': 'nanbeichao', '北周': 'nanbeichao',
    '隋': 'sui-tang', '唐': 'sui-tang',
    '後唐': 'five-dynasties', '南唐': 'five-dynasties', '後梁': 'five-dynasties',
    '後晉': 'five-dynasties', '後周': 'five-dynasties', '後蜀': 'five-dynasties',
    '前蜀': 'five-dynasties', '五代': 'five-dynasties',
    '遼': 'liao-jin-yuan', '金': 'liao-jin-yuan', '元': 'liao-jin-yuan',
    '明': 'ming', '清': 'qing', '國朝': 'qing',
}


def prefix_of(work):
    """從清史稿著錄語取「朝代＋撰人」，撰人須與本條 authors[0] 相符。"""
    au = (work.get('authors') or [{}])[0]
    nm = au.get('name')
    if not nm:
        return None          # 無撰人名則無從分辨姓氏與朝代同形者（陳汝錫、吳國倫、周必大…）
    for r in work.get('indexed_by') or []:
        if r.get('source') != '清史稿藝文志':
            continue         # 只信清史稿：他志著錄式不同，前綴多為姓氏
        m = PAT.match(str(r.get('summary') or '').strip())
        if not m:
            continue
        dy, pn = m.group(1), m.group(2)
        if pn != nm:
            continue
        # 先秦稱謂：「魏公子牟」之「魏」是戰國魏，非曹魏。清史稿此類不可逕取前綴
        if re.match(r'^(公子|太子|王子|公孫|季子)', pn) or re.match(r'^(公子|太子|王子)', nm):
            return None
        p = MAP.get(dy)
        if p:
            return dy, p, str(r.get('summary'))[:60], au
    return None


def main():
    fixed = skipped_same = skipped_bound = 0
    log = []
    for root in ROOTS:
        for f in glob.glob(f'{root}/Work/*/*/*/*.json'):
            try:
                d = json.load(open(f, encoding='utf-8'))
            except Exception:
                continue
            if d.get('_promoted_to'):
                continue
            got = prefix_of(d)
            if not got:
                continue
            dy, p, ev, au = got
            old_dy = (au.get('dynasty') or '').strip()
            if old_dy == dy:
                continue
            # 關鍵閘門：舊值若映到同一 period，則只是詳略之別，庫中既有者更精，不改。
            # 須用 DYNASTY_PERIOD 全表——本檔之 MAP 只是清史稿前綴詞表，缺「三國吳」
            # 「前涼」「齊梁」之屬，用之則把詳值誤判為異代而改壞。
            if old_dy and DYNASTY_PERIOD.get(old_dy) == p:
                skipped_same += 1
                continue
            ub = tightest([r.get('source') for r in d.get('indexed_by') or [] if r.get('source')])
            if ub and I[p] > I[ub]:
                skipped_bound += 1
                continue
            old_p = d.get('period')
            au['dynasty'] = dy
            au['dynasty_basis'] = f'清史稿藝文志著錄語之朝代前綴（2026-08-21 訂正）：「{ev}」'
            d['period'] = p
            d['period_basis'] = (f'據 authors[0].dynasty「{dy}」（2026-08-21 訂正：原標「{old_dy or "闕"}」，'
                                 f'據清史稿著錄語之朝代前綴改）')
            d.pop('period_upper', None)
            d.pop('period_upper_basis', None)
            d['ai_note'] = ((d.get('ai_note') or '') +
                            f'\n\n2026-08-21 撰人朝代訂正：原作「{old_dy or "闕"}」，period 為 {old_p}。'
                            f'《清史稿·藝文志》著錄語作「{ev}」——其式為「朝代＋撰人＋書名＋卷數」，'
                            f'撰人朝代明書於前。今據以改 dynasty 為「{dy}」、period 為 {p}。').strip()
            if APPLY:
                with open(f, 'w', encoding='utf-8', newline='\n') as fh:
                    fh.write(json.dumps(d, ensure_ascii=False, indent=2))
            fixed += 1
            log.append(f'   {d["id"]} 《{d.get("title")}》 {au["name"]}：{old_dy or "闕"}→{dy}  period {old_p}→{p}')
    print('\n'.join(log))
    print(f'\n訂正 {fixed} 條'
          f'（{skipped_same} 條同 period 之詳略差不改、{skipped_bound} 條新值仍逾 catalog_bound）'
          + ('' if APPLY else '  (dry-run)'))


if __name__ == '__main__':
    main()
