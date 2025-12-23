# app.py
from flask import request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re
import secrets

from __init__ import create_app, db
from models import Service, Customer, Employee, Booking, Account, Settings
import dao
from dao import *
from decorator import admin_required, validate_json, handle_errors, cors_enabled, rate_limit
from admin import init_admin

# Tạo Flask app
app = create_app()

# Khởi tạo Flask-Admin
admin = init_admin(app)


# Cấu hình CORS
@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response


# Handle OPTIONS requests cho CORS preflight
@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_cors(path):
    from flask import make_response
    response = make_response()
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response


# AUTHENTICATION APIs

@app.route('/api/auth/register', methods=['POST'])
@validate_json(['username', 'password', 'name', 'phone'])
@handle_errors
@rate_limit(max_requests=10, per_minutes=1)
def register():
    """Đăng ký tài khoản mới"""
    data = request.get_json()

    # Validate phone: chỉ cho phép số, 9–11 chữ số
    phone = data['phone']
    if not re.fullmatch(r'\d{9,11}', phone):
        return jsonify({
            'success': False,
            'message': 'Số điện thoại không hợp lệ (chỉ gồm 9–11 chữ số)'
        }), 400

    # Kiểm tra username đã tồn tại
    if dao.get_account_by_username(data['username']):
        return jsonify({'success': False, 'message': 'Username đã tồn tại'}), 400

    # Kiểm tra độ dài password (tối thiểu 6 ký tự)
    if len(data['password']) < 6:
        return jsonify({'success': False, 'message': 'Password phải có ít nhất 6 ký tự'}), 400

    # Tạo Customer mới
    customer_id = dao.generate_customer_id()
    customer_data = {
        'customerId': customer_id,
        'loyaltyPoints': 0,
        'membershipLevel': 'Basic'
    }
    customer = dao.create_customer(customer_data)

    # Hash password và tạo Account mới
    password_hash = generate_password_hash(data['password'])
    account_data = {
        'accountId': dao.generate_account_id(),
        'username': data['username'],
        'passwordHash': password_hash,
        'role': 'Customer',
        'fullName': data['name'],
        'phone': data['phone'],
        'email': data.get('email', '')
    }
    account = dao.create_account(account_data, customer_id)

    return jsonify({
        'success': True,
        'message': 'Đăng ký thành công',
        'data': dao.get_account_info_by_role(account)
    }), 201


@app.route('/api/auth/login', methods=['POST'])
@validate_json(['username', 'password'])
@handle_errors
@rate_limit(max_requests=20, per_minutes=1)
def login():
    """Đăng nhập"""
    data = request.get_json()

    # Tìm tài khoản theo username
    account = dao.get_account_by_username(data['username'])

    # Kiểm tra tài khoản tồn tại
    if not account:
        return jsonify({'success': False, 'message': 'Username hoặc password không đúng'}), 401

    # Kiểm tra password
    if not check_password_hash(account.passwordHash, data['password']):
        return jsonify({'success': False, 'message': 'Username hoặc password không đúng'}), 401

    # Lấy thông tin chi tiết theo role từ account table
    user_info = dao.get_account_info_by_role(account)

    return jsonify({
        'success': True,
        'message': 'Đăng nhập thành công',
        'data': user_info
    }), 200


@app.route('/api/auth/change-password', methods=['PUT'])
@validate_json(['username', 'oldPassword', 'newPassword'])
@handle_errors
def change_password():
    """Đổi mật khẩu"""
    data = request.get_json()

    # Kiểm tra độ dài password mới
    if len(data['newPassword']) < 6:
        return jsonify({'success': False, 'message': 'Password mới phải có ít nhất 6 ký tự'}), 400

    # Tìm tài khoản
    account = dao.get_account_by_username(data['username'])

    if not account:
        return jsonify({'success': False, 'message': 'Tài khoản không tồn tại'}), 404

    # Kiểm tra password cũ
    if not check_password_hash(account.passwordHash, data['oldPassword']):
        return jsonify({'success': False, 'message': 'Password cũ không đúng'}), 401

    # Cập nhật password mới
    new_password_hash = generate_password_hash(data['newPassword'])
    dao.update_account_password(data['username'], new_password_hash)

    return jsonify({
        'success': True,
        'message': 'Đổi mật khẩu thành công'
    }), 200


@app.route('/api/auth/profile', methods=['GET'])
@handle_errors
def get_profile():
    """Lấy thông tin profile từ account table"""
    username = request.args.get('username')

    if not username:
        return jsonify({'success': False, 'message': 'Thiếu username'}), 400

    account = dao.get_account_by_username(username)

    if not account:
        return jsonify({'success': False, 'message': 'Tài khoản không tồn tại'}), 404

    # Lấy thông tin chi tiết từ account
    profile = dao.get_account_info_by_role(account)

    return jsonify({'success': True, 'data': profile}), 200


@app.route('/api/auth/change-role', methods=['PUT'])
@admin_required
@validate_json(['username', 'newRole'])
@handle_errors
def change_role():
    """Đổi role tài khoản - chỉ admin"""
    data = request.get_json()

    # Validate role hợp lệ
    valid_roles = ['Customer', 'Employee', 'Admin', 'Cashier']
    if data['newRole'] not in valid_roles:
        return jsonify({'success': False, 'message': 'Role không hợp lệ'}), 400

    # Tìm tài khoản cần đổi role
    target_account = dao.get_account_by_username(data['username'])
    if not target_account:
        return jsonify({'success': False, 'message': 'Tài khoản không tồn tại'}), 404

    old_role = target_account.role
    new_role = data['newRole']

    # Nếu role không thay đổi
    if old_role == new_role:
        return jsonify({'success': True, 'message': 'Role không thay đổi'}), 200

    # Backup thông tin hiện tại từ account
    backup_name = target_account.fullName or data.get('name', target_account.username)
    backup_phone = target_account.phone or data.get('phone', '')
    backup_email = target_account.email or data.get('email', '')

    # Soft delete records cũ
    if target_account.customer:
        target_account.customer.active = False
    if target_account.employee:
        target_account.employee.active = False

    # Xử lý role mới
    target_account.customerId = None
    target_account.employeeId = None

    if new_role == 'Customer':
        # Tạo Customer record mới
        customer_data = {
            'customerId': dao.generate_customer_id(),
            'loyaltyPoints': 0,
            'membershipLevel': 'Basic'
        }
        customer = dao.create_customer(customer_data)
        target_account.customerId = customer.customerId

    elif new_role in ['Employee', 'Cashier']:
        # Tạo Employee record mới
        employee_data = {
            'employeeId': dao.generate_employee_id(),
            'position': 'Thu ngân' if new_role == 'Cashier' else 'Kỹ thuật viên',
            'department': 'Thu ngân' if new_role == 'Cashier' else 'Dịch vụ'
        }
        employee = dao.create_employee(employee_data)
        target_account.employeeId = employee.employeeId

    # Cập nhật thông tin cơ bản trong account
    target_account.role = new_role
    target_account.fullName = backup_name
    target_account.phone = backup_phone
    target_account.email = backup_email

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Đổi role thành công từ {old_role} thành {new_role}',
        'data': {
            'username': target_account.username,
            'oldRole': old_role,
            'newRole': new_role
        }
    }), 200


@app.route('/api/auth/accounts', methods=['GET'])
@admin_required
@handle_errors
def get_all_accounts():
    """Lấy danh sách tất cả tài khoản - chỉ admin"""
    try:
        accounts = dao.get_all_accounts()
        data = []

        for acc in accounts:
            account_info = dao.get_account_info_by_role(acc)
            data.append(account_info)

        return jsonify({'success': True, 'data': data}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'Có lỗi xảy ra: {str(e)}'}), 500


# CUSTOMER APIs

@app.route('/api/customers', methods=['POST'])
@handle_errors
def create_customer():
    """Tạo khách hàng mới"""
    data = request.get_json()
    dao.create_customer(data)
    return jsonify({'success': True, 'message': "Tạo khách hàng thành công"}), 201


@app.route('/api/customers', methods=['GET'])
@handle_errors
def get_customers():
    """Lấy danh sách khách hàng active"""
    customers = dao.get_all_customers()
    data = []
    for c in customers:
        customer_info = {
            'customerId': c.customerId,
            'loyaltyPoints': c.loyaltyPoints,
            'membershipLevel': c.membershipLevel
        }

        # Tìm account tương ứng với customer này
        account = Account.query.filter_by(customerId=c.customerId).first()
        if account:
            customer_info.update({
                'name': account.fullName or '',
                'phone': account.phone or '',
                'email': account.email or ''
            })
        else:
            customer_info.update({
                'name': 'N/A',
                'phone': '',
                'email': ''
            })

        data.append(customer_info)
    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/customers/<customerId>', methods=['GET'])
@handle_errors
def get_customer(customerId):
    """Lấy thông tin khách hàng theo ID"""
    customer = dao.get_customer_by_id(customerId)
    if not customer:
        return jsonify({'success': False, 'message': 'Không tìm thấy khách hàng'}), 404

    customer_info = {
        'customerId': customer.customerId,
        'loyaltyPoints': customer.loyaltyPoints,
        'membershipLevel': customer.membershipLevel
    }

    # Tìm account tương ứng với customer này
    account = Account.query.filter_by(customerId=customer.customerId).first()
    if account:
        customer_info.update({
            'name': account.fullName or '',
            'phone': account.phone or '',
            'email': account.email or ''
        })
    else:
        customer_info.update({
            'name': 'N/A',
            'phone': '',
            'email': ''
        })

    return jsonify({'success': True, 'data': customer_info}), 200


@app.route('/api/customers/<customerId>', methods=['PUT'])
@handle_errors
def update_customer(customerId):
    """Cập nhật thông tin khách hàng"""
    customer = dao.get_customer_by_id(customerId)
    if not customer:
        return jsonify({'success': False, 'message': 'Không tìm thấy khách hàng'}), 404

    data = request.get_json()
    dao.update_customer(customerId, data)

    return jsonify({'success': True, 'message': 'Cập nhật khách hàng thành công'}), 200


@app.route('/api/customers/<customerId>', methods=['DELETE'])
@handle_errors
def delete_customer_api(customerId):
    """Xóa khách hàng"""
    customer = dao.get_customer_by_id(customerId)
    if not customer:
        return jsonify({'success': False, 'message': 'Không tìm thấy khách hàng'}), 404

    if customer.bookings:
        return jsonify({'success': False, 'message': 'Không thể xóa khách hàng vì còn lịch'}), 400

    dao.delete_customer(customerId)
    return jsonify({'success': True, 'message': 'Xóa khách hàng thành công'}), 200


# EMPLOYEE APIs

@app.route('/api/employees', methods=['POST'])
@handle_errors
def create_employee():
    """Tạo nhân viên mới"""
    data = request.get_json()
    dao.create_employee(data)
    return jsonify({'success': True, 'message': "Tạo nhân viên thành công"}), 201


@app.route('/api/employees', methods=['GET'])
@handle_errors
def get_employees():
    """Lấy danh sách nhân viên active (không bao gồm cashier)"""
    employees = dao.get_all_employees()
    data = []
    for e in employees:
        employee_info = {
            'employeeId': e.employeeId,
            'position': e.position,
            'department': e.department
        }

        # Tìm account tương ứng với employee này
        account = Account.query.filter_by(employeeId=e.employeeId).first()
        if account:
            employee_info.update({
                'name': account.fullName or '',
                'phone': account.phone or '',
                'email': account.email or ''
            })
        else:
            employee_info.update({
                'name': 'N/A',
                'phone': '',
                'email': ''
            })

        data.append(employee_info)
    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/employees/<employeeId>', methods=['GET'])
@handle_errors
def get_employee(employeeId):
    """Lấy thông tin nhân viên theo ID"""
    employee = dao.get_employee_by_id(employeeId)
    if not employee:
        return jsonify({'success': False, 'message': 'Không tìm thấy nhân viên'}), 404

    employee_info = {
        'employeeId': employee.employeeId,
        'position': employee.position,
        'department': employee.department
    }

    # Tìm account tương ứng với employee này
    account = Account.query.filter_by(employeeId=employee.employeeId).first()
    if account:
        employee_info.update({
            'name': account.fullName or '',
            'phone': account.phone or '',
            'email': account.email or ''
        })
    else:
        employee_info.update({
            'name': 'N/A',
            'phone': '',
            'email': ''
        })

    return jsonify({'success': True, 'data': employee_info}), 200


@app.route('/api/employees/<employeeId>', methods=['PUT'])
@handle_errors
def update_employee(employeeId):
    """Cập nhật thông tin nhân viên"""
    employee = dao.get_employee_by_id(employeeId)
    if not employee:
        return jsonify({'success': False, 'message': 'Không tìm thấy nhân viên'}), 404

    data = request.get_json()
    dao.update_employee(employeeId, data)

    return jsonify({'success': True, 'message': 'Cập nhật nhân viên thành công'}), 200


@app.route('/api/employees/<employeeId>', methods=['DELETE'])
@handle_errors
def delete_employee_api(employeeId):
    """Xóa nhân viên"""
    employee = dao.get_employee_by_id(employeeId)
    if not employee:
        return jsonify({'success': False, 'message': 'Không tìm thấy nhân viên'}), 404

    if employee.bookings:
        return jsonify({'success': False, 'message': 'Không thể xóa nhân viên vì còn lịch'}), 400

    dao.delete_employee(employeeId)
    return jsonify({'success': True, 'message': 'Xóa nhân viên thành công'}), 200


# SERVICE APIs

@app.route('/api/services/generate-id', methods=['GET'])
@cors_enabled
def generate_service_id():
    """Tạo mã dịch vụ tự động"""
    service_id = 'SV' + secrets.token_hex(4).upper()
    return jsonify({'success': True, 'servicesId': service_id}), 200


@app.route('/api/services/submit', methods=['POST'])
@validate_json(['name', 'durration', 'price'])
@handle_errors
@cors_enabled
def create_service():
    """Tạo dịch vụ mới"""
    data = request.get_json()

    # Tạo mã dịch vụ tự động nếu không có
    if not data.get('servicesId'):
        data['servicesId'] = 'SV' + secrets.token_hex(4).upper()

    if dao.get_service_by_id(data['servicesId']):
        return jsonify({'success': False, 'message': 'Mã dịch vụ đã tồn tại'}), 400

    d = int(data['durration'])
    if d < 15 or d > 120:
        return jsonify({'success': False, 'message': 'Thời lượng dịch vụ phải từ 15-120 phút'}), 400

    dao.create_service(data)
    return jsonify({'success': True, 'message': "Tạo dịch vụ thành công"}), 201


@app.route('/api/services', methods=['GET'])
@cors_enabled
@handle_errors
def get_services():
    """Lấy danh sách dịch vụ"""
    services = dao.get_all_services()
    data = [{
        'servicesId': s.servicesId,
        'name': s.name,
        'durration': s.durration,
        'price': float(s.price) if s.price is not None else 0.0,
        'note': s.note
    } for s in services]
    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/services/<servicesId>', methods=['GET'])
@handle_errors
def get_service(servicesId):
    """Lấy thông tin dịch vụ theo ID"""
    service = dao.get_service_by_id(servicesId)
    if not service:
        return jsonify({'success': False, 'message': 'Không tìm thấy dịch vụ'}), 404
    return jsonify({'success': True, 'data': {
        'servicesId': service.servicesId,
        'name': service.name,
        'durration': service.durration,
        'price': float(service.price) if service.price is not None else 0.0,
        'note': service.note
    }}), 200


@app.route('/api/services/<servicesId>', methods=['PUT'])
@handle_errors
def update_service(servicesId):
    """Cập nhật thông tin dịch vụ"""
    service = dao.get_service_by_id(servicesId)
    if not service:
        return jsonify({'success': False, 'message': 'Không tìm thấy dịch vụ'}), 404

    data = request.get_json()
    if "durration" in data:
        d = int(data["durration"])
        if d < 15 or d > 120:
            return jsonify({'success': False, 'message': 'Thời lượng dịch vụ phải từ 15-120 phút'}), 400

    dao.update_service(servicesId, data)
    return jsonify({'success': True, 'message': 'Cập nhật dịch vụ thành công'}), 200


@app.route('/api/services/<servicesId>', methods=['DELETE'])
@handle_errors
def delete_service(servicesId):
    """Xóa dịch vụ"""
    service = dao.get_service_by_id(servicesId)
    if not service:
        return jsonify({'success': False, 'message': 'Không tìm thấy dịch vụ'}), 404

    if service.bookings:
        return jsonify({'success': False, 'message': 'Không thể xóa dịch vụ vì có lịch sử booking'}), 400

    dao.delete_service(servicesId)
    return jsonify({'success': True, 'message': 'Xóa dịch vụ thành công'}), 200


# BOOKING APIs

@app.route('/api/bookings', methods=['POST'])
@handle_errors
def create_booking():
    """Tạo booking mới"""
    data = request.get_json()

    customer = dao.get_customer_by_id(data['customerId'])
    service = dao.get_service_by_id(data['servicesId'])
    employee = dao.get_employee_by_id(data['employeeId'])

    if not customer or not service or not employee:
        return jsonify({'success': False, 'message': 'Sai thông tin customer/service/employee'}), 404

    booking_time = datetime.fromisoformat(data['time'])

    # Kiểm tra lịch trùng cho nhân viên
    if dao.check_employee_booking_conflicts(employee.employeeId, booking_time, service.durration):
        return jsonify({'success': False, 'message': "Nhân viên đã có lịch trùng"}), 400

    # Kiểm tra giới hạn booking/ngày
    max_bookings = int(dao.get_setting_value('max_bookings_per_day', '5'))
    count = dao.count_employee_bookings_on_date(employee.employeeId, booking_time)

    if count >= max_bookings:
        return jsonify({'success': False, 'message': f"Nhân viên đã đạt {max_bookings} lịch trong ngày"}), 400

    # Kiểm tra khách hàng có lịch trùng
    if dao.check_customer_booking_conflicts(customer.customerId, booking_time, service.durration):
        return jsonify({'success': False, 'message': "Khách hàng đã có lịch trùng"}), 400

    # Tạo booking
    dao.create_booking(data)
    return jsonify({'success': True, 'message': "Tạo lịch thành công"}), 201


@app.route('/api/bookings', methods=['GET'])
@handle_errors
def get_bookings():
    """Lấy danh sách booking với thông tin từ account"""
    bookings = dao.get_all_bookings()
    data = []
    for b in bookings:
        # Tìm account cho customer và employee
        customer_account = Account.query.filter_by(customerId=b.customerId).first()
        employee_account = Account.query.filter_by(employeeId=b.employeeId).first()

        customer_name = customer_account.fullName if customer_account else 'N/A'
        employee_name = employee_account.fullName if employee_account else 'N/A'

        data.append({
            'bookingId': b.bookingId,
            'time': b.time.isoformat(),
            'status': b.status,
            'customer': {'customerId': b.customerId, 'name': customer_name},
            'service': {
                'servicesId': b.servicesId,
                'name': b.service.name,
                'price': float(b.service.price) if b.service.price is not None else 0.0,
                'durration': b.service.durration
            },
            'employee': {'employeeId': b.employeeId, 'name': employee_name}
        })
    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/bookings/<bookingId>', methods=['GET'])
@handle_errors
def get_booking(bookingId):
    """Lấy thông tin booking theo ID"""
    b = dao.get_booking_by_id(bookingId)
    if not b:
        return jsonify({'success': False, 'message': 'Không tìm thấy lịch'}), 404

    # Tìm account cho customer và employee
    customer_account = Account.query.filter_by(customerId=b.customerId).first()
    employee_account = Account.query.filter_by(employeeId=b.employeeId).first()

    customer_name = customer_account.fullName if customer_account else 'N/A'
    employee_name = employee_account.fullName if employee_account else 'N/A'

    return jsonify({'success': True, 'data': {
        'bookingId': b.bookingId,
        'time': b.time.isoformat(),
        'status': b.status,
        'customer': {'customerId': b.customerId, 'name': customer_name},
        'service': {
            'servicesId': b.servicesId,
            'name': b.service.name,
            'price': float(b.service.price) if b.service.price is not None else 0.0,
            'durration': b.service.durration
        },
        'employee': {'employeeId': b.employeeId, 'name': employee_name}
    }}), 200


@app.route('/api/bookings/<bookingId>', methods=['PUT'])
@handle_errors
def update_booking(bookingId):
    """Cập nhật booking"""
    booking = dao.get_booking_by_id(bookingId)
    if not booking:
        return jsonify({'success': False, 'message': 'Không tìm thấy lịch'}), 404

    data = request.get_json()
    dao.update_booking(bookingId, data)
    return jsonify({'success': True, 'message': "Cập nhật lịch thành công"}), 200


@app.route('/api/bookings/<bookingId>', methods=['DELETE'])
@handle_errors
def delete_booking(bookingId):
    """Xóa booking"""
    booking = dao.get_booking_by_id(bookingId)
    if not booking:
        return jsonify({'success': False, 'message': 'Không tìm thấy lịch'}), 404

    dao.delete_booking(bookingId)
    return jsonify({'success': True, 'message': "Xóa lịch thành công"}), 200


# INVOICE APIs

@app.route('/api/invoices/preview', methods=['POST'])
@handle_errors
def preview_invoice():
    """Tính toán preview hóa đơn trước khi xuất"""
    data = request.get_json()

    booking = dao.get_booking_by_id(data['bookingId'])
    if not booking:
        return jsonify({'success': False, 'message': 'Không tìm thấy booking'}), 404

    # Lấy service từ booking
    service = booking.service
    if not service:
        return jsonify({'success': False, 'message': 'Không tìm thấy dịch vụ'}), 404

    # Xử lý price
    price = service.price
    if price is None:
        price = 0

    try:
        total = float(price)
    except (ValueError, TypeError):
        total = 0.0

    # Lấy cấu hình từ settings
    vat_rate = float(dao.get_setting_value('vat_rate', '10'))
    max_discount_rate = float(dao.get_setting_value('max_discount', '20'))

    discount_percent = float(data.get('discount', 0))
    if discount_percent < 0 or discount_percent > max_discount_rate:
        return jsonify({'success': False, 'message': f'Giảm giá tối đa {max_discount_rate}%'}), 400

    # Tính toán
    discount = total * discount_percent / 100
    subtotal = total - discount
    vat = subtotal * vat_rate / 100
    finalTotal = subtotal + vat

    # Lấy tên customer từ account
    customer_account = Account.query.filter_by(customerId=booking.customerId).first()
    customer_name = customer_account.fullName if customer_account else 'N/A'

    return jsonify({
        'success': True,
        'data': {
            'serviceName': service.name,
            'customerName': customer_name,
            'total': total,
            'discount': discount,
            'discountPercent': discount_percent,
            'vat': vat,
            'vatPercent': vat_rate,
            'finalTotal': finalTotal
        }
    }), 200


@app.route('/api/invoices', methods=['POST'])
@handle_errors
def create_invoice():
    """Tạo hóa đơn thanh toán cho booking"""
    data = request.get_json()

    booking = dao.get_booking_by_id(data['bookingId'])
    if not booking:
        return jsonify({'success': False, 'message': 'Không tìm thấy booking'}), 404

    if booking.invoiceId:
        return jsonify({'success': False, 'message': 'Booking đã có hóa đơn'}), 400

    if dao.get_invoice_by_id(data['invoiceId']):
        return jsonify({'success': False, 'message': 'Mã hóa đơn đã tồn tại'}), 400

    # Lấy service từ booking.service relationship
    service = booking.service
    if not service:
        return jsonify({'success': False, 'message': 'Không tìm thấy dịch vụ'}), 404

    # Kiểm tra và xử lý price
    price = service.price
    if price is None:
        price = 0

    # Convert to float safely
    try:
        total = float(price)
    except (ValueError, TypeError):
        total = 0.0

    # Nếu price vẫn bằng 0, báo lỗi
    if total <= 0:
        return jsonify({'success': False,
                        'message': f'Giá dịch vụ "{service.name}" chưa được thiết lập. Vui lòng cập nhật giá dịch vụ trong trang quản lý.'}), 400

    # Lấy cấu hình từ settings
    vat_rate = float(dao.get_setting_value('vat_rate', '10'))
    max_discount_rate = float(dao.get_setting_value('max_discount', '20'))

    discount_percent = float(data.get('discount', 0))
    if discount_percent < 0 or discount_percent > max_discount_rate:
        return jsonify({'success': False, 'message': f'Giảm giá tối đa {max_discount_rate}%'}), 400

    # Tính toán
    discount = total * discount_percent / 100
    subtotal = total - discount
    vat = subtotal * vat_rate / 100
    finalTotal = subtotal + vat

    invoice_data = {
        'invoiceId': data['invoiceId'],
        'customerId': booking.customerId,
        'total': total,
        'vat': vat,
        'discount': discount,
        'finalTotal': finalTotal
    }

    invoice = dao.create_invoice(invoice_data, data['bookingId'])

    # Lấy tên customer từ account
    customer_account = Account.query.filter_by(customerId=booking.customerId).first()
    customer_name = customer_account.fullName if customer_account else 'N/A'

    return jsonify({
        'success': True,
        'message': 'Tạo hóa đơn thành công',
        'data': {
            'invoiceId': invoice.invoiceId,
            'customerId': invoice.customerId,
            'customerName': customer_name,
            'serviceName': service.name,
            'total': total,
            'discount': discount,
            'vat': vat,
            'finalTotal': finalTotal
        }
    }), 201


@app.route('/api/invoices', methods=['GET'])
@handle_errors
def get_invoices():
    """Lấy danh sách hóa đơn"""
    invoices = dao.get_all_invoices()
    data = []

    for inv in invoices:
        booking = inv.booking

        # Lấy customer name từ account
        customer_account = Account.query.filter_by(customerId=inv.customerId).first()
        customer_name = customer_account.fullName if customer_account else 'N/A'

        data.append({
            'invoiceId': inv.invoiceId,
            'customerId': inv.customerId,
            'customerName': customer_name,
            'serviceName': booking.service.name if booking else '',
            'total': inv.total,
            'discount': inv.discount,
            'vat': inv.vat,
            'finalTotal': inv.finalTotal
        })

    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/invoices/<invoiceId>', methods=['GET'])
@handle_errors
def get_invoice(invoiceId):
    """Lấy thông tin hóa đơn theo ID"""
    invoice = dao.get_invoice_by_id(invoiceId)
    if not invoice:
        return jsonify({'success': False, 'message': 'Không tìm thấy hóa đơn'}), 404

    booking = invoice.booking

    # Lấy thông tin customer và employee từ account
    customer_account = Account.query.filter_by(customerId=invoice.customerId).first()
    employee_account = Account.query.filter_by(employeeId=booking.employeeId).first() if booking else None

    customer_name = customer_account.fullName if customer_account else 'N/A'
    customer_phone = customer_account.phone if customer_account else 'N/A'
    employee_name = employee_account.fullName if employee_account else 'N/A'

    return jsonify({
        'success': True,
        'data': {
            'invoiceId': invoice.invoiceId,
            'customerId': invoice.customerId,
            'customerName': customer_name,
            'customerPhone': customer_phone,
            'serviceName': booking.service.name if booking else '',
            'servicePrice': booking.service.price if booking else 0,
            'employeeName': employee_name,
            'bookingTime': booking.time.isoformat() if booking else '',
            'total': invoice.total,
            'discount': invoice.discount,
            'vat': invoice.vat,
            'finalTotal': invoice.finalTotal
        }
    }), 200


@app.route('/api/invoices/<invoiceId>', methods=['PUT'])
@handle_errors
def update_invoice(invoiceId):
    """Cập nhật hóa đơn"""
    invoice = dao.get_invoice_by_id(invoiceId)
    if not invoice:
        return jsonify({'success': False, 'message': 'Không tìm thấy hóa đơn'}), 404

    data = request.get_json()

    booking = invoice.booking
    if not booking:
        return jsonify({'success': False, 'message': 'Không tìm thấy booking liên quan'}), 404

    service = dao.get_service_by_id(booking.servicesId)
    if not service:
        return jsonify({'success': False, 'message': 'Không tìm thấy dịch vụ'}), 404

    total = float(service.price)

    vat_rate = float(dao.get_setting_value('vat_rate', '10'))
    max_discount_rate = float(dao.get_setting_value('max_discount', '20'))

    discount_percent = float(data.get('discount', 0))
    if discount_percent < 0 or discount_percent > max_discount_rate:
        return jsonify({'success': False, 'message': f'Giảm giá tối đa {max_discount_rate}%'}), 400

    discount = total * discount_percent / 100
    subtotal = total - discount
    vat = subtotal * vat_rate / 100
    finalTotal = subtotal + vat

    invoice_data = {
        'total': total,
        'discount': discount,
        'vat': vat,
        'finalTotal': finalTotal
    }

    dao.update_invoice(invoiceId, invoice_data)

    return jsonify({
        'success': True,
        'message': 'Cập nhật hóa đơn thành công',
        'data': {
            'invoiceId': invoice.invoiceId,
            'total': total,
            'discount': discount,
            'vat': vat,
            'finalTotal': finalTotal
        }
    }), 200


@app.route('/api/invoices/<invoiceId>', methods=['DELETE'])
@handle_errors
def delete_invoice(invoiceId):
    """Xóa hóa đơn"""
    invoice = dao.get_invoice_by_id(invoiceId)
    if not invoice:
        return jsonify({'success': False, 'message': 'Không tìm thấy hóa đơn'}), 404

    dao.delete_invoice(invoiceId)
    return jsonify({'success': True, 'message': 'Xóa hóa đơn thành công'}), 200


# SETTINGS APIs

@app.route('/api/settings', methods=['GET'])
@handle_errors
def get_all_settings():
    """Lấy tất cả cài đặt"""
    settings = dao.get_all_settings()
    data = [{
        'settingId': s.settingId,
        'value': s.value,
        'description': s.description
    } for s in settings]

    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/settings/<settingId>', methods=['GET'])
@handle_errors
def get_setting(settingId):
    """Lấy cài đặt theo ID"""
    setting = dao.get_setting_by_id(settingId)
    if not setting:
        return jsonify({'success': False, 'message': 'Không tìm thấy cài đặt'}), 404

    return jsonify({
        'success': True,
        'data': {
            'settingId': setting.settingId,
            'value': setting.value,
            'description': setting.description
        }
    }), 200


@app.route('/api/settings/<settingId>', methods=['PUT'])
@handle_errors
def update_setting(settingId):
    """Cập nhật cài đặt"""
    setting = dao.get_setting_by_id(settingId)
    if not setting:
        return jsonify({'success': False, 'message': 'Không tìm thấy cài đặt'}), 404

    data = request.get_json()
    new_value = data.get('value')

    if not new_value:
        return jsonify({'success': False, 'message': 'Thiếu giá trị cài đặt'}), 400

    try:
        if settingId == 'vat_rate':
            val = float(new_value)
            if val < 0 or val > 100:
                return jsonify({'success': False, 'message': 'VAT phải từ 0-100%'}), 400

        elif settingId == 'max_bookings_per_day':
            val = int(new_value)
            if val < 1:
                return jsonify({'success': False, 'message': 'Số booking/ngày phải >= 1'}), 400

        elif settingId == 'max_discount':
            val = float(new_value)
            if val < 0 or val > 100:
                return jsonify({'success': False, 'message': 'Giảm giá phải từ 0-100%'}), 400

    except ValueError:
        return jsonify({'success': False, 'message': 'Giá trị không hợp lệ'}), 400

    dao.update_setting(settingId, new_value)

    return jsonify({
        'success': True,
        'message': 'Cập nhật cài đặt thành công',
        'data': {
            'settingId': setting.settingId,
            'value': new_value,
            'description': setting.description
        }
    }), 200


@app.route('/api/settings/service-price/<servicesId>', methods=['PUT'])
@handle_errors
def update_service_price_via_settings(servicesId):
    """Cập nhật giá dịch vụ qua settings"""
    service = dao.get_service_by_id(servicesId)
    if not service:
        return jsonify({'success': False, 'message': 'Không tìm thấy dịch vụ'}), 404

    data = request.get_json()
    new_price = data.get('price')

    if not new_price:
        return jsonify({'success': False, 'message': 'Thiếu giá mới'}), 400

    try:
        price = float(new_price)
        if price < 0:
            return jsonify({'success': False, 'message': 'Giá phải >= 0'}), 400
    except ValueError:
        return jsonify({'success': False, 'message': 'Giá không hợp lệ'}), 400

    service.price = price
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Cập nhật giá dịch vụ thành công',
        'data': {
            'servicesId': service.servicesId,
            'name': service.name,
            'price': service.price
        }
    }), 200


# REPORTS APIs

@app.route('/api/reports/daily-revenue', methods=['GET'])
@handle_errors
def get_daily_revenue_report():
    """Báo cáo doanh thu theo ngày trong tháng"""
    month = request.args.get('month')
    year = request.args.get('year')

    if not month or not year:
        return jsonify({'success': False, 'message': 'Thiếu tham số month hoặc year'}), 400

    try:
        month = int(month)
        year = int(year)
    except:
        return jsonify({'success': False, 'message': 'Tham số month/year không hợp lệ'}), 400

    # Lấy tất cả booking có hóa đơn trong tháng
    from calendar import monthrange
    _, days_in_month = monthrange(year, month)

    daily_revenue = {}
    total_revenue = 0

    # Khởi tạo doanh thu 0 cho tất cả ngày trong tháng
    for day in range(1, days_in_month + 1):
        daily_revenue[day] = 0

    # Lấy tất cả invoice trong tháng
    invoices = dao.get_all_invoices()
    for invoice in invoices:
        if invoice.booking:
            booking_date = invoice.booking.time.date()
            if booking_date.month == month and booking_date.year == year:
                day = booking_date.day
                daily_revenue[day] += invoice.finalTotal
                total_revenue += invoice.finalTotal

    # Chuyển đổi thành list để dễ hiển thị
    daily_list = []
    for day in range(1, days_in_month + 1):
        daily_list.append({
            'day': day,
            'revenue': daily_revenue[day]
        })

    return jsonify({
        'success': True,
        'data': {
            'month': month,
            'year': year,
            'daily_revenue': daily_list,
            'total_revenue': total_revenue
        }
    }), 200


@app.route('/api/reports/service-frequency', methods=['GET'])
@handle_errors
def get_service_frequency_report():
    """Báo cáo tần suất sử dụng dịch vụ theo tháng"""
    month = request.args.get('month')
    year = request.args.get('year')

    if not month or not year:
        return jsonify({'success': False, 'message': 'Thiếu tham số month hoặc year'}), 400

    try:
        month = int(month)
        year = int(year)
    except:
        return jsonify({'success': False, 'message': 'Tham số month/year không hợp lệ'}), 400

    # Lấy tất cả invoice trong tháng để đếm tần suất
    service_frequency = {}
    total_count = 0

    invoices = dao.get_all_invoices()
    for invoice in invoices:
        if invoice.booking:
            booking_date = invoice.booking.time.date()
            if booking_date.month == month and booking_date.year == year:
                service_id = invoice.booking.servicesId
                service_name = invoice.booking.service.name

                if service_id not in service_frequency:
                    service_frequency[service_id] = {
                        'servicesId': service_id,
                        'name': service_name,
                        'count': 0,
                        'revenue': 0
                    }

                service_frequency[service_id]['count'] += 1
                service_frequency[service_id]['revenue'] += invoice.finalTotal
                total_count += 1

    result = sorted(service_frequency.values(), key=lambda x: x['count'], reverse=True)

    return jsonify({
        'success': True,
        'data': {
            'month': month,
            'year': year,
            'services': result,
            'total_count': total_count
        }
    }), 200


# SERVICE FORMS APIs

@app.route('/api/service-forms', methods=['POST'])
@validate_json(['bookingId', 'employeeId', 'serviceName', 'serviceDuration', 'servicePrice'])
@handle_errors
@cors_enabled
def create_service_form():
    """Tạo phiếu dịch vụ mới"""
    data = request.get_json()

    # Kiểm tra booking tồn tại
    booking = dao.get_booking_by_id(data['bookingId'])
    if not booking:
        return jsonify({'success': False, 'message': 'Booking không tồn tại'}), 404

    # Kiểm tra employee tồn tại
    employee = dao.get_employee_by_id(data['employeeId'])
    if not employee:
        return jsonify({'success': False, 'message': 'Nhân viên không tồn tại'}), 404

    # Kiểm tra đã có phiếu dịch vụ chưa
    if dao.check_service_form_exists(data['bookingId']):
        return jsonify({'success': False, 'message': 'Booking này đã có phiếu dịch vụ'}), 400

    # Validate dữ liệu
    duration = int(data['serviceDuration'])
    if duration < 15 or duration > 120:
        return jsonify({'success': False, 'message': 'Thời lượng dịch vụ phải từ 15-120 phút'}), 400

    price = float(data['servicePrice'])
    if price <= 0:
        return jsonify({'success': False, 'message': 'Giá dịch vụ phải lớn hơn 0'}), 400

    # Tạo mã phiếu dịch vụ
    form_data = data.copy()
    form_data['formId'] = 'SF' + secrets.token_hex(4).upper()

    service_form = dao.create_service_form(form_data)

    return jsonify({
        'success': True,
        'message': 'Tạo phiếu dịch vụ thành công',
        'data': {
            'formId': service_form.formId,
            'bookingId': service_form.bookingId,
            'employeeId': service_form.employeeId,
            'serviceName': service_form.serviceName,
            'serviceDuration': service_form.serviceDuration,
            'servicePrice': service_form.servicePrice,
            'serviceNote': service_form.serviceNote,
            'createdAt': service_form.createdAt.isoformat()
        }
    }), 201


@app.route('/api/service-forms', methods=['GET'])
@handle_errors
def get_service_forms():
    """Lấy danh sách phiếu dịch vụ"""
    service_forms = dao.get_all_service_forms()
    data = []

    for sf in service_forms:
        # Tìm account cho employee và customer
        employee_account = Account.query.filter_by(employeeId=sf.employeeId).first()
        customer_account = None
        if sf.booking and sf.booking.customerId:
            customer_account = Account.query.filter_by(customerId=sf.booking.customerId).first()

        employee_name = employee_account.fullName if employee_account else 'N/A'
        customer_name = customer_account.fullName if customer_account else 'N/A'

        data.append({
            'formId': sf.formId,
            'bookingId': sf.bookingId,
            'employeeId': sf.employeeId,
            'employeeName': employee_name,
            'customerName': customer_name,
            'serviceName': sf.serviceName,
            'serviceDuration': sf.serviceDuration,
            'servicePrice': sf.servicePrice,
            'serviceNote': sf.serviceNote,
            'createdAt': sf.createdAt.isoformat()
        })

    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/service-forms/<formId>', methods=['GET'])
@handle_errors
def get_service_form(formId):
    """Lấy thông tin phiếu dịch vụ theo ID"""
    service_form = dao.get_service_form_by_id(formId)
    if not service_form:
        return jsonify({'success': False, 'message': 'Không tìm thấy phiếu dịch vụ'}), 404

    # Tìm account cho employee và customer
    employee_account = Account.query.filter_by(employeeId=service_form.employeeId).first()
    customer_account = None
    if service_form.booking and service_form.booking.customerId:
        customer_account = Account.query.filter_by(customerId=service_form.booking.customerId).first()

    employee_name = employee_account.fullName if employee_account else 'N/A'
    customer_name = customer_account.fullName if customer_account else 'N/A'

    return jsonify({
        'success': True,
        'data': {
            'formId': service_form.formId,
            'bookingId': service_form.bookingId,
            'employeeId': service_form.employeeId,
            'employeeName': employee_name,
            'customerName': customer_name,
            'serviceName': service_form.serviceName,
            'serviceDuration': service_form.serviceDuration,
            'servicePrice': service_form.servicePrice,
            'serviceNote': service_form.serviceNote,
            'createdAt': service_form.createdAt.isoformat()
        }
    }), 200


@app.route('/api/service-forms/employee/<employeeId>', methods=['GET'])
@handle_errors
def get_service_forms_by_employee(employeeId):
    """Lấy danh sách phiếu dịch vụ của nhân viên"""
    employee = dao.get_employee_by_id(employeeId)
    if not employee:
        return jsonify({'success': False, 'message': 'Nhân viên không tồn tại'}), 404

    service_forms = dao.get_service_forms_by_employee(employeeId)
    data = []

    for sf in service_forms:
        customer_account = None
        if sf.booking and sf.booking.customerId:
            customer_account = Account.query.filter_by(customerId=sf.booking.customerId).first()

        customer_name = customer_account.fullName if customer_account else 'N/A'

        data.append({
            'formId': sf.formId,
            'bookingId': sf.bookingId,
            'customerName': customer_name,
            'serviceName': sf.serviceName,
            'serviceDuration': sf.serviceDuration,
            'servicePrice': sf.servicePrice,
            'serviceNote': sf.serviceNote,
            'createdAt': sf.createdAt.isoformat()
        })

    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/service-forms/<formId>', methods=['PUT'])
@handle_errors
def update_service_form(formId):
    """Cập nhật phiếu dịch vụ"""
    service_form = dao.get_service_form_by_id(formId)
    if not service_form:
        return jsonify({'success': False, 'message': 'Không tìm thấy phiếu dịch vụ'}), 404

    data = request.get_json()

    # Validate nếu có dữ liệu
    if 'serviceDuration' in data:
        duration = int(data['serviceDuration'])
        if duration < 15 or duration > 120:
            return jsonify({'success': False, 'message': 'Thời lượng dịch vụ phải từ 15-120 phút'}), 400

    if 'servicePrice' in data:
        price = float(data['servicePrice'])
        if price <= 0:
            return jsonify({'success': False, 'message': 'Giá dịch vụ phải lớn hơn 0'}), 400

    dao.update_service_form(formId, data)

    return jsonify({'success': True, 'message': 'Cập nhật phiếu dịch vụ thành công'}), 200


@app.route('/api/service-forms/<formId>', methods=['DELETE'])
@handle_errors
def delete_service_form(formId):
    """Xóa phiếu dịch vụ"""
    service_form = dao.get_service_form_by_id(formId)
    if not service_form:
        return jsonify({'success': False, 'message': 'Không tìm thấy phiếu dịch vụ'}), 404

    dao.delete_service_form(formId)
    return jsonify({'success': True, 'message': 'Xóa phiếu dịch vụ thành công'}), 200


# Route để redirect đến Flask-Admin
@app.route('/admin')
def redirect_to_admin():
    """Redirect đến Flask-Admin interface"""
    from flask import redirect
    admin_user = request.args.get('user', 'admin')
    return redirect(f'/admin/?admin={admin_user}')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        dao.init_default_settings()
    app.run(debug=True)