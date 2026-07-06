"""居民用户路由"""
from flask import Blueprint
from flask_jwt_extended import jwt_required

user_bp = Blueprint('user', __name__)

@user_bp.route('/info', methods=['GET'])
@jwt_required()
def get_user_info():
    """获取用户信息（此功能已在auth.py中实现）"""
    from routes.auth import get_profile
    return get_profile()

