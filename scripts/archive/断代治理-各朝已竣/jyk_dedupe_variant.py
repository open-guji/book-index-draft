#!/usr/bin/env python3
"""補正本會話所建之六條重出——皆異體字補表之前所建

普查全庫「同題同撰」時查出：本會話據《經義考》所建之 work 中，有六條與庫中
既有之條同題同撰而只差一異體字。其由可考——`jyk_triage` 之異體表是分三次補
的，緫／總、𤣥／玄、隠／隱三對補在乙2、丙兩輪之後，補表之前所建者遂漏。

  《五經緫類》張雲鸞 ←→ 庫《五經總類》（緫／總）
  《公榖緫例》成𤣥   ←→ 庫《公榖總例》成玄（緫／總、𤣥／玄）
  《大衍索隠》丁易東 ←→ 庫《大衍索隱》（隠／隱）
  《讀易索隠》洪鼐   ←→ 庫《讀易索隱》（隠／隱）
  《孟子注》鄭玄     ←→ 庫《孟子注》鄭玄（東漢）——此條無異體之異，是甲1 之
                        閘在乙1 一輪尚未收 &KR0975;＝玄 之還原，遂兩不相認
  《易索隠》鄭廷芬   ←→ 《易索隱》鄭廷芬——**二條俱本會話所建**，同出《經義
                        考》而一作隠一作隱

法：留庫中既有之條（《易索隱》一組留正字之條），刪本會話所建者，其
`indexed_by[]` 之《經義考》一源移於所留之條。
"""
import json, os, sys, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jyk_triage import load_index
from jyk_create_works import shard

# 刪者 → 留者
PAIRS = [
    ('1exsy6shs5qfp', '1ev3bchbbw9og', '緫／總'),
    ('1exvbnnhxaob2', '1evgoq33gk4qo', '緫／總、𤣥／玄'),
    ('1exndo90di1l8', '1ev3bblh3v4lc', '隠／隱'),
    ('1exg4c1l2d5cj', '1ev0r92c8p5hc', '隠／隱'),
    ('1ex2zjzt1e3is', '1evftwxo1i680', '無異體之異——甲1 之閘於乙1 一輪尚未收 &KR0975;＝玄 之還原'),
    ('1ex9e1bi0oiir', '1exlve1kofe24', '隠／隱；二條俱本會話所建，留正字之條'),
]
DATA = '.claude/known-issues/經義考待裁.json'


def main():
    apply = '--apply' in sys.argv
    works = load_index('works')
    for a, b, why in PAIRS:
        if a not in works or b not in works:
            print('！id 不在庫:', a, b)
            return
        print(f"  刪 {a}《{works[a]['title']}》→ 留 {b}《{works[b]['title']}》（{why}）")
    if not apply:
        print('（乾跑。加 --apply 方寫檔）')
        return
    shards = {s: json.load(open(f'index/works/{s}.json')) for s in '0123456789abcdef'}
    D = json.load(open(DATA))
    for a, b, why in PAIRS:
        da = json.load(open(works[a]['path']))
        db = json.load(open(works[b]['path']))
        idx = db.setdefault('indexed_by', [])
        for e in (da.get('indexed_by') or []):
            if any(x.get('source') == e.get('source') and x.get('page') == e.get('page')
                   for x in idx):
                continue
            e = dict(e)
            e['note'] = (e.get('note', '') + ('　' if e.get('note') else '')
                         + f'本條前次誤判為庫中所無而別建（{a}），其實與本條同題同撰，'
                           f'只差異體（{why}）；今刪所建，源移於此。')
            idx.append(e)
        with open(works[b]['path'], 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
            f.write('\n')
        os.remove(works[a]['path'])
        shards[shard(a)].pop(a, None)
        for d in D:
            if d.get('created_work') == a:
                d.pop('created_work')
                d['attached_to'] = b
    for s, obj in shards.items():
        with open(f'index/works/{s}.json', 'w', encoding='utf-8') as f:
            json.dump(dict(sorted(obj.items())), f, ensure_ascii=False, indent=2)
            f.write('\n')
    json.dump(D, open(DATA, 'w'), ensure_ascii=False, indent=1)
    print('已併', len(PAIRS))


if __name__ == '__main__':
    main()
