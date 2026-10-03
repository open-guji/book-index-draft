#!/usr/bin/env python3
"""补写缺 description 的先秦相关条目。文字據該條目自身已錄之志書著錄 + 四庫提要通說。"""
import sys, json
from book_index_manager import BookIndexManager
from book_index_manager.id_generator import BookIndexType

APPLY = '--apply' in sys.argv
mgr = BookIndexManager(storage_root='/workspace')

FILL = {
 '1ev3bbv3az9c0': {
   'text': '《鬼穀子》一卷（《崇文總目》《隋志》作三卷，《舊唐志》作二卷）。舊題鬼谷子撰，'
           '其人姓名不傳，《史記·蘇秦列傳》稱蘇秦、張儀「俱事鬼谷先生」，'
           '《隋書·經籍志》注「鬼穀子，周世隱於鬼穀」。全書論縱橫捭闔之術，'
           '今本有《捭闔》《反應》《內揵》《抵巇》《飛箝》《忤合》《揣》《摩》《權》《謀》《決》《符言》諸篇，'
           '另附《本經陰符七術》《持樞》《中經》。《四庫全書總目》著錄一卷，入子部縱橫家類，'
           '為縱橫家唯一傳世專書。歷代注本有皇甫謐注、樂壹（一作樂台）注、尹知章注等。'
           '其書真偽自唐柳宗元《辯鬼谷子》以來聚訟不已，或謂戰國縱橫家言之所輯，或謂六朝人依託。',
   'sources': ['隋書經籍志', '欽定四庫全書總目'],
 },
 '1ev3b9y2ehm2o': {
   'text': '《詩序》二卷。《毛詩》各篇篇首之小序，與《關雎》篇前之大序，合輯單行之本。'
           '舊題子夏（卜商）作，然說者不一：鄭玄謂大序子夏所作、小序子夏毛公合作；'
           '《後漢書·儒林傳》謂衛宏作《毛詩序》；朱熹《詩序辨說》則疑其出於漢儒之手。'
           '《四庫全書總目》著錄《詩序》二卷，入經部詩類。宋以後說《詩》者分尊序、廢序兩派，'
           '此書即其爭訟之所在。',
   'sources': ['欽定四庫全書總目', '經義考'],
 },
 '1ev7vo5qfkidc': {
   'text': '《難經》二卷，全稱《黃帝八十一難經》。設八十一問答以發明《內經》之旨，'
           '論脈診、經絡、藏象、腧穴、鍼法諸端，「獨取寸口」之診法及三焦、命門之說皆本書所倡，'
           '為中醫四大經典之一。舊題秦越人（扁鵲）撰，然書中稱引《內經》而文體近東漢，'
           '學界多以為成於東漢而託名扁鵲，成書年代迄無定論。'
           '《隋書·經籍志》已著錄《黃帝八十一難》二卷、吳太醫令呂廣注。'
           '歷代注本甚多，元滑壽《難經本義》最為通行。',
   'sources': ['隋書經籍志', '直齋書錄解題'],
 },
 '1evinckalh1xc': {
   'text': '《難經集注》五卷，又題《王翰林集注黃帝八十一難經》。彙輯三國吳呂廣、唐楊玄操、'
           '宋丁德用、虞庶、楊康侯五家之注，為《難經》現存最早之集注本。'
           '其書中土久佚，賴日本傳本得存，清嘉慶間阮元自日本得之進呈，'
           '收入《佚存叢書》以活字排印行世（本條所繫 Book 11qkhuwlucwe8 即此本）。',
   'sources': ['書目答問'],
 },
 '1evcsw6n98r9c': {
   'text': '《大學》本為《禮記》第四十二篇，宋以後與《中庸》《論語》《孟子》合稱四書。'
           '舊傳經一章為孔子之言而曾子述之，傳十章為曾子之意而門人記之；'
           '朱熹《大學章句》分經傳、補格物傳，程朱一系奉為「初學入德之門」。'
           '本條所繫者為鄭玄注一系（鄭玄注《禮記》，《大學》在其中），'
           '《宋史·藝文志》著錄《大學》，所繫 Book 11qki0hz7v2f4 為清咸豐間稽古樓刊十三經注之一。',
   'sources': ['宋史藝文志'],
 },
}

# 附帶標記（不逕改，記入 ai_note 供後續建模決策）
FLAG = {
 '1evinckalh1xc': '建模待決：本條 authors 作「秦越人 撰」，然秦越人乃《難經》原典舊題撰人，'
                  '非《集注》之輯者；集注實輯呂廣以下五家、明王九思等校刊。'
                  'period 亦因此懸而未定。俟原典／注本層級依「原典注疏關係設計」釐定後一併訂正。',
 '1evcsw6n98r9c': '建模待決：authors[0].role 為「注」（鄭玄），依錄入規範「role 為注／傳／疏者 title 含注者名」，'
                  'title 宜作《大學鄭玄注》一類；今仍題《大學》，與原典層《大學》易混。俟四書原典層釐定後訂正。',
}

n = 0
for wid, desc in FILL.items():
    d = mgr.get_item(wid)
    cur = d.get('description') or {}
    if isinstance(cur, dict) and cur.get('text'):
        print(f'skip {wid}: 已有 description')
        continue
    d['description'] = desc
    if wid in FLAG:
        note = d.get('ai_note', '') or ''
        if FLAG[wid] not in note:
            d['ai_note'] = (note + ' | ' + FLAG[wid]).strip(' |') if note else FLAG[wid]
    print(f'fill {wid} 《{d.get("title")}》 {len(desc["text"])} 字')
    n += 1
    if APPLY:
        mgr.save_item(d, type_val=BookIndexType.Work)
print(('APPLY' if APPLY else 'DRY-RUN'), n, '条')
