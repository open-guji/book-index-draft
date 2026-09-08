#!/usr/bin/env python3
"""題名重出 Round 2：續合併低風險「題名+撰人/注者」式空殼 Work。"""

import fix_title_duplicates_round1 as base

base.OUT = base.ROOT / ".claude" / "known-issues" / "題名重出_round2已合併.json"
base.ROUND_NAME = "題名重出 Round 2"
base.PAIRS = [
    ("1evc5pccs6m0w", "1evcpct2znqio", "尚書新釋李顒撰 → 尚書新釋"),
    ("1evc5pct57f28", "1evfublcdml1c", "禮音劉昌宗撰 → 禮音"),
    ("1evc5pd3t5b7k", "1evcpk00jqrk0", "禮記要鈔緱氏撰 → 禮記要鈔"),
    ("1evc5pdqvgk5c", "1evfubodnmf40", "春秋左氏函傳義干寶撰 → 春秋左氏函傳義"),
    ("1evc5pdxk4iyo", "1evftejg7rmdc", "春秋外傳章句王肅撰 → 春秋外傳章句"),
    ("1evc5pdxot340", "1evgoq5so1mo0", "春秋外傳國語韋昭注 → 春秋外傳國語"),
    ("1evc5pe005g5c", "1evfubqe4jv9c", "春秋穀梁傳孔君揩撰 → 春秋穀梁傳"),
    ("1evc5pe0558u8", "1evfubptoiadc", "春秋穀梁傳義徐邈撰 → 春秋穀梁傳義"),
    ("1evc5pee74xds", "1evgor8rltukg", "廣雅音曹憲撰 → 廣雅音"),
    ("1evc5pesbb9q8", "1evgoravuurk0", "勸學蔡邕撰 → 勸學"),
    ("1evc5pf4qxkow", "1evgorbqsa96o", "古今字圖雜錄曹憲撰 → 古今字圖雜錄"),
    ("1evcml0zqmg3k", "1evgpibstx7gg", "鮑泉新儀 → 新儀"),
    ("1evdx90z4m7sw", "1evcml1zrlh4w", "司馬彪續漢書 → 續漢書"),
    ("1evdxnq2p7wg0", "1evgoq3qi8wlc", "張傑春秋圖 → 春秋圖"),
    ("1evdxnrcfhhc0", "1evgpha1tsg00", "包諝河洛春秋 → 河洛春秋"),
]

if __name__ == "__main__":
    base.main()
