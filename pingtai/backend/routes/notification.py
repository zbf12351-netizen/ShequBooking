"""消息通知路由"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Notification, User
from extensions import db

notification_bp = Blueprint('notification', __name__)

# ==================== 公开公告API（无需登录） ====================

@notification_bp.route('/public/announcements', methods=['GET'])
def get_public_announcements():
    """
    获取公开公告列表（无需登录）
    用于首页公告栏展示
    """
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 5, type=int)

    # 只获取全员通知(target_type='all')
    query = Notification.query.filter(
        Notification.target_type == 'all'
    ).order_by(Notification.created_at.desc())

    pagination = query.paginate(page=page, per_page=page_size, error_out=False)

    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': {
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'announcements': [n.to_dict() for n in pagination.items]
        }
    })


@notification_bp.route('/public/detail/<int:notification_id>', methods=['GET'])
def get_public_announcement_detail(notification_id):
    """
    获取公告详情（无需登录）
    """
    notification = db.session.get(Notification, notification_id)

    if not notification:
        return jsonify({'code': 404, 'message': '公告不存在'}), 404

    # 只允许查看全员通知
    if notification.target_type != 'all':
        return jsonify({'code': 403, 'message': '无权查看'}), 403

    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': notification.to_dict()
    })


# ==================== 用户通知API（需要登录） ====================

@notification_bp.route('/list', methods=['GET'])
@jwt_required()
def get_notifications():
    """获取通知列表"""
    current_user_id = get_jwt_identity()
    
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    
    # 查询条件：个人通知(发给当前用户) 或 全员通知(包含旧数据target_type为NULL的情况)
    query = Notification.query.filter(
        db.or_(
            Notification.user_id == current_user_id,
            Notification.target_type == 'all',
            Notification.target_type == None  # 兼容旧数据
        )
    )
    
    if unread_only:
        query = query.filter_by(is_read=False)
    
    query = query.order_by(Notification.created_at.desc())
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': {
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'unread_count': Notification.query.filter(
                db.or_(
                    Notification.user_id == current_user_id,
                    Notification.target_type == 'all',
                    Notification.target_type == None  # 兼容旧数据
                ),
                Notification.is_read == False
            ).count(),
            'notifications': [n.to_dict() for n in pagination.items]
        }
    })

@notification_bp.route('/detail/<int:notification_id>', methods=['GET'])
@jwt_required()
def get_notification_detail(notification_id):
    """获取通知详情"""
    current_user_id = get_jwt_identity()
    notification = db.session.get(Notification, notification_id)
    
    if not notification:
        return jsonify({'code': 404, 'message': '通知不存在'}), 404
    
    # 检查权限：个人通知必须是接收者，全员通知任何人都可以查看
    is_all_notification = notification.target_type == 'all' or notification.target_type is None
    if not is_all_notification and notification.user_id != current_user_id:
        return jsonify({'code': 403, 'message': '无权查看'}), 403
    
    # 标记为已读
    if not notification.is_read:
        notification.is_read = True
        db.session.commit()
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': notification.to_dict()
    })

@notification_bp.route('/read/<int:notification_id>', methods=['POST'])
@jwt_required()
def mark_as_read(notification_id):
    """标记通知为已读"""
    current_user_id = get_jwt_identity()
    notification = db.session.get(Notification, notification_id)
    
    if not notification:
        return jsonify({'code': 404, 'message': '通知不存在'}), 404
    
    # 检查权限：个人通知必须是接收者，全员通知任何人都可以标记（兼容旧数据）
    is_all_notification = notification.target_type == 'all' or notification.target_type == None
    if not is_all_notification and notification.user_id != current_user_id:
        return jsonify({'code': 403, 'message': '无权操作'}), 403
    
    notification.is_read = True
    
    try:
        db.session.commit()
        return jsonify({
            'code': 200,
            'message': '标记成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'操作失败: {str(e)}'}), 500

@notification_bp.route('/read-all', methods=['POST'])
@jwt_required()
def mark_all_as_read():
    """标记所有通知为已读"""
    current_user_id = get_jwt_identity()
    
    try:
        # 标记个人通知和全员通知为已读（兼容旧数据）
        Notification.query.filter(
            db.or_(
                Notification.user_id == current_user_id,
                Notification.target_type == 'all',
                Notification.target_type == None  # 兼容旧数据
            ),
            Notification.is_read == False
        ).update({'is_read': True}, synchronize_session=False)
        db.session.commit()
        return jsonify({
            'code': 200,
            'message': '标记成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'操作失败: {str(e)}'}), 500

@notification_bp.route('/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    """获取未读通知数量"""
    current_user_id = get_jwt_identity()
    
    # 统计个人通知 + 全员通知的未读数量（兼容旧数据）
    count = Notification.query.filter(
        db.or_(
            Notification.user_id == current_user_id,
            Notification.target_type == 'all',
            Notification.target_type == None  # 兼容旧数据
        ),
        Notification.is_read == False
    ).count()
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': {'count': count}
    })


def create_notification(user_id, title, content, notification_type='system'):
    """创建通知（内部调用）"""
    notification = Notification(
        user_id=user_id,
        title=title,
        content=content,
        type=notification_type
    )
    db.session.add(notification)
    return notification


# ==================== 管理员通知管理API ====================

@notification_bp.route('/admin/publish', methods=['POST'])
@jwt_required()
def admin_publish_notification():
    """
    管理员发布全员通知
    """
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    
    if not current_user or current_user.role != 'admin':
        return jsonify({'code': 403, 'message': '只有管理员才能发布通知'}), 403
    
    data = request.get_json()
    title = data.get('title')
    content = data.get('content')
    notification_type = data.get('type', 'system')
    
    if not title or not content:
        return jsonify({'code': 400, 'message': '标题和内容不能为空'}), 400
    
    try:
        # 创建全员通知
        notification = Notification(
            user_id=current_user_id,
            title=title,
            content=content,
            type=notification_type,
            target_type='all'
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '通知已成功发布给所有用户',
            'data': {'notification_id': notification.notification_id}
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'发布通知失败: {str(e)}'}), 500


@notification_bp.route('/admin/list', methods=['GET'])
@jwt_required()
def admin_list_notifications():
    """
    管理员查看已发布的通知列表
    按通知内容分组，每条通知只显示一次
    """
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    
    if not current_user or current_user.role != 'admin':
        return jsonify({'code': 403, 'message': '只有管理员才能查看'}), 403
    
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    
    # 获取管理员发送的所有通知（按标题、内容、类型分组，每组只取最早的一条）
    # 使用子查询找到每组的最早ID
    subquery = db.session.query(
        Notification.title,
        Notification.content,
        Notification.type,
        db.func.min(Notification.notification_id).label('min_id')
    ).filter(
        Notification.title.isnot(None)
    ).group_by(
        Notification.title,
        Notification.content,
        Notification.type
    ).subquery()
    
    query = Notification.query.join(
        subquery,
        Notification.notification_id == subquery.c.min_id
    ).order_by(Notification.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    
    # 构建去重后的通知列表
    result = []
    seen_titles = set()
    for n in pagination.items:
        key = f"{n.title}_{n.content}_{n.type}"
        if key not in seen_titles:
            seen_titles.add(key)
            result.append(n.to_dict())
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': {
            'total': len(seen_titles),
            'page': page,
            'page_size': page_size,
            'notifications': result
        }
    })
