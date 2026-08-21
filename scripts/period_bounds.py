"""著錄志之時代上限表（catalog_bound）。見 SCHEMA〈period_upper〉。

一書見於某志，其時代不得晚於該志。只給上限，不給下限——早期志書亡佚極多，
一部漢代之書可能遲至《宋史·藝文志》方首見著錄。
"""
ORD = ['pre-qin', 'qin-han', 'three-kingdoms', 'jin', 'nanbeichao', 'sui-tang',
       'five-dynasties', 'song', 'liao-jin-yuan', 'ming', 'qing', 'modern']
I = {p: i for i, p in enumerate(ORD)}

BOUND = {
    '漢書藝文志':       ('qin-han',        '班固《漢書》成於東漢建初，本劉歆《七略》'),
    '漢藝文志考證':     ('qin-han',        '宋王應麟考證漢志'),
    '後漢藝文志':       ('qin-han',        '清姚振宗補後漢，斷代'),
    '三國藝文志':       ('three-kingdoms', '清姚振宗補三國，斷代'),
    '補晋書藝文志':     ('jin',            '清人補晉，斷代'),
    '隋書經籍志':       ('sui-tang',       '唐長孫無忌等，成於顯慶元年（656）'),
    '隋書經籍志考證':   ('sui-tang',       '清姚振宗考證隋志'),
    '舊唐書經籍志':     ('sui-tang',       '後晉劉昫，本唐開元《群書四部錄》'),
    '新唐書藝文志':     ('sui-tang',       '宋歐陽修等（1060），著錄唐代著述'),
    '崇文總目':         ('song',           '宋王堯臣等（1041），北宋崇文院藏書'),
    '直齋書錄解題':     ('song',           '南宋陳振孫（1249）'),
    '宋史藝文志':       ('song',           '元脫脫等（1345），著錄宋代藏書'),
    '宋史藝文志補':     ('song',           '清人補'),
    '元史藝文志':       ('liao-jin-yuan',  '清錢大昕補元，斷代'),
    '補遼金元藝文志':   ('liao-jin-yuan',  '清人補遼金元，斷代'),
    '明史藝文志':       ('ming',           '清張廷玉等（1739），只錄明人著述，斷代'),
    '國史經籍志':       ('ming',           '明焦竑（1590）'),
    '經義考':           ('qing',           '清朱彝尊（1700）'),
    '欽定四庫全書總目': ('qing',           '清紀昀等（1782）'),
    '四庫全書總目':     ('qing',           '同上'),
    '書目答問':         ('qing',           '清張之洞（1875）'),
    '清史稿藝文志':     ('qing',           '民國趙爾巽等（1927），著錄清人著述'),
    '四庫全書存目叢書': ('qing',           '現代影印，收明清'),
    '續修四庫全書':     ('modern',         '現代影印'),
    '中國通俗小說書目': ('modern',         '孫楷第（1933）'),
}

# 大量著錄古書之清人輯本／注本者——見於此類志書不足以判 qing
QING_JIYI = {'清史稿藝文志', '欽定四庫全書總目', '四庫全書總目', '經義考',
             '書目答問', '四庫全書存目叢書', '續修四庫全書'}


def tightest(sources):
    """諸志中最緊之上限；無可據者返 None。

    sources 可為志書名之序列，亦可為 indexed_by 之節（dict）——後者會跳過
    標了 misattached 的節（同題異書誤併，非本書之著錄，見 mark_misattached_nodes.py）。
    """
    bs = []
    for s in sources:
        if isinstance(s, dict):
            if s.get('misattached'):
                continue
            s = s.get('source')
        if s in BOUND:
            bs.append(BOUND[s][0])
    return min(bs, key=lambda x: I[x]) if bs else None


# ═══ dynasty → period 全表（規則1 粗粒度自消歧）═══
# 判「兩個 dynasty 寫法是否同代」用此表，勿用他處之簡表——
# 簡表缺「三國吳」「前涼」「齊梁」之屬，會把詳值誤判為異代而改壞。
DYNASTY_PERIOD = {
    # 先秦
    '先秦': 'pre-qin', '上古': 'pre-qin', '上古傳說': 'pre-qin', '商': 'pre-qin',
    '春秋': 'pre-qin', '戰國': 'pre-qin', '春秋魯': 'pre-qin', '春秋晉': 'pre-qin',
    '春秋齊': 'pre-qin', '春秋吳': 'pre-qin', '春秋鄭': 'pre-qin', '春秋衛': 'pre-qin',
    '戰國楚': 'pre-qin', '戰國齊': 'pre-qin', '戰國魏': 'pre-qin', '戰國趙': 'pre-qin',
    '戰國韓': 'pre-qin', '戰國燕': 'pre-qin', '戰國秦': 'pre-qin',
    # 秦漢
    '秦': 'qin-han', '漢': 'qin-han', '東漢': 'qin-han', '西漢': 'qin-han',
    '後漢': 'qin-han', '兩漢': 'qin-han', '新': 'qin-han',
    # 三國
    '三國': 'three-kingdoms', '三國魏': 'three-kingdoms', '曹魏': 'three-kingdoms',
    '三國吳': 'three-kingdoms', '孫吳': 'three-kingdoms', '三國蜀': 'three-kingdoms',
    '蜀漢': 'three-kingdoms',
    # 晉（含十六國）
    '晉': 'jin', '西晉': 'jin', '東晉': 'jin', '兩晉': 'jin',
    '前秦': 'jin', '後秦': 'jin', '前涼': 'jin', '後涼': 'jin', '北涼': 'jin',
    '西涼': 'jin', '南涼': 'jin', '前燕': 'jin', '後燕': 'jin', '南燕': 'jin',
    '北燕': 'jin', '夏': 'jin', '成漢': 'jin', '十六國': 'jin',
    # 南北朝
    '南北朝': 'nanbeichao', '南朝': 'nanbeichao', '北朝': 'nanbeichao',
    '劉宋': 'nanbeichao', '南朝宋': 'nanbeichao', '南齊': 'nanbeichao', '南朝齊': 'nanbeichao',
    '南朝梁': 'nanbeichao', '南朝陳': 'nanbeichao', '齊梁': 'nanbeichao',
    '北魏': 'nanbeichao', '後魏': 'nanbeichao', '東魏': 'nanbeichao', '西魏': 'nanbeichao',
    '北齊': 'nanbeichao', '北周': 'nanbeichao',
    # 隋唐
    '隋': 'sui-tang', '唐': 'sui-tang', '隋唐': 'sui-tang',
    # 五代十國
    '五代': 'five-dynasties', '後梁': 'five-dynasties', '後唐': 'five-dynasties',
    '後晉': 'five-dynasties', '後周': 'five-dynasties', '南唐': 'five-dynasties',
    '前蜀': 'five-dynasties', '後蜀': 'five-dynasties', '吳越': 'five-dynasties',
    # 宋
    '北宋': 'song', '南宋': 'song',
    # 遼金元
    '遼': 'liao-jin-yuan', '金': 'liao-jin-yuan', '元': 'liao-jin-yuan',
    '遼金元': 'liao-jin-yuan', '西夏': 'liao-jin-yuan',
    # 明清近代
    '明': 'ming', '清': 'qing',
    '中華民國': 'modern', '民國': 'modern', '中華人民共和國': 'modern',
    '現代': 'modern', '近代': 'modern',
}

# 歧義寫法：單書此字不足以定代，須以 catalog_bound 或他證消歧
# 「國朝」「皇朝」「本朝」之義隨志書而異——《國史經籍志》（明焦竑）之「國朝」是明，
# 《清史稿》之「國朝」是清。不可入 DYNASTY_PERIOD，須看所出之志。
AMBIGUOUS = {'宋', '魏', '周', '吳', '蜀', '齊', '梁', '陳', '燕', '涼', '漢後',
             '國朝', '皇朝', '本朝'}

# 「國朝」之解：以著錄之志為據
GUOCHAO = {
    '國史經籍志': 'ming',        # 明焦竑
    '明史藝文志': 'ming',
    '欽定四庫全書總目': 'qing', '四庫全書總目': 'qing',
    '清史稿藝文志': 'qing', '經義考': 'qing', '書目答問': 'qing',
    '宋史藝文志': 'song', '崇文總目': 'song', '直齋書錄解題': 'song',
    '新唐書藝文志': 'sui-tang', '舊唐書經籍志': 'sui-tang', '隋書經籍志': 'sui-tang',
}


def same_period(a, b):
    """兩個 dynasty 寫法是否同代。任一為歧義寫法或不在表中則返 None（不可判）。"""
    if not a or not b:
        return None
    if a in AMBIGUOUS or b in AMBIGUOUS:
        return None
    pa, pb = DYNASTY_PERIOD.get(a), DYNASTY_PERIOD.get(b)
    if pa is None or pb is None:
        return None
    return pa == pb
