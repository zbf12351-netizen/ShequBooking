#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
社区设施预订平台 - 启动脚本
"""
import os
import sys

def check_requirements():
    """检查依赖是否安装"""
    try:
        import flask
        import flask_sqlalchemy
        import flask_cors
        import flask_jwt_extended
        print("✓ 依赖检查通过")
        return True
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def check_env():
    """检查环境配置"""
    if not os.path.exists('.env'):
        print("✗ 未找到.env配置文件")
        print("请复制.env.example并修改配置")
        return False
    print("✓ 环境配置检查通过")
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("  社区设施预订与优化服务平台")
    print("  Community Facility Booking Platform")
    print("=" * 60)
    print()
    
    # 检查依赖
    if not check_requirements():
        sys.exit(1)
    
    # 检查环境配置
    if not check_env():
        sys.exit(1)
    
    # 切换到backend目录
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    if os.path.exists(backend_dir):
        os.chdir(backend_dir)
    
    print()
    print("正在启动服务...")
    print("后端服务: http://localhost:5000")
    print("API文档: http://localhost:5000/api/health")
    print()
    print("按 Ctrl+C 停止服务")
    print("=" * 60)
    print()
    
    # 启动Flask应用
    try:
        from app import create_app
        app = create_app()
        app.run(
            host=os.getenv('FLASK_HOST', '0.0.0.0'),
            port=int(os.getenv('FLASK_PORT', 5000)),
            debug=True
        )
    except Exception as e:
        print(f"✗ 启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

