"""
输出评分矩阵和相似度矩阵为表格文件
用于论文验证协同过滤算法
"""
import sys
import os

backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_dir)

from collections import defaultdict
from models import User, Facility, UserBehavior
from extensions import db
from algorithms.recommender import CollaborativeFilter
from app import create_app
import csv
from datetime import datetime

app = create_app()

with app.app_context():
    cf = CollaborativeFilter()
    scores = cf.get_user_facility_matrix()

    all_facilities = Facility.query.all()
    facility_names = {f.facility_id: f.name for f in all_facilities}

    all_users = User.query.all()
    # 不再需要用户名称映射，直接使用用户ID

    users = sorted(scores.keys())
    facilities = sorted(facility_names.keys())

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # ========== 1. 评分矩阵 ==========
    score_file = os.path.join(base_dir, f"评分矩阵_{timestamp}.csv")
    with open(score_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        header = ['用户\\设施'] + [f"{facility_names.get(fid, f'设施{fid}')}" for fid in facilities]
        writer.writerow(header)
        for uid in users:
            row = [f"用户{uid}"]  # 使用用户ID而非真实姓名
            for fid in facilities:
                row.append(scores[uid].get(fid, 0.0))
            writer.writerow(row)
    print(f"评分矩阵已保存: {score_file}")

    # ========== 2. 相似度矩阵 ==========
    sim_file = os.path.join(base_dir, f"相似度矩阵_{timestamp}.csv")
    with open(sim_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        header = ['用户\\用户'] + [f"用户{uid}" for uid in users]
        writer.writerow(header)
        for uid1 in users:
            row = [f"用户{uid1}"]  # 使用用户ID而非真实姓名
            for uid2 in users:
                if uid1 == uid2:
                    row.append(1.0)
                else:
                    row.append(cf.calculate_user_similarity(uid1, uid2, scores))
            writer.writerow(row)
    print(f"相似度矩阵已保存: {sim_file}")

def str_width(s):
    """计算字符串显示宽度（中文字符=2，英文=1）"""
    width = 0
    for c in str(s):
        if ord(c) > 127:  # 非ASCII字符
            width += 2
        else:
            width += 1
    return width

def pad_center(s, width):
    """居中填充到指定显示宽度"""
    w = str_width(s)
    left = (width - w) // 2
    right = width - w - left
    return ' ' * left + str(s) + ' ' * right

def pad_left(s, width):
    """左对齐填充到指定显示宽度"""
    w = str_width(s)
    return ' ' * (width - w) + str(s)

def pad_right(s, width):
    """右对齐填充到指定显示宽度"""
    w = str_width(str(s))
    return str(s) + ' ' * (width - w)

# ========== 3. 终端输出预览 ==========
# 限制显示数量，避免超出终端宽度
max_display_users = 6
max_display_facilities = 6

display_users = users[:max_display_users]
display_facilities = facilities[:max_display_facilities]

print("\n" + "=" * 70)
print("评分矩阵预览 (前{}个用户 x 前{}个设施)".format(len(display_users), len(display_facilities)))
print("=" * 70)

# 表头
col_width = 10
header = pad_right("用户", col_width) + "".join(pad_center(facility_names.get(f, f)[:6], col_width) for f in display_facilities)
print(header)
print("-" * (col_width + col_width * len(display_facilities)))

# 数据行
for uid in display_users:
    row = pad_right(f"U{uid}"[:6], col_width)  # 使用U+ID格式
    for fid in display_facilities:
        score = scores[uid].get(fid, 0.0)
        row += pad_left(f"{score:.1f}", col_width)
    print(row)

if len(users) > max_display_users or len(facilities) > max_display_facilities:
    print(f"... (共 {len(users)} 用户, {len(facilities)} 设施)")

print("\n" + "=" * 70)
print("相似度矩阵预览 (前{}个用户)".format(len(display_users)))
print("=" * 70)

# 相似度矩阵表头
sim_col_width = 8
sim_header = pad_right("用户", sim_col_width) + "".join(pad_center(f"U{u}"[:4], sim_col_width) for u in display_users)
print(sim_header)
print("-" * (sim_col_width + sim_col_width * len(display_users)))

# 相似度矩阵数据
for uid1 in display_users:
    row = pad_right(f"U{uid1}"[:4], sim_col_width)  # 使用U+ID格式
    for uid2 in display_users:
        if uid1 == uid2:
            row += pad_left("1.00", sim_col_width)
        else:
            sim = cf.calculate_user_similarity(uid1, uid2, scores)
            row += pad_left(f"{sim:.2f}", sim_col_width)
    print(row)

if len(users) > max_display_users:
    print(f"... (共 {len(users)} 用户)")

print("\n完整矩阵已保存到CSV文件，可在Excel中查看")
