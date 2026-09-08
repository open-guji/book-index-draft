#!/usr/bin/env python3
"""B2：著錄條目分詞邊界之訂正落庫（2026-08-24）。

症狀：志書著錄原文切分有誤，致 title／authors[].name／authors[].dynasty 三欄俱錯。
其形有四（見 known-issues/著錄分詞邊界誤-20260824.json）：
  甲 人名末字被切給書名之首——「宋秦九韶數學九章」切作 name 秦九／title 韶數學九章
  乙 姓氏誤作朝代，整個切分左移——「周巽性情集」切作 dynasty 周／name 巽性／title 情集
  丙 舊題、注者混入——「舊題周老子月波洞中記」切作 name 周老／title 子月波洞中記
  丁 本無誤（假陽性）——書名恰以「子」起首而已

**改 title 須連檔名一並改**（檔名格式 `<id>-<title>.json`），並同步
index/works 之 title 與 path。dynasty 既改，period_upper 之「歧義朝代取最晚解」
所據亦變，故一並撤舊上限，令 mark_period_upper 重算。

用法：python3 scripts/apply_token_fix.py <result.json> [--apply]
"""
import json, glob, os, sys, datetime


def shard(i):
    h = 0
    for c in i:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return '%x' % (h % 16)


def main():
    res = json.load(open(sys.argv[1]))
    apply_ = '--apply' in sys.argv
    fixes = [r for r in res if r.get('action') == 'fix']
    keeps = [r for r in res if r.get('action') != 'fix']
    print(f'訂正 {len(fixes)}　留 {len(keeps)}')
    if not apply_:
        for r in fixes[:8]:
            print(f"  {r['id']} → title「{r['title']}」 "
                  f"authors {[(a.get('name'), a.get('dynasty')) for a in r['authors']]}")
        print('（dry-run，加 --apply 方寫入）')
        return

    IW = {s: json.load(open(f'index/works/{s}.json')) for s in '0123456789abcdef'}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    n_ren = 0
    for r in fixes:
        wid = r['id']
        hits = glob.glob(f'Work/{wid[0]}/{wid[1]}/{wid[2]}/{wid}-*.json')
        if not hits:
            print('  !! 檔不見', wid)
            continue
        p = hits[0]
        d = json.load(open(p, encoding='utf-8'))
        old_title = d.get('title')
        d['title'] = r['title']
        d['authors'] = [{k: v for k, v in a.items() if v} for a in r['authors']]
        note = (f'2026-08-24 B2 著錄分詞訂正：舊記 title「{old_title}」、'
                f'撰人 {[(a.get("name"), a.get("dynasty")) for a in (d.get("authors") or [])]}'
                f'——{r.get("reason") or ""}')
        d['ai_note'] = ((d.get('ai_note') or '') + '\n\n' + note).strip()
        # dynasty 既改，舊上限所據之「歧義朝代取最晚解」不復成立，撤之令重算
        if d.get('period_upper_basis', '').startswith('撰人朝代作'):
            d.pop('period_upper', None)
            d.pop('period_upper_basis', None)
        d['updated_at'] = now
        newp = f'Work/{wid[0]}/{wid[1]}/{wid[2]}/{wid}-{r["title"]}.json'
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
        if newp != p:
            os.rename(p, newp)
            n_ren += 1
        e = IW[shard(wid)].get(wid)
        if e is not None:
            e['title'] = r['title']
            e['path'] = newp
            a0 = d['authors'][0] if d.get('authors') else {}
            if a0.get('name'):
                e['author'] = a0['name']
            if a0.get('dynasty'):
                e['dynasty'] = a0['dynasty']
            else:
                e.pop('dynasty', None)
            if a0.get('role'):
                e['role'] = a0['role']
    for s, obj in IW.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    print(f'已訂正 {len(fixes)}（改檔名 {n_ren}）')


if __name__ == '__main__':
    main()
