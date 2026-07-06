"""预约管理路由"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Booking, Facility, BookingRule, User
from algorithms import GreedyScheduler, CollaborativeFilter
from datetime import datetime, timedelta
from sqlalchemy import and_
from extensions import db

booking_bp = Blueprint('booking', __name__)

@booking_bp.route('/create', methods=['POST'])
@jwt_required()
def create_booking():
    """创建预约（草稿或直接提交）"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # 验证必填字段
    required_fields = ['facility_id', 'booking_date', 'start_time', 'end_time']
    for field in required_fields:
        if field not in data:
            return jsonify({'code': 400, 'message': f'缺少必填字段: {field}'}), 400
    
    facility_id = data['facility_id']
    booking_date = datetime.strptime(data['booking_date'], '%Y-%m-%d').date()
    start_time = datetime.strptime(data['start_time'], '%H:%M').time()
    end_time = datetime.strptime(data['end_time'], '%H:%M').time()
    purpose = data.get('purpose', '')
    is_draft = data.get('is_draft', False)  # 是否为草稿
    
    # 验证设施是否存在
    facility = db.session.get(Facility, facility_id)
    if not facility or facility.status != 1:
        return jsonify({'code': 404, 'message': '设施不存在或已停用'}), 404
    
    # 获取设施容量
    capacity = facility.capacity if facility.capacity else 1
    
    # 检查该时间段已预约人数是否已满
    # 查询该时间段内的已有预约数量
    current_bookings_count = Booking.query.filter(
        Booking.facility_id == facility_id,
        Booking.booking_date == booking_date,
        Booking.status.in_(['pending', 'approved']),
        and_(
            Booking.start_time < end_time,
            Booking.end_time > start_time
        )
    ).count()
    
    if capacity > 1:
        # 有容量的设施：检查是否已满
        if current_bookings_count >= capacity:
            return jsonify({'code': 400, 'message': f'该时间段预约已满（{current_bookings_count}/{capacity}）'}), 400
    else:
        # 无容量的设施（capacity=1）：检查是否有任何预约
        if current_bookings_count > 0:
            return jsonify({'code': 400, 'message': '该时间段已被预约'}), 400
    
    # ========== 检查预约规则 ==========
    # 先查找设施专属规则，如果没有则使用全局规则
    rule = BookingRule.query.filter_by(facility_id=facility_id, status=1).first()
    if not rule:
        rule = BookingRule.query.filter_by(facility_id=None, status=1).first()
    
    if rule:
        # 检查每日预约次数限制
        today_bookings_count = Booking.query.filter(
            Booking.user_id == current_user_id,
            Booking.facility_id == facility_id,
            Booking.booking_date == booking_date,
            Booking.status.in_(['pending', 'approved', 'completed'])
        ).count()
        
        if today_bookings_count >= rule.daily_limit:
            return jsonify({
                'code': 400,
                'message': f'该设施每日预约次数已达上限（{rule.daily_limit}次）'
            }), 400
        
        # 检查预约时间是否在开放时间内
        if rule.start_time and rule.end_time:
            if start_time < rule.start_time or end_time > rule.end_time:
                return jsonify({
                    'code': 400,
                    'message': f'预约时间需在 {rule.start_time.strftime("%H:%M")} - {rule.end_time.strftime("%H:%M")} 之间'
                }), 400
        
        # 检查预约时长限制
        duration_minutes = (datetime.combine(datetime.today(), end_time) - datetime.combine(datetime.today(), start_time)).seconds // 60
        if rule.min_duration and duration_minutes < rule.min_duration:
            return jsonify({
                'code': 400,
                'message': f'预约时长不能少于 {rule.min_duration} 分钟'
            }), 400
        if rule.max_duration and duration_minutes > rule.max_duration:
            return jsonify({
                'code': 400,
                'message': f'预约时长不能超过 {rule.max_duration} 分钟'
            }), 400
        
        # 检查提前预约天数限制
        booking_datetime = datetime.combine(booking_date, start_time)
        days_in_advance = (booking_datetime - datetime.now()).days
        if days_in_advance > rule.max_advance_days:
            return jsonify({
                'code': 400,
                'message': f'最多只能提前 {rule.max_advance_days} 天预约'
            }), 400
    
    # 创建预约
    booking = Booking(
        user_id=current_user_id,
        facility_id=facility_id,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        purpose=purpose,
        status='draft' if is_draft else 'pending'
    )
    
    try:
        db.session.add(booking)
        db.session.commit()
        
        # 如果提交审核，记录预约行为
        if not is_draft:
            cf = CollaborativeFilter()
            cf.record_behavior(current_user_id, facility_id, 'booking')
        
        return jsonify({
            'code': 200,
            'message': '保存成功' if is_draft else '提交成功，等待审核',
            'data': booking.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'操作失败: {str(e)}'}), 500

@booking_bp.route('/submit/<int:booking_id>', methods=['POST'])
@jwt_required()
def submit_booking(booking_id):
    """提交草稿预约"""
    current_user_id = get_jwt_identity()
    booking = db.session.get(Booking, booking_id)
    
    if not booking:
        return jsonify({'code': 404, 'message': '预约不存在'}), 404
    
    if booking.user_id != current_user_id:
        return jsonify({'code': 403, 'message': '无权操作'}), 403
    
    if booking.status != 'draft':
        return jsonify({'code': 400, 'message': '只能提交草稿状态的预约'}), 400
    
    # 再次检查时间冲突（考虑容量）
    facility = db.session.get(Facility, booking.facility_id)
    capacity = facility.capacity if facility and facility.capacity else 1
    
    current_bookings_count = Booking.query.filter(
        Booking.facility_id == booking.facility_id,
        Booking.booking_date == booking.booking_date,
        Booking.status.in_(['pending', 'approved']),
        Booking.booking_id != booking_id,
        and_(
            Booking.start_time < booking.end_time,
            Booking.end_time > booking.start_time
        )
    ).count()
    
    if capacity > 1:
        if current_bookings_count >= capacity:
            return jsonify({'code': 400, 'message': f'该时间段预约已满（{current_bookings_count}/{capacity}）'}), 400
    else:
        if current_bookings_count > 0:
            return jsonify({'code': 400, 'message': '该时间段已被预约'}), 400
    
    # 检查预约规则
    rule = BookingRule.query.filter_by(facility_id=booking.facility_id, status=1).first()
    if not rule:
        rule = BookingRule.query.filter_by(facility_id=None, status=1).first()
    
    if rule:
        # 检查每日预约次数限制
        today_bookings_count = Booking.query.filter(
            Booking.user_id == current_user_id,
            Booking.facility_id == booking.facility_id,
            Booking.booking_date == booking.booking_date,
            Booking.status.in_(['pending', 'approved', 'completed']),
            Booking.booking_id != booking_id
        ).count()
        
        if today_bookings_count >= rule.daily_limit:
            return jsonify({
                'code': 400,
                'message': f'该设施每日预约次数已达上限（{rule.daily_limit}次）'
            }), 400
    
    booking.status = 'pending'
    
    try:
        db.session.commit()
        
        # 记录预约行为
        cf = CollaborativeFilter()
        cf.record_behavior(current_user_id, booking.facility_id, 'booking')
        
        return jsonify({
            'code': 200,
            'message': '提交成功，等待审核',
            'data': booking.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'提交失败: {str(e)}'}), 500

@booking_bp.route('/my-bookings', methods=['GET'])
@jwt_required()
def get_my_bookings():
    """获取我的预约列表"""
    from sqlalchemy.orm import selectinload

    current_user_id = get_jwt_identity()

    # 查询参数
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    status = request.args.get('status', '')

    # 构建查询，使用selectinload预加载关系避免重复查询
    query = Booking.query \
        .options(
            selectinload(Booking.user),
            selectinload(Booking.facility),
            selectinload(Booking.auditor)
        ) \
        .filter_by(user_id=current_user_id)

    if status:
        query = query.filter_by(status=status)

    # 按创建时间倒序
    query = query.order_by(Booking.created_at.desc())

    # 分页
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)

    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': {
            'total': pagination.total,  # 使用分页对象的真实总数
            'page': page,
            'page_size': page_size,
            'bookings': [b.to_dict() for b in pagination.items]
        }
    })

@booking_bp.route('/detail/<int:booking_id>', methods=['GET'])
@jwt_required()
def get_booking_detail(booking_id):
    """获取预约详情"""
    current_user_id = get_jwt_identity()
    booking = db.session.get(Booking, booking_id)
    
    if not booking:
        return jsonify({'code': 404, 'message': '预约不存在'}), 404
    
    # 只能查看自己的预约
    if booking.user_id != current_user_id:
        # 除非是审核员或管理员
        user = db.session.get(User, current_user_id)
        if user.role not in ['auditor', 'admin']:
            return jsonify({'code': 403, 'message': '无权查看'}), 403
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': booking.to_dict()
    })

@booking_bp.route('/cancel/<int:booking_id>', methods=['POST'])
@jwt_required()
def cancel_booking(booking_id):
    """取消预约"""
    current_user_id = get_jwt_identity()
    booking = db.session.get(Booking, booking_id)
    
    if not booking:
        return jsonify({'code': 404, 'message': '预约不存在'}), 404
    
    if booking.user_id != current_user_id:
        return jsonify({'code': 403, 'message': '无权操作'}), 403
    
    if booking.status not in ['draft', 'pending', 'approved']:
        return jsonify({'code': 400, 'message': '当前状态不能取消'}), 400
    
    booking.status = 'cancelled'
    
    try:
        db.session.commit()
        
        # 记录取消行为
        cf = CollaborativeFilter()
        cf.record_behavior(current_user_id, booking.facility_id, 'cancel')
        
        return jsonify({
            'code': 200,
            'message': '取消成功',
            'data': booking.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'取消失败: {str(e)}'}), 500

@booking_bp.route('/available-times', methods=['GET'])
@jwt_required()
def get_available_times():
    """获取可用时间段（基于贪心算法）"""
    facility_id = request.args.get('facility_id', type=int)
    date_str = request.args.get('date')
    duration = request.args.get('duration', 60, type=int)
    
    if not facility_id or not date_str:
        return jsonify({'code': 400, 'message': '缺少必填参数'}), 400
    
    try:
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'code': 400, 'message': '日期格式错误'}), 400
    
    # 验证设施
    facility = db.session.get(Facility, facility_id)
    if not facility or facility.status != 1:
        return jsonify({'code': 404, 'message': '设施不存在或已停用'}), 404
    
    # 获取当前用户ID
    user_id = get_jwt_identity()
    
    # 使用贪心算法获取可用时间段
    scheduler = GreedyScheduler()
    available_times = scheduler.get_available_time_slots(facility_id, booking_date, duration, user_id)
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': available_times
    })

@booking_bp.route('/suggest-time', methods=['GET'])
@jwt_required()
def suggest_best_time():
    """推荐最佳时间段（贪心算法）"""
    print("\n" + "="*60)
    print("[路由] 收到推荐请求")
    
    facility_id = request.args.get('facility_id', type=int)
    date_str = request.args.get('date')
    duration = request.args.get('duration', 60, type=int)
    preferred_start = request.args.get('preferred_start')
    
    print(f"[路由] 参数:")
    print(f"  facility_id: {facility_id}")
    print(f"  date: {date_str}")
    print(f"  duration: {duration}")
    print(f"  preferred_start: {preferred_start}")
    
    if not facility_id or not date_str:
        print("[路由] 缺少必填参数")
        return jsonify({'code': 400, 'message': '缺少必填参数'}), 400
    
    try:
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        print("[路由] 日期格式错误")
        return jsonify({'code': 400, 'message': '日期格式错误'}), 400
    
    # 验证设施
    facility = db.session.get(Facility, facility_id)
    if not facility or facility.status != 1:
        print("[路由] 设施不存在或已停用")
        return jsonify({'code': 404, 'message': '设施不存在或已停用'}), 404
    
    # 获取当前用户ID
    user_id = get_jwt_identity()
    
    # 使用贪心算法推荐最佳时间
    print(f"[路由] 调用贪心调度器...")
    scheduler = GreedyScheduler()
    best_times = scheduler.suggest_best_time(facility_id, booking_date, duration, user_id, preferred_start)
    
    if not best_times:
        print(f"[路由] 返回: 当天暂无可用时间段")
        return jsonify({
            'code': 200,
            'message': '当天暂无可用时间段',
            'data': []
        })
    
    print(f"[路由] 返回: {len(best_times)} 个推荐时段")
    print("="*60 + "\n")
    
    return jsonify({
        'code': 200,
        'message': '推荐成功',
        'data': best_times
    })


@booking_bp.route('/checkin/<int:booking_id>', methods=['POST'])
@jwt_required()
def checkin_booking(booking_id):
    """
    签到
    只有已审核通过的预约才能签到
    签到时间范围：预约开始时间前30分钟到预约开始时间后15分钟内
    支持位置校验：如果设施设置了签到范围，则需要用户位置在范围内
    """
    current_user_id = get_jwt_identity()
    booking = db.session.get(Booking, booking_id)

    if not booking:
        return jsonify({'code': 404, 'message': '预约不存在'}), 404

    if booking.user_id != current_user_id:
        return jsonify({'code': 403, 'message': '无权操作'}), 403

    if booking.status != 'approved':
        return jsonify({'code': 400, 'message': '只有已通过的预约才能签到'}), 400

    if booking.checked_in:
        return jsonify({'code': 400, 'message': '已经签到过了'}), 400

    # 检查签到时间范围
    now = datetime.now()
    booking_datetime = datetime.combine(booking.booking_date, booking.start_time)
    checkin_start = booking_datetime - timedelta(minutes=30)
    checkin_end = booking_datetime + timedelta(minutes=15)

    if now < checkin_start:
        return jsonify({
            'code': 400,
            'message': f'签到时间尚未开放，请在 {checkin_start.strftime("%H:%M")} 后签到'
        }), 400

    if now > checkin_end:
        return jsonify({
            'code': 400,
            'message': '签到时间已过，请联系工作人员处理'
        }), 400

    # 获取用户提交的经纬度和设施信息
    facility = booking.facility
    user_lat = None
    user_lon = None
    actual_distance = None
    is_within_radius = 1
    checkin_radius = 0
    checkin_status = 'success'

    print(f"[DEBUG] ========== 签到调试信息 ==========")
    print(f"[DEBUG] 预约ID: {booking_id}")
    print(f"[DEBUG] 设施名称: {facility.name if facility else '未知'}")
    print(f"[DEBUG] 设施位置: 经度={facility.longitude if facility else None}, 纬度={facility.latitude if facility else None}")
    print(f"[DEBUG] 是否需要位置验证: {facility.require_checkin_location if facility else False}")
    print(f"[DEBUG] 签到范围半径: {facility.checkin_radius if facility else 0} 米")

    # 检查是否需要位置校验
    if facility and facility.require_checkin_location and facility.latitude and facility.longitude:
        # 获取用户提交的经纬度
        data = request.get_json() or {}
        user_lat = data.get('latitude')
        user_lon = data.get('longitude')

        print(f"[DEBUG] 用户位置: 经度={user_lon}, 纬度={user_lat}")

        if user_lat is None or user_lon is None:
            return jsonify({
                'code': 400,
                'message': '请提供您的当前位置信息',
                'data': {
                    'require_location': True,
                    'facility_location': {
                        'latitude': float(facility.latitude),
                        'longitude': float(facility.longitude),
                        'radius': facility.checkin_radius
                    }
                }
            }), 400

        # 验证位置并计算距离
        from utils.geolocation import is_within_checkin_range, haversine_distance, validate_coordinates

        print(f"[DEBUG] 验证坐标格式...")

        if not validate_coordinates(user_lat, user_lon):
            print(f"[DEBUG] 坐标格式验证失败")
            return jsonify({'code': 400, 'message': '位置信息格式不正确'}), 400

        # 计算实际距离
        # 注意：haversine_distance 参数顺序是 lat, lon
        actual_distance = haversine_distance(
            float(facility.latitude), float(facility.longitude),
            float(user_lat), float(user_lon)
        )
        
        print(f"[DEBUG] 计算结果:")
        print(f"[DEBUG]   设施坐标: 纬度={facility.latitude}, 经度={facility.longitude}")
        print(f"[DEBUG]   用户坐标: 纬度={user_lat}, 经度={user_lon}")
        print(f"[DEBUG]   实际距离: {actual_distance:.2f} 米")
        print(f"[DEBUG]   允许范围: {facility.checkin_radius} 米")

        # 判断是否在签到范围内
        within_range = is_within_checkin_range(
            float(facility.latitude), float(facility.longitude),
            float(user_lat), float(user_lon),
            facility.checkin_radius
        )

        print(f"[DEBUG]   是否在范围内: {within_range}")

        if not within_range:
            is_within_radius = 0
            checkin_status = 'failed'
            print(f"[DEBUG] 签到失败: 不在范围内")
            return jsonify({
                'code': 400,
                'message': f'您不在签到范围内（当前位置距离设施 {int(actual_distance)} 米，范围 {facility.checkin_radius} 米）',
                'data': {
                    'within_range': False,
                    'actual_distance': int(actual_distance),
                    'allowed_radius': facility.checkin_radius,
                    'facility_location': {
                        'latitude': float(facility.latitude),
                        'longitude': float(facility.longitude)
                    },
                    'debug_info': {
                        'facility_coords': [float(facility.latitude), float(facility.longitude)],
                        'user_coords': [float(user_lat), float(user_lon)],
                        'distance_meters': round(actual_distance, 2),
                        'radius_meters': facility.checkin_radius
                    }
                }
            }), 400

        print(f"[DEBUG] 位置验证通过，签到成功")
        checkin_radius = facility.checkin_radius
    else:
        print(f"[DEBUG] 无需位置验证")

    print(f"[DEBUG] ========== 签到调试结束 ==========")

    # 保存签到记录到 checkin_records 表
    from models import CheckinRecord
    checkin_record = CheckinRecord(
        booking_id=booking_id,
        user_id=current_user_id,
        facility_id=booking.facility_id,
        checkin_time=now,
        user_latitude=float(user_lat) if user_lat else 0,
        user_longitude=float(user_lon) if user_lon else 0,
        facility_latitude=float(facility.latitude) if facility.latitude else 0,
        facility_longitude=float(facility.longitude) if facility.longitude else 0,
        distance_meters=float(actual_distance) if actual_distance else None,
        is_within_radius=is_within_radius,
        checkin_radius=checkin_radius,
        status=checkin_status
    )
    db.session.add(checkin_record)

    # 更新预约状态
    booking.checked_in = True
    booking.checkin_time = now
    booking.status = 'completed'  # 签到后自动变成已完成状态

    try:
        db.session.commit()

        # 记录完成预约行为
        cf = CollaborativeFilter()
        cf.record_behavior(current_user_id, booking.facility_id, 'complete')

        return jsonify({
            'code': 200,
            'message': '签到成功',
            'data': {
                'checkin_time': booking.checkin_time.strftime('%Y-%m-%d %H:%M:%S'),
                'distance_meters': int(actual_distance) if actual_distance else None,
                'within_range': bool(is_within_radius),
                'booking': booking.to_dict()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'签到失败: {str(e)}'}), 500


@booking_bp.route('/review/<int:booking_id>', methods=['POST'])
@jwt_required()
def review_booking(booking_id):
    """
    评价预约
    只有已完成且未评价的预约才能评价
    """
    current_user_id = get_jwt_identity()
    booking = db.session.get(Booking, booking_id)
    
    if not booking:
        return jsonify({'code': 404, 'message': '预约不存在'}), 404
    
    if booking.user_id != current_user_id:
        return jsonify({'code': 403, 'message': '无权操作'}), 403
    
    if booking.status != 'completed':
        return jsonify({'code': 400, 'message': '只有已完成的预约才能评价'}), 400
    
    if booking.has_reviewed:
        return jsonify({'code': 400, 'message': '已经评价过了'}), 400
    
    data = request.get_json()
    rating = data.get('rating')
    content = data.get('content', '')
    
    if not rating or not 1 <= rating <= 5:
        return jsonify({'code': 400, 'message': '请给出1-5星的评分'}), 400
    
    # 创建评价
    from models import Review
    review = Review(
        user_id=current_user_id,
        facility_id=booking.facility_id,
        booking_id=booking_id,
        rating=rating,
        content=content
    )
    
    try:
        db.session.add(review)
        booking.has_reviewed = True
        
        # 更新设施评分
        facility = booking.facility
        all_reviews = Review.query.filter_by(facility_id=facility.facility_id).all()
        
        if all_reviews:
            avg_rating = sum(r.rating for r in all_reviews) / len(all_reviews)
            facility.rating = round(avg_rating, 2)
        else:
            facility.rating = 0
        
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '评价成功，感谢您的反馈！',
            'data': review.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'评价失败: {str(e)}'}), 500


@booking_bp.route('/review/<int:booking_id>', methods=['GET'])
@jwt_required()
def get_review(booking_id):
    """获取预约评价"""
    current_user_id = get_jwt_identity()
    booking = db.session.get(Booking, booking_id)
    
    if not booking:
        return jsonify({'code': 404, 'message': '预约不存在'}), 404
    
    from models import Review
    review = Review.query.filter_by(booking_id=booking_id).first()
    
    if not review:
        return jsonify({'code': 404, 'message': '暂无评价'}), 404
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': review.to_dict()
    })


@booking_bp.route('/pending-checkin', methods=['GET'])
@jwt_required()
def get_pending_checkin():
    """
    获取待签到的预约列表
    返回已审核通过、未签到、且在签到时间范围内的预约
    用于前端提醒用户签到
    """
    current_user_id = get_jwt_identity()
    
    now = datetime.now()
    
    # 获取所有已审核通过且未签到的预约
    bookings = Booking.query.filter(
        Booking.user_id == current_user_id,
        Booking.status == 'approved',
        Booking.checked_in == False
    ).all()
    
    # 筛选在签到时间范围内的预约
    pending_checkins = []
    for booking in bookings:
        booking_datetime = datetime.combine(booking.booking_date, booking.start_time)
        checkin_start = booking_datetime - timedelta(minutes=30)
        checkin_end = booking_datetime + timedelta(minutes=15)
        
        if checkin_start <= now <= checkin_end:
            pending_checkins.append({
                'booking_id': booking.booking_id,
                'facility_name': booking.facility.name if booking.facility else None,
                'booking_date': booking.booking_date.strftime('%Y-%m-%d'),
                'start_time': booking.start_time.strftime('%H:%M'),
                'end_time': booking.end_time.strftime('%H:%M'),
                'checkin_deadline': checkin_end.strftime('%H:%M')
            })
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': {
            'count': len(pending_checkins),
            'bookings': pending_checkins
        }
    })