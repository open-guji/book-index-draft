#!/bin/bash
# 先秦 D 类修复全流程。幂等前提：从 book-index-draft 的干净 HEAD 出发。
set -e
cd /workspace
export PYTHONIOENCODING=utf-8

echo "########## 1. 五组 Work 合并"
for pair in "1evincino4a9s 1ev3bbf491j40" "1evjr3lt3ydq8 1ev3bbf36ncao" \
            "1evcmncjvyvwg 1ev3bbf3pdkw0" "1evjr3k5q21a8 1ev7xm2khqigw" \
            "1evr5e3miqk1o 1ev3bck7g5wjk"; do
  echo "-- merge $pair"
  python3 /workspace/preqin-fix/merge_works_v2.py $pair | python3 -c "import json,sys;d=json.load(sys.stdin);print('  ',d['merged'],d['rewritten']['files'],'files, deleted',d['source_deleted'])"
done

echo "########## 2. 清理山海經自指关系"
python3 /workspace/preqin-fix/clean_selfref.py

echo "########## 3. period / dynasty / 作者串位修复"
python3 /workspace/preqin-fix/fix_period_dynasty.py --apply | head -3

echo "########## 4. 补写 description"
python3 /workspace/preqin-fix/fill_descriptions.py --apply | tail -2

echo "########## 5. 补掉数组形式的残留引用"
python3 /workspace/preqin-fix/fix_orphan_refs.py --apply

echo "########## 6. 撤销 CLI 的意外重命名"
python3 /workspace/preqin-fix/undo_rename.py

echo "########## 7. 索引归一化（回填 period + indent=1）"
python3 /workspace/preqin-fix/normalize_index.py | tail -2
