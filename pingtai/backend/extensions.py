"""
Flask 扩展统一出口（避免循环导入/多实例问题）
"""

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
jwt = JWTManager()

