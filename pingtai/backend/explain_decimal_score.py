"""
解释为什么用户对设施的评分为小数
"""
from datetime import datetime

print("=" * 70)
print("用户设施评分为什么是小数？")
print("=" * 70)

# 行为权重
BEHAVIOR_WEIGHTS = {
    'view': 1.0,
    'booking': 3.0,
    'complete': 5.0,
    'cancel': -2.0,
    'favorite': 4.0
}

# 时间衰减参数
DECAY_DAYS = 30
DECAY_RATE = 0.1
DECAY_MIN = 0.5

def calc_decay(created_at_str):
    """计算时间衰减因子"""
    created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
    now = datetime.now()
    days = (now - created_at).days
    
    print(f"  行为时间: {created_at_str}")
    print(f"  距今天数: {days} 天")
    
    if days <= DECAY_DAYS:
        decay = 1.0
        print(f"  {days} ≤ {DECAY_DAYS}，衰减因子 = 1.0 (无衰减)")
    else:
        periods = (days - DECAY_DAYS) / DECAY_DAYS
        decay = max(DECAY_MIN, 1.0 - periods * DECAY_RATE)
        print(f"  {days} > {DECAY_DAYS}")
        print(f"  衰减周期 = ({days} - {DECAY_DAYS}) / {DECAY_DAYS} = {periods:.4f}")
        print(f"  衰减因子 = max(0.5, 1.0 - {periods:.4f} × 0.1) = {decay:.4f}")
    
    return decay

print("\n" + "-" * 70)
print("示例1: 用户40对羽毛球馆(设施2)的评分计算")
print("-" * 70)

print("\n行为记录:")
behaviors = [
    ('2026-04-04 17:36:04', 'view'),
    ('2026-04-04 17:36:04', 'view'),
    ('2026-04-04 17:37:11', 'view'),
    ('2026-04-04 17:37:11', 'view'),
]

total_score = 0
for i, (time_str, btype) in enumerate(behaviors, 1):
    print(f"\n第{i}次行为: {btype}")
    decay = calc_decay(time_str)
    weighted = BEHAVIOR_WEIGHTS[btype] * decay
    total_score += weighted
    print(f"  评分 = 权重({BEHAVIOR_WEIGHTS[btype]}) × 衰减({decay:.4f}) = {weighted:.4f}")

print(f"\n" + "=" * 70)
print(f"用户40对羽毛球馆的 总评分 = {total_score:.4f}")
print("=" * 70)

print("\n" + "-" * 70)
print("示例2: 如果有 booking 和 complete 行为")
print("-" * 70)

behaviors2 = [
    ('2026-04-04 17:36:04', 'view', 1.0),
    ('2026-04-04 17:40:00', 'view', 1.0),
    ('2026-04-04 17:45:00', 'booking', 3.0),
    ('2026-04-04 18:00:00', 'complete', 5.0),
]

total2 = 0
for time_str, btype, expected_decay in behaviors2:
    print(f"\n行为: {btype}, 时间: {time_str}")
    decay = calc_decay(time_str)
    weighted = BEHAVIOR_WEIGHTS[btype] * decay
    total2 += weighted
    print(f"  评分 = {BEHAVIOR_WEIGHTS[btype]} × {decay:.4f} = {weighted:.4f}")

print(f"\n总评分 = {total2:.4f}")

print("\n" + "=" * 70)
print("结论")
print("=" * 70)
print("""
评分 = Σ(行为权重 × 时间衰减因子)

出现小数的原因：
1. 【时间衰减因子是小数】
   - 行为发生在30天前以上时，衰减因子 < 1.0
   - 例如: 43天前 → 衰减 = max(0.5, 1.0 - 0.13 × 0.1) = 0.987

2. 【多次行为的累加】
   - 用户可能对同一设施有多次行为
   - 每次行为的评分累加

3. 【不同行为类型的组合】
   - view(权重1.0) + booking(权重3.0) + complete(权重5.0)
   - 组合后形成小数
""")
