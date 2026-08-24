#!/usr/bin/env python3
"""CBDB 公開 API 查人名之朝代（本地 CBDB SQLite 不在時的替代路徑）。

本庫定例以 CBDB 為撰人朝代之補強（見 /match-cbdb-authors）。本腳本走
官方 API https://cbdb.fas.harvard.edu/cbdbapi/person.php，逐名查詢並落 cache。

**只取無歧義者**：一名而 CBDB 有多人且朝代不一者，記為 ambiguous 不用——
同名異人是本庫既有之患，寧缺毋濫。

限流：單進程多線程（預設 6 並發），失敗指數退避。cache 定期落地，可斷點續跑。
**不可多進程共寫一個 cache**——實測會互相覆蓋（本腳本初版之誤）。

用法：python3 scripts/cbdb_api_lookup.py <todo.json> <cache.json> [--limit N] [--workers N]
      todo.json 每條須有 "name"
"""
import json, sys, time, os, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = 'https://cbdb.fas.harvard.edu/cbdbapi/person.php'
DELAY = float(os.environ.get('CBDB_DELAY', '1.0'))


def fetch(name, retries=3):
    """查一名。

    **空回應即「無此人」，非錯誤**——CBDB 於查無記錄之名返回空 body。
    初版把它當解析失敗而重試三次加退避，每個查無之名遂耗九秒有餘，
    是本腳本初跑奇慢之由（庫中待查之名過半查無記錄）。
    """
    url = f'{API}?name={urllib.parse.quote(name)}&o=json'
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                body = r.read().decode('utf-8').strip()
            if not body:
                return {}
            try:
                return json.loads(body)
            except ValueError:
                return {}
        except Exception as e:
            if i == retries - 1:
                return {'_error': str(e)}
            time.sleep(2 ** i)
    return {'_error': 'unreachable'}


def persons(js):
    """API 之 Person 或為單物件或為陣列，歸一。"""
    try:
        pi = js['Package']['PersonAuthority']['PersonInfo']
    except (KeyError, TypeError):
        return []
    p = (pi or {}).get('Person')
    if p is None:
        return []
    return p if isinstance(p, list) else [p]


def summarize(js):
    out = []
    for p in persons(js):
        b = p.get('BasicInfo') or {}
        out.append({
            'id': b.get('PersonId'), 'name': b.get('ChName'),
            'dynasty': b.get('Dynasty'), 'dynasty_id': b.get('DynastyId'),
            'birth': b.get('YearBirth'), 'death': b.get('YearDeath'),
            'index_year': b.get('IndexYear'),
        })
    return out


def main():
    todo_p, cache_p = sys.argv[1], sys.argv[2]
    limit = None
    if '--limit' in sys.argv:
        limit = int(sys.argv[sys.argv.index('--limit') + 1])
    todo = json.load(open(todo_p))
    cache = json.load(open(cache_p)) if os.path.exists(cache_p) else {}

    names = []
    for t in todo:
        n = t.get('name')
        if n and n not in cache:
            names.append(n)
    if limit:
        names = names[:limit]
    print(f'待查 {len(names)}（cache 已有 {len(cache)}）', flush=True)

    workers = 6
    if '--workers' in sys.argv:
        workers = int(sys.argv[sys.argv.index('--workers') + 1])

    def job(n):
        return n, summarize(fetch(n))

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for n, res in ex.map(job, names):
            cache[n] = res
            done += 1
            if done % 50 == 0 or done == len(names):
                json.dump(cache, open(cache_p, 'w'), ensure_ascii=False, indent=1)
                print(f'  {done}/{len(names)} 已存', flush=True)
    json.dump(cache, open(cache_p, 'w'), ensure_ascii=False, indent=1)

    hit = sum(1 for v in cache.values() if v)
    uniq = sum(1 for v in cache.values()
               if v and len({x['dynasty'] for x in v if x.get('dynasty')}) == 1)
    print(f'cache {len(cache)}　有記錄 {hit}　朝代唯一 {uniq}')


if __name__ == '__main__':
    main()
