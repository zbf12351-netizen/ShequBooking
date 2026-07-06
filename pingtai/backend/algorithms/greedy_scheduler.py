"""
贪心算法优化调度
根据设施可用性和用户偏好优化预约时间段

综合考虑以下因素计算各时间段的优先级分数：
1. 黄金时段（如晚上19:00-21:00）
2. 连续预约（连续时段分数更高）
3. 已有预约数量（预约数较少时段优先推荐）
4. 预约规则符合度（符合开放时间、时长限制等规则）
"""
from datetime import datetime, date, time, timedelta
from models import Booking, Facility, BookingRule
from extensions import db
from sqlalchemy import and_, or_


class GreedyScheduler:
    """贪心调度算法"""

    # 黄金时段定义（晚上19:00-21:00为最佳时段）
    GOLDEN_HOURS = [(19, 21)]  # 黄金时段：19:00-21:00
    GOOD_HOURS = [(8, 10), (17, 19)]  # 较好时段：早8-10，晚17-19
    NORMAL_HOURS = [(10, 12), (14, 18)]  # 一般时段：上午10-12，下午14-18
    OFF_PEAK_HOURS = [(12, 14)]  # 低峰时段：中午12-14

    def get_available_time_slots(self, facility_id, booking_date, duration_minutes=60, user_id=None):
        """
        获取指定设施在指定日期的所有可用时间段
        使用贪心策略优先推荐最优时间段

        Args:
            facility_id: 设施ID
            booking_date: 预约日期
            duration_minutes: 预约时长（分钟）
            user_id: 当前用户ID（用于计算相邻惩罚时排除自己的预约）

        Returns:
            可用时间段列表 [{'start_time': '09:00', 'end_time': '10:00', 'score': 85}, ...]
        """
        # 获取预约规则
        rule = BookingRule.query.filter(
            or_(BookingRule.facility_id == facility_id,
                BookingRule.facility_id.is_(None))
        ).filter_by(status=1).first()

        if not rule:
            # 默认规则
            rule_start = time(8, 0)
            rule_end = time(22, 0)
            min_duration = 30
            max_duration = 240
        else:
            rule_start = rule.start_time if rule.start_time else time(8, 0)
            rule_end = rule.end_time if rule.end_time else time(22, 0)
            min_duration = getattr(rule, 'min_duration', 30) or 30
            max_duration = getattr(rule, 'max_duration', 240) or 240

        # 验证预约时长是否符合规则
        if duration_minutes < min_duration:
            duration_minutes = min_duration
        if duration_minutes > max_duration:
            duration_minutes = max_duration

        # 获取该日期已有的预约（用于冲突检测，包含所有用户）
        all_bookings = Booking.query.filter(
            Booking.facility_id == facility_id,
            Booking.booking_date == booking_date,
            Booking.status.in_(['pending', 'approved'])
        ).all()

        # 获取设施容量
        facility = db.session.get(Facility, facility_id)
        capacity = facility.capacity if facility and facility.capacity else 1

        # 获取当前用户自己的预约（用于连续预约加分）
        user_bookings = []
        if user_id:
            user_id_int = int(user_id) if user_id else None
            user_bookings = Booking.query.filter(
                Booking.facility_id == facility_id,
                Booking.booking_date == booking_date,
                Booking.user_id == user_id_int,
                Booking.status.in_(['pending', 'approved'])
            ).all()
            # 过滤掉时间未设置的预约
            user_bookings = [b for b in user_bookings if b.start_time is not None and b.end_time is not None]

        # 用于冲突检测的预约列表：如果指定了user_id则排除自己的预约
        user_id_int = int(user_id) if user_id else None
        existing_bookings = [b for b in all_bookings if b.user_id != user_id_int] if user_id_int else all_bookings
        # 过滤掉时间未设置的预约
        existing_bookings = [b for b in existing_bookings if b.start_time is not None and b.end_time is not None]
        all_bookings = [b for b in all_bookings if b.start_time is not None and b.end_time is not None]

        print(f"[GREEDY] facility_id={facility_id}, date={booking_date}, 容量={capacity}, 已有预约数={len(all_bookings)}, 用户自己的预约数={len(user_bookings)}, user_id={user_id_int}")
        for b in all_bookings:
            print(f"[GREEDY]   预约: {b.start_time}-{b.end_time}, user_id={b.user_id}, status={b.status}")

        # 获取当前时间（如果是预约今天的日期，只推荐当前时间之后的时段）
        now = datetime.now()
        today = date.today()
        is_today = booking_date == today
        current_time_cutoff = None
        if is_today:
            # 设置一个5分钟后的时间作为截止点（给用户操作时间）
            current_time_cutoff = now + timedelta(minutes=5)

        # 生成所有可能的时间段（以30分钟为单位）
        available_slots = []
        current_time = datetime.combine(booking_date, rule_start)
        end_datetime = datetime.combine(booking_date, rule_end)
        
        print(f"\n[GREEDY] 开始生成时段:")
        print(f"  开放时间: {rule_start}-{rule_end}")
        print(f"  预约时长: {duration_minutes}分钟")
        print(f"  已有预约数: {len(existing_bookings)}")

        while current_time < end_datetime:
            slot_end = current_time + timedelta(minutes=duration_minutes)
            if slot_end.time() <= rule_end:
                # 如果是今天预约，过滤掉已经过去的时段
                if is_today and current_time < current_time_cutoff:
                    print(f"[GREEDY]   时段 {current_time.strftime('%H:%M')}-{slot_end.strftime('%H:%M')}: 已过期，跳过")
                    current_time += timedelta(minutes=30)
                    continue

                # 检查这个时间段是否与已有预约冲突（考虑容量）
                overlapping_count = 0
                conflict_reason = ""
                print(f"\n[GREEDY]   检查时段 {current_time.strftime('%H:%M')}-{slot_end.strftime('%H:%M')}:")
                for booking in existing_bookings:
                    # 跳过时间未设置的预约
                    if booking.start_time is None or booking.end_time is None:
                        continue
                    booking_start = datetime.combine(booking_date, booking.start_time)
                    booking_end = datetime.combine(booking_date, booking.end_time)

                    # 检查时间重叠
                    if not (slot_end <= booking_start or current_time >= booking_end):
                        overlapping_count += 1
                        print(f"       重叠: {booking.start_time}-{booking.end_time}, 当前重叠数={overlapping_count}/{capacity}")
                    else:
                        print(f"       无冲突: {booking.start_time}-{booking.end_time}")

                # 判断是否可用：如果重叠数 >= 容量，则不可用
                is_available = overlapping_count < capacity
                if not is_available:
                    conflict_reason = f"预约已满（{overlapping_count}/{capacity}）"
                    print(f"       -> 时段不可用: {conflict_reason}")
                else:
                    # 如果有容量，检查是否已满并计算分数
                    if overlapping_count > 0:
                        conflict_reason = f"已有 {overlapping_count}/{capacity} 人预约"

                if is_available:
                    # 计算这个时间段的优先级分数
                    print(f"       -> 时段可用，开始计算分数:")
                    score = self.calculate_slot_score(
                        current_time.time(),
                        slot_end.time(),
                        existing_bookings,
                        all_bookings,
                        is_today,
                        current_time_cutoff,
                        booking_date,
                        user_bookings
                    )

                    available_slots.append({
                        'start_time': current_time.strftime('%H:%M'),
                        'end_time': slot_end.strftime('%H:%M'),
                        'score': score
                    })
                    print(f"       最终分数: {score}")
                else:
                    print(f"       不可用: {conflict_reason}")

            current_time += timedelta(minutes=30)  # 每次递增30分钟

        # 按分数降序排序（贪心策略：优先推荐高分时间段）
        available_slots.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"\n[GREEDY] 时段生成完成, 可用时段数: {len(available_slots)}")

        return available_slots

    def calculate_slot_score(self, start_time, end_time, existing_bookings, all_bookings,
                             is_today=False, current_time=None, booking_date=None, user_bookings=None):
        """
        计算时间段的优先级分数
        综合考虑以下因素：
        1. 黄金时段（如晚上19:00-21:00）- 最高优先级
        2. 连续预约（连续时段分数更高）
        3. 已有预约数量（预约数较少时段优先推荐）
        4. 预约规则符合度（符合开放时间、时长限制等规则）

        Returns:
            优先级分数 (0-100)
        """
        # 输入验证：确保时间参数不是 None
        if start_time is None or end_time is None:
            return 0

        score = 0  # 从0开始，所有因素累加
        hour = start_time.hour

        # ========== 1. 黄金时段分数 (最高权重：40分) ==========
        golden_score = self._calculate_golden_hour_score(start_time, is_today, current_time)
        score += golden_score
        print(f"    [分项] 黄金时段: {golden_score}分")

        # ========== 2. 连续预约分数 (最高权重：25分) ==========
        continuity_score = self._calculate_continuity_score(
            start_time, end_time, existing_bookings, user_bookings, booking_date
        )
        score += continuity_score
        print(f"    [分项] 连续预约: {continuity_score}分")

        # ========== 3. 已有预约数量分数 (最高权重：20分) ==========
        booking_count_score = self._calculate_booking_count_score(
            start_time, end_time, existing_bookings
        )
        score += booking_count_score
        print(f"    [分项] 预约数量: {booking_count_score}分")

        # ========== 4. 预约规则符合度分数 (最高权重：15分) ==========
        rule_score = self._calculate_rule_score(start_time, end_time)
        score += rule_score
        print(f"    [分项] 规则符合: {rule_score}分")

        # 确保分数在0-100范围内
        final_score = min(max(score, 0), 100)

        print(f"    [总分] {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}: {final_score}分")
        return final_score

        return final_score

    def _calculate_golden_hour_score(self, start_time, is_today=False, current_time=None):
        """
        计算黄金时段分数
        黄金时段（如晚上19:00-21:00）得分最高
        今天预约时：保留黄金时段基础分 + 时间临近度加分
        """
        # 输入验证
        if start_time is None:
            return 0
        
        hour = start_time.hour
        minute = start_time.minute

        # 第一步：计算基础时段分（无论是否今天都适用）
        if 19 <= hour < 21:
            base_score = 40  # 黄金时段
        elif (8 <= hour < 10) or (17 <= hour < 19):
            base_score = 30  # 较好时段
        elif (10 <= hour < 12) or (14 <= hour < 17):
            base_score = 20  # 一般时段
        elif (12 <= hour < 14) or hour >= 21:
            base_score = 10  # 低峰时段
        else:
            base_score = 15  # 其他时段

        # 第二步：如果今天预约，增加时间临近度加分
        if is_today and current_time:
            # 计算完整的时间差（小时+分钟）
            current_minutes = current_time.hour * 60 + current_time.minute
            slot_minutes = hour * 60 + minute  # 修复：加上分钟

            if slot_minutes > current_minutes:
                time_diff_minutes = slot_minutes - current_minutes
                time_diff_hours = time_diff_minutes / 60

                # 时间越近，加分越多（最高+8分）
                if time_diff_hours <= 0.5:
                    proximity_bonus = 8  # 30分钟内：最高加分
                elif time_diff_hours <= 1:
                    proximity_bonus = 6  # 1小时内
                elif time_diff_hours <= 2:
                    proximity_bonus = 4  # 2小时内
                elif time_diff_hours <= 3:
                    proximity_bonus = 2  # 3小时内
                else:
                    proximity_bonus = 0  # 3小时外：无加分

                return base_score + proximity_bonus
            else:
                return 0  # 已过去的时段

        return base_score

    def _calculate_continuity_score(self, start_time, end_time, existing_bookings,
                                    user_bookings, booking_date):
        """
        计算连续预约分数
        连续时段分数更高（资源利用率更高）
        """
        # 输入验证
        if start_time is None or end_time is None:
            print(f"  [连续性] 输入验证失败, 分数=0")
            return 0

        score = 0
        print(f"  [连续性] 计算 {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}")

        # 检查是否与其他预约相邻（对于资源利用来说是好的）
        is_adjacent_to_other = False
        is_between_bookings = False  # 是否夹在两个预约之间

        # 将预约分为两类：在时间段之前的和之后的
        bookings_before = []  # 在时间段之前的预约（结束时间 < 时段开始时间）
        bookings_after = []   # 在时间段之后的预约（开始时间 > 时段结束时间）

        for booking in existing_bookings:
            # 跳过时间未设置的预约
            if booking.start_time is None or booking.end_time is None:
                continue
            booking_start = datetime.combine(booking_date, booking.start_time)
            booking_end = datetime.combine(booking_date, booking.end_time)
            slot_start = datetime.combine(booking_date, start_time)
            slot_end = datetime.combine(booking_date, end_time)

            # 判断与当前时段的关系
            if booking_end <= slot_start:
                # 预约在时段之前
                if 0 < (slot_start - booking_end).total_seconds() <= 1800:
                    is_adjacent_to_other = True
                bookings_before.append(booking)
            elif booking_start >= slot_end:
                # 预约在时段之后
                if 0 < (booking_start - slot_end).total_seconds() <= 1800:
                    is_adjacent_to_other = True
                bookings_after.append(booking)

        # 检测是否夹在两个预约之间（前一个结束后紧接，后一个开始前紧接）
        if bookings_before and bookings_after:
            # 找最近的前面预约和最近的后面预约
            latest_before = max(bookings_before, key=lambda b:
                (datetime.combine(booking_date, b.end_time)).timestamp())
            earliest_after = min(bookings_after, key=lambda b:
                (datetime.combine(booking_date, b.start_time)).timestamp())

            slot_start_dt = datetime.combine(booking_date, start_time)
            slot_end_dt = datetime.combine(booking_date, end_time)
            before_end_dt = datetime.combine(booking_date, latest_before.end_time)
            after_start_dt = datetime.combine(booking_date, earliest_after.start_time)

            # 如果时间段正好填满两个预约之间的空隙
            gap_before = (slot_start_dt - before_end_dt).total_seconds() / 60
            gap_after = (after_start_dt - slot_end_dt).total_seconds() / 60

            if gap_before <= 30 and gap_after <= 30:
                is_between_bookings = True

        # 计算前后空闲时间（找到最近的前后预约）
        nearest_before_gap = None
        nearest_after_gap = None

        for booking in existing_bookings:
            # 跳过时间未设置的预约
            if booking.start_time is None or booking.end_time is None:
                continue
            booking_end = datetime.combine(booking_date, booking.end_time)
            booking_start = datetime.combine(booking_date, booking.start_time)
            slot_start = datetime.combine(booking_date, start_time)
            slot_end = datetime.combine(booking_date, end_time)

            # 计算与前面预约的间隔（预约结束 < 时段开始）
            if booking_end <= slot_start:
                gap = (slot_start - booking_end).total_seconds() / 60
                if nearest_before_gap is None or gap < nearest_before_gap:
                    nearest_before_gap = gap
            # 计算与后面预约的间隔（预约开始 > 时段结束）
            elif booking_start >= slot_end:
                gap = (booking_start - slot_end).total_seconds() / 60
                if nearest_after_gap is None or gap < nearest_after_gap:
                    nearest_after_gap = gap

        # 判断是否"夹在"两个预约之间（前后间隔都<=30分钟）
        is_between_bookings = (nearest_before_gap is not None and
                                nearest_after_gap is not None and
                                nearest_before_gap <= 30 and
                                nearest_after_gap <= 30)

        # 评分规则：基于与最近预约的间隔
        # 设计原则：用户视角 - 独立时段更自由，应该给高分
        #           夹在预约之间意味着"拥挤"，应该给低分

        if is_between_bookings:
            # 夹在两个预约之间（太拥挤）：低分
            score = 10
            print(f"    [连续性] 夹在预约之间: 10分")
        elif nearest_before_gap is not None and nearest_after_gap is not None:
            # 前后都有预约，但间隔较大
            min_gap = min(nearest_before_gap, nearest_after_gap)
            max_gap = max(nearest_before_gap, nearest_after_gap)
            if max_gap is not None and max_gap <= 60:
                score = 18  # 间隔都在1小时内：较拥挤
            elif max_gap is not None and max_gap <= 120:
                score = 14  # 最大间隔2小时
            elif max_gap is not None and max_gap <= 180:
                score = 10  # 最大间隔3小时
            else:
                score = 8   # 间隔都很大
            print(f"    [连续性] 前后都有预约, 间隔={nearest_before_gap:.0f}/{nearest_after_gap:.0f}分钟: {score}分")
        elif nearest_before_gap is not None or nearest_after_gap is not None:
            # 只有一侧有预约
            if nearest_before_gap is not None and nearest_after_gap is not None:
                gap = min(nearest_before_gap, nearest_after_gap)
            else:
                gap = nearest_before_gap if nearest_before_gap is not None else nearest_after_gap
            if gap is not None and gap <= 60:
                score = 16  # 紧邻预约
            elif gap is not None and gap <= 120:
                score = 12
            elif gap is not None and gap <= 180:
                score = 8
            else:
                score = 6
            print(f"    [连续性] 单侧有预约, 间隔={gap:.0f}分钟: {score}分")
        else:
            # 没有相邻预约时：完全独立，时间段完整，给最高分
            score = 25
            print(f"    [连续性] 独立时段: 25分")

        # 如果与用户自己的预约相邻（可能造成时间冲突），降低分数
        if user_bookings:
            for booking in user_bookings:
                # 跳过时间未设置的预约
                if booking.start_time is None or booking.end_time is None:
                    continue
                booking_start = datetime.combine(booking_date, booking.start_time)
                booking_end = datetime.combine(booking_date, booking.end_time)
                slot_start = datetime.combine(booking_date, start_time)
                slot_end = datetime.combine(booking_date, end_time)

                # 与自己的预约间隔小于60分钟，降低推荐度
                if 0 < (slot_start - booking_end).total_seconds() <= 3600:
                    score = int(score * 0.7)  # 降低30%
                    print(f"    [连续性] 与用户预约相邻: 降低30%到 {score}分")
                elif 0 < (booking_start - slot_end).total_seconds() <= 3600:
                    score = int(score * 0.7)
                    print(f"    [连续性] 与用户预约相邻: 降低30%到 {score}分")

        return score

    def _calculate_booking_count_score(self, start_time, end_time, existing_bookings):
        """
        计算已有预约数量分数
        预约数较少的时段优先推荐（负载均衡）
        """
        # 输入验证
        if start_time is None or end_time is None:
            return 0

        score = 0

        if not existing_bookings:
            # 没有预约的时段：最高分
            return 20
        else:
            # 统计该时段周围（前后1小时内）的预约数量
            booking_date = datetime.combine(date.today(), start_time).date()
            slot_start = datetime.combine(booking_date, start_time)
            slot_end = datetime.combine(booking_date, end_time)

            nearby_bookings = 0
            for booking in existing_bookings:
                # 跳过时间未设置的预约
                if booking.start_time is None or booking.end_time is None:
                    continue
                b_start = datetime.combine(booking_date, booking.start_time)
                b_end = datetime.combine(booking_date, booking.end_time)

                # 计算两个时间段的距离
                # 如果时间段重叠或者在前后1小时内
                if not (slot_end <= b_start - timedelta(hours=1) or slot_start >= b_end + timedelta(hours=1)):
                    nearby_bookings += 1

            # 评分规则：
            # 0个相邻预约：20分
            # 1个相邻预约：15分
            # 2个相邻预约：10分
            # 3个及以上：5分
            if nearby_bookings == 0:
                score = 20
            elif nearby_bookings == 1:
                score = 15
            elif nearby_bookings == 2:
                score = 10
            else:
                score = 5

        return score

    def _calculate_rule_score(self, start_time, end_time):
        """
        计算预约规则符合度分数
        符合开放时间、时长限制等规则
        """
        # 输入验证
        if start_time is None or end_time is None:
            print(f"  [评分] {start_time}-{end_time}: 输入验证失败, 分数=0")
            return 0

        score = 0
        hour = start_time.hour

        # 1. 时间完整性：时段是否完整落在开放时间内
        # 开放时间通常是8:00-22:00，检查是否偏离
        if 8 <= hour < 21:
            score += 8  # 在常规开放时间内
            print(f"  [评分] {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}: 开放时间=+8")
        else:
            score += 4  # 边缘时段
            print(f"  [评分] {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}: 边缘时段=+4")

        # 2. 时长合理性：1-2小时的时段最合理
        start_minutes = hour * 60 + start_time.minute
        end_minutes = (end_time.hour * 60 + end_time.minute) if end_time else 0
        duration = end_minutes - start_minutes

        if 60 <= duration <= 120:
            score += 5  # 1-2小时，最佳时长
            print(f"  [评分]   时长={duration}分钟(1-2小时)=+5")
        elif 30 <= duration < 60:
            score += 3  # 短时段
            print(f"  [评分]   时长={duration}分钟(30-60分钟)=+3")
        elif 120 < duration <= 180:
            score += 3  # 稍长时段
            print(f"  [评分]   时长={duration}分钟(2-3小时)=+3")
        else:
            score += 1  # 超长时段
            print(f"  [评分]   时长={duration}分钟(其他)=+1")

        # 3. 时段边缘：避免在奇怪的时刻开始（如11:37）
        if start_time.minute == 0:
            score += 2  # 整点开始，最佳
            print(f"  [评分]   整点开始=+2")
        elif start_time.minute == 30:
            score += 2  # 半点开始，良好
            print(f"  [评分]   半点开始=+2")
        else:
            score += 0  # 非标准时刻
            print(f"  [评分]   非标准时刻=+0")

        final_score = min(score, 15)
        print(f"  [评分]   规则分={score}, 最终={final_score}")
        return final_score

    def suggest_best_time(self, facility_id, booking_date, duration_minutes=60, user_id=None, preferred_start=None):
        """
        推荐最佳预约时间
        贪心策略：选择得分最高的时间段
        如果用户指定了preferred_start，优先推荐该时间附近的时段
        """
        print("\n" + "="*60)
        print(f"[推荐系统] 开始推荐")
        print(f"  设施ID: {facility_id}")
        print(f"  日期: {booking_date}")
        print(f"  时长: {duration_minutes} 分钟")
        print(f"  用户ID: {user_id}")
        print(f"  期望开始时间: {preferred_start}")
        print("="*60)
        
        available_slots = self.get_available_time_slots(facility_id,
                                                         booking_date,
                                                         duration_minutes,
                                                         user_id)

        if not available_slots:
            print("[推荐系统] 没有可用时段!")
            return None

        print(f"\n[推荐系统] 找到 {len(available_slots)} 个可用时段:")
        for i, slot in enumerate(available_slots, 1):
            print(f"  {i}. {slot['start_time']}-{slot['end_time']}, 分数={slot['score']}")

        # 如果用户指定了期望的开始时间，优先推荐该时间附近的时段
        if preferred_start:
            print(f"\n[推荐系统] 用户期望时间: {preferred_start}, 正在匹配...")
            try:
                preferred_time = datetime.strptime(preferred_start, '%H:%M').time()
                # 找到与用户期望最接近的时段，优先放在推荐列表第一位
                preferred_slot = None
                other_slots = []
                for slot in available_slots:
                    slot_start = datetime.strptime(slot['start_time'], '%H:%M').time()
                    # 计算时间差（分钟）
                    diff = abs((slot_start.hour * 60 + slot_start.minute) - 
                              (preferred_time.hour * 60 + preferred_time.minute))
                    slot['time_diff'] = diff
                    print(f"  比较: 用户期望 {preferred_start} vs 时段 {slot['start_time']}, 差={diff}分钟")
                    if diff <= 60:  # 在1小时内的时段视为候选
                        if preferred_slot is None or diff < preferred_slot['time_diff']:
                            preferred_slot = slot
                            print(f"    -> 更新最佳匹配: {slot['start_time']}-{slot['end_time']}, 差={diff}分钟")
                        else:
                            other_slots.append(slot)
                    else:
                        other_slots.append(slot)
                
                # 重新排序：优先推荐用户选择的时间段
                if preferred_slot:
                    print(f"\n[推荐系统] 最佳匹配: {preferred_slot['start_time']}-{preferred_slot['end_time']}, 差={preferred_slot['time_diff']}分钟")
                    result = [preferred_slot] + [s for s in available_slots if s != preferred_slot]
                    print(f"[推荐系统] 最终推荐结果:")
                    for i, s in enumerate(result[:3], 1):
                        print(f"  {i}. {s['start_time']}-{s['end_time']}, 分数={s['score']}")
                    return result[:3]
                else:
                    print(f"\n[推荐系统] 1小时内没有可用时段")
            except ValueError:
                print(f"[推荐系统] 时间格式错误")
                pass  # 时间格式错误，使用默认排序

        # 返回得分最高的前3个时间段
        print(f"\n[推荐系统] 最终推荐结果 (默认排序):")
        for i, slot in enumerate(available_slots[:3], 1):
            print(f"  {i}. {slot['start_time']}-{slot['end_time']}, 分数={slot['score']}")
        return available_slots[:3]

    def suggest_best_time_with_explanation(self, facility_id, booking_date, duration_minutes=60, user_id=None, preferred_start=None):
        """
        推荐最佳预约时间（带详细说明）
        返回推荐结果及其理由
        """
        available_slots = self.get_available_time_slots(facility_id,
                                                         booking_date,
                                                         duration_minutes,
                                                         user_id)

        if not available_slots:
            return None

        # 如果用户指定了期望的开始时间，优先推荐该时间附近的时段
        if preferred_start:
            try:
                preferred_time = datetime.strptime(preferred_start, '%H:%M').time()
                # 找到与用户期望最接近的时段
                preferred_slot = None
                for slot in available_slots:
                    slot_start = datetime.strptime(slot['start_time'], '%H:%M').time()
                    diff = abs((slot_start.hour * 60 + slot_start.minute) - 
                              (preferred_time.hour * 60 + preferred_time.minute))
                    slot['time_diff'] = diff
                    if preferred_slot is None or diff < preferred_slot['time_diff']:
                        if diff <= 60:
                            preferred_slot = slot
            except ValueError:
                pass
            
            if preferred_slot:
                best_slots = [preferred_slot] + [s for s in available_slots if s != preferred_slot]
                best_slots = best_slots[:3]
            else:
                best_slots = available_slots[:3]
        else:
            best_slots = available_slots[:3]

        # 为每个推荐时段生成说明
        result = []
        for slot in best_slots:
            explanation = self._generate_explanation(slot, available_slots)
            result.append({
                **slot,
                'explanation': explanation
            })

        return result

    def _generate_explanation(self, slot, all_slots):
        """为推荐时段生成说明文字"""
        explanations = []
        score = slot['score']

        # 基于分数给出总体评价
        if score >= 80:
            explanations.append("最佳推荐")
        elif score >= 60:
            explanations.append("推荐")
        elif score >= 40:
            explanations.append("可选择")

        # 基于时段特点
        start_hour = int(slot['start_time'].split(':')[0])
        if 19 <= start_hour < 21:
            explanations.append("黄金时段")
        elif (8 <= start_hour < 10) or (17 <= start_hour < 19):
            explanations.append("较好时段")

        return "，".join(explanations) if explanations else "普通推荐"

    def optimize_multiple_bookings(self, bookings_request):
        """
        优化多个预约请求
        贪心策略：按优先级和可用性分配时间段

        Args:
            bookings_request: [{'facility_id': 1, 'date': '2026-01-21', 'duration': 60}, ...]

        Returns:
            优化后的预约方案
        """
        optimized = []

        # 按设施受欢迎程度排序（预约次数多的优先）
        facilities = Facility.query.filter(
            Facility.facility_id.in_([req['facility_id'] for req in bookings_request])
        ).all()

        facility_priority = {f.facility_id: f.booking_count for f in facilities}

        sorted_requests = sorted(bookings_request,
                               key=lambda x: facility_priority.get(x['facility_id'], 0),
                               reverse=True)

        for request in sorted_requests:
            best_time = self.suggest_best_time(
                request['facility_id'],
                datetime.strptime(request['date'], '%Y-%m-%d').date(),
                request.get('duration', 60)
            )

            if best_time:
                optimized.append({
                    'facility_id': request['facility_id'],
                    'date': request['date'],
                    'suggested_times': best_time
                })

        return optimized
