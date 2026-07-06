from extensions import db
from datetime import datetime

class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(11), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    role = db.Column(db.Enum('resident', 'auditor', 'admin'), default='resident')
    wechat_openid = db.Column(db.String(64), unique=True, nullable=True)
    status = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    bookings = db.relationship('Booking', back_populates='user', foreign_keys='Booking.user_id', viewonly=True)
    feedbacks = db.relationship('Feedback', back_populates='user', foreign_keys='Feedback.user_id', viewonly=True)
    behaviors = db.relationship('UserBehavior', back_populates='user')
    favorites = db.relationship('Favorite', back_populates='user', cascade='all, delete-orphan')
    views = db.relationship('FacilityView', back_populates='user', cascade='all, delete-orphan')

    def set_password(self, password):
        """设置密码（纯文本存储，仅限测试环境）"""
        self.password = password

    def check_password(self, password):
        """验证密码（纯文本对比，仅限测试环境）"""
        return self.password == password

    def to_dict(self):
        """转换为字典"""
        return {
            'user_id': self.user_id,
            'phone': self.phone,
            'username': self.username,
            'role': self.role,
            'avatar': getattr(self, 'avatar', None),
            'wechat_openid': self.wechat_openid,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    @staticmethod
    def get_by_wechat_openid(openid):
        """通过微信OpenID获取用户"""
        return User.query.filter_by(wechat_openid=openid).first()

class Facility(db.Model):
    """设施模型"""
    __tablename__ = 'facilities'

    facility_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(255), nullable=False)
    capacity = db.Column(db.Integer, default=1)
    image_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.Integer, default=1)
    booking_count = db.Column(db.Integer, default=0)
    rating = db.Column(db.Numeric(3, 2), default=0.00)

    # 签到范围设置（地理位置）
    latitude = db.Column(db.Numeric(10, 7), nullable=True)  # 纬度
    longitude = db.Column(db.Numeric(10, 7), nullable=True)  # 经度
    checkin_radius = db.Column(db.Integer, default=200)  # 签到范围半径（米），默认200米
    require_checkin_location = db.Column(db.Boolean, default=False)  # 是否需要位置校验，默认关闭

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    bookings = db.relationship('Booking', back_populates='facility')
    behaviors = db.relationship('UserBehavior', back_populates='facility')
    rules = db.relationship('BookingRule', back_populates='facility')
    favorites = db.relationship('Favorite', back_populates='facility', cascade='all, delete-orphan')
    views = db.relationship('FacilityView', back_populates='facility', cascade='all, delete-orphan')

    def to_dict(self):
        """转换为字典"""
        return {
            'facility_id': self.facility_id,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'location': self.location,
            'capacity': self.capacity,
            'image_url': self.image_url,
            'status': self.status,
            'booking_count': self.booking_count,
            'rating': float(self.rating) if self.rating else 0.0,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            # 签到范围设置
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'checkin_radius': self.checkin_radius,
            'require_checkin_location': self.require_checkin_location
        }

class Booking(db.Model):
    """预约模型"""
    __tablename__ = 'bookings'

    booking_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.facility_id'), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    purpose = db.Column(db.Text)
    status = db.Column(db.Enum('draft', 'pending', 'approved', 'rejected', 'cancelled', 'completed'), default='draft')
    auditor_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    audit_time = db.Column(db.DateTime)
    audit_comment = db.Column(db.Text)

    # 签到相关字段
    checked_in = db.Column(db.Boolean, default=False)
    checkin_time = db.Column(db.DateTime)
    has_reviewed = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    user = db.relationship('User', back_populates='bookings', foreign_keys='Booking.user_id', viewonly=True)
    facility = db.relationship('Facility', back_populates='bookings')
    auditor = db.relationship('User', foreign_keys='Booking.auditor_id', viewonly=True)
    review = db.relationship('Review', back_populates='booking', uselist=False)

    def to_dict(self):
        """转换为字典"""
        # 获取设施的位置信息（用于签到验证）
        facility_location = None
        if self.facility:
            facility_location = {
                'latitude': float(self.facility.latitude) if self.facility.latitude else None,
                'longitude': float(self.facility.longitude) if self.facility.longitude else None,
                'checkin_radius': self.facility.checkin_radius,
                'require_checkin_location': self.facility.require_checkin_location,
                'name': self.facility.name,
                'location': self.facility.location
            }

        return {
            'booking_id': self.booking_id,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else None,
            'user_phone': self.user.phone if self.user else None,
            'facility_id': self.facility_id,
            'facility_name': self.facility.name if self.facility else None,
            'booking_date': self.booking_date.strftime('%Y-%m-%d'),
            'start_time': self.start_time.strftime('%H:%M'),
            'end_time': self.end_time.strftime('%H:%M'),
            'purpose': self.purpose,
            'status': self.status,
            'auditor_id': self.auditor_id,
            'auditor_name': self.auditor.username if self.auditor else None,
            'audit_time': self.audit_time.strftime('%Y-%m-%d %H:%M:%S') if self.audit_time else None,
            'audit_comment': self.audit_comment,
            'checked_in': self.checked_in,
            'checkin_time': self.checkin_time.strftime('%Y-%m-%d %H:%M:%S') if self.checkin_time else None,
            'has_reviewed': self.has_reviewed,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'facility': facility_location
        }

class UserBehavior(db.Model):
    """用户行为模型"""
    __tablename__ = 'user_behaviors'

    behavior_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.facility_id'), nullable=False)
    behavior_type = db.Column(db.Enum('view', 'booking', 'cancel', 'complete', 'favorite'), nullable=False)
    score = db.Column(db.Numeric(3, 2), default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 关系
    user = db.relationship('User', back_populates='behaviors')
    facility = db.relationship('Facility', back_populates='behaviors')

class FacilityView(db.Model):
    """设施浏览记录模型"""
    __tablename__ = 'facility_views'

    view_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.facility_id'), nullable=False)
    view_date = db.Column(db.Date, nullable=False)
    view_count = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    user = db.relationship('User', back_populates='views')
    facility = db.relationship('Facility', back_populates='views')

    # 唯一约束
    __table_args__ = (
        db.UniqueConstraint('user_id', 'facility_id', 'view_date', name='uk_user_facility_date'),
    )

    def to_dict(self):
        return {
            'view_id': self.view_id,
            'user_id': self.user_id,
            'facility_id': self.facility_id,
            'facility_name': self.facility.name if self.facility else None,
            'view_date': self.view_date.strftime('%Y-%m-%d') if self.view_date else None,
            'view_count': self.view_count,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

class Feedback(db.Model):
    """反馈模型"""
    __tablename__ = 'feedbacks'

    feedback_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    type = db.Column(db.Enum('consultation', 'complaint', 'suggestion'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum('pending', 'replied', 'closed'), default='pending')
    reply = db.Column(db.Text)
    replier_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    reply_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    user = db.relationship('User', back_populates='feedbacks', foreign_keys='Feedback.user_id', viewonly=True)
    replier = db.relationship('User', foreign_keys='Feedback.replier_id', viewonly=True)

    def to_dict(self):
        """转换为字典"""
        return {
            'feedback_id': self.feedback_id,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else None,
            'user_phone': self.user.phone if self.user else None,
            'type': self.type,
            'content': self.content,
            'status': self.status,
            'reply': self.reply,
            'replier_id': self.replier_id,
            'replier_name': self.replier.username if self.replier else None,
            'reply_time': self.reply_time.strftime('%Y-%m-%d %H:%M:%S') if self.reply_time else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class BookingRule(db.Model):
    """预约规则模型"""
    __tablename__ = 'booking_rules'

    rule_id = db.Column(db.Integer, primary_key=True)
    rule_name = db.Column(db.String(100), nullable=False)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.facility_id'))
    max_advance_days = db.Column(db.Integer, default=7)
    min_duration = db.Column(db.Integer, default=30)
    max_duration = db.Column(db.Integer, default=120)
    daily_limit = db.Column(db.Integer, default=1)
    start_time = db.Column(db.Time, default='08:00:00')
    end_time = db.Column(db.Time, default='22:00:00')
    status = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    facility = db.relationship('Facility', back_populates='rules')

    def to_dict(self):
        """转换为字典"""
        return {
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'facility_id': self.facility_id,
            'facility_name': self.facility.name if self.facility else '全局规则',
            'max_advance_days': self.max_advance_days,
            'min_duration': self.min_duration,
            'max_duration': self.max_duration,
            'daily_limit': self.daily_limit,
            'start_time': self.start_time.strftime('%H:%M'),
            'end_time': self.end_time.strftime('%H:%M'),
            'status': self.status
        }

class Favorite(db.Model):
    """收藏模型"""
    __tablename__ = 'favorites'

    favorite_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.facility_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 唯一约束
    __table_args__ = (
        db.UniqueConstraint('user_id', 'facility_id', name='uk_user_facility'),
    )

    # 关系
    user = db.relationship('User', back_populates='favorites')
    facility = db.relationship('Facility', back_populates='favorites')

    def to_dict(self):
        return {
            'favorite_id': self.favorite_id,
            'user_id': self.user_id,
            'facility_id': self.facility_id,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class OperationLog(db.Model):
    """操作日志模型"""
    __tablename__ = 'operation_logs'

    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    module = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 关系
    user = db.relationship('User')

    def to_dict(self):
        """转换为字典"""
        return {
            'log_id': self.log_id,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else None,
            'action': self.action,
            'module': self.module,
            'description': self.description,
            'ip_address': self.ip_address,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class Review(db.Model):
    """评价模型"""
    __tablename__ = 'reviews'

    review_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.facility_id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.booking_id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 关系
    user = db.relationship('User')
    facility = db.relationship('Facility')
    booking = db.relationship('Booking', back_populates='review')

    def to_dict(self):
        """转换为字典"""
        return {
            'review_id': self.review_id,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else None,
            'facility_id': self.facility_id,
            'facility_name': self.facility.name if self.facility else None,
            'booking_id': self.booking_id,
            'rating': self.rating,
            'content': self.content,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class Notification(db.Model):
    """消息通知模型"""
    __tablename__ = 'notifications'

    notification_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    type = db.Column(db.Enum('booking', 'audit', 'system', 'reminder'), default='system')
    is_read = db.Column(db.Boolean, default=False)
    target_type = db.Column(db.Enum('personal', 'all'), default='personal')
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 关系
    user = db.relationship('User')

    def to_dict(self):
        """转换为字典"""
        return {
            'notification_id': self.notification_id,
            'user_id': self.user_id,
            'title': self.title,
            'content': self.content,
            'type': self.type,
            'is_read': self.is_read,
            'target_type': self.target_type,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


class CheckinRecord(db.Model):
    """签到记录模型"""
    __tablename__ = 'checkin_records'

    checkin_id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.booking_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.facility_id'), nullable=False)
    checkin_time = db.Column(db.DateTime, nullable=False)
    user_latitude = db.Column(db.Numeric(10, 7), nullable=False)
    user_longitude = db.Column(db.Numeric(10, 7), nullable=False)
    facility_latitude = db.Column(db.Numeric(10, 7), nullable=False)
    facility_longitude = db.Column(db.Numeric(10, 7), nullable=False)
    distance_meters = db.Column(db.Numeric(10, 2))
    is_within_radius = db.Column(db.Boolean, default=0)
    checkin_radius = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum('success', 'failed', 'timeout'), default='success')
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 关系
    booking = db.relationship('Booking')
    user = db.relationship('User')
    facility = db.relationship('Facility')

    def to_dict(self):
        """转换为字典"""
        return {
            'checkin_id': self.checkin_id,
            'booking_id': self.booking_id,
            'user_id': self.user_id,
            'facility_id': self.facility_id,
            'checkin_time': self.checkin_time.strftime('%Y-%m-%d %H:%M:%S') if self.checkin_time else None,
            'user_latitude': float(self.user_latitude) if self.user_latitude else None,
            'user_longitude': float(self.user_longitude) if self.user_longitude else None,
            'facility_latitude': float(self.facility_latitude) if self.facility_latitude else None,
            'facility_longitude': float(self.facility_longitude) if self.facility_longitude else None,
            'distance_meters': float(self.distance_meters) if self.distance_meters else None,
            'is_within_radius': bool(self.is_within_radius),
            'checkin_radius': self.checkin_radius,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
