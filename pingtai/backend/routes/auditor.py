"""审核员路由"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Booking, Feedback, User, Facility, Notification
from utils.decorators import role_required, log_operation
from extensions import db
from datetime import datetime
from algorithms import CollaborativeFilter
from sqlalchemy import desc, or_

auditor_bp = Blueprint('auditor', __name__)

@auditor_bp.route('/bookings/pending', methods=['GET'])
@jwt_required()
@role_required('auditor', 'admin')
def get_pending_bookings():
    """获取待审核的预约列表"""
    # 查询参数
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    
    # 查询待审核预约
    query = Booking.query.filter_by(status='pending')\
        .order_by(Booking.created_at.asc())
    
    # 分页
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': {
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'bookings': [b.to_dict() for b in pagination.items]
        }
    })

@auditor_bp.route('/bookings/audit/<int:booking_id>', methods=['POST'])
@jwt_required()
@role_required('auditor', 'admin')
@log_operation('audit_booking', 'booking_management')
def audit_booking(booking_id):
    """审核预约"""
    current_user_id = get_jwt_identity()
    booking = db.session.get(Booking, booking_id)
    
    if not booking:
        return jsonify({'code': 404, 'message': '预约不存在'}), 404
    
    if booking.status != 'pending':
        return jsonify({'code': 400, 'message': '只能审核待审核状态的预约'}), 400
    
    data = request.get_json()
    action = data.get('action')  # 'approve' or 'reject'
    comment = data.get('comment', '')
    
    if action not in ['approve', 'reject']:
        return jsonify({'code': 400, 'message': '审核操作不正确'}), 400
    
    # 更新预约状态
    booking.status = 'approved' if action == 'approve' else 'rejected'
    booking.auditor_id = current_user_id
    booking.audit_time = datetime.now()
    booking.audit_comment = comment
    
    try:
        db.session.commit()
        
        # ============ 发送审核结果通知 ============
        if action == 'approve':
            # 计算签到时间范围
            from datetime import timedelta
            booking_datetime = datetime.combine(booking.booking_date, booking.start_time)
            checkin_start = booking_datetime - timedelta(minutes=30)
            checkin_end = booking_datetime + timedelta(minutes=15)
            
            # 审核通过通知（包含签到提醒）
            notification = Notification(
                user_id=booking.user_id,
                title='预约审核通过',
                content=f'您预约的「{booking.facility.name}」已审核通过！\n\n📅 预约时间：{booking.booking_date} {booking.start_time}~{booking.end_time}\n\n🔔 签到提醒：可在 {checkin_start.strftime("%H:%M")} 至 {checkin_end.strftime("%H:%M")} 期间签到',
                type='audit',
                target_type='personal'
            )
            db.session.add(notification)
        else:
            # 审核拒绝通知
            notification = Notification(
                user_id=booking.user_id,
                title='预约审核未通过',
                content=f'您预约的「{booking.facility.name}」未通过审核。\n原因：{comment}\n预约时间：{booking.booking_date} {booking.start_time}~{booking.end_time}',
                type='audit',
                target_type='personal'
            )
            db.session.add(notification)
        db.session.commit()
        # ============ 通知发送完成 ============
        
        # 如果审核通过，增加设施预约次数
        if action == 'approve':
            facility = db.session.get(Facility, booking.facility_id)
            if facility:
                facility.booking_count += 1
                db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '审核成功',
            'data': booking.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'审核失败: {str(e)}'}), 500

@auditor_bp.route('/bookings/audited', methods=['GET'])
@jwt_required()
@role_required('auditor', 'admin')
def get_audited_bookings():
    """获取已审核的预约列表"""
    # 查询参数
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    status = request.args.get('status', '')  # 'approved', 'rejected', 'completed', 'cancelled'
    
    print(f"[DEBUG] 获取已审核列表 - page:{page}, page_size:{page_size}, status:{status}")

    # 构建查询 - 获取已审核的预约（包括已通过、已拒绝、已完成、已取消）
    query = Booking.query.filter(
        Booking.status.in_(['approved', 'rejected', 'completed', 'cancelled'])
    )

    # 调试：打印所有符合状态条件的记录数
    total_matching = query.count()
    print(f"[DEBUG] 符合状态条件的记录总数: {total_matching}")
    
    # 如果指定了状态筛选
    if status and status != 'exception':
        query = query.filter_by(status=status)
    
    # 异常处理：筛选已过期但仍为 approved 状态的预约
    if status == 'exception':
        from datetime import date
        query = query.filter(
            Booking.status == 'approved',
            Booking.booking_date < date.today()
        )
    
    # 按审核时间倒序，如果没有审核时间则按创建时间倒序
    query = query.order_by(desc(Booking.audit_time), desc(Booking.created_at))
    
    # 分页
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    
    print(f"[DEBUG] 查询结果 - total:{pagination.total}, items_count:{len(pagination.items)}")
    print(f"[DEBUG] 返回的booking IDs: {[b.booking_id for b in pagination.items]}")
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': {
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'bookings': [b.to_dict() for b in pagination.items]
        }
    })

@auditor_bp.route('/bookings/handle-exception/<int:booking_id>', methods=['POST'])
@jwt_required()
@role_required('auditor', 'admin')
@log_operation('handle_exception', 'booking_management')
def handle_booking_exception(booking_id):
    """处理预约异常"""
    booking = db.session.get(Booking, booking_id)
    
    if not booking:
        return jsonify({'code': 404, 'message': '预约不存在'}), 404
    
    data = request.get_json()
    action = data.get('action')  # 'cancel' or 'complete'
    comment = data.get('comment', '')
    
    if action == 'cancel':
        booking.status = 'cancelled'
    elif action == 'complete':
        booking.status = 'completed'
        # 记录完成行为
        cf = CollaborativeFilter()
        cf.record_behavior(booking.user_id, booking.facility_id, 'complete')
    else:
        return jsonify({'code': 400, 'message': '操作不正确'}), 400
    
    booking.audit_comment = f"{booking.audit_comment}\n异常处理: {comment}" if booking.audit_comment else f"异常处理: {comment}"
    
    try:
        db.session.commit()
        return jsonify({
            'code': 200,
            'message': '处理成功',
            'data': booking.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'处理失败: {str(e)}'}), 500

@auditor_bp.route('/feedbacks/pending', methods=['GET'])
@jwt_required()
@role_required('auditor', 'admin')
def get_pending_feedbacks():
    """获取待处理的反馈列表"""
    # 查询参数
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    
    # 构建查询
    query = Feedback.query.filter_by(status='pending')
    
    # 审核员只能查看"咨询"类型，管理员可以查看所有
    if current_user and current_user.role == 'auditor':
        query = query.filter_by(type='consultation')
    
    query = query.order_by(Feedback.created_at.asc())
    
    # 分页
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': {
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'feedbacks': [f.to_dict() for f in pagination.items]
        }
    })

@auditor_bp.route('/feedbacks/reply/<int:feedback_id>', methods=['POST'])
@jwt_required()
@role_required('auditor', 'admin')
@log_operation('reply_feedback', 'feedback_management')
def reply_feedback(feedback_id):
    """回复反馈"""
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    feedback = db.session.get(Feedback, feedback_id)
    
    if not feedback:
        return jsonify({'code': 404, 'message': '反馈不存在'}), 404
    
    # 审核员只能回复咨询类型
    if user.role == 'auditor' and feedback.type != 'consultation':
        return jsonify({'code': 403, 'message': '无权回复此类型的反馈'}), 403
    
    data = request.get_json()
    reply = data.get('reply')
    
    if not reply:
        return jsonify({'code': 400, 'message': '回复内容不能为空'}), 400
    
    # 更新反馈
    feedback.reply = reply
    feedback.replier_id = current_user_id
    feedback.reply_time = datetime.now()
    feedback.status = 'replied'
    
    try:
        db.session.commit()
        
        # ============ 发送反馈回复通知 ============
        notification = Notification(
            user_id=feedback.user_id,
            title='您的反馈已有回复',
            content=f'您提交的「{feedback.type}」类型的反馈已收到回复：{reply}',
            type='system',
            target_type='personal'
        )
        db.session.add(notification)
        db.session.commit()
        # ============ 通知发送完成 ============
        
        return jsonify({
            'code': 200,
            'message': '回复成功',
            'data': feedback.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'回复失败: {str(e)}'}), 500

@auditor_bp.route('/feedbacks/replied', methods=['GET'])
@jwt_required()
@role_required('auditor', 'admin')
def get_replied_feedbacks():
    """获取已回复的反馈列表"""
    # 查询参数
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    
    # 构建查询
    query = Feedback.query.filter(Feedback.status.in_(['replied', 'closed']))
    
    # 审核员只能查看"咨询"类型，管理员可以查看所有
    if current_user and current_user.role == 'auditor':
        query = query.filter_by(type='consultation')
    
    query = query.order_by(Feedback.reply_time.desc())
    
    # 分页
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': {
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'feedbacks': [f.to_dict() for f in pagination.items]
        }
    })

