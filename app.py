# app.py
from flask import request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re

from __init__ import create_app, db
from models import Service, Customer, Employee, Booking
import dao
from dao import *

# Tạo Flask app
app = create_app()

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
def register():
    """Đăng ký tài khoản mới"""
    data = request.get_json()

    # Validate dữ liệu đầu vào
    if not data.get('username') or not data.get('password'):
        return jsonify({'success': False, 'message': 'Thiếu username hoặc password'}), 400

    if not data.get('name') or not data.get('phone'):
        return jsonify({'success': False, 'message': 'Thiếu thông tin name hoặc phone'}), 400

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
        'name': data['name'],
        'phone': data['phone'],
        'email': data.get('email', '')
    }
    customer = dao.create_customer(customer_data)

    # Hash password và tạo Account mới
    password_hash = generate_password_hash(data['password'])
    account_data = {
        'accountId': dao.generate_account_id(),
        'username': data['username'],
        'passwordHash': password_hash,
        'role': 'Customer'
    }
    account = dao.create_account(account_data, customer_id)

    return jsonify({
        'success': True,
        'message': 'Đăng ký thành công',
        'data': {
            'accountId': account.accountId,
            'username': account.username,
            'role': account.role,
            'customerId': customer_id,
            'name': customer.name,
            'createdAt': account.createdAt.isoformat()
        }
    }), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Đăng nhập"""
    data = request.get_json()

    # Validate dữ liệu đầu vào
    if not data.get('username') or not data.get('password'):
        return jsonify({'success': False, 'message': 'Thiếu username hoặc password'}), 400

    # Tìm tài khoản theo username
    account = dao.get_account_by_username(data['username'])

    # Kiểm tra tài khoản tồn tại
    if not account:
        return jsonify({'success': False, 'message': 'Username hoặc password không đúng'}), 401

    # Kiểm tra password
    if not check_password_hash(account.passwordHash, data['password']):
        return jsonify({'success': False, 'message': 'Username hoặc password không đúng'}), 401

    # Lấy thông tin chi tiết theo role
    user_info = {
        'accountId': account.accountId,
        'username': account.username,
        'role': account.role,
        'createdAt': account.createdAt.isoformat()
    }

    # Nếu là Customer, lấy thông tin customer
    if account.role == 'Customer' and account.customer:
        user_info['customerId'] = account.customer.customerId
        user_info['name'] = account.customer.name
        user_info['phone'] = account.customer.phone
        user_info['email'] = account.customer.email

    # Nếu là Employee, lấy thông tin employee
    if account.role == 'Employee' and account.employee:
        user_info['employeeId'] = account.employee.employeeId
        user_info['name'] = account.employee.name
        user_info['employeeRole'] = account.employee.role

    return jsonify({
        'success': True,
        'message': 'Đăng nhập thành công',
        'data': user_info
    }), 200


@app.route('/api/auth/change-password', methods=['PUT'])
def change_password():
    """Đổi mật khẩu"""
    data = request.get_json()

    # Validate dữ liệu đầu vào
    if not data.get('username') or not data.get('oldPassword') or not data.get('newPassword'):
        return jsonify({'success': False, 'message': 'Thiếu thông tin'}), 400

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
def get_profile():
    """Lấy thông tin profile"""
    username = request.args.get('username')

    if not username:
        return jsonify({'success': False, 'message': 'Thiếu username'}), 400

    account = dao.get_account_by_username(username)

    if not account:
        return jsonify({'success': False, 'message': 'Tài khoản không tồn tại'}), 404

    # Lấy thông tin chi tiết
    profile = {
        'accountId': account.accountId,
        'username': account.username,
        'role': account.role,
        'createdAt': account.createdAt.isoformat()
    }

    # Thông tin Customer
    if account.role == 'Customer' and account.customer:
        profile['customerId'] = account.customer.customerId
        profile['name'] = account.customer.name
        profile['phone'] = account.customer.phone
        profile['email'] = account.customer.email

    # Thông tin Employee
    if account.role == 'Employee' and account.employee:
        profile['employeeId'] = account.employee.employeeId
        profile['name'] = account.employee.name
        profile['employeeRole'] = account.employee.role

    return jsonify({
        'success': True,
        'data': profile
    }), 200


@app.route('/api/auth/change-role', methods=['PUT'])
def change_role():
    """Đổi role tài khoản - chỉ admin"""
    data = request.get_json()

    # Validate dữ liệu đầu vào
    if not data.get('username') or not data.get('newRole'):
        return jsonify({'success': False, 'message': 'Thiếu username hoặc newRole'}), 400

    # Validate role hợp lệ
    valid_roles = ['Customer', 'Employee', 'Admin', 'Cashier']
    if data['newRole'] not in valid_roles:
        return jsonify({'success': False, 'message': 'Role không hợp lệ'}), 400

    # Kiểm tra quyền admin
    if not data.get('adminUsername'):
        return jsonify({'success': False, 'message': 'Thiếu thông tin admin'}), 400

    admin_account = dao.get_account_by_username(data['adminUsername'])
    if not admin_account or admin_account.role != 'Admin':
        return jsonify({'success': False, 'message': 'Không có quyền thực hiện'}), 403

    # Tìm tài khoản cần đổi role
    target_account = dao.get_account_by_username(data['username'])
    if not target_account:
        return jsonify({'success': False, 'message': 'Tài khoản không tồn tại'}), 404

    old_role = target_account.role
    new_role = data['newRole']

    # Nếu role không thay đổi
    if old_role == new_role:
        return jsonify({'success': True, 'message': 'Role không thay đổi'}), 200

    # Xử lý thay đổi role
    if old_role == 'Customer' and new_role == 'Employee':
        # Lấy thông tin customer để tạo employee
        customer_name = target_account.customer.name if target_account.customer else data['username']
        customer_phone = target_account.customer.phone if target_account.customer else ''
        customer_email = target_account.customer.email if target_account.customer else ''

        # Tạo Employee record với phone và email
        employee_data = {
            'employeeId': dao.generate_employee_id(),
            'name': customer_name,
            'role': 'Nhân viên',
            'phone': customer_phone,  # THÊM PHONE
            'email': customer_email  # THÊM EMAIL
        }
        employee = dao.create_employee(employee_data)

        # Xóa customer record
        if target_account.customer:
            dao.delete_customer(target_account.customerId)

        # Cập nhật account
        target_account.customerId = None
        target_account.employeeId = employee.employeeId

    elif old_role == 'Employee' and new_role == 'Customer':
        # Lấy thông tin employee để tạo customer
        employee_name = target_account.employee.name if target_account.employee else data['username']
        employee_phone = target_account.employee.phone if target_account.employee else data.get('phone', '')
        employee_email = target_account.employee.email if target_account.employee else data.get('email', '')

        # Tạo Customer record
        customer_data = {
            'customerId': dao.generate_customer_id(),
            'name': employee_name,
            'phone': employee_phone,
            'email': employee_email
        }
        customer = dao.create_customer(customer_data)

        # Xóa employee record
        if target_account.employee:
            dao.delete_employee(target_account.employeeId)

        # Cập nhật account
        target_account.employeeId = None
        target_account.customerId = customer.customerId

    elif old_role == 'Customer' and new_role == 'Admin':
        # Xóa customer record
        if target_account.customer:
            dao.delete_customer(target_account.customerId)
        target_account.customerId = None

    elif old_role == 'Employee' and new_role == 'Admin':
        # Xóa employee record
        if target_account.employee:
            dao.delete_employee(target_account.employeeId)
        target_account.employeeId = None

    elif old_role == 'Admin' and new_role == 'Customer':
        # Tạo Customer record mới
        customer_data = {
            'customerId': dao.generate_customer_id(),
            'name': data.get('name', data['username']),
            'phone': data.get('phone', ''),
            'email': data.get('email', '')
        }
        customer = dao.create_customer(customer_data)
        target_account.customerId = customer.customerId

    elif old_role == 'Admin' and new_role == 'Employee':
        # Tạo Employee record mới
        employee_data = {
            'employeeId': dao.generate_employee_id(),
            'name': data.get('name', data['username']),
            'role': 'Nhân viên',
            'phone': data.get('phone', ''),  # THÊM PHONE
            'email': data.get('email', '')  # THÊM EMAIL
        }
        employee = dao.create_employee(employee_data)
        target_account.employeeId = employee.employeeId

    elif old_role == 'Admin' and new_role == 'Cashier':
        # Tạo Employee record mới với role Cashier
        employee_data = {
            'employeeId': dao.generate_employee_id(),
            'name': data.get('name', data['username']),
            'role': 'Thu ngân',
            'phone': data.get('phone', ''),
            'email': data.get('email', '')
        }
        employee = dao.create_employee(employee_data)
        target_account.employeeId = employee.employeeId

    elif old_role == 'Employee' and new_role == 'Cashier':
        # Cập nhật role của employee hiện tại
        if target_account.employee:
            target_account.employee.role = 'Thu ngân'

    elif old_role == 'Cashier' and new_role == 'Employee':
        # Cập nhật role của employee hiện tại
        if target_account.employee:
            target_account.employee.role = 'Nhân viên'

    elif old_role == 'Cashier' and new_role == 'Customer':
        # Lấy thông tin employee để tạo customer
        employee_name = target_account.employee.name if target_account.employee else data['username']
        employee_phone = target_account.employee.phone if target_account.employee else data.get('phone', '')
        employee_email = target_account.employee.email if target_account.employee else data.get('email', '')

        # Tạo Customer record
        customer_data = {
            'customerId': dao.generate_customer_id(),
            'name': employee_name,
            'phone': employee_phone,
            'email': employee_email
        }
        customer = dao.create_customer(customer_data)

        # Xóa employee record
        if target_account.employee:
            dao.delete_employee(target_account.employeeId)

        # Cập nhật account
        target_account.employeeId = None
        target_account.customerId = customer.customerId

    elif old_role == 'Cashier' and new_role == 'Admin':
        # Xóa employee record
        if target_account.employee:
            dao.delete_employee(target_account.employeeId)
        target_account.employeeId = None

    elif old_role == 'Customer' and new_role == 'Cashier':
        # Lấy thông tin customer để tạo employee
        customer_name = target_account.customer.name if target_account.customer else data['username']
        customer_phone = target_account.customer.phone if target_account.customer else data.get('phone', '')
        customer_email = target_account.customer.email if target_account.customer else data.get('email', '')

        # Tạo Employee record với role Thu ngân
        employee_data = {
            'employeeId': dao.generate_employee_id(),
            'name': customer_name,
            'role': 'Thu ngân',
            'phone': customer_phone,
            'email': customer_email
        }
        employee = dao.create_employee(employee_data)

        # Xóa customer record
        if target_account.customer:
            dao.delete_customer(target_account.customerId)

        # Cập nhật account
        target_account.customerId = None
        target_account.employeeId = employee.employeeId

    # Cập nhật role
    target_account.role = new_role
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
def get_all_accounts():
    """Lấy danh sách tất cả tài khoản - chỉ admin"""
    admin_username = request.args.get('adminUsername')

    if not admin_username:
        return jsonify({'success': False, 'message': 'Thiếu thông tin admin'}), 400

    admin_account = dao.get_account_by_username(admin_username)
    if not admin_account or admin_account.role != 'Admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403

    try:
        accounts = dao.get_all_accounts()
        data = []

        for acc in accounts:
            account_info = {
                'accountId': acc.accountId,
                'username': acc.username,
                'role': acc.role,
                'createdAt': acc.createdAt.isoformat()
            }

            # Thêm thông tin chi tiết theo role
            if acc.role == 'Customer' and acc.customer:
                account_info['name'] = acc.customer.name
                account_info['phone'] = acc.customer.phone
                account_info['email'] = acc.customer.email
            elif acc.role == 'Employee' and acc.employee:
                account_info['name'] = acc.employee.name
                account_info['phone'] = acc.employee.phone or ''  # THÊM PHONE
                account_info['email'] = acc.employee.email or ''  # THÊM EMAIL
                account_info['employeeRole'] = acc.employee.role
            else:
                # Admin hoặc không có record liên kết
                account_info['name'] = acc.username
                account_info['phone'] = ''
                account_info['email'] = ''

            data.append(account_info)

        return jsonify({'success': True, 'data': data}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'Có lỗi xảy ra: {str(e)}'}), 500


# CUSTOMER APIs

@app.route('/api/customers', methods=['POST'])
def create_customer():
    """Tạo khách hàng mới"""
    data = request.get_json()
    dao.create_customer(data)
    return jsonify({'success': True, 'message': "Tạo khách hàng thành công"}), 201


@app.route('/api/customers', methods=['GET'])
def get_customers():
    """Lấy danh sách khách hàng"""
    customers = dao.get_all_customers()
    data = [{
        'customerId': c.customerId,
        'name': c.name,
        'phone': c.phone,
        'email': c.email
    } for c in customers]
    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/customers/<customerId>', methods=['GET'])
def get_customer(customerId):
    """Lấy thông tin khách hàng theo ID"""
    customer = dao.get_customer_by_id(customerId)
    if not customer:
        return jsonify({'success': False, 'message': 'Không tìm thấy khách hàng'}), 404
    return jsonify({
        'success': True,
        'data': {
            'customerId': customer.customerId,
            'name': customer.name,
            'phone': customer.phone,
            'email': customer.email
        }
    }), 200


@app.route('/api/customers/<customerId>', methods=['PUT'])
def update_customer(customerId):
    """Cập nhật thông tin khách hàng"""
    customer = dao.get_customer_by_id(customerId)
    if not customer:
        return jsonify({'success': False, 'message': 'Không tìm thấy khách hàng'}), 404

    data = request.get_json()
    dao.update_customer(customerId, data)

    return jsonify({'success': True, 'message': 'Cập nhật khách hàng thành công'}), 200


@app.route('/api/customers/<customerId>', methods=['DELETE'])
def delete_customer(customerId):
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
def create_employee():
    """Tạo nhân viên mới"""
    data = request.get_json()
    dao.create_employee(data)
    return jsonify({'success': True, 'message': "Tạo nhân viên thành công"}), 201


@app.route('/api/employees', methods=['GET'])
def get_employees():
    """Lấy danh sách nhân viên"""
    employees = dao.get_all_employees()
    data = [{
        'employeeId': e.employeeId,
        'name': e.name,
        'role': e.role,
        'phone': e.phone or '',  # THÊM PHONE
        'email': e.email or ''  # THÊM EMAIL
    } for e in employees]
    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/employees/<employeeId>', methods=['GET'])
def get_employee(employeeId):
    """Lấy thông tin nhân viên theo ID"""
    employee = dao.get_employee_by_id(employeeId)
    if not employee:
        return jsonify({'success': False, 'message': 'Không tìm thấy nhân viên'}), 404
    return jsonify({'success': True, 'data': {
        'employeeId': employee.employeeId,
        'name': employee.name,
        'role': employee.role,
        'phone': employee.phone or '',  # THÊM PHONE
        'email': employee.email or ''  # THÊM EMAIL
    }}), 200


@app.route('/api/employees/<employeeId>', methods=['PUT'])
def update_employee(employeeId):
    """Cập nhật thông tin nhân viên"""
    employee = dao.get_employee_by_id(employeeId)
    if not employee:
        return jsonify({'success': False, 'message': 'Không tìm thấy nhân viên'}), 404

    data = request.get_json()
    dao.update_employee(employeeId, data)

    return jsonify({'success': True, 'message': 'Cập nhật nhân viên thành công'}), 200


@app.route('/api/employees/<employeeId>', methods=['DELETE'])
def delete_employee(employeeId):
    """Xóa nhân viên"""
    employee = dao.get_employee_by_id(employeeId)
    if not employee:
        return jsonify({'success': False, 'message': 'Không tìm thấy nhân viên'}), 404

    if employee.bookings:
        return jsonify({'success': False, 'message': 'Không thể xóa nhân viên vì còn lịch'}), 400

    dao.delete_employee(employeeId)
    return jsonify({'success': True, 'message': 'Xóa nhân viên thành công'}), 200


# SERVICE APIs

@app.route('/api/services/form', methods=['GET'])
def get_service_form():
    """Lấy form dịch vụ"""
    return jsonify({
        'success': True,
        'form': {
            'title': 'Phiếu Dịch Vụ',
            'fields': [
                {'name': 'servicesId', 'type': 'text', 'required': True},
                {'name': 'name', 'type': 'text', 'required': True},
                {'name': 'durration', 'type': 'number', 'min': 15, 'max': 120},
                {'name': 'price', 'type': 'number', 'min': 0, 'required': True},
                {'name': 'note', 'type': 'textarea', 'required': False}
            ]
        }
    }), 200


@app.route('/api/services/submit', methods=['POST'])
def create_service():
    """Tạo dịch vụ mới"""
    data = request.get_json()

    if dao.get_service_by_id(data['servicesId']):
        return jsonify({'success': False, 'message': 'Mã dịch vụ đã tồn tại'}), 400

    d = int(data['durration'])
    if d < 15 or d > 120:
        return jsonify({'success': False, 'message': 'Thời lượng dịch vụ phải từ 15-120 phút'}), 400

    dao.create_service(data)
    return jsonify({'success': True, 'message': "Tạo dịch vụ thành công"}), 201


@app.route('/api/services', methods=['GET'])
def get_services():
    """Lấy danh sách dịch vụ"""
    services = dao.get_all_services()
    data = [{
        'servicesId': s.servicesId,
        'name': s.name,
        'durration': s.durration,
        'price': s.price,
        'note': s.note
    } for s in services]
    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/services/<servicesId>', methods=['GET'])
def get_service(servicesId):
    """Lấy thông tin dịch vụ theo ID"""
    service = dao.get_service_by_id(servicesId)
    if not service:
        return jsonify({'success': False, 'message': 'Không tìm thấy dịch vụ'}), 404
    return jsonify({'success': True, 'data': {
        'servicesId': service.servicesId,
        'name': service.name,
        'durration': service.durration,
        'price': service.price,
        'note': service.note
    }}), 200


@app.route('/api/services/<servicesId>', methods=['PUT'])
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
def get_bookings():
    """Lấy danh sách booking"""
    bookings = dao.get_all_bookings()
    data = []
    for b in bookings:
        data.append({
            'bookingId': b.bookingId,
            'time': b.time.isoformat(),
            'status': b.status,
            'customer': {'customerId': b.customerId, 'name': b.customer.name},
            'service': {'servicesId': b.servicesId, 'name': b.service.name},
            'employee': {'employeeId': b.employeeId, 'name': b.employee.name}
        })
    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/bookings/<bookingId>', methods=['GET'])
def get_booking(bookingId):
    """Lấy thông tin booking theo ID"""
    b = dao.get_booking_by_id(bookingId)
    if not b:
        return jsonify({'success': False, 'message': 'Không tìm thấy lịch'}), 404

    return jsonify({'success': True, 'data': {
        'bookingId': b.bookingId,
        'time': b.time.isoformat(),
        'status': b.status,
        'customer': {'customerId': b.customerId, 'name': b.customer.name},
        'service': {'servicesId': b.servicesId, 'name': b.service.name},
        'employee': {'employeeId': b.employeeId, 'name': b.employee.name}
    }}), 200


@app.route('/api/bookings/<bookingId>', methods=['PUT'])
def update_booking(bookingId):
    """Cập nhật booking"""
    booking = dao.get_booking_by_id(bookingId)
    if not booking:
        return jsonify({'success': False, 'message': 'Không tìm thấy lịch'}), 404

    data = request.get_json()
    dao.update_booking(bookingId, data)
    return jsonify({'success': True, 'message': "Cập nhật lịch thành công"}), 200


@app.route('/api/bookings/<bookingId>', methods=['DELETE'])
def delete_booking(bookingId):
    """Xóa booking"""
    booking = dao.get_booking_by_id(bookingId)
    if not booking:
        return jsonify({'success': False, 'message': 'Không tìm thấy lịch'}), 404

    dao.delete_booking(bookingId)
    return jsonify({'success': True, 'message': "Xóa lịch thành công"}), 200


# INVOICE APIs

@app.route('/api/invoices', methods=['POST'])
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

    service = Service.query.get(booking.servicesId)

    # Lấy cấu hình từ settings
    vat_rate = float(dao.get_setting_value('vat_rate', '10'))
    max_discount_rate = float(dao.get_setting_value('max_discount', '20'))

    total = service.price

    discount_percent = float(data.get('discount', 0))
    if discount_percent < 0 or discount_percent > max_discount_rate:
        return jsonify({'success': False, 'message': f'Giảm giá tối đa {max_discount_rate}%'}), 400

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

    return jsonify({
        'success': True,
        'message': 'Tạo hóa đơn thành công',
        'data': {
            'invoiceId': invoice.invoiceId,
            'customerId': invoice.customerId,
            'customerName': booking.customer.name,
            'serviceName': service.name,
            'total': total,
            'discount': discount,
            'vat': vat,
            'finalTotal': finalTotal
        }
    }), 201


@app.route('/api/invoices', methods=['GET'])
def get_invoices():
    """Lấy danh sách hóa đơn"""
    invoices = dao.get_all_invoices()
    data = []

    for inv in invoices:
        booking = inv.booking

        data.append({
            'invoiceId': inv.invoiceId,
            'customerId': inv.customerId,
            'customerName': inv.customer.name,
            'serviceName': booking.service.name if booking else '',
            'total': inv.total,
            'discount': inv.discount,
            'vat': inv.vat,
            'finalTotal': inv.finalTotal
        })

    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/invoices/<invoiceId>', methods=['GET'])
def get_invoice(invoiceId):
    """Lấy thông tin hóa đơn theo ID"""
    invoice = dao.get_invoice_by_id(invoiceId)
    if not invoice:
        return jsonify({'success': False, 'message': 'Không tìm thấy hóa đơn'}), 404

    booking = invoice.booking

    return jsonify({
        'success': True,
        'data': {
            'invoiceId': invoice.invoiceId,
            'customerId': invoice.customerId,
            'customerName': invoice.customer.name,
            'customerPhone': invoice.customer.phone,
            'serviceName': booking.service.name if booking else '',
            'servicePrice': booking.service.price if booking else 0,
            'employeeName': booking.employee.name if booking else '',
            'bookingTime': booking.time.isoformat() if booking else '',
            'total': invoice.total,
            'discount': invoice.discount,
            'vat': invoice.vat,
            'finalTotal': invoice.finalTotal
        }
    }), 200


@app.route('/api/invoices/<invoiceId>', methods=['PUT'])
def update_invoice(invoiceId):
    """Cập nhật hóa đơn"""
    invoice = dao.get_invoice_by_id(invoiceId)
    if not invoice:
        return jsonify({'success': False, 'message': 'Không tìm thấy hóa đơn'}), 404

    data = request.get_json()

    booking = invoice.booking
    service = Service.query.get(booking.servicesId)
    total = service.price

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
def delete_invoice(invoiceId):
    """Xóa hóa đơn"""
    invoice = dao.get_invoice_by_id(invoiceId)
    if not invoice:
        return jsonify({'success': False, 'message': 'Không tìm thấy hóa đơn'}), 404

    dao.delete_invoice(invoiceId)
    return jsonify({'success': True, 'message': 'Xóa hóa đơn thành công'}), 200


# SETTINGS APIs

@app.route('/api/settings', methods=['GET'])
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


# RUN APP

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        dao.init_default_settings()
    app.run(debug=True)