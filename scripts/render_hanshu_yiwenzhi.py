"""从漢志 collated_edition json 生成 md 框架（第一遍，不识别 ⟨⟩ 小注）。

仅用于首次搬迁。后续细节（⟨...⟩ 包裹班固自注）第二遍再加工。
已手动精细处理过的卷（方技略/六藝略/總序）不要重跑。
"""
import json
import sys
from pathlib import Path

PREFIXES = ['諸子', '六藝', '方技', '兵書', '詩賦', '數術']


def extract_class_name(title: str) -> str:
    for p in PREFIXES:
        if title.startswith(p):
            title = title[len(p):]
            break
    if title.endswith('類'):
        title = title[:-1]
    return title


def render_juan(juan_path: Path) -> str:
    j = json.loads(juan_path.read_text(encoding='utf-8'))
    top_title = j.get('title', '')
    lines = [f'# {top_title}', '']
    prev_book_content = None  # 连续相同 content 的书目去重（多 Work 共用 content）
    for sec in j['sections']:
        typ = sec.get('type', '')
        content = sec.get('content', '').strip()
        title = sec.get('title', '')
        if typ == '类':
            lines += [f'## {extract_class_name(title)}', '']
            if content:
                lines += [content, '']
            prev_book_content = None
        elif typ == '书':
            if content:
                if content == prev_book_content:
                    continue
                lines += [content, '']
                prev_book_content = content
        elif typ in ('结语', '序'):
            if content:
                for para in content.split('\n'):
                    para = para.strip()
                    if para:
                        lines += [para, '']
            prev_book_content = None
    while lines and lines[-1] == '':
        lines.pop()
    return '\n'.join(lines) + '\n'


def main():
    base = Path('Work/1/e/u/1euhm19a23jsw/collated_edition')
    text_dir = base / 'text'
    text_dir.mkdir(exist_ok=True)
    targets = sys.argv[1:] or ['諸子略', '詩賦略', '兵書略', '數術略']
    for juan in targets:
        src = base / f'{juan}.json'
        dst = text_dir / f'{juan}.md'
        md = render_juan(src)
        dst.write_text(md, encoding='utf-8')
        print(f'Wrote {dst} ({len(md)} chars)')


if __name__ == '__main__':
    main()
