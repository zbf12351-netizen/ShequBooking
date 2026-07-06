# -*- coding: utf-8 -*-
"""Admin statistics routes"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User, Facility, Booking, Feedback
from extensions import db
from sqlalchemy import func, and_, case
from datetime import datetime, timedelta

admin_stats_bp = Blueprint('admin_stats', __name__)


def get_date_range(period):
    """Get date range based on period"""
    now = datetime.now()
    if period == 'today':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == 'week':
        start = now - timedelta(days=7)
        end = now
    elif period == 'month':
        start = now - timedelta(days=30)
        end = now
    elif period == 'year':
        start = now - timedelta(days=365)
        end = now
    else:
        start = now - timedelta(days=30)
        end = now
    return start, end


@admin_stats_bp.route('/overview', methods=['GET'])
@jwt_required()
def get_overview():
    """Get data overview"""
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    
    if not current_user or current_user.role != 'admin':
        return jsonify({'code': 403, 'message': 'Admin access required'}), 403
    
    try:
        # Users count
        total_users = User.query.filter_by(role='resident').count()
        
        # Facilities count
        total_facilities = Facility.query.count()
        
        # Booking stats
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        total_bookings = Booking.query.count()
        pending_bookings = Booking.query.filter_by(status='pending').count()
        today_bookings = Booking.query.filter(Booking.created_at >= today_start).count()
        today_checkins = Booking.query.filter(
            Booking.checked_in == True,
            Booking.checkin_time >= today_start
        ).count()
        
        return jsonify({
            'code': 200,
            'message': 'Success',
            'data': {
                'users': {'total': total_users},
                'facilities': total_facilities,
                'bookings': {
                    'total': total_bookings,
                    'pending': pending_bookings,
                    'today_new': today_bookings,
                    'today_checkins': today_checkins
                }
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'Error: {str(e)}'}), 500


@admin_stats_bp.route('/bookings', methods=['GET'])
@jwt_required()
def get_booking_stats():
    """Get booking statistics"""
    period = request.args.get('period', 'month')
    start_date, end_date = get_date_range(period)
    
    # Total and status distribution
    total_bookings = Booking.query.filter(
        Booking.created_at >= start_date,
        Booking.created_at <= end_date
    ).count()
    
    status_distribution = {}
    for status in ['pending', 'approved', 'rejected', 'completed', 'cancelled']:
        count = Booking.query.filter(
            Booking.status == status,
            Booking.created_at >= start_date,
            Booking.created_at <= end_date
        ).count()
        status_distribution[status] = count
    
    # Daily trend
    daily_stats = db.session.query(
        func.date(Booking.created_at).label('date'),
        func.count(Booking.booking_id).label('count')
    ).filter(
        Booking.created_at >= start_date,
        Booking.created_at <= end_date
    ).group_by(func.date(Booking.created_at)).order_by(func.date(Booking.created_at)).all()
    
    daily = [{'date': str(s.date), 'count': s.count} for s in daily_stats]
    
    return jsonify({
        'code': 200,
        'message': 'Success',
        'data': {
            'period': period,
            'total': total_bookings,
            'status_distribution': status_distribution,
            'daily': daily
        }
    })


@admin_stats_bp.route('/facilities/usage', methods=['GET'])
@jwt_required()
def get_facility_usage():
    """Get facility usage ranking"""
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    
    if not current_user or current_user.role != 'admin':
        return jsonify({'code': 403, 'message': 'Admin access required'}), 403
    
    period = request.args.get('period', 'month')
    limit = request.args.get('limit', 10, type=int)
    
    try:
        start_date, end_date = get_date_range(period)
        
        facility_stats = db.session.query(
            Facility.name,
            Facility.category,
            func.count(Booking.booking_id).label('booking_count'),
            func.sum(
                case(
                    (Booking.checked_in == True, 1),
                    else_=0
                )
            ).label('checkin_count')
        ).outerjoin(
            Booking, and_(
                Facility.facility_id == Booking.facility_id,
                Booking.created_at >= start_date,
                Booking.created_at <= end_date
            )
        ).group_by(Facility.facility_id).order_by(
            func.count(Booking.booking_id).desc()
        ).limit(limit).all()
        
        result = []
        for f in facility_stats:
            booking_count = int(f.booking_count) if f.booking_count else 0
            checkin_count = int(f.checkin_count) if f.checkin_count else 0
            usage_rate = round((checkin_count / booking_count * 100), 1) if booking_count > 0 else 0
            
            result.append({
                'name': f.name,
                'category': f.category,
                'booking_count': booking_count,
                'checkin_count': checkin_count,
                'usage_rate': usage_rate
            })
        
        return jsonify({
            'code': 200,
            'message': 'Success',
            'data': {
                'period': period,
                'rankings': result
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'Error: {str(e)}'}), 500


@admin_stats_bp.route('/users/activity', methods=['GET'])
@jwt_required()
def get_user_activity():
    """Get user activity statistics"""
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    
    if not current_user or current_user.role != 'admin':
        return jsonify({'code': 403, 'message': 'Admin access required'}), 403
    
    period = request.args.get('period', 'month')
    limit = request.args.get('limit', 10, type=int)
    
    try:
        start_date, end_date = get_date_range(period)
        
        # New users
        new_users = User.query.filter(
            User.created_at >= start_date,
            User.created_at <= end_date,
            User.role == 'resident'
        ).count()
        
        # Active users
        active_users_stats = db.session.query(
            User.username,
            User.phone,
            func.count(Booking.booking_id).label('booking_count')
        ).join(
            Booking, User.user_id == Booking.user_id
        ).filter(
            Booking.created_at >= start_date,
            Booking.created_at <= end_date
        ).group_by(User.user_id).order_by(
            func.count(Booking.booking_id).desc()
        ).limit(limit).all()
        
        active_users = [{
            'username': u.username,
            'phone': u.phone,
            'booking_count': int(u.booking_count) if u.booking_count else 0
        } for u in active_users_stats]
        
        return jsonify({
            'code': 200,
            'message': 'Success',
            'data': {
                'period': period,
                'new_users': new_users,
                'active_users': active_users
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'Error: {str(e)}'}), 500


@admin_stats_bp.route('/auditors', methods=['GET'])
@jwt_required()
def get_auditors_stats():
    """Get auditor statistics"""
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    
    if not current_user or current_user.role != 'admin':
        return jsonify({'code': 403, 'message': 'Admin access required'}), 403
    
    period = request.args.get('period', 'month')
    
    try:
        start_date, end_date = get_date_range(period)
        
        auditor_stats = db.session.query(
            User.username,
            User.phone,
            func.count(Booking.booking_id).label('total_audited'),
            func.sum(
                case(
                    (Booking.status == 'approved', 1),
                    else_=0
                )
            ).label('approved'),
            func.sum(
                case(
                    (Booking.status == 'rejected', 1),
                    else_=0
                )
            ).label('rejected')
        ).outerjoin(
            Booking, and_(
                User.user_id == Booking.auditor_id,
                Booking.audit_time >= start_date,
                Booking.audit_time <= end_date
            )
        ).filter(
            User.role == 'auditor'
        ).group_by(User.user_id).all()
        
        result = []
        for a in auditor_stats:
            total = int(a.total_audited) if a.total_audited else 0
            approved = int(a.approved) if a.approved else 0
            rejected = int(a.rejected) if a.rejected else 0
            
            result.append({
                'username': a.username,
                'phone': a.phone,
                'total_audited': total,
                'approved': approved,
                'rejected': rejected,
                'approval_rate': round((approved / total * 100), 1) if total > 0 else 0
            })
        
        return jsonify({
            'code': 200,
            'message': 'Success',
            'data': {
                'period': period,
                'auditors': result
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'Error: {str(e)}'}), 500


@admin_stats_bp.route('/auditors/workload', methods=['GET'])
@jwt_required()
def get_auditor_workload():
    """Get auditor workload statistics"""
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    
    if not current_user or current_user.role != 'admin':
        return jsonify({'code': 403, 'message': 'Admin access required'}), 403
    
    try:
        period = request.args.get('period', 'month')
        start_date, end_date = get_date_range(period)
        
        # Get all auditor workload with time filter
        auditor_query = db.session.query(
            User.username,
            User.phone,
            func.count(Booking.booking_id).label('total_audited'),
            func.sum(
                case(
                    (Booking.status.in_(['approved', 'completed']), 1),
                    else_=0
                )
            ).label('approved'),
            func.sum(
                case(
                    (Booking.status == 'rejected', 1),
                    else_=0
                )
            ).label('rejected'),
            func.sum(
                case(
                    (Booking.status == 'cancelled', 1),
                    else_=0
                )
            ).label('cancelled')
        ).outerjoin(
            Booking, User.user_id == Booking.auditor_id
        ).filter(
            User.role == 'auditor'
        )
        
        # Apply time filter if applicable
        if period != 'all':
            auditor_query = auditor_query.filter(
                Booking.created_at >= start_date
            )
        
        auditor_stats = auditor_query.group_by(User.user_id).all()
        
        result = []
        for a in auditor_stats:
            total = int(a.total_audited) if a.total_audited else 0
            approved = int(a.approved) if a.approved else 0
            rejected = int(a.rejected) if a.rejected else 0
            cancelled = int(a.cancelled) if a.cancelled else 0
            
            result.append({
                'username': a.username,
                'phone': a.phone,
                'total_audited': total,
                'approved': approved,
                'rejected': rejected,
                'cancelled': cancelled,
                'approval_rate': round((approved / total * 100), 1) if total > 0 else 0
            })
        
        return jsonify({
            'code': 200,
            'message': 'Success',
            'data': {
                'auditors': result
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'Error: {str(e)}'}), 500


@admin_stats_bp.route('/feedbacks', methods=['GET'])
@jwt_required()
def get_feedback_stats():
    """Get feedback statistics"""
    current_user_id = get_jwt_identity()
    current_user = db.session.get(User, current_user_id)
    
    if not current_user or current_user.role != 'admin':
        return jsonify({'code': 403, 'message': 'Admin access required'}), 403
    
    try:
        # Status distribution with Chinese labels
        status_stats = db.session.query(
            Feedback.status,
            func.count(Feedback.feedback_id)
        ).group_by(Feedback.status).all()
        
        # Map status to Chinese labels
        status_map = {
            'pending': 'pending',
            'replied': 'resolved',
            'closed': 'closed'
        }
        
        status_distribution = {}
        total = 0
        for s in status_stats:
            key = status_map.get(s.status, s.status)
            count = int(s[1]) if s[1] else 0
            status_distribution[key] = count
            total += count
        
        # Ensure all keys exist
        if 'pending' not in status_distribution:
            status_distribution['pending'] = 0
        if 'resolved' not in status_distribution:
            status_distribution['resolved'] = 0
        
        # Type distribution
        type_stats = db.session.query(
            Feedback.type,
            func.count(Feedback.feedback_id)
        ).group_by(Feedback.type).all()
        
        type_distribution = {}
        for t in type_stats:
            type_distribution[t.type] = int(t[1]) if t[1] else 0
        
        return jsonify({
            'code': 200,
            'message': 'Success',
            'data': {
                'total': total,
                'status_distribution': status_distribution,
                'type_distribution': type_distribution
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'code': 500, 'message': f'Error: {str(e)}'}), 500
