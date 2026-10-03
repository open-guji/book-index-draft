"""对漢志目录下所有 json 和 md 做简→繁字符级统一。

关键：json 里仅对文本字段（title/content/author_info/description/name）做替换，
不动 type/level/work_id 等结构字段，避免破坏 section.type 的 5 种标准值。
md 文件可以整体替换。
"""
import json
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

# 只对这些字段做繁化；避开 type/level/work_id 等结构字段
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
    root = Path('Work/1/e/u/1euhm19a23jsw')
    changed = 0
    for f in root.glob('**/*.json'):
        obj = json.loads(f.read_text(encoding='utf-8'))
        diff = convert_json_obj(obj)
        if diff:
            f.write_text(
                json.dumps(obj, ensure_ascii=False, indent=2) + '\n',
                encoding='utf-8',
            )
            changed += 1
            print(f'{f}: {diff} chars changed (json)')
    for f in root.glob('**/*.md'):
        original = f.read_text(encoding='utf-8')
        converted = convert(original)
        if original != converted:
            f.write_text(converted, encoding='utf-8')
            changed += 1
            n_diff = sum(1 for a, b in zip(original, converted) if a != b)
            print(f'{f}: {n_diff} chars changed (md)')
    print(f'Total files changed: {changed}')


if __name__ == '__main__':
    main()
