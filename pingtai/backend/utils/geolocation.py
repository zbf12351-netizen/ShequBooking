"""
地理位置工具函数
包含距离计算、坐标转换等功能
"""
import math


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    使用Haversine公式计算两个经纬度坐标之间的距离

    Args:
        lat1: 第一个点的纬度
        lon1: 第一个点的经度
        lat2: 第二个点的纬度
        lon2: 第二个点的经度

    Returns:
        两点之间的距离（单位：米）
    """
    # 地球半径（米）
    R = 6371000

    # 将角度转换为弧度
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine公式
    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # 计算距离
    distance = R * c
    return distance


def is_within_checkin_range(facility_lat, facility_lon, user_lat, user_lon, radius):
    """
    判断用户是否在签到范围内

    Args:
        facility_lat: 设施纬度
        facility_lon: 设施经度
        user_lat: 用户纬度
        user_lon: 用户经度
        radius: 签到范围半径（米）

    Returns:
        True 如果用户在范围内，否则 False
    """
    if None in [facility_lat, facility_lon, user_lat, user_lon]:
        return False

    distance = haversine_distance(facility_lat, facility_lon, user_lat, user_lon)
    return distance <= radius


def validate_coordinates(lat, lon):
    """
    验证经纬度坐标是否有效

    Args:
        lat: 纬度（应为 -90 到 90 之间的数字）
        lon: 经度（应为 -180 到 180 之间的数字）

    Returns:
        True 如果坐标有效，否则 False
    """
    try:
        lat = float(lat)
        lon = float(lon)
        return -90 <= lat <= 90 and -180 <= lon <= 180
    except (TypeError, ValueError):
        return False
