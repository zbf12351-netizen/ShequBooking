from flask import Flask
from flask_cors import CORS
from config import config
import os
import sys

# 设置控制台输出编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    # 设置控制台代码页为 UTF-8
    os.system('chcp 65001 > nul')

# 初始化扩展（统一从 extensions 引用，避免多实例）
from extensions import db, jwt

def create_app(config_name=None):
    """应用工厂函数"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    app.static_folder = 'static'
    app.static_url_path = '/static'
    
    # 初始化扩展
    db.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # 注册蓝图
    from routes.auth import auth_bp
    from routes.user import user_bp
    from routes.facility import facility_bp
    from routes.booking import booking_bp
    from routes.feedback import feedback_bp
    from routes.admin import admin_bp
    from routes.auditor import auditor_bp
    from routes.notification import notification_bp
    from routes.admin_stats import admin_stats_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(facility_bp, url_prefix='/api/facility')
    app.register_blueprint(booking_bp, url_prefix='/api/booking')
    app.register_blueprint(feedback_bp, url_prefix='/api/feedback')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(auditor_bp, url_prefix='/api/auditor')
    app.register_blueprint(notification_bp, url_prefix='/api/notification')
    app.register_blueprint(admin_stats_bp, url_prefix='/api/admin/stats')
    
    # 健康检查端点
    @app.route('/api/health')
    def health_check():
        return {'status': 'ok', 'message': 'Service is running'}
    
    return app

if __name__ == '__main__':
    print("=" * 60)
    print("  社区设施预订与优化服务平台")
    print("  Community Facility Booking Platform")
    print("=" * 60)
    print()
    print("提示: 请先手动创建数据库")
    print("执行命令: mysql -u root -p < database.sql")
    print()
    
    app = create_app()
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    print(f"后端服务: http://localhost:{port}")
    print(f"API健康检查: http://localhost:{port}/api/health")
    print("\n按 Ctrl+C 停止服务")
    print("=" * 60)
    print()
    
    app.run(host=host, port=port, debug=True)

