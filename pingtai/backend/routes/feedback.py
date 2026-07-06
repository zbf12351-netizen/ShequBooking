"""反馈管理路由"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Feedback, User
from extensions import db
from datetime import datetime

feedback_bp = Blueprint('feedback', __name__)

@feedback_bp.route('/create', methods=['POST'])
@jwt_required()
def create_feedback():
    """创建反馈"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # 验证必填字段
    if 'type' not in data or 'content' not in data:
        return jsonify({'code': 400, 'message': '缺少必填字段'}), 400
    
    feedback_type = data['type']
    content = data['content']
    images = data.get('images', [])
    
    # 验证反馈类型
    if feedback_type not in ['consultation', 'complaint', 'suggestion']:
        return jsonify({'code': 400, 'message': '反馈类型不正确'}), 400
    
    # 创建反馈
    feedback = Feedback(
        user_id=current_user_id,
        type=feedback_type,
        content=content
    )
    
    try:
        db.session.add(feedback)
        db.session.commit()
        return jsonify({
            'code': 200,
            'message': '提交成功',
            'data': feedback.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'提交失败: {str(e)}'}), 500

@feedback_bp.route('/my-feedbacks', methods=['GET'])
@jwt_required()
def get_my_feedbacks():
    """获取我的反馈列表"""
    current_user_id = get_jwt_identity()
    
    # 查询参数
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    status = request.args.get('status', '')
    
    # 构建查询
    query = Feedback.query.filter_by(user_id=current_user_id)
    
    if status:
        query = query.filter_by(status=status)
    
    # 按创建时间倒序
    query = query.order_by(Feedback.created_at.desc())
    
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

@feedback_bp.route('/detail/<int:feedback_id>', methods=['GET'])
@jwt_required()
def get_feedback_detail(feedback_id):
    """获取反馈详情"""
    current_user_id = get_jwt_identity()
    feedback = db.session.get(Feedback, feedback_id)
    
    if not feedback:
        return jsonify({'code': 404, 'message': '反馈不存在'}), 404
    
    # 只能查看自己的反馈
    user = db.session.get(User, current_user_id)
    if feedback.user_id != current_user_id and user.role not in ['auditor', 'admin']:
        return jsonify({'code': 403, 'message': '无权查看'}), 403
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': feedback.to_dict()
    })

@feedback_bp.route('/pending', methods=['GET'])
@jwt_required()
def get_all_pending_feedbacks():
    """管理员获取所有待处理反馈（支持类型筛选）"""
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    
    # 权限检查
    if user.role not in ['admin', 'auditor']:
        return jsonify({'code': 403, 'message': '无权访问'}), 403
    
    # 查询参数
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    feedback_type = request.args.get('type', '')
    
    # 构建查询
    query = Feedback.query.filter_by(status='pending')
    
    # 如果指定了类型筛选
    if feedback_type:
        query = query.filter_by(type=feedback_type)
    
    # 审核员只能查看咨询类型
    if user.role == 'auditor':
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

@feedback_bp.route('/replied', methods=['GET'])
@jwt_required()
def get_all_replied_feedbacks():
    """管理员获取所有已处理反馈（支持类型筛选）"""
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    
    # 权限检查
    if user.role not in ['admin', 'auditor']:
        return jsonify({'code': 403, 'message': '无权访问'}), 403
    
    # 查询参数
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    feedback_type = request.args.get('type', '')
    
    # 构建查询
    query = Feedback.query.filter(Feedback.status.in_(['replied', 'closed']))
    
    # 如果指定了类型筛选
    if feedback_type:
        query = query.filter_by(type=feedback_type)
    
    # 审核员只能查看咨询类型
    if user.role == 'auditor':
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

@feedback_bp.route('/pending-count', methods=['GET'])
@jwt_required()
def get_pending_count():
    """获取待处理反馈数量"""
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    
    # 构建查询
    query = Feedback.query.filter_by(status='pending')
    
    # 审核员只能查看咨询类型
    if user.role == 'auditor':
        query = query.filter_by(type='consultation')
    
    count = query.count()
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': {'count': count}
    })

@feedback_bp.route('/replied-count', methods=['GET'])
@jwt_required()
def get_replied_count():
    """获取已处理反馈数量"""
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    
    # 构建查询
    query = Feedback.query.filter(Feedback.status.in_(['replied', 'closed']))
    
    # 审核员只能查看咨询类型
    if user.role == 'auditor':
        query = query.filter_by(type='consultation')
    
    count = query.count()
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': {'count': count}
    })
