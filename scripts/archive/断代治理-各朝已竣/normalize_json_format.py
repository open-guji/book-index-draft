#!/usr/bin/env python3
"""全庫 JSON 書寫格式歸一化。

約定（見 SCHEMA.md〈JSON 書寫格式〉）：
    indent=2、ensure_ascii=False、分隔符預設（": " / ", "）、
    鍵序**不重排**（保持檔中原序）、檔尾一個換行。

用法：
    python3 scripts/normalize_json_format.py                    # 乾跑，只印
    python3 scripts/normalize_json_format.py --apply            # 真跑
    python3 scripts/normalize_json_format.py --apply --skip-list <file>
        # 跳過清單中的路徑（用於避開在飛分支所改之檔，見 .claude/plans/升格並行方案.md §六）
    python3 scripts/normalize_json_format.py --apply --newline-only
        # 只補檔尾換行，不動縮排
    python3 scripts/normalize_json_format.py --apply --indent-only
        # 只改縮排（順帶補該檔尾換行）；缺尾換行而縮排本已合者不動

安全性：每一檔改寫後以 `json.loads(新) == json.loads(舊)` 驗證語義不變，
不等則跳過並報出。故本腳本不會改變任何一條資料，只改寫書寫格式。
"""
import json, glob, os, re, sys, argparse

INDENT = 2
SKIP_PREFIX = ('node_modules/', 'book-index/', '.git/')


def probe_indent(raw):
    for ln in raw.split('\n')[1:]:
        m = re.match(r'^( +)\S', ln)
        if m:
            return len(m.group(1))
    return None


def targets():
    for f in sorted(glob.glob('**/*.json', recursive=True)):
        if any(f.startswith(p) for p in SKIP_PREFIX):
            continue
        yield f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--skip-list')
    ap.add_argument('--newline-only', action='store_true')
    ap.add_argument('--indent-only', action='store_true',
                    help='只改縮排（順帶補該檔尾換行），不單獨處理缺尾換行之檔')
    ap.add_argument('--only-prefix', default='')
    a = ap.parse_args()

    skip = set()
    if a.skip_list:
        for ln in open(a.skip_list, encoding='utf-8'):
            ln = ln.strip()
            if ln.startswith('"'):          # git 對非 ASCII 路徑加引號並轉義
                ln = (ln[1:-1].encode('latin1', 'backslashreplace')
                      .decode('unicode_escape').encode('latin1').decode('utf-8'))
            if ln:
                skip.add(ln)

    n_ind = n_nl = n_skip = n_bad = 0
    bad = []
    for f in targets():
        if a.only_prefix and not f.startswith(a.only_prefix):
            continue
        if f in skip:
            n_skip += 1
            continue
        try:
            raw = open(f, encoding='utf-8').read()
        except Exception:
            continue
        if not raw.strip():
            continue
        cur = probe_indent(raw)
        need_ind = (not a.newline_only) and cur is not None and cur != INDENT
        need_nl = not raw.endswith('\n')
        if not (need_ind or need_nl):
            continue
        if a.indent_only and not need_ind:
            continue
        if need_ind:
            try:
                obj = json.loads(raw)
            except Exception as e:
                n_bad += 1
                bad.append((f, 'parse: %s' % e))
                continue
            new = json.dumps(obj, ensure_ascii=False, indent=INDENT) + '\n'
            try:
                if json.loads(new) != obj:
                    raise ValueError('round-trip 不等')
            except Exception as e:
                n_bad += 1
                bad.append((f, str(e)))
                continue
            n_ind += 1
        else:
            new = raw + '\n'
            n_nl += 1
        if a.apply:
            open(f, 'w', encoding='utf-8').write(new)

    print('改縮排 %d　只補尾換行 %d　跳過（在飛）%d　驗證不過 %d%s'
          % (n_ind, n_nl, n_skip, n_bad, '' if a.apply else '　（乾跑，未寫檔）'))
    for x in bad[:10]:
        print('  !!', x)
    return 1 if n_bad else 0


if __name__ == '__main__':
    sys.exit(main())
