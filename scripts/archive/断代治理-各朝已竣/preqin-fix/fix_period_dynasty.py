#!/usr/bin/env python3
"""先秦条目 period / dynasty / 作者串位修复。

依据 book-index-draft/SCHEMA.md §period 三重判准：
  规则1 粗粒度自消歧  -> P1 / P2
  规则2 著录之志为时代上限 -> P3
另修 P4：作者朝代错 / entity 串位。
"""
import json, glob, os, sys
from book_index_manager import BookIndexManager
from book_index_manager.id_generator import BookIndexType

ROOT = '/workspace'
DRAFT = '/workspace/book-index-draft'
PQ = {'夏','商','西周','東周','春秋','戰國','先秦','春秋齊','春秋晉','春秋吳','春秋魯',
      '戰國齊','戰國楚','戰國趙','戰國魏','戰國韓','上古','上古傳說'}
APPLY = '--apply' in sys.argv
mgr = BookIndexManager(storage_root=ROOT)

idx = {}
for f in glob.glob(f'{DRAFT}/index/works/*.json'):
    idx.update(json.load(open(f)))

log = []


def save(d, why):
    log.append(why)
    if APPLY:
        mgr.save_item(d, type_val=BookIndexType.Work)


def note(d, text):
    n = d.get('ai_note', '') or ''
    if text not in n:
        d['ai_note'] = (n + ' | ' + text).strip(' |') if n else text


# ---- P1：dynasty「齊」被误判为 nanbeichao（春秋齊/戰國齊 皆 pre-qin）
P1 = ['1ev3baig01kw0', '1ev3bbyca5ts0']
for wid in P1:
    d = mgr.get_item(wid)
    dy = (d.get('authors') or [{}])[0].get('dynasty')
    old = d.get('period')
    d['period'] = 'pre-qin'
    d['period_basis'] = f'據 authors[0].dynasty「{dy}」（規則1 粗粒度自消歧）。' \
                        f'訂正 {old}：原派生誤將諸侯國「齊」讀作南朝齊／北齊。'
    note(d, f'period 訂正：{old} → pre-qin。原基準「據 authors[0].dynasty「齊」」把春秋／戰國之齊國誤作南北朝之齊。')
    save(d, f'P1 {wid} 《{d.get("title")}》 period {old} → pre-qin（dynasty={dy}）')

# ---- P2：dynasty 已是先秦规范名，但 period 为空
P2 = []
for k, v in idx.items():
    d0 = json.load(open(os.path.join(DRAFT, v['path'])))
    if d0.get('period'):          # 以檔案為準：save_item 會把 period 從 index entry 抹掉
        continue
    au = d0.get('authors') or []
    dy = au[0].get('dynasty') if au and isinstance(au[0], dict) else None
    if dy in PQ:
        P2.append((k, dy))
for wid, dy in P2:
    d = mgr.get_item(wid)
    d['period'] = 'pre-qin'
    d['period_basis'] = f'據 authors[0].dynasty「{dy}」（規則1 粗粒度自消歧）'
    save(d, f'P2 {wid} 《{d.get("title")}》 period null → pre-qin（dynasty={dy}）')

# ---- P3：见于《漢書藝文志》，period 不得晚于 qin-han，却被断代志规则误判
P3 = {
    '1ev7w0euvaeww': '論語',
    '1evl7nl7lsg00': '周禮',
    '1ev7xkhw8670g': '青史子',
    '1ev85dj2nnmkg': '論語齊',
}
for wid, title in P3.items():
    d = mgr.get_item(wid)
    old = d.get('period')
    d['period'] = 'pre-qin'
    d['period_basis'] = ('見於《漢書藝文志》，依規則2「著錄之志為時代上限」其時代不得晚於 qin-han；'
                         f'本書為先秦典籍，故定 pre-qin。訂正 {old}（原依規則3 斷代志逕定，'
                         '然本條另見漢志，斷代志之判與規則2 相牴觸，規則2 為硬界，勝之）。')
    note(d, f'period 訂正：{old} → pre-qin。原判據斷代志（清史稿／明史藝文志），與漢志著錄上限相牴觸。')
    save(d, f'P3 {wid} 《{title}》 period {old} → pre-qin（漢志上限）')

# ---- P4a：孟軻 dynasty 西周 → 戰國（Work + Entity）
d = mgr.get_item('1ev7xm3w3445c')
for a in (d.get('authors') or []):
    if a.get('name') == '孟軻' and a.get('dynasty') == '西周':
        a['dynasty'] = '戰國'
        a['dynasty_basis'] = '訂正：孟軻為戰國鄒人，原「西周」係 entity 1j967cp1zdr1p 誤值傳播'
note(d, 'authors[0].dynasty 訂正：西周 → 戰國（孟軻，戰國鄒人）。同步訂正 entity 1j967cp1zdr1p。')
save(d, 'P4a 1ev7xm3w3445c 《孟子》 authors[0].dynasty 西周 → 戰國')

ent = glob.glob(f'{DRAFT}/Entity/*/*/*/1j967cp1zdr1p-*.json')
if ent:
    e = json.load(open(ent[0]))
    if e.get('dynasty') == '西周':
        e['dynasty'] = '戰國'
        log.append('P4a entity 1j967cp1zdr1p 孟軻 dynasty 西周 → 戰國')
        if APPLY:
            json.dump(e, open(ent[0], 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

# ---- P4b：呂不韋 dynasty 缺 → 戰國，period → pre-qin（Work + Entity）
d = mgr.get_item('1ev3bbv3z0j5s')
for a in (d.get('authors') or []):
    if a.get('name') == '呂不韋' and not a.get('dynasty'):
        a['dynasty'] = '戰國'
        a['dynasty_basis'] = '呂不韋，戰國衛人，相秦莊襄王、始皇'
d['period'] = 'pre-qin'
d['period_basis'] = '據 authors[0].dynasty「戰國」（規則1 粗粒度自消歧）'
save(d, 'P4b 1ev3bbv3z0j5s 《呂氏春秋》 dynasty 補「戰國」，period null → pre-qin')

ent = glob.glob(f'{DRAFT}/Entity/*/*/*/1j96heq45tqm8-*.json')
if ent:
    e = json.load(open(ent[0]))
    if not e.get('dynasty'):
        e['dynasty'] = '戰國'
        log.append('P4b entity 1j96heq45tqm8 呂不韋 dynasty 補「戰國」')
        if APPLY:
            json.dump(e, open(ent[0], 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

# ---- P4c：鬼穀子 作者串位（公孫龍 → 鬼谷子）
d = mgr.get_item('1ev3bbv3az9c0')
d['authors'] = [{
    'name': '鬼谷子',
    'role': '託名',
    'dynasty': '先秦',
    'note': '隋志：「鬼穀子，周世隱於鬼穀。」舊題撰人，其人其書皆有依託之疑',
}]
note(d, '作者訂正：原作「公孫龍」，係《國立故宮博物院善本舊籍》目錄「周公孫龍撰」一條串位誤入'
        '（該記錄屬《公孫龍子》），並誤掛 entity 1j96heq3o17nk（公孫龍）。'
        '今依《隋書經籍志》「鬼穀子，周世隱於鬼穀」改題鬼谷子，role 用「託名」。'
        'entity 暫不掛：庫中「鬼谷」1j96hee5obpc0 與「鬼谷先生」1j96haaea6hog 兩條重出，待 entity 去重後再繫。')
save(d, 'P4c 1ev3bbv3az9c0 《鬼穀子》 作者 公孫龍 → 鬼谷子（託名），移除誤掛 entity')

print(f'{"APPLY" if APPLY else "DRY-RUN"}  共 {len(log)} 项')
for x in log[:12]:
    print('  ', x)
print(f'  ... P2 批量 {len(P2)} 条（详见下）')
