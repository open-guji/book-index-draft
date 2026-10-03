"""把 W2 武職選簿 整理本 26 册全部 简→繁（OpenCC s2t），保留与影印本一致的繁体形式。

只改 sections 内 title/content 字符串，不改 metadata 等结构。
之后需 re-render markdown + reindex。
"""
import json
from pathlib import Path
import opencc

CE_DIR = Path('D:/workspace/book-index-draft/Work/1/e/v/1evimvfvm0veo/collated_edition')
cc = opencc.OpenCC('s2t')


def convert_value(v):
    if isinstance(v, str):
        return cc.convert(v)
    if isinstance(v, list):
        return [convert_value(x) for x in v]
    if isinstance(v, dict):
        return {k: convert_value(val) for k, val in v.items()}
    return v


def convert_juan(path: Path):
    d = json.loads(path.read_text(encoding='utf-8'))
    # title 与 sections 全部 convert
    for k in ('title',):
        if k in d:
            d[k] = cc.convert(d[k])
    if 'sections' in d:
        for sec in d['sections']:
            for field in ('title', 'content'):
                if field in sec and isinstance(sec[field], str):
                    sec[field] = cc.convert(sec[field])
    path.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')


def main():
    converted = 0
    for f in sorted(CE_DIR.glob('*.json')):
        if f.name == 'collated_edition_index.json':
            continue
        convert_juan(f)
        converted += 1
        print(f'  {f.name} ✓')
    print(f'\n共 {converted} 册转完繁体')


if __name__ == '__main__':
    main()
