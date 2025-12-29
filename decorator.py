# Chứa decorator tuỳ chỉnh dùng trong project (ví dụ: kiểm tra quyền, xác thực, caching hoặc logging cho các view/func...)
# decorator.py
from functools import wraps
from flask import request, jsonify, session
import jwt
from werkzeug.security import check_password_hash
import dao


def login_required(f):
    """Decorator yêu cầu đăng nhập"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Kiểm tra header Authorization hoặc session
        auth_header = request.headers.get('Authorization')
        if not auth_header and not session.get('user_id'):
            return jsonify({'success': False, 'message': 'Chưa đăng nhập'}), 401
        return f(*args, **kwargs)

    return decorated_function


def role_required(*allowed_roles):
    """Decorator kiểm tra quyền truy cập theo role"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Lấy thông tin user từ session hoặc token
            user_role = session.get('user_role')

            # Có thể lấy từ request args cho đơn giản
            username = request.args.get('adminUsername') or request.json.get('adminUsername') if request.json else None

            if username:
                account = dao.get_account_by_username(username)
                if account:
                    user_role = account.role

            if not user_role or user_role not in allowed_roles:
                return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(f):
    """Decorator chỉ cho phép Admin"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        username = request.args.get('adminUsername') or (request.json.get('adminUsername') if request.json else None)

        if not username:
            return jsonify({'success': False, 'message': 'Thiếu thông tin admin'}), 400

        account = dao.get_account_by_username(username)
        if not account or account.role != 'Admin':
            return jsonify({'success': False, 'message': 'Không có quyền admin'}), 403

        return f(*args, **kwargs)

    return decorated_function


def validate_json(required_fields=None):
    """Decorator validate dữ liệu JSON đầu vào"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({'success': False, 'message': 'Dữ liệu phải là JSON'}), 400

            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Dữ liệu trống'}), 400

            if required_fields:
                missing_fields = [field for field in required_fields if field not in data or not data[field]]
                if missing_fields:
                    return jsonify({
                        'success': False,
                        'message': f'Thiếu trường bắt buộc: {", ".join(missing_fields)}'
                    }), 400

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def handle_errors(f):
    """Decorator xử lý lỗi chung"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return jsonify({'success': False, 'message': f'Dữ liệu không hợp lệ: {str(e)}'}), 400
        except Exception as e:
            return jsonify({'success': False, 'message': f'Có lỗi xảy ra: {str(e)}'}), 500

    return decorated_function


def rate_limit(max_requests=60, per_minutes=1):
    """Decorator giới hạn số request (đơn giản)"""
    request_counts = {}

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            import time
            client_ip = request.remote_addr
            current_time = time.time()

            # Reset counter sau khoảng thời gian
            if client_ip in request_counts:
                if current_time - request_counts[client_ip]['start_time'] > per_minutes * 60:
                    request_counts[client_ip] = {'count': 1, 'start_time': current_time}
                else:
                    request_counts[client_ip]['count'] += 1
            else:
                request_counts[client_ip] = {'count': 1, 'start_time': current_time}

            if request_counts[client_ip]['count'] > max_requests:
                return jsonify({'success': False, 'message': 'Quá nhiều requests'}), 429

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def log_activity(action_type="unknown"):
    """Decorator ghi log hoạt động"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            import datetime

            # Ghi log đơn giản
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ip = request.remote_addr

            print(f"[{timestamp}] {action_type} - IP: {ip} - Endpoint: {request.endpoint}")

            result = f(*args, **kwargs)
            return result

        return decorated_function

    return decorator


def cors_enabled(f):
    """Decorator thêm CORS headers"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)

        # Nếu response là tuple (data, status_code)
        if isinstance(response, tuple):
            data, status_code = response
            from flask import make_response
            resp = make_response(data, status_code)
        else:
            resp = response

        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        resp.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'

        return resp

    return decorated_function