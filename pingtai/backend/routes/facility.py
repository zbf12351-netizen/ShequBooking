"""设施管理路由"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import Facility, User, Favorite, Review, FacilityView
from sqlalchemy import func, text
from algorithms import CollaborativeFilter
from extensions import db
from datetime import date

facility_bp = Blueprint('facility', __name__)


def attach_favorite_meta(facilities, user_id):
    """为设施列表附加收藏标记与收藏数
    
    Args:
        facilities: 设施列表
        user_id: 用户ID，如果为None则只返回收藏数不标记已收藏
    """
    print(f"[attach_favorite_meta] user_id={user_id}, facilities_count={len(facilities)}")
    
    facility_ids = [f.facility_id for f in facilities]
    if not facility_ids:
        return [f.to_dict() for f in facilities]
    
    # 收藏数查询（所有用户通用）
    count_rows = db.session.query(
        Favorite.facility_id,
        func.count(Favorite.favorite_id).label('cnt')
    ).filter(Favorite.facility_id.in_(facility_ids))\
     .group_by(Favorite.facility_id).all()
    favorite_counts = {row.facility_id: row.cnt for row in count_rows}
    print(f"[attach_favorite_meta] favorite_counts={favorite_counts}")
    
    # 已收藏设施查询（仅当user_id不为None时）
    favorite_ids = set()
    if user_id:
        favorites = Favorite.query.filter(
            Favorite.user_id == user_id,
            Favorite.facility_id.in_(facility_ids)
        ).all()
        favorite_ids = {fav.facility_id for fav in favorites}
        print(f"[attach_favorite_meta] user={user_id} 已收藏的设施: {favorite_ids}")
    
    result = []
    for f in facilities:
        data = f.to_dict()
        data['is_favorite'] = f.facility_id in favorite_ids if user_id else False
        data['favorite_count'] = favorite_counts.get(f.facility_id, 0)
        result.append(data)
    return result

@facility_bp.route('/list', methods=['GET'])
def list_facilities():
    """获取设施列表（公开API，无需登录）"""
    # 获取查询参数
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    category = request.args.get('category', '')
    keyword = request.args.get('keyword', '')
    
    # 构建查询
    query = Facility.query.filter_by(status=1)
    
    if category:
        query = query.filter_by(category=category)
    
    if keyword:
        query = query.filter(Facility.name.like(f'%{keyword}%'))
    
    # 分页
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    
    # 获取当前用户ID（如果已登录）
    current_user_id = None
    auth_header = request.headers.get('Authorization')
    print(f"[设施列表] Authorization: {auth_header}")
    
    try:
        # 必须先调用 verify_jwt_in_request 才能获取 jwt_identity
        verify_jwt_in_request()
        current_user_id = get_jwt_identity()
        print(f"[设施列表] 用户已登录: user_id={current_user_id}")
    except Exception as e:
        print(f"[设施列表] JWT验证失败: {e}")
        current_user_id = None
    
    # 附加收藏信息
    if current_user_id:
        facilities_with_flag = attach_favorite_meta(pagination.items, current_user_id)
    else:
        print(f"[设施列表] 未附加用户收藏状态")
        # 未登录用户也需要显示收藏总数
        facility_ids = [f.facility_id for f in pagination.items]
        favorite_counts = {}
        if facility_ids:
            count_rows = db.session.query(
                Favorite.facility_id,
                func.count(Favorite.favorite_id).label('cnt')
            ).filter(Favorite.facility_id.in_(facility_ids))\
             .group_by(Favorite.facility_id).all()
            favorite_counts = {row.facility_id: row.cnt for row in count_rows}
        
        facilities_with_flag = []
        for f in pagination.items:
            data = f.to_dict()
            data['is_favorite'] = False
            data['favorite_count'] = favorite_counts.get(f.facility_id, 0)
            facilities_with_flag.append(data)
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': {
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'facilities': facilities_with_flag
        }
    })

@facility_bp.route('/detail/<int:facility_id>', methods=['GET'])
def get_facility_detail(facility_id):
    """获取设施详情（公开API，无需登录）"""
    facility = db.session.get(Facility, facility_id)
    
    if not facility:
        return jsonify({'code': 404, 'message': '设施不存在'}), 404
    
    data = facility.to_dict()
    
    # 获取当前用户ID（如果已登录）
    current_user_id = None
    try:
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        verify_jwt_in_request(optional=True)  # 使用 optional=True 更优雅
        current_user_id = get_jwt_identity()
        print(f"[FACILITY] 用户ID: {current_user_id}, 设施ID: {facility_id}")
    except Exception as e:
        print(f"[FACILITY] JWT验证失败: {e}")
        current_user_id = None
    
    # 收藏状态（仅登录用户）
    if current_user_id:
        favorite_exists = Favorite.query.filter_by(
            user_id=current_user_id,
            facility_id=facility_id
        ).first()
        data['is_favorite'] = bool(favorite_exists)
        
        # 记录浏览行为
        try:
            from algorithms.recommender import CollaborativeFilter
            cf = CollaborativeFilter()
            cf.record_behavior(current_user_id, facility_id, 'view')
        except Exception as e:
            db.session.rollback()
            print(f"[FACILITY] 行为记录失败: {e}")
        
        # 使用 INSERT ... ON DUPLICATE KEY UPDATE 原子操作，避免并发竞态
        try:
            today = date.today()
            stmt = text("""
                INSERT INTO facility_views (user_id, facility_id, view_date, view_count, created_at, updated_at)
                VALUES (:user_id, :facility_id, :view_date, 1, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    view_count = view_count + 1,
                    updated_at = NOW()
            """)
            db.session.execute(stmt, {
                'user_id': current_user_id,
                'facility_id': facility_id,
                'view_date': today
            })
            db.session.commit()
            print(f"[FACILITY] 浏览记录已保存到facility_views表")
        except Exception as e:
            db.session.rollback()
            print(f"[FACILITY] 浏览记录保存失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        data['is_favorite'] = False
    
    # 收藏总数
    fav_count = Favorite.query.filter_by(facility_id=facility_id).count()
    data['favorite_count'] = fav_count
    
    # 获取评价列表
    page = request.args.get('review_page', 1, type=int)
    page_size = request.args.get('review_page_size', 10, type=int)
    
    reviews_query = Review.query.filter_by(facility_id=facility_id).order_by(Review.created_at.desc())
    reviews_pagination = reviews_query.paginate(page=page, per_page=page_size, error_out=False)
    
    data['reviews'] = {
        'total': reviews_pagination.total,
        'page': page,
        'page_size': page_size,
        'items': [r.to_dict() for r in reviews_pagination.items]
    }
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': data
    })

@facility_bp.route('/categories', methods=['GET'])
def get_categories():
    """获取设施类别列表（公开API，无需登录）"""
    categories = db.session.query(Facility.category)\
        .filter_by(status=1)\
        .distinct()\
        .all()
    
    category_list = [c[0] for c in categories]
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': category_list
    })

@facility_bp.route('/recommend', methods=['GET'])
def recommend_facilities():
    """智能推荐设施（公开API，用于首页展示）

    如果用户已登录，会排除用户已预约/已完成的设施
    """
    # 如果用户已登录，尝试获取个性化推荐
    try:
        verify_jwt_in_request()
        current_user_id = get_jwt_identity()
    except:
        # 用户未登录时使用热门设施兜底
        current_user_id = None

    limit = request.args.get('limit', 8, type=int)

    cf = CollaborativeFilter()

    if current_user_id:
        # 已登录用户：获取个性化推荐（会排除已预约的设施）
        recommended_facilities, rec_sources = cf.recommend_for_user_with_sources(current_user_id, limit)
        if not recommended_facilities:
            # 如果个性化推荐为空，用热门设施兜底（也排除已预约的）
            recommended_facilities = cf.recommend_popular_facilities(limit, exclude_user_id=current_user_id)
            rec_sources = {f.facility_id: '热门兜底' for f in recommended_facilities}

        # ========== 调试输出协同过滤推荐过程 ==========
        print("\n" + "=" * 70)
        print(f"[协同过滤推荐] 用户ID: {current_user_id}, 请求数量: {limit}")
        print("-" * 70)

        # 1. 检查是否为新用户
        from models import UserBehavior
        behavior_count = UserBehavior.query.filter_by(user_id=current_user_id).count()
        print(f"[1] 用户行为数据: {behavior_count} 条")

        # 2. 获取已预约设施
        from models import Booking
        booked = {b.facility_id for b in Booking.query.filter(
            Booking.user_id == current_user_id,
            Booking.status.in_(['pending', 'approved', 'completed'])
        ).all()}
        print(f"[2] 已预约设施: {len(booked)} 个 -> {booked if booked else '无'}")

        # 3. 获取评分矩阵中的用户数
        scores = cf.get_user_facility_matrix()
        print(f"[3] 评分矩阵: {len(scores)} 个用户, 总评分数: {sum(len(s) for s in scores.values())}")

        # 4. 获取相似用户
        similar_users = cf.find_similar_users(current_user_id, scores)
        print(f"[4] 相似用户(前5): {[(uid, round(sim, 3)) for uid, sim in similar_users[:5]]}")

        # 5. 输出推荐结果
        print(f"\n[5] 推荐结果 ({len(recommended_facilities)} 个):")
        if recommended_facilities:
            print(f"{'排名':<4} {'设施名称':<20} {'类别':<10} {'推荐分数':<10}")
            print("-" * 50)
            for idx, fac in enumerate(recommended_facilities, 1):
                score = round(cf.get_facility_score(fac.facility_id, current_user_id), 2)
                print(f"{idx:<4} {fac.name:<20} {fac.category:<10} {score:<10}")
        else:
            print("    无推荐结果")

        print("=" * 70 + "\n")
        # ==========================================

        facilities_with_flag = attach_favorite_meta(recommended_facilities, current_user_id)
    else:
        # 未登录用户返回热门设施
        popular_facilities = cf.recommend_popular_facilities(limit)
        
        # 批量查询总收藏数
        facility_ids = [f.facility_id for f in popular_facilities]
        favorite_counts = {}
        if facility_ids:
            count_rows = db.session.query(
                Favorite.facility_id,
                func.count(Favorite.favorite_id).label('cnt')
            ).filter(Favorite.facility_id.in_(facility_ids))\
             .group_by(Favorite.facility_id).all()
            favorite_counts = {row.facility_id: row.cnt for row in count_rows}
        
        facilities_with_flag = []
        for f in popular_facilities:
            data = f.to_dict()
            data['is_favorite'] = False
            data['favorite_count'] = favorite_counts.get(f.facility_id, 0)
            facilities_with_flag.append(data)
    
    return jsonify({
        'code': 200,
        'message': '推荐成功',
        'data': facilities_with_flag
    })

@facility_bp.route('/popular', methods=['GET'])
def get_popular_facilities():
    """获取热门设施（公开API，用于首页展示）
    
    如果用户已登录，会排除用户已预约/已完成的设施，并显示收藏状态
    收藏数：显示该设施的总收藏数
    """
    limit = request.args.get('limit', 8, type=int)
    cf = CollaborativeFilter()
    
    # 检查用户是否已登录
    try:
        verify_jwt_in_request()
        current_user_id = get_jwt_identity()
        # 已登录：排除用户已预约的设施
        popular_facilities = cf.recommend_popular_facilities(limit, exclude_user_id=current_user_id)
        facilities_with_flag = attach_favorite_meta(popular_facilities, current_user_id)
    except:
        # 未登录用户
        popular_facilities = cf.recommend_popular_facilities(limit)
        
        # 批量查询总收藏数
        facility_ids = [f.facility_id for f in popular_facilities]
        favorite_counts = {}
        if facility_ids:
            count_rows = db.session.query(
                Favorite.facility_id,
                func.count(Favorite.favorite_id).label('cnt')
            ).filter(Favorite.facility_id.in_(facility_ids))\
             .group_by(Favorite.facility_id).all()
            favorite_counts = {row.facility_id: row.cnt for row in count_rows}
        
        facilities_with_flag = []
        for f in popular_facilities:
            data = f.to_dict()
            data['is_favorite'] = False
            data['favorite_count'] = favorite_counts.get(f.facility_id, 0)
            facilities_with_flag.append(data)
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': facilities_with_flag
    })


@facility_bp.route('/favorite/<int:facility_id>', methods=['POST'])
@jwt_required()
def add_favorite(facility_id):
    """收藏设施"""
    current_user_id = get_jwt_identity()
    print(f"[收藏] user_id={current_user_id}, facility_id={facility_id}")
    
    facility = db.session.get(Facility, facility_id)
    if not facility or facility.status != 1:
        print(f"[收藏] 失败: 设施不存在或已停用")
        return jsonify({'code': 404, 'message': '设施不存在或已停用'}), 404
    
    exists = Favorite.query.filter_by(user_id=current_user_id, facility_id=facility_id).first()
    if exists:
        print(f"[收藏] 失败: 已收藏过")
        return jsonify({'code': 200, 'message': '已收藏'}), 200
    
    favorite = Favorite(user_id=current_user_id, facility_id=facility_id)
    db.session.add(favorite)
    db.session.commit()
    
    print(f"[收藏] 成功: user_id={current_user_id}, facility_id={facility_id}")
    return jsonify({'code': 201, 'message': '收藏成功'})


@facility_bp.route('/favorite/<int:facility_id>', methods=['DELETE'])
@jwt_required()
def remove_favorite(facility_id):
    """取消收藏"""
    print(f"[取消收藏] 用户尝试取消收藏: facility_id={facility_id}")
    current_user_id = get_jwt_identity()
    
    favorite = Favorite.query.filter_by(user_id=current_user_id, facility_id=facility_id).first()
    if not favorite:
        print(f"[取消收藏] 未找到收藏记录: user_id={current_user_id}, facility_id={facility_id}")
        return jsonify({'code': 404, 'message': '未收藏'}), 404
    
    db.session.delete(favorite)
    db.session.commit()
    
    print(f"[取消收藏] 取消成功: user_id={current_user_id}, facility_id={facility_id}")
    return jsonify({'code': 200, 'message': '取消收藏成功'})


@facility_bp.route('/favorite/status/<int:facility_id>', methods=['GET'])
@jwt_required()
def favorite_status(facility_id):
    """查询收藏状态"""
    current_user_id = get_jwt_identity()
    favorite = Favorite.query.filter_by(user_id=current_user_id, facility_id=facility_id).first()
    return jsonify({'code': 200, 'message': '查询成功', 'data': {'is_favorite': bool(favorite)}})


@facility_bp.route('/favorites', methods=['GET'])
@jwt_required()
def list_favorites():
    """获取我的收藏列表"""
    current_user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    
    query = Favorite.query.filter_by(user_id=current_user_id).order_by(Favorite.created_at.desc())
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    
    facility_ids = [fav.facility_id for fav in pagination.items]
    
    # 如果没有收藏，返回空列表
    if not facility_ids:
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'total': pagination.total,
                'page': page,
                'page_size': page_size,
                'favorites': []
            }
        })
    
    facilities = Facility.query.filter(Facility.facility_id.in_(facility_ids)).all()
    facility_dict = {f.facility_id: f for f in facilities}
    
    favorite_list = []
    # 收藏数缓存
    count_rows = db.session.query(
        Favorite.facility_id,
        func.count(Favorite.favorite_id).label('cnt')
    ).filter(Favorite.facility_id.in_(facility_ids))\
     .group_by(Favorite.facility_id).all()
    favorite_counts = {row.facility_id: row.cnt for row in count_rows}
    
    for fav in pagination.items:
        facility = facility_dict.get(fav.facility_id)
        if facility:
            data = facility.to_dict()
            data['is_favorite'] = True
            data['favorite_count'] = favorite_counts.get(fav.facility_id, 0)
            favorite_list.append(data)
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': {
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'favorites': favorite_list
        }
    })

