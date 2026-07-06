"""工具装饰器"""
from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from models import User, OperationLog
from extensions import db

# 操作类型中文映射
ACTION_CHINESE = {
    # 用户管理
    'create_auditor': '创建审核员',
    'toggle_user_status': '切换用户状态',
    # 设施管理
    'create_facility': '创建设施',
    'update_facility': '更新设施',
    'delete_facility': '删除设施',
    # 规则管理
    'create_rule': '创建规则',
    'update_rule': '更新规则',
    # 预约管理
    'audit_booking': '审核预约',
    'handle_exception': '处理预约异常',
    # 反馈管理
    'reply_feedback': '回复反馈',
}

# 模块中文映射
MODULE_CHINESE = {
    'user_management': '用户管理',
    'facility_management': '设施管理',
    'rule_management': '规则管理',
    'booking_management': '预约管理',
    'feedback_management': '反馈管理',
}

def role_required(*allowed_roles):
    """
    角色权限验证装饰器
    Usage: @role_required('admin', 'auditor')
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            current_user_id = get_jwt_identity()
            print(f"[DEBUG role_required] current_user_id: {current_user_id}")
            user = db.session.get(User, current_user_id)
            
            if not user:
                print(f"[DEBUG role_required] 用户不存在")
                return jsonify({'code': 401, 'message': '用户不存在'}), 401
            
            print(f"[DEBUG role_required] user.role: {user.role}, allowed: {allowed_roles}")
            
            if user.role not in allowed_roles:
                print(f"[DEBUG role_required] 权限不足")
                return jsonify({'code': 403, 'message': '权限不足'}), 403
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def log_operation(action, module):
    """
    操作日志装饰器
    Usage: @log_operation('create_user', 'user_management')
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # 先获取当前用户
            try:
                verify_jwt_in_request()
                current_user_id = get_jwt_identity()
            except Exception:
                current_user_id = None
            
            # 执行原函数
            result = fn(*args, **kwargs)
            
            # 记录日志（无论操作是否成功都记录）
            try:
                # 判断操作结果
                is_success = False
                if isinstance(result, tuple):
                    response_data = result[0].get_json() if hasattr(result[0], 'get_json') else {}
                    is_success = response_data.get('code') in [200, 201]
                elif hasattr(result, 'get_json'):
                    response_data = result.get_json()
                    is_success = response_data.get('code') in [200, 201]
                
                action_text = ACTION_CHINESE.get(action, action)
                module_text = MODULE_CHINESE.get(module, module)
                description = f'{action_text}'
                
                log = OperationLog(
                    user_id=current_user_id,
                    action=action,
                    module=module,
                    description=description,
                    ip_address=request.remote_addr
                )
                db.session.add(log)
                db.session.commit()
            except Exception as e:
                print(f"Failed to log operation: {e}")
            
            return result
        return wrapper
    return decorator

