# -*- coding: utf-8 -*-
"""老子／道德經 原典—注疏体系重整：计划数据。

原典定为 1evkaeh09axhc《道德經》，additional_titles 加《老子》。
注本统一命名「老子＋撰者＋體裁」，original_title 记原书书名。
有傳世專名者保留原名（《老子道德經品》《老子河上公章句》）。
"""

CANON = '1evkaeh09axhc'          # 原典《道德經》
MAGNET = '1evcmnccovx1c'         # 待拆解的磁铁条目《老子》

# ── P1 并入原典（都是原典层的志书著录，非注本）──
MERGE_INTO_CANON = [
    ('1evcmncbkb2f4', '隋志「《老子道德經》二卷周柱下史李耳撰」為原典著錄，撰人誤標作鐘會'),
    ('1evr5e3mifbg9', '直齋書錄解題「老子道德經」無撰人，原典著錄'),
    ('1evjr364pnb40', '續修四庫所收為馬王堆帛書影印本，屬版本層；著錄併入原典，另宜建 Book'),
]

# ── P2〜P4 注本合并：正条 ← [并入者...]  ──
MERGE_GROUPS = {
    # 王弼注：正条 bk=3、三國藝文志考證最详
    '1evftepodelfk': ['1ev3bcqaotbls', '1evkao1qdl81s', '1evkpy1pzn20w'],
    # 河上公：正条 desc 最完整
    '1evqp46oh0sg0': ['1evcua6zf603k', '1evkpxj94h98g', '1evgpn7pot340', '1evcsxpgs7hmo'],
    # 梁曠：正条题名最全（舊唐志）
    '1evcpd0xjm03k': ['1evcs0lwxu41s', '1evgpn8r5a9s0'],
    # 以下 6 组：正条取舊唐志系列（命名已规范且已有 original_title）
    '1evcua71obpc0': ['1evdxnrl5i7sw'],   # 孫登
    '1evcua74xdp1c': ['1evdxnsdafaio'],   # 成玄英
    '1evcua749nnr4': ['1evdxnrtochs0'],   # 楊上善
    '1evcua71d35s0': ['1evdxnrjor400'],   # 蜀才
    '1evcua74l7fuo': ['1evdxnrwkaio0'],   # 辟閭仁諝
    '1evcua73yf474': ['1evdxnrs8j3ls'],   # 傅奕／傅弈（異體）
}

# ── 正条的题名与撰者订正 ──
RETITLE = {
    '1evftepodelfk': dict(title='老子王弼注',
                          authors=[dict(name='王弼', role='注', dynasty='三國魏')]),
    '1evqp46oh0sg0': dict(title='老子河上公章句',
                          authors=[dict(name='河上公', role='章句', dynasty='西漢',
                                        note='託名。學界主流判東漢中後期至魏晉間道教徒編纂')]),
    '1evcpd0xjm03k': dict(title='老子道德經品',
                          authors=[dict(name='梁曠', role='注', dynasty='北周',
                                        note='安定人，周文帝侍讀十二人之一。《唐志》題《道德經品》')]),
}

# ── P5 语序倒置／冗赘的注本改名（統一「老子＋撰者＋體裁」）──
RENAME = {
    '1evdxnrmm9bls': '老子安丘望之章句',      # 安丘望之老子章句
    '1evdxnrqu9w5c': '老子馮廓指歸',          # 馮廓老子指歸
    '1evdxnrxyuyo0': '老子賈大隱述義',        # 賈大隱老子述義
    '1evdxnsaeh9mo': '老子陸德明疏',          # 陸德明老子疏
    '1evdxnsbux4w0': '老子陳庭玉疏',          # 陳庭玉老子疏
    '1evdxnsivrcw0': '老子梁簡文帝私記',      # 梁簡文帝老子私記
    '1evdxnro1g8ow': '老子葛洪序訣',          # 葛洪老子道德經序訣
    '1evdxnrpg0oow': '老子李軌音',            # 李軌老子音
    '1evdxnrzg8jk0': '老子盧藏用注',          # 已合规，仅统一
    '1evdxns0vfgn4': '老子邢南和注',
    '1evdxns2bvbwg': '老子馮朝隱注',
    '1evdxns42x9mo': '老子白履忠注',
    '1evdxns5qutxc': '老子李播注',
    '1evdxns7cahvk': '老子尹知章注',
    '1evdxnseoohz4': '老子孫思邈注',
    '1evdxnsoeaadc': '老子劉進喜通諸論',      # 道士劉進喜老子通諸論
    '1evgpne567l6o': '老子呂氏昌言',          # 老子昌言（呂氏）
}

# ── P6 非《老子》注本，从原典关系中剔出 ──
NOT_LAOZI_COMMENTARY = {
    '1evdxnsk8rm68': '注的是《老子西升經》，道教另一部書',
    '1evdxnsln0tmo': '注的是《老子西升經》',
    '1evdxnsg3vf28': '兼記老子、莊子、周易三書之學',
    '1evdxnrf9k2yo': '道教衍生（神符易），非注本',
    '1evdxno08hvcw': '道教衍生（心鏡），非注本',
    '1evdxnsn0cbgg': '道教衍生（玄譜），非注本',
}

# ── 原典 description ──
CANON_DESC = {
    'text': '道家根本經典，全書五千餘言，分《道經》《德經》兩篇，故稱《道德經》；'
            '先秦兩漢多逕稱《老子》，唐以後尊為《道德真經》。'
            '舊題周柱下史李耳（老聃）撰，《隋書·經籍志》著錄「《老子道德經》二卷，周柱下史李耳撰」。'
            '其成書年代與作者聚訟已久：《史記·老子韓非列傳》已載老子其人三說並存，'
            '近世或主春秋末年老聃自著，或主戰國中晚期成編。'
            '出土文獻大幅改寫了此書的流傳認識——郭店楚墓竹簡本（戰國中期，甲乙丙三組，'
            '為現存最早鈔本）、馬王堆漢墓帛書甲乙本（德經在前、道經在後）、'
            '北京大學藏西漢竹書本，與傳世本章序、文字均有出入。'
            '注本自漢以降不絕，河上公章句與王弼注並稱兩大古注，唐玄宗、宋徽宗、明太祖、'
            '清世祖皆有御注，歷代注家逾七百。',
    'sources': ['隋書經籍志', '史記·老子韓非列傳'],
}
