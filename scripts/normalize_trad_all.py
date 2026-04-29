"""对所有 Work 下 collated_edition 的 json+md 做简→繁字符级统一。

json: 仅替换文本字段（title/content/author_info/description/name/note），
不动 type/level/work_id 等结构字段。
md: 全文替换。
"""
import json
import sys
from pathlib import Path

SIMP2TRAD = {
    '与': '與', '见': '見', '儿': '兒', '龙': '龍', '庞': '龐', '轸': '軫',
    '汤': '湯', '龟': '龜', '鸟': '鳥', '鸣': '鳴', '战': '戰', '国': '國',
    '岁': '歲', '风': '風', '师': '師', '时': '時', '学': '學', '书': '書',
    '称': '稱', '内': '內', '热': '熱', '鹊': '鵲', '伤': '傷', '颠': '顛',
    '疭': '瘲', '妇': '婦', '尧': '堯', '盘': '盤', '养': '養', '戏': '戲',
    '马': '馬', '鱼': '魚', '庄': '莊', '阳': '陽', '阴': '陰', '齐': '齊',
    '邓': '鄧', '赵': '趙', '韩': '韓', '陈': '陳', '汉': '漢', '刘': '劉',
    '张': '張', '孙': '孫', '录': '錄', '万': '萬', '听': '聽', '灵': '靈',
    '无': '無', '为': '為', '杀': '殺', '乱': '亂', '语': '語', '说': '說',
    '论': '論', '议': '議', '诗': '詩', '记': '記', '礼': '禮', '经': '經',
    '传': '傳', '会': '會', '们': '們', '对': '對', '东': '東', '园': '園',
    '编': '編', '终': '終', '结': '結', '贵': '貴', '卖': '賣', '图': '圖',
    '铁': '鐵', '钟': '鐘', '谊': '誼', '谣': '謠', '辽': '遼', '颛': '顓',
    '鲍': '鮑', '声': '聲', '庙': '廟', '买': '買', '围': '圍', '辑': '輯',
    '邻': '鄰', '郑': '鄭', '陇': '隴', '隐': '隱',
}

TEXT_FIELDS = {'title', 'content', 'author_info', 'description', 'name', 'note'}


def convert(text: str) -> str:
    for s, t in SIMP2TRAD.items():
        text = text.replace(s, t)
    return text


def convert_json_obj(obj):
    changes = [0]

    def walk(o):
        if isinstance(o, dict):
            for k, v in list(o.items()):
                if k in TEXT_FIELDS and isinstance(v, str):
                    new = convert(v)
                    if new != v:
                        changes[0] += sum(1 for a, b in zip(v, new) if a != b)
                        o[k] = new
                else:
                    walk(v)
        elif isinstance(o, list):
            for item in o:
                walk(item)

    walk(obj)
    return changes[0]


def main():
    ce_dirs = sorted(Path('Work').glob('**/collated_edition'))
    json_changed = md_changed = 0
    for d in ce_dirs:
        for jf in d.glob('*.json'):
            try:
                obj = json.loads(jf.read_text(encoding='utf-8'))
            except Exception as e:
                print(f'SKIP {jf}: {e}', file=sys.stderr)
                continue
            diff = convert_json_obj(obj)
            if diff:
                jf.write_text(
                    json.dumps(obj, ensure_ascii=False, indent=2) + '\n',
                    encoding='utf-8',
                )
                json_changed += 1
        text_dir = d / 'text'
        if text_dir.exists():
            for mf in text_dir.glob('*.md'):
                original = mf.read_text(encoding='utf-8')
                converted = convert(original)
                if original != converted:
                    mf.write_text(converted, encoding='utf-8')
                    md_changed += 1
    print(f'json changed: {json_changed}, md changed: {md_changed}')


if __name__ == '__main__':
    main()
