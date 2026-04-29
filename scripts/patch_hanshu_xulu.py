"""为汉志 兵書略 和 詩賦略 补齐缺失的类小序和略结尾 section。

这两略 json 只有 type="类" 和 type="书"，没有任何 type="结语" 的 section，
对照维基文库原文，在每个类 section 后面插入对应的小序，末尾加一个略结尾。
"""
import json
from pathlib import Path


def insert_summaries(jp: Path, summaries_after_class: dict, final_summary: dict):
    j = json.loads(jp.read_text(encoding='utf-8'))
    new_sections = []
    current_class = None
    for sec in j['sections']:
        if sec.get('type') == '类':
            if current_class and current_class in summaries_after_class:
                new_sections.append(summaries_after_class[current_class])
            current_class = sec.get('title')
        new_sections.append(sec)
    if current_class and current_class in summaries_after_class:
        new_sections.append(summaries_after_class[current_class])
    if final_summary:
        new_sections.append(final_summary)
    j['sections'] = new_sections
    jp.write_text(json.dumps(j, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return len(new_sections)


def _xu(content: str):
    return {'title': '小序', 'level': 2, 'type': '结语', 'content': content}


def _zongjie(title: str, content: str):
    return {'title': title, 'level': 1, 'type': '结语', 'content': content}


BINGSHU_XU = {
    '兵書兵權謀類': _xu(
        '右兵權謀十三家，二百五十九篇。\n'
        '權謀者，以正守國，以奇用兵，先計而後戰，兼形勢，包陰陽，用技巧者也。'
    ),
    '兵書兵形勢類': _xu(
        '右兵形勢十一家，九十二篇。圖十八卷。\n'
        '形勢者，雷動風舉，後發而先至，離合背鄉，變化無常，以輕疾制敵者也。'
    ),
    '兵書陰陽類': _xu(
        '右陰陽十六家，二百四十九篇，圖十卷。\n'
        '陰陽者，順時而發，推刑德，隨斗擊，因五勝，假鬼神而為助者也。'
    ),
    '兵書兵技巧類': _xu(
        '右兵技巧十三家，百九十九篇。\n'
        '技巧者，習手足，便器械，積機關，以立攻守之勝者也。'
    ),
}

BINGSHU_ZONGJIE = _zongjie(
    '兵書略總結',
    '凡兵書五十三家，七百九十篇，圖四十三卷。\n'
    '兵家者，蓋出古司馬之職，王官之武備也。洪範八政，八曰師。孔子曰為國者「足食足兵」，'
    '「以不教民戰，是謂棄之」，明兵之重也。《易》曰「古者弦木為弧，剡木為矢，弧矢之利，'
    '以威天下」，其用上矣。後世燿金為刃，割革為甲，器械甚備。下及湯武受命，以師克亂而濟百姓，'
    '動之以仁義，行之以禮讓，司馬法是其遺事也。自春秋至於戰國，出奇設伏，變詐之兵並作。'
    '漢興，張良、韓信序次兵法，凡百八十二家，刪取要用，定著三十五家。諸呂用事而盜取之。'
    '武帝時，軍政楊僕捃摭遺逸，紀奏兵錄，猶未能備。至于孝成，命任宏論次兵書為四種。'
)

SHIFU_XU = {
    '詩賦賦類': _xu(
        '右賦二十家，三百六十一篇。\n'
        '右賦二十一家，二百七十四篇。\n'
        '右賦二十五家，百三十六篇。'
    ),
    '詩賦歌詩類': _xu('右歌詩二十八家，三百一十四篇。'),
    '詩賦雜賦類': _xu('右雜賦十二家，二百三十三篇。'),
}

SHIFU_ZONGJIE = _zongjie(
    '詩賦略總結',
    '凡詩賦百六家，千三百一十八篇。\n'
    '傳曰：「不歌而誦謂之賦，登高能賦可以為大夫。」言感物造耑，材知深美，可與圖事，'
    '故可以為列大夫也。古者諸侯卿大夫交接鄰國，以微言相感，當揖讓之時，必稱詩以諭其志，'
    '蓋以別賢不肖而觀盛衰焉。故孔子曰「不學詩，無以言」也。春秋之後，周道浸壞，聘問歌詠不行於列國，'
    '學詩之士逸在布衣，而賢人失志之賦作矣。大儒孫卿及楚臣屈原離讒憂國，皆作賦以風，'
    '咸有惻隱古詩之義。其後宋玉、唐勒，漢興枚乘、司馬相如，下及揚子雲，競為侈麗閎衍之詞，'
    '沒其風諭之義。是以揚子悔之，曰：「詩人之賦麗以則，辭人之賦麗以淫；如孔氏之門人用賦也，'
    '則賈誼登堂，相如入室矣，如其不用何！」自孝武立樂府而采歌謠，於是有代趙之謳，秦楚之風，'
    '皆感於哀樂，緣事而發，亦可以觀風俗，知薄厚云。詩賦為五種。'
)


def main():
    base = Path('Work/1/e/u/1euhm19a23jsw/collated_edition')
    n = insert_summaries(base / '兵書略.json', BINGSHU_XU, BINGSHU_ZONGJIE)
    print(f'兵書略: now {n} sections')
    n = insert_summaries(base / '詩賦略.json', SHIFU_XU, SHIFU_ZONGJIE)
    print(f'詩賦略: now {n} sections')


if __name__ == '__main__':
    main()
