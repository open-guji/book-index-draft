import json,sys,glob
IW={}
for f in glob.glob('index/works/*.json'): IW.update(json.load(open(f,encoding='utf-8')))
for wid in sys.argv[1:]:
    d=json.load(open(IW[wid]['path'],encoding='utf-8'))
    print('='*8, wid, d.get('title'), '|', [a.get('name') for a in d.get('authors') or []],
          '| juan', (d.get('juan_count') or {}).get('number'), '|', IW[wid]['path'])
    for e in d.get('indexed_by') or []:
        print('  ['+str(e.get('source'))+']', e.get('title_info'), '||', (e.get('summary') or '')[:300])
    for e in d.get('emendated_by') or []:
        print('  {emend '+str(e.get('source'))+'}', (e.get('summary') or '')[:200])
    if d.get('description'): print('  desc:', json.dumps(d['description'],ensure_ascii=False)[:300])
    if d.get('related_works'): print('  rel:', json.dumps(d['related_works'],ensure_ascii=False)[:300])
    if d.get('books'): print('  books:', d['books'])
