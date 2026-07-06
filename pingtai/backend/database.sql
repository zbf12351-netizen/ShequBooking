-- 创建数据库
CREATE DATABASE IF NOT EXISTS community_booking DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE community_booking;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    user_id INT(11) PRIMARY KEY AUTO_INCREMENT,
    phone VARCHAR(11) UNIQUE NOT NULL COMMENT '手机号',
    password VARCHAR(255) NOT NULL COMMENT '密码(加密)',
    username VARCHAR(50) NOT NULL COMMENT '用户名',
    role ENUM('resident', 'auditor', 'admin') DEFAULT 'resident' COMMENT '用户角色',
    wechat_openid VARCHAR(64) UNIQUE DEFAULT NULL COMMENT '微信OpenID',
    status TINYINT DEFAULT 1 COMMENT '状态：0-禁用，1-启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_phone (phone),
    INDEX idx_role (role),
    INDEX idx_wechat_openid (wechat_openid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 设施表
CREATE TABLE IF NOT EXISTS facilities (
    facility_id INT(11) PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '设施名称',
    category VARCHAR(50) NOT NULL COMMENT '设施类别',
    description TEXT COMMENT '设施描述',
    location VARCHAR(255) NOT NULL COMMENT '设施位置',
    capacity INT(11) DEFAULT 1 COMMENT '容纳人数',
    image_url VARCHAR(500) DEFAULT NULL COMMENT '设施图片URL',
    status TINYINT DEFAULT 1 COMMENT '状态：0-停用，1-启用',
    booking_count INT(11) DEFAULT 0 COMMENT '预约次数(用于热门推荐)',
    rating DECIMAL(3,2) DEFAULT 0.00 COMMENT '评分',
    -- 签到范围设置（地理位置）
    latitude DECIMAL(10,7) DEFAULT NULL COMMENT '设施纬度',
    longitude DECIMAL(10,7) DEFAULT NULL COMMENT '设施经度',
    checkin_radius INT(11) DEFAULT 200 COMMENT '签到范围半径（米），默认200米',
    require_checkin_location TINYINT(1) DEFAULT 1 COMMENT '是否需要位置校验：0-否，1-是',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_category (category),
    INDEX idx_status (status),
    INDEX idx_booking_count (booking_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设施表';

-- 预约表
CREATE TABLE IF NOT EXISTS bookings (
    booking_id INT(11) PRIMARY KEY AUTO_INCREMENT,
    user_id INT(11) NOT NULL COMMENT '用户ID',
    facility_id INT(11) NOT NULL COMMENT '设施ID',
    booking_date DATE NOT NULL COMMENT '预约日期',
    start_time TIME NOT NULL COMMENT '开始时间',
    end_time TIME NOT NULL COMMENT '结束时间',
    purpose TEXT COMMENT '预约目的',
    status ENUM('draft', 'pending', 'approved', 'rejected', 'cancelled', 'completed') DEFAULT 'draft' COMMENT '状态：草稿、待审核、通过、拒绝、取消、已完成',
    auditor_id INT(11) DEFAULT NULL COMMENT '审核员ID',
    audit_time DATETIME DEFAULT NULL COMMENT '审核时间',
    audit_comment TEXT COMMENT '审核意见',
    checked_in TINYINT(1) DEFAULT 0 COMMENT '是否已签到',
    checkin_time DATETIME DEFAULT NULL COMMENT '签到时间',
    has_reviewed TINYINT(1) DEFAULT 0 COMMENT '是否已评价',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (facility_id) REFERENCES facilities(facility_id) ON DELETE CASCADE,
    FOREIGN KEY (auditor_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_facility_id (facility_id),
    INDEX idx_status (status),
    INDEX idx_booking_date (booking_date),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预约表';

-- 用户行为表（用于协同过滤推荐）
CREATE TABLE IF NOT EXISTS user_behaviors (
    behavior_id INT(11) PRIMARY KEY AUTO_INCREMENT,
    user_id INT(11) NOT NULL COMMENT '用户ID',
    facility_id INT(11) NOT NULL COMMENT '设施ID',
    behavior_type ENUM('view', 'booking', 'cancel', 'complete', 'favorite') NOT NULL COMMENT '行为类型：view-浏览, booking-预约, cancel-取消, complete-完成, favorite-收藏',
    score DECIMAL(3,2) DEFAULT 0.00 COMMENT '评分',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (facility_id) REFERENCES facilities(facility_id) ON DELETE CASCADE,
    INDEX idx_user_facility (user_id, facility_id),
    INDEX idx_behavior_type (behavior_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户行为表（用于协同过滤推荐）';

-- 反馈表
CREATE TABLE IF NOT EXISTS feedbacks (
    feedback_id INT(11) PRIMARY KEY AUTO_INCREMENT,
    user_id INT(11) NOT NULL COMMENT '用户ID',
    type ENUM('consultation', 'complaint', 'suggestion') NOT NULL COMMENT '类型：consultation-咨询, complaint-投诉, suggestion-建议',
    content TEXT NOT NULL COMMENT '反馈内容',
    status ENUM('pending', 'replied', 'closed') DEFAULT 'pending' COMMENT '状态：待回复、已回复、已关闭',
    reply TEXT COMMENT '回复内容',
    replier_id INT(11) DEFAULT NULL COMMENT '回复人ID',
    reply_time DATETIME DEFAULT NULL COMMENT '回复时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (replier_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='反馈表';

-- 预约规则表
CREATE TABLE IF NOT EXISTS booking_rules (
    rule_id INT(11) PRIMARY KEY AUTO_INCREMENT,
    rule_name VARCHAR(100) NOT NULL COMMENT '规则名称',
    facility_id INT(11) DEFAULT NULL COMMENT '设施ID(NULL表示全局规则)',
    max_advance_days INT(11) DEFAULT 7 COMMENT '最多提前预约天数',
    min_duration INT(11) DEFAULT 30 COMMENT '最小预约时长(分钟)',
    max_duration INT(11) DEFAULT 120 COMMENT '最大预约时长(分钟)',
    daily_limit INT(11) DEFAULT 1 COMMENT '每日预约次数限制',
    start_time TIME DEFAULT '08:00:00' COMMENT '可预约开始时间',
    end_time TIME DEFAULT '22:00:00' COMMENT '可预约结束时间',
    status TINYINT DEFAULT 1 COMMENT '状态：0-禁用，1-启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (facility_id) REFERENCES facilities(facility_id) ON DELETE CASCADE,
    INDEX idx_facility_id (facility_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预约规则表';

-- 操作日志表
CREATE TABLE IF NOT EXISTS operation_logs (
    log_id INT(11) PRIMARY KEY AUTO_INCREMENT,
    user_id INT(11) NOT NULL COMMENT '操作用户ID',
    action VARCHAR(50) NOT NULL COMMENT '操作类型',
    module VARCHAR(50) NOT NULL COMMENT '模块',
    description TEXT COMMENT '操作描述',
    ip_address VARCHAR(50) COMMENT 'IP地址',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作日志表';

-- 收藏表
CREATE TABLE IF NOT EXISTS favorites (
    favorite_id INT(11) PRIMARY KEY AUTO_INCREMENT,
    user_id INT(11) NOT NULL COMMENT '用户ID',
    facility_id INT(11) NOT NULL COMMENT '设施ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (facility_id) REFERENCES facilities(facility_id) ON DELETE CASCADE,
    UNIQUE KEY uk_user_facility (user_id, facility_id),
    INDEX idx_user_id (user_id),
    INDEX idx_facility_id (facility_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='收藏表';

-- 评价表
CREATE TABLE IF NOT EXISTS reviews (
    review_id INT(11) PRIMARY KEY AUTO_INCREMENT,
    user_id INT(11) NOT NULL COMMENT '用户ID',
    facility_id INT(11) NOT NULL COMMENT '设施ID',
    booking_id INT(11) NOT NULL COMMENT '预约ID',
    rating INT(11) NOT NULL COMMENT '评分(1-5)',
    content TEXT COMMENT '评价内容',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (facility_id) REFERENCES facilities(facility_id) ON DELETE CASCADE,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_facility_id (facility_id),
    INDEX idx_booking_id (booking_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评价表';

-- 消息通知表
CREATE TABLE IF NOT EXISTS notifications (
    notification_id INT(11) PRIMARY KEY AUTO_INCREMENT,
    user_id INT(11) NOT NULL COMMENT '用户ID',
    title VARCHAR(100) NOT NULL COMMENT '通知标题',
    content TEXT NOT NULL COMMENT '通知内容',
    type ENUM('booking', 'audit', 'system', 'reminder') DEFAULT 'system' COMMENT '通知类型：booking-预约相关, audit-审核结果, system-系统公告, reminder-签到提醒',
    is_read TINYINT(1) DEFAULT 0 COMMENT '是否已读',
    target_type ENUM('personal', 'all') DEFAULT 'personal' COMMENT '通知目标类型：personal-个人通知, all-全员通知',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_is_read (is_read),
    INDEX idx_type (type),
    INDEX idx_target_type (target_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息通知表';

-- 设施浏览记录表（独立浏览历史）
CREATE TABLE IF NOT EXISTS facility_views (
    view_id INT(11) PRIMARY KEY AUTO_INCREMENT COMMENT '浏览记录ID',
    user_id INT(11) NOT NULL COMMENT '用户ID',
    facility_id INT(11) NOT NULL COMMENT '设施ID',
    view_date DATE NOT NULL COMMENT '浏览日期',
    view_count INT(11) DEFAULT 1 COMMENT '当日浏览次数',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '首次浏览时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后浏览时间',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (facility_id) REFERENCES facilities(facility_id) ON DELETE CASCADE,
    UNIQUE KEY uk_user_facility_date (user_id, facility_id, view_date),
    INDEX idx_user_id (user_id),
    INDEX idx_facility_id (facility_id),
    INDEX idx_view_date (view_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设施浏览记录表';

-- ==================== 签到记录表（位置签到） ====================
CREATE TABLE IF NOT EXISTS checkin_records (
    checkin_id INT(11) PRIMARY KEY AUTO_INCREMENT,
    booking_id INT(11) NOT NULL COMMENT '预约ID',
    user_id INT(11) NOT NULL COMMENT '用户ID',
    facility_id INT(11) NOT NULL COMMENT '设施ID',
    checkin_time DATETIME NOT NULL COMMENT '签到时间',
    user_latitude DECIMAL(10,7) NOT NULL COMMENT '用户签到纬度',
    user_longitude DECIMAL(10,7) NOT NULL COMMENT '用户签到经度',
    facility_latitude DECIMAL(10,7) NOT NULL COMMENT '设施纬度',
    facility_longitude DECIMAL(10,7) NOT NULL COMMENT '设施经度',
    distance_meters DECIMAL(10,2) DEFAULT NULL COMMENT '签到位置与设施的距离(米)',
    is_within_radius TINYINT(1) DEFAULT 0 COMMENT '是否在允许范围内',
    checkin_radius INT(11) NOT NULL COMMENT '当时的签到半径设置(米)',
    status ENUM('success', 'failed', 'timeout') DEFAULT 'success' COMMENT '签到状态：成功、失败、超时',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (facility_id) REFERENCES facilities(facility_id) ON DELETE CASCADE,
    UNIQUE KEY uk_booking_id (booking_id),
    INDEX idx_user_id (user_id),
    INDEX idx_facility_id (facility_id),
    INDEX idx_checkin_time (checkin_time),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='签到记录表';

-- ==================== 计算两点距离的函数（Haversine公式） ====================
DROP FUNCTION IF EXISTS get_distance_meters;
DELIMITER //
CREATE FUNCTION get_distance_meters(
    lat1 DECIMAL(10,7), lon1 DECIMAL(10,7),
    lat2 DECIMAL(10,7), lon2 DECIMAL(10,7)
) RETURNS DECIMAL(10,2)
DETERMINISTIC
BEGIN
    DECLARE R INT DEFAULT 6371000;
    DECLARE dLat DECIMAL(10,7);
    DECLARE dLon DECIMAL(10,7);
    DECLARE a DECIMAL(20,15);
    DECLARE c DECIMAL(20,15);
    SET dLat = RADIANS(lat2 - lat1);
    SET dLon = RADIANS(lon2 - lon1);
    SET a = SIN(dLat/2)*SIN(dLat/2) + COS(RADIANS(lat1))*COS(RADIANS(lat2))*SIN(dLon/2)*SIN(dLon/2);
    SET c = 2*ATAN2(SQRT(a), SQRT(1-a));
    RETURN R * c;
END //
DELIMITER ;

-- ==================== 位置签到存储过程 ====================
DROP PROCEDURE IF EXISTS sp_location_checkin;
DELIMITER //
CREATE PROCEDURE sp_location_checkin(
    IN p_booking_id INT,
    IN p_user_latitude DECIMAL(10,7),
    IN p_user_longitude DECIMAL(10,7)
)
BEGIN
    DECLARE v_facility_id INT;
    DECLARE v_user_id INT;
    DECLARE v_facility_lat DECIMAL(10,7);
    DECLARE v_facility_lng DECIMAL(10,7);
    DECLARE v_checkin_radius INT;
    DECLARE v_require_location TINYINT(1);
    DECLARE v_distance DECIMAL(10,2);
    DECLARE v_is_within_radius TINYINT(1);
    DECLARE v_checkin_status ENUM('success', 'failed', 'timeout');

    SELECT user_id, facility_id INTO v_user_id, v_facility_id FROM bookings WHERE booking_id = p_booking_id;
    SELECT latitude, longitude, checkin_radius, require_checkin_location
    INTO v_facility_lat, v_facility_lng, v_checkin_radius, v_require_location
    FROM facilities WHERE facility_id = v_facility_id;

    SET v_distance = get_distance_meters(p_user_latitude, p_user_longitude, v_facility_lat, v_facility_lng);

    IF v_require_location = 0 THEN
        SET v_is_within_radius = 1; SET v_checkin_status = 'success';
    ELSEIF v_distance <= v_checkin_radius THEN
        SET v_is_within_radius = 1; SET v_checkin_status = 'success';
    ELSE
        SET v_is_within_radius = 0; SET v_checkin_status = 'failed';
    END IF;

    INSERT INTO checkin_records (
        booking_id, user_id, facility_id, checkin_time,
        user_latitude, user_longitude, facility_latitude, facility_longitude,
        distance_meters, is_within_radius, checkin_radius, status
    ) VALUES (
        p_booking_id, v_user_id, v_facility_id, NOW(),
        p_user_latitude, p_user_longitude, v_facility_lat, v_facility_lng,
        v_distance, v_is_within_radius, v_checkin_radius, v_checkin_status
    );

    IF v_checkin_status = 'success' THEN
        UPDATE bookings SET checked_in = 1, checkin_time = NOW() WHERE booking_id = p_booking_id;
    END IF;

    SELECT v_checkin_status AS checkin_status, v_distance AS distance_meters, 
           v_checkin_radius AS allowed_radius, v_is_within_radius AS is_within_radius;
END //
DELIMITER ;

-- ==================== 插入测试用户账户 ====================
-- 注意：以下是测试账户，生产环境请删除或修改密码

-- 1. 管理员账户（1个）
INSERT INTO users (phone, password, username, role) VALUES
('13800138000', 'admin123', '张管理', 'admin');
-- 密码: admin123 (明文，仅测试)

-- 2. 审核员账户（2个）
INSERT INTO users (phone, password, username, role) VALUES
('13800138001', 'admin123', '李审核', 'auditor'),
('13800138002', 'admin123', '王审核', 'auditor');
-- 密码: admin123 (明文，仅测试)

-- 3. 居民用户账户（5个）
INSERT INTO users (phone, password, username, role) VALUES
('13900000001', 'admin123', '赵居民', 'resident'),
('13900000002', 'admin123', '钱居民', 'resident'),
('13900000003', 'admin123', '孙居民', 'resident'),
('13900000004', 'admin123', '李居民', 'resident'),
('13900000005', 'admin123', '周居民', 'resident');
-- 密码: admin123 (明文，仅测试)

-- 插入示例设施数据
INSERT INTO facilities (name, category, description, location, capacity, booking_count) VALUES
-- 运动设施
('篮球场A', '运动设施', '标准篮球场地，配备照明设施', '社区东区体育场', 10, 15),
('篮球场B', '运动设施', '半场篮球场地，适合练习', '社区西区广场', 6, 8),
('羽毛球馆', '运动设施', '室内羽毛球场地，4片场地', '社区活动中心2楼', 20, 25),
('乒乓球室', '运动设施', '6张乒乓球台', '社区活动中心地下一层', 24, 18),
('健身房', '运动设施', '配备各类健身器材，跑步机、哑铃等', '社区服务中心3楼', 25, 30),
('网球场', '运动设施', '标准网球场地2片', '社区北区网球场', 8, 12),
('游泳池', '运动设施', '室内恒温游泳池，25米赛道', '社区体育中心B1', 50, 45),
('瑜伽室', '运动设施', '专业瑜伽教室，配备瑜伽垫和镜子', '社区活动中心4楼', 20, 22),
-- 会议场所
('会议室101', '会议场所', '可容纳30人的中型会议室，配备投影仪', '社区服务中心1楼', 30, 20),
('会议室102', '会议场所', '小型会议室，可容纳10人', '社区服务中心1楼', 10, 12),
('大会议室', '会议场所', '大型会议室，可容纳80人，配备音响系统', '社区服务中心5楼', 80, 35),
('培训室', '会议场所', '电脑培训室，20台电脑', '社区服务中心2楼', 25, 15),
-- 文化设施
('阅览室', '文化设施', '安静的阅读环境，藏书丰富', '社区图书馆1楼', 50, 28),
('电子阅览室', '文化设施', '电子阅览区，提供电脑和网络', '社区图书馆2楼', 30, 16),
('棋牌室', '文化设施', '设有麻将桌和棋牌桌椅', '社区活动中心B1', 40, 32),
-- 活动场所
('多功能厅', '活动场所', '可用于举办各类活动，面积200平米', '社区活动中心1楼', 100, 50),
('舞蹈室', '活动场所', '配备镜面墙和音响设备', '社区活动中心3楼', 30, 25),
('儿童活动室', '活动场所', '专为儿童设计的安全活动空间', '社区服务中心B1', 35, 40),
('老年人活动中心', '活动场所', '提供老年休闲娱乐设施', '社区服务中心4楼', 50, 22);

-- 插入默认预约规则
INSERT INTO booking_rules (rule_name, facility_id, max_advance_days, min_duration, max_duration, daily_limit, start_time, end_time) VALUES
('全局默认规则', NULL, 7, 30, 120, 2, '08:00:00', '22:00:00');

-- 插入示例公告数据
INSERT INTO notifications (user_id, title, content, type, is_read, target_type) VALUES
(1, '🏠 欢迎使用社区设施预订平台', '亲爱的社区居民：\n\n欢迎使用德城区新园社区设施预订平台！您可以在线预约篮球场、羽毛球馆、会议室等公共设施，享受便捷的社区服务。\n\n祝您使用愉快！', 'system', 0, 'all'),
(1, '📢 设施开放时间调整通知', '各位居民朋友：\n\n为更好地服务社区居民，自本周起，各设施开放时间调整为每天8:00-22:00。请大家合理安排预约时间。\n\n如有疑问，请联系社区服务中心。', 'system', 0, 'all'),
(1, '🏃 周末体育设施免费开放日', '好消息！\n\n本周末（周六、周日）社区内所有体育设施将对居民免费开放，包括健身房、游泳池、羽毛球馆等。欢迎大家积极参加体育锻炼！', 'reminder', 0, 'all');

