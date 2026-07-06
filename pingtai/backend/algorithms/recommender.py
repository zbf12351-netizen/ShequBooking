"""
协同过滤推荐算法
基于用户行为和相似用户偏好进行设施推荐
"""
import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta
from sqlalchemy import func
from models import UserBehavior, Booking, Facility, Favorite
from extensions import db

class CollaborativeFilter:
    """协同过滤推荐系统"""
    
    def __init__(self):
        self.behavior_weights = {
            'view': 1.0,
            'booking': 3.0,
            'complete': 5.0,
            'cancel': -2.0,
            'favorite': 4.0  # 收藏行为权重
        }
        # 时间衰减参数：30天内行为保持完整权重，之后每30天衰减10%
        self.decay_days = 30
        self.decay_rate = 0.1
        # 行为条数低于此值视为新用户：走「同类热门」优先，不做协同过滤
        # （避免刚好 5 条就切到老用户，协同过滤压过运动类偏好）
        self.new_user_behavior_threshold = 10
    
    def get_user_facility_matrix(self):
        """构建用户-设施评分矩阵
        
        查询UserBehavior表中所有用户行为记录，对不同行为赋予不同分数：
        浏览1.0分、预约3.0分、完成为5.0分、收藏为4.0分、取消为-2.0分
        同时考虑时间衰减：越近期的行为权重越高
        """
        behaviors = UserBehavior.query.all()
        scores = defaultdict(lambda: defaultdict(float))
        now = datetime.now()
        
        for b in behaviors:
            # 计算时间衰减因子
            decay_factor = 1.0
            if b.created_at:
                days_ago = (now - b.created_at).days
                if days_ago > self.decay_days:
                    # 每超过decay_days天，衰减decay_rate
                    decay_periods = (days_ago - self.decay_days) / self.decay_days
                    decay_factor = max(0.5, 1.0 - decay_periods * self.decay_rate)
            
            base_weight = self.behavior_weights[b.behavior_type]
            scores[b.user_id][b.facility_id] += base_weight * decay_factor
        return scores
    
    def calculate_user_similarity(self, uid1, uid2, scores):
        """计算两个用户之间的余弦相似度
        
        获取两个用户共同评价过的设施集合，计算评分向量的点积除以模长
        """
        common = set(scores[uid1].keys()) & set(scores[uid2].keys())
        if not common: return 0.0
        num = sum(scores[uid1][f] * scores[uid2][f] for f in common)
        den = np.sqrt(sum(scores[uid1][f]**2 for f in common)) * \
              np.sqrt(sum(scores[uid2][f]**2 for f in common))
        return num / den if den else 0.0
    
    def find_similar_users(self, user_id, scores, top_n=10):
        """找到与目标用户最相似的N个用户"""
        similarities = []
        # 使用 list() 复制键列表，避免迭代过程中字典大小改变
        for other in list(scores.keys()):
            if other != user_id:
                sim = self.calculate_user_similarity(user_id, other, scores)
                if sim > 0: similarities.append((other, sim))
        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_n]

    def recommend_for_user(self, user_id, limit=10):
        """为用户推荐设施
        
        通过协同过滤找出相似用户，结合用户自身偏好生成推荐
        融合策略：协同过滤 + 类别扩展 + 热门推荐
        """
        # 排除已预约的设施
        booked = {b.facility_id for b in Booking.query.filter(
            Booking.user_id == user_id,
            Booking.status.in_(['pending', 'approved', 'completed'])
        ).all()}
        
        # 获取用户行为数量，判断用户类型
        behavior_count = UserBehavior.query.filter_by(user_id=user_id).count()
        is_new_user = behavior_count < self.new_user_behavior_threshold

        scores = self.get_user_facility_matrix()
        recs = defaultdict(float)
        rec_sources = {}  # 记录推荐来源

        # 各类别行为占比（0~1），老用户用于压制「全局热门压过兴趣类」
        category_weight = self._get_user_category_weights(user_id)

        # ========== 新用户策略：类别偏好 + 热门推荐 ==========
        if is_new_user:
            user_categories = self._get_user_preferred_categories(user_id)

            if user_categories:
                # 只在用户偏好的类别里取热门，避免全局前几名全是活动场所
                category_popular = self.recommend_popular_facilities(
                    limit=limit * 3,
                    exclude_user_id=user_id,
                    only_categories=user_categories,
                )
                for idx, f in enumerate(category_popular):
                    if f.facility_id not in booked:
                        rank_bonus = max(20, 60 - idx * 3)
                        recs[f.facility_id] += rank_bonus
                        rec_sources[f.facility_id] = '类别热门'

            if len(recs) < limit:
                popular = self.recommend_popular_facilities(
                    limit=limit * 2,
                    exclude_user_id=user_id,
                )
                for idx, f in enumerate(popular):
                    if f.facility_id not in booked and f.facility_id not in recs:
                        recs[f.facility_id] += max(10, 35 - idx * 2)
                        rec_sources[f.facility_id] = '全局热门'

        # ========== 老用户策略：协同过滤 + 强类别亲和 + 同类热门 ==========
        else:
            similar_users = self.find_similar_users(user_id, scores)
            # 若没有有效相似用户，退化为「同类热门 + 全局热门」
            if not similar_users:
                user_categories = self._get_user_preferred_categories(user_id) or list(category_weight.keys())
                if user_categories:
                    category_popular = self.recommend_popular_facilities(
                        limit=limit * 3,
                        exclude_user_id=user_id,
                        only_categories=user_categories,
                    )
                    for idx, f in enumerate(category_popular):
                        if f.facility_id not in booked:
                            recs[f.facility_id] += max(25, 55 - idx * 3)
                if len(recs) < limit:
                    for idx, f in enumerate(
                        self.recommend_popular_facilities(limit=limit * 2, exclude_user_id=user_id)
                    ):
                        if f.facility_id not in booked and f.facility_id not in recs:
                            recs[f.facility_id] += max(8, 28 - idx * 2)
            else:
                # 只使用相似度 > 0.5 的用户，减少噪声干扰
                for uid, sim in similar_users:
                    if sim > 0.5:  # 相似度阈值过滤
                        for fid, s in scores[uid].items():
                            recs[fid] += sim * s
                            rec_sources[fid] = rec_sources.get(fid, set()) | {'协同过滤'}

                for fid, s in scores.get(user_id, {}).items():
                    recs[fid] += s * 0.8
                    rec_sources[fid] = rec_sources.get(fid, set()) | {'自身偏好'}

                user_categories = self._get_user_preferred_categories(user_id)
                if user_categories:
                    category_popular = self.recommend_popular_facilities(
                        limit=limit * 3,
                        exclude_user_id=user_id,
                        only_categories=user_categories,
                    )
                    for idx, f in enumerate(category_popular):
                        if f.facility_id not in booked:
                            rank_bonus = max(15, 45 - idx * 2)
                            recs[f.facility_id] += rank_bonus
                            rec_sources[f.facility_id] = rec_sources.get(f.facility_id, set()) | {'类别扩展'}

                if len(recs) < limit:
                    for idx, f in enumerate(
                        self.recommend_popular_facilities(limit=limit * 2, exclude_user_id=user_id)
                    ):
                        if f.facility_id not in booked and f.facility_id not in recs:
                            recs[f.facility_id] += max(5, 20 - idx * 2)
                            rec_sources[f.facility_id] = rec_sources.get(f.facility_id, set()) | {'热门兜底'}

            # 按浏览行为占比给「设施所属类别」加权，避免协同过滤把无关大类顶到前面
            if category_weight and recs:
                max_w = max(category_weight.values()) or 1.0
                for fid in list(recs.keys()):
                    fac = Facility.query.get(fid)
                    if not fac or not fac.category:
                        continue
                    w = category_weight.get(fac.category, 0.0)
                    recs[fid] += 35.0 * (w / max_w)
        
        # ========== 归一化处理 ==========
        if recs:
            max_score = max(recs.values())
            if max_score > 0:
                for fid in recs:
                    recs[fid] = recs[fid] / max_score * 100
        
        # 过滤已预约设施并排序返回
        result = sorted(recs.items(), key=lambda x: x[1], reverse=True)
        return [Facility.query.get(fid) for fid, _ in result
                if fid not in booked][:limit]

    def recommend_for_user_with_sources(self, user_id, limit=10):
        """为用户推荐设施（带推荐来源）

        返回: (推荐设施列表, 推荐来源字典 {facility_id: 来源标签})
        """
        # 排除已预约的设施
        booked = {b.facility_id for b in Booking.query.filter(
            Booking.user_id == user_id,
            Booking.status.in_(['pending', 'approved', 'completed'])
        ).all()}

        # 获取用户行为数量，判断用户类型
        behavior_count = UserBehavior.query.filter_by(user_id=user_id).count()
        is_new_user = behavior_count < self.new_user_behavior_threshold

        scores = self.get_user_facility_matrix()
        recs = defaultdict(float)
        rec_sources = {}  # 记录推荐来源

        # 各类别行为占比（0~1），老用户用于压制「全局热门压过兴趣类」
        category_weight = self._get_user_category_weights(user_id)

        # ========== 新用户策略：类别偏好 + 热门推荐 ==========
        if is_new_user:
            user_categories = self._get_user_preferred_categories(user_id)

            if user_categories:
                category_popular = self.recommend_popular_facilities(
                    limit=limit * 3,
                    exclude_user_id=user_id,
                    only_categories=user_categories,
                )
                for idx, f in enumerate(category_popular):
                    if f.facility_id not in booked:
                        rank_bonus = max(20, 60 - idx * 3)
                        recs[f.facility_id] += rank_bonus
                        rec_sources[f.facility_id] = '类别热门'

            if len(recs) < limit:
                popular = self.recommend_popular_facilities(
                    limit=limit * 2,
                    exclude_user_id=user_id,
                )
                for idx, f in enumerate(popular):
                    if f.facility_id not in booked and f.facility_id not in recs:
                        recs[f.facility_id] += max(10, 35 - idx * 2)
                        rec_sources[f.facility_id] = '全局热门'

        # ========== 老用户策略：协同过滤 + 强类别亲和 + 同类热门 ==========
        else:
            similar_users = self.find_similar_users(user_id, scores)
            if not similar_users:
                user_categories = self._get_user_preferred_categories(user_id) or list(category_weight.keys())
                if user_categories:
                    category_popular = self.recommend_popular_facilities(
                        limit=limit * 3,
                        exclude_user_id=user_id,
                        only_categories=user_categories,
                    )
                    for idx, f in enumerate(category_popular):
                        if f.facility_id not in booked:
                            recs[f.facility_id] += max(25, 55 - idx * 3)
                if len(recs) < limit:
                    for idx, f in enumerate(
                        self.recommend_popular_facilities(limit=limit * 2, exclude_user_id=user_id)
                    ):
                        if f.facility_id not in booked and f.facility_id not in recs:
                            recs[f.facility_id] += max(8, 28 - idx * 2)
            else:
                # 只使用相似度 > 0.5 的用户，减少噪声干扰
                for uid, sim in similar_users:
                    if sim > 0.5:  # 相似度阈值过滤
                        for fid, s in scores[uid].items():
                            recs[fid] += sim * s
                            rec_sources[fid] = '协同过滤'

                for fid, s in scores.get(user_id, {}).items():
                    recs[fid] += s * 0.7  # 用户自身偏好权重
                    rec_sources[fid] = '我的浏览'

                user_categories = self._get_user_preferred_categories(user_id)
                if user_categories:
                    category_popular = self.recommend_popular_facilities(
                        limit=limit * 3,
                        exclude_user_id=user_id,
                        only_categories=user_categories,
                    )
                    for idx, f in enumerate(category_popular):
                        if f.facility_id not in booked:
                            rank_bonus = max(15, 45 - idx * 2)
                            recs[f.facility_id] += rank_bonus
                            if f.facility_id in rec_sources:
                                rec_sources[f.facility_id] += '+类别扩展'
                            else:
                                rec_sources[f.facility_id] = '类别扩展'

                if len(recs) < limit:
                    for idx, f in enumerate(
                        self.recommend_popular_facilities(limit=limit * 2, exclude_user_id=user_id)
                    ):
                        if f.facility_id not in booked and f.facility_id not in recs:
                            recs[f.facility_id] += max(5, 20 - idx * 2)
                            rec_sources[f.facility_id] = '热门兜底'

            # 按浏览行为占比给「设施所属类别」加权
            if category_weight and recs:
                max_w = max(category_weight.values()) or 1.0
                for fid in list(recs.keys()):
                    fac = Facility.query.get(fid)
                    if not fac or not fac.category:
                        continue
                    w = category_weight.get(fac.category, 0.0)
                    recs[fid] += 35.0 * (w / max_w)

        # ========== 归一化处理 ==========
        self._rec_scores = recs  # 保存分数供 get_facility_score 使用

        if recs:
            max_score = max(recs.values())
            if max_score > 0:
                for fid in recs:
                    recs[fid] = recs[fid] / max_score * 100

        # 过滤已预约设施并排序返回
        result = sorted(recs.items(), key=lambda x: x[1], reverse=True)
        facilities = [Facility.query.get(fid) for fid, _ in result if fid not in booked][:limit]

        # 处理来源标签（可能有多个来源，用 + 连接）
        final_sources = {}
        for fid, _ in result:
            if fid not in booked:
                src = rec_sources.get(fid, '')
                if isinstance(src, set):
                    src = '+'.join(sorted(src))
                final_sources[fid] = src

        return facilities, final_sources

    def get_facility_score(self, facility_id, user_id=None):
        """获取设施的推荐分数"""
        if hasattr(self, '_rec_scores') and facility_id in self._rec_scores:
            return self._rec_scores[facility_id]
        return 0.0

    def _get_user_preferred_categories(self, user_id):
        """获取用户偏好的设施类别"""
        # 从用户行为中统计各类别的偏好分数
        category_scores = defaultdict(float)
        
        behaviors = UserBehavior.query.filter_by(user_id=user_id).all()
        for b in behaviors:
            facility = Facility.query.get(b.facility_id)
            if facility and facility.category:
                # 考虑行为权重和时间衰减
                days_ago = (datetime.now() - b.created_at).days if b.created_at else 0
                decay_factor = max(0.5, 1.0 - max(0, days_ago - 30) / 30 * 0.1)
                category_scores[facility.category] += self.behavior_weights[b.behavior_type] * decay_factor
        
        # 返回分数大于平均值的类别
        if not category_scores:
            return []
        avg_score = sum(category_scores.values()) / len(category_scores)
        return [cat for cat, score in category_scores.items() if score >= avg_score]

    def _get_user_category_weights(self, user_id):
        """按用户行为统计各类别权重，总和为 1（用于老用户类别亲和加分）"""
        raw = defaultdict(float)
        behaviors = UserBehavior.query.filter_by(user_id=user_id).all()
        for b in behaviors:
            facility = Facility.query.get(b.facility_id)
            if facility and facility.category:
                days_ago = (datetime.now() - b.created_at).days if b.created_at else 0
                decay_factor = max(0.5, 1.0 - max(0, days_ago - 30) / 30 * 0.1)
                raw[facility.category] += self.behavior_weights[b.behavior_type] * decay_factor
        total = sum(raw.values())
        if total <= 0:
            return {}
        return {c: v / total for c, v in raw.items()}

    def recommend_popular_facilities(
        self,
        limit=10,
        exclude_user_id=None,
        exclude_categories=None,
        only_categories=None,
    ):
        """推荐热门设施（按预约次数和收藏数排序）

        Args:
            limit: 返回数量
            exclude_user_id: 如果指定，排除该用户已预约的设施
            exclude_categories: 如果指定，排除这些类别的设施
            only_categories: 如果指定，只保留这些类别（用于「同类热门」）
        """
        # 获取所有可用设施
        facilities = Facility.query.filter_by(status=1).all()
        
        if not facilities:
            return []
        
        facility_ids = [f.facility_id for f in facilities]
        
        # 如果指定了排除用户，获取该用户已预约的设施
        exclude_facilities = set()
        if exclude_user_id:
            # 只排除已预约的设施，不排除已收藏的（收藏代表感兴趣，更应推荐）
            booked = {
                b.facility_id for b in Booking.query.filter(
                    Booking.user_id == exclude_user_id,
                    Booking.status.in_(['pending', 'approved', 'completed'])
                ).all()
            }
            exclude_facilities = booked
        
        # 统计每个设施的收藏数量
        favorite_counts = db.session.query(
            Favorite.facility_id,
            func.count(Favorite.favorite_id).label('cnt')
        ).filter(Favorite.facility_id.in_(facility_ids))\
         .group_by(Favorite.facility_id).all()
        favorite_counts_dict = {row.facility_id: row.cnt for row in favorite_counts}
        
        # 计算综合热度分数 = 预约次数 * 2 + 收藏数 * 1.5
        # 这样预约次数的权重稍高一些
        facility_scores = []
        for facility in facilities:
            # 排除用户已预约或已收藏的设施
            if facility.facility_id in exclude_facilities:
                continue
            # 排除指定类别
            if exclude_categories and facility.category in exclude_categories:
                continue
            if only_categories is not None and facility.category not in only_categories:
                continue
            booking_score = (facility.booking_count or 0) * 2.0
            favorite_score = (favorite_counts_dict.get(facility.facility_id, 0)) * 1.5
            total_score = booking_score + favorite_score
            facility_scores.append((facility, total_score))
        
        # 按热度分数降序排序
        facility_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前N个设施
        return [f[0] for f in facility_scores[:limit]]
    
    def record_behavior(self, user_id, facility_id, behavior_type):
        """记录用户行为并计算评分"""
        print(f"[RECORD] 开始记录行为: user={user_id}, facility={facility_id}, type={behavior_type}")

        # 根据行为类型计算评分
        behavior_scores = {
            'view': 1.0,       # 浏览：1分
            'booking': 2.0,     # 预约：2分
            'complete': 5.0,   # 完成使用：5分
            'cancel': -2.0,    # 取消预约：-2分
            'favorite': 1.5     # 收藏：1.5分
        }
        score = behavior_scores.get(behavior_type, 0.0)

        behavior = UserBehavior(
            user_id=user_id,
            facility_id=facility_id,
            behavior_type=behavior_type,
            score=score
        )
        db.session.add(behavior)
        db.session.commit()
        print(f"[RECORD] 行为记录成功保存到数据库, score={score}")
        # 验证保存
        saved = UserBehavior.query.filter_by(
            user_id=user_id,
            facility_id=facility_id,
            behavior_type=behavior_type
        ).first()
        print(f"[RECORD] 验证查询结果: {saved}")

