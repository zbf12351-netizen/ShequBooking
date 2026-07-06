"""用户认证路由"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import User
from config import Config
from extensions import db
from routes.notification import create_notification
import re
import requests

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """居民用户注册"""
    data = request.get_json()
    
    # 验证必填字段
    required_fields = ['phone', 'password', 'username']
    for field in required_fields:
        if field not in data:
            return jsonify({'code': 400, 'message': f'缺少必填字段: {field}'}), 400
    
    phone = str(data.get('phone', '')).strip()
    password = str(data.get('password', ''))
    username = str(data.get('username', '')).strip()
    
    # 验证手机号格式
    if not re.match(r'^1[3-9]\d{9}$', phone):
        return jsonify({'code': 400, 'message': '手机号格式不正确'}), 400
    
    # 验证密码长度
    if len(password) < 6:
        return jsonify({'code': 400, 'message': '密码长度至少6位'}), 400
    
    # 检查手机号是否已注册
    if User.query.filter_by(phone=phone).first():
        return jsonify({'code': 400, 'message': '该手机号已注册'}), 400
    
    # 创建用户
    user = User(
        phone=phone,
        username=username,
        role='resident'
    )
    user.set_password(password)
    
    try:
        db.session.add(user)
        db.session.commit()
        return jsonify({
            'code': 200,
            'message': '注册成功',
            'data': user.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'注册失败: {str(e)}'}), 500

@auth_bp.route('/wechat-login', methods=['POST'])
def wechat_login():
    """
    微信授权登录
    流程：
    1. 前端调用 wx.login() 获取 code
    2. 前端将 code 发送到后端
    3. 后端使用 code 换取 openid 和 session_key
    4. 后端创建/获取用户信息，返回 JWT token
    """
    data = request.get_json()
    code = data.get('code')
    user_info = data.get('userInfo', {})  # 可选，用户授权的头像昵称
    
    if not code:
        return jsonify({'code': 400, 'message': '缺少微信登录凭证'}), 400
    
    # 调试日志：打印配置和请求参数
    print(f"=== 微信登录调试 ===")
    print(f"AppID: {Config.WECHAT_APPID}")
    print(f"Code: {code}")
    
    # 1. 调用微信接口获取 openid（使用 jscode2session 接口）
    url = f'https://api.weixin.qq.com/sns/jscode2session?appid={Config.WECHAT_APPID}&secret={Config.WECHAT_SECRET}&js_code={code}&grant_type=authorization_code'
    print(f"请求URL: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        wechat_data = response.json()
        print(f"微信返回: {wechat_data}")
        
        if 'errcode' in wechat_data and wechat_data['errcode'] != 0:
            return jsonify({
                'code': 400, 
                'message': f'微信登录失败: {wechat_data.get("errmsg", "未知错误")}'
            }), 400
        
        openid = wechat_data.get('openid')
        unionid = wechat_data.get('unionid')
        
        if not openid:
            return jsonify({'code': 400, 'message': '无法获取微信OpenID'}), 400
        
    except Exception as e:
        print(f"连接微信服务器错误: {str(e)}")
        return jsonify({'code': 500, 'message': f'连接微信服务器失败: {str(e)}'}), 500
    
    # 2. 查找或创建用户
    user = User.get_by_wechat_openid(openid)
    
    if not user:
        # 新用户，自动注册
        # 生成随机用户名（微信昵称或默认）
        username = user_info.get('nickName', f'微信用户_{openid[-6:]}') if user_info else f'微信用户_{openid[-6:]}'
        
        # 如果有手机号，可以尝试绑定
        phone = data.get('phone')
        
        # 临时手机号（微信用户使用短格式）
        temp_phone = f'wx_{openid[-6:]}' if not phone else phone
        
        user = User(
            phone=temp_phone,
            username=username,
            role='resident',
            wechat_openid=openid
        )
        # 微信登录用户设置一个随机密码
        import random
        user.set_password(''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=12)))
        
        try:
            db.session.add(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # 如果手机号冲突，尝试更短的格式
            if 'phone' in str(e).lower():
                user.phone = f'w{openid[-4:]}'
                db.session.add(user)
                db.session.commit()
            else:
                return jsonify({'code': 500, 'message': f'创建用户失败: {str(e)}'}), 500
    
    # 3. 检查用户状态
    if user.status != 1:
        return jsonify({'code': 403, 'message': '账户已被禁用'}), 403
    
    # 4. 更新用户信息
    
    try:
        db.session.commit()
    except:
        db.session.rollback()
    
    # 5. 生成JWT令牌
    access_token = create_access_token(identity=user.user_id)
    
    return jsonify({
        'code': 200,
        'message': '登录成功',
        'data': {
            'user': user.to_dict(),
            'token': access_token,
            'is_new_user': user.phone.startswith('wechat_')  # 是否需要绑定手机号
        }
    })


@auth_bp.route('/bind-phone', methods=['POST'])
@jwt_required()
def bind_phone():
    """
    绑定手机号（微信用户后续绑定手机号）
    """
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404
    
    data = request.get_json()
    phone = str(data.get('phone', '')).strip()
    
    if not re.match(r'^1[3-9]\d{9}$', phone):
        return jsonify({'code': 400, 'message': '手机号格式不正确'}), 400
    
    # 检查手机号是否已被其他用户使用
    existing = User.query.filter_by(phone=phone).first()
    if existing and existing.user_id != user.user_id:
        return jsonify({'code': 400, 'message': '该手机号已被绑定'}), 400
    
    user.phone = phone
    user.set_password(data.get('password', 'wechat_user'))  # 设置默认密码或用户提供的密码
    
    try:
        db.session.commit()
        return jsonify({
            'code': 200,
            'message': '手机号绑定成功',
            'data': user.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'绑定失败: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    
    phone = str(data.get('phone', '')).strip()
    password = str(data.get('password', ''))
    
    if not phone or not password:
        return jsonify({'code': 400, 'message': '手机号和密码不能为空'}), 400
    
    # 查找用户
    user = User.query.filter_by(phone=phone).first()
    
    if not user or not user.check_password(password):
        return jsonify({'code': 401, 'message': '手机号或密码错误'}), 401
    
    # 检查用户状态
    if user.status != 1:
        return jsonify({'code': 403, 'message': '账户已被禁用'}), 403
    
    # 生成访问令牌
    access_token = create_access_token(identity=user.user_id)
    
    return jsonify({
        'code': 200,
        'message': '登录成功',
        'data': {
            'user': user.to_dict(),
            'token': access_token
        }
    })

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """获取当前用户信息"""
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404
    
    return jsonify({
        'code': 200,
        'message': '获取成功',
        'data': user.to_dict()
    })

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """更新用户信息"""
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404
    
    data = request.get_json()
    
    # 可更新字段
    if 'username' in data:
        user.username = data['username']
    
    try:
        db.session.commit()
        return jsonify({
            'code': 200,
            'message': '更新成功',
            'data': user.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'更新失败: {str(e)}'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """修改密码"""
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    
    if not user:
        return jsonify({'code': 404, 'message': '用户不存在'}), 404
    
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({'code': 400, 'message': '旧密码和新密码不能为空'}), 400
    
    # 验证旧密码
    if not user.check_password(old_password):
        return jsonify({'code': 401, 'message': '旧密码错误'}), 401
    
    # 验证新密码长度
    if len(new_password) < 6:
        return jsonify({'code': 400, 'message': '新密码长度至少6位'}), 400
    
    # 更新密码
    user.set_password(new_password)
    
    try:
        db.session.commit()
        return jsonify({'code': 200, 'message': '密码修改成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'密码修改失败: {str(e)}'}), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    退出登录
    对于前端：只需清除本地 token/用户信息即可。
    此接口仅返回成功，未做黑名单处理（测试环境）。
    """
    return jsonify({'code': 200, 'message': '已退出登录'})

