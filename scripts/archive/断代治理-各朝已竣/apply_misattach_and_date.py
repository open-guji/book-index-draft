#!/usr/bin/env python3
"""B4：同題異書之著錄節標 misattached，並據裁定補 period（2026-08-24）。

症狀：period 或引文所示之代與 period_upper 相斥。根因不是斷代判錯，而是
**同題異書被併到一個 work 上**——早志所著錄之某書與晚出目錄所著錄之同題書
本是二事，上限取自早志而 period 取自晚出撰人，遂相斥。

處置只摘節（標 misattached），**不拆 work、不建新條**——拆併是 B 車道另一事，
須逐條裁；本腳本只解「此節非本條之書」。period_bounds.tightest 已會跳過
標了 misattached 之節，故摘節後上限自動重算。

用法：python3 scripts/apply_misattach_and_date.py <result.json> [--apply]
"""
import json, glob, sys, datetime


def shard(i):
    h = 0
    for c in i:
        h = ((h * 31) + ord(c)) & 0xFFFFFFFF
    return '%x' % (h % 16)


def main():
    res = json.load(open(sys.argv[1]))
    apply_ = '--apply' in sys.argv
    mis = [r for r in res if r.get('verdict') == 'misattach']
    keep = [r for r in res if r.get('verdict') == 'keep']
    unc = [r for r in res if r.get('verdict') == 'uncertain']
    print(f'摘節 {len(mis)}　留 {len(keep)}　存疑 {len(unc)}')
    for r in mis:
        print(f"  {r['id']} 摘 {r.get('misattached_indices')} → period {r.get('period')}")
    if not apply_:
        print('（dry-run，加 --apply 方寫入）')
        return

    IW = {s: json.load(open(f'index/works/{s}.json')) for s in '0123456789abcdef'}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    n_node = n_per = 0
    for r in mis + keep:
        wid = r['id']
        hits = glob.glob(f'Work/{wid[0]}/{wid[1]}/{wid[2]}/{wid}-*.json')
        if not hits:
            continue
        p = hits[0]
        d = json.load(open(p, encoding='utf-8'))
        if r.get('verdict') == 'misattach':
            nodes = d.get('indexed_by') or []
            for i in (r.get('misattached_indices') or []):
                if 0 <= i < len(nodes):
                    nodes[i]['misattached'] = True
                    nodes[i]['misattached_note'] = (
                        f'2026-08-24 B4 逐條裁：此節非本條之書——{r.get("reason") or ""}')
                    n_node += 1
            # 上限所據既變，撤舊值令 mark_period_upper 重算
            d.pop('period_upper', None)
            d.pop('period_upper_basis', None)
        if r.get('period') and not d.get('period'):
            d['period'] = r['period']
            d['period_basis'] = (f'{r.get("reason") or ""}'
                                 '（2026-08-24 B4 同題異書逐條裁）')
            n_per += 1
            e = IW[shard(wid)].get(wid)
            if e is not None:
                e['period'] = r['period']
        d['updated_at'] = now
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
    for s, obj in IW.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    print(f'標 misattached 節 {n_node}　補 period {n_per}')


if __name__ == '__main__':
    main()
