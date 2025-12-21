# app.py
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import re

# APP CONFIG
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///spa_booking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False

db = SQLAlchemy(app)

class Settings(db.Model):
    __tablename__ = 'settings'
    settingId = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))


class Account(db.Model):
    __tablename__ = 'accounts'
    accountId = db.Column(db.String(50), primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    passwordHash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='Customer')  # Customer, Employee, Admin
    customerId = db.Column(db.String(50), db.ForeignKey('customers.customerId'))
    employeeId = db.Column(db.String(50), db.ForeignKey('employees.employeeId'))
    createdAt = db.Column(db.DateTime, default=datetime.now)

    customer = db.relationship('Customer', backref='account', uselist=False, lazy=True)
    employee = db.relationship('Employee', backref='account', uselist=False, lazy=True)


class Customer(db.Model):
    __tablename__ = 'customers'
    customerId = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100))
    bookings = db.relationship('Booking', backref='customer', lazy=True)


class Service(db.Model):
    __tablename__ = 'services'
    servicesId = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    durration = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(200))
    bookings = db.relationship('Booking', backref='service', lazy=True)


class Employee(db.Model):
    __tablename__ = 'employees'
    employeeId = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    bookings = db.relationship('Booking', backref='employee', lazy=True)


class Invoice(db.Model):
    __tablename__ = 'invoices'
    invoiceId = db.Column(db.String(50), primary_key=True)
    customerId = db.Column(db.String(50), db.ForeignKey('customers.customerId'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    vat = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0)
    finalTotal = db.Column(db.Float, nullable=False)
    customer = db.relationship('Customer', backref='invoices', lazy=True)
    booking = db.relationship('Booking', backref='invoice', uselist=False, lazy=True)


class Booking(db.Model):
    __tablename__ = 'bookings'
    bookingId = db.Column(db.String(50), primary_key=True)
    time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='Đã xác nhận')
    customerId = db.Column(db.String(50), db.ForeignKey('customers.customerId'), nullable=False)
    servicesId = db.Column(db.String(50), db.ForeignKey('services.servicesId'), nullable=False)
    employeeId = db.Column(db.String(50), db.ForeignKey('employees.employeeId'), nullable=False)
    invoiceId = db.Column(db.String(50), db.ForeignKey('invoices.invoiceId'))


# HELPER FUNCTIONS

def get_setting_value(setting_id, default_value):
    """Lấy giá trị cài đặt từ database"""
    setting = Settings.query.get(setting_id)
    if setting:
        return setting.value
    return default_value


def init_default_settings():
    """Khởi tạo các cài đặt mặc định"""
    default_settings = [
        {'settingId': 'vat_rate', 'value': '10', 'description': 'Mức VAT (%)'},
        {'settingId': 'max_bookings_per_day', 'value': '5',
         'description': 'Số lượng booking tối đa mỗi nhân viên mỗi ngày'},
        {'settingId': 'max_discount', 'value': '20', 'description': 'Phần trăm giảm giá tối đa (%)'}
    ]

    for setting in default_settings:
        if not Settings.query.get(setting['settingId']):
            new_setting = Settings(
                settingId=setting['settingId'],
                value=setting['value'],
                description=setting['description']
            )
            db.session.add(new_setting)

    db.session.commit()


def generate_account_id():
    return 'ACC' + secrets.token_hex(4).upper()


def generate_customer_id():
    return 'C' + secrets.token_hex(4).upper()


# AUTHENTICATION APIs

@app.route('/api/auth/register', methods=['POST'])
def register():
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
    if Account.query.filter_by(username=data['username']).first():
        return jsonify({'success': False, 'message': 'Username đã tồn tại'}), 400

    # Kiểm tra độ dài password (tối thiểu 6 ký tự)
    if len(data['password']) < 6:
        return jsonify({'success': False, 'message': 'Password phải có ít nhất 6 ký tự'}), 400

    # Tạo Customer mới
    customer_id = generate_customer_id()
    customer = Customer(
        customerId=customer_id,
        name=data['name'],
        phone=data['phone'],
        email=data.get('email', '')
    )

    # Hash password
    password_hash = generate_password_hash(data['password'])

    # Tạo Account mới
    account_id = generate_account_id()
    account = Account(
        accountId=account_id,
        username=data['username'],
        passwordHash=password_hash,
        role='Customer',
        customerId=customer_id,
        createdAt=datetime.now()
    )

    # Lưu vào database
    db.session.add(customer)
    db.session.add(account)
    db.session.commit()

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
    data = request.get_json()

    # Validate dữ liệu đầu vào
    if not data.get('username') or not data.get('password'):
        return jsonify({'success': False, 'message': 'Thiếu username hoặc password'}), 400

    # Tìm tài khoản theo username
    account = Account.query.filter_by(username=data['username']).first()

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
    data = request.get_json()

    # Validate dữ liệu đầu vào
    if not data.get('username') or not data.get('oldPassword') or not data.get('newPassword'):
        return jsonify({'success': False, 'message': 'Thiếu thông tin'}), 400

    # Kiểm tra độ dài password mới
    if len(data['newPassword']) < 6:
        return jsonify({'success': False, 'message': 'Password mới phải có ít nhất 6 ký tự'}), 400

    # Tìm tài khoản
    account = Account.query.filter_by(username=data['username']).first()

    if not account:
        return jsonify({'success': False, 'message': 'Tài khoản không tồn tại'}), 404

    # Kiểm tra password cũ
    if not check_password_hash(account.passwordHash, data['oldPassword']):
        return jsonify({'success': False, 'message': 'Password cũ không đúng'}), 401

    # Cập nhật password mới
    account.passwordHash = generate_password_hash(data['newPassword'])
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Đổi mật khẩu thành công'
    }), 200


@app.route('/api/auth/profile', methods=['GET'])
def get_profile():
    username = request.args.get('username')

    if not username:
        return jsonify({'success': False, 'message': 'Thiếu username'}), 400

    account = Account.query.filter_by(username=username).first()

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


# CUSTOMER APIs

@app.route('/api/customers', methods=['POST'])
def create_customer():
    data = request.get_json()
    customer = Customer(
        customerId=data['customerId'],
        name=data['name'],
        phone=data['phone'],
        email=data.get('email', '')
    )
    db.session.add(customer)
    db.session.commit()
    return jsonify({'success': True, 'message': "Tạo khách hàng thành công"}), 201


@app.route('/api/customers', methods=['GET'])
def get_customers():
    customers = Customer.query.all()
    data = [{
        'customerId': c.customerId,
        'name': c.name,
        'phone': c.phone,
        'email': c.email
    } for c in customers]
    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/customers/<customerId>', methods=['GET'])
def get_customer(customerId):
    customer = Customer.query.get(customerId)
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
    customer = Customer.query.get(customerId)
    if not customer:
        return jsonify({'success': False, 'message': 'Không tìm thấy khách hàng'}), 404

    data = request.get_json()
    customer.name = data.get('name', customer.name)
    customer.phone = data.get('phone', customer.phone)
    customer.email = data.get('email', customer.email)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Cập nhật khách hàng thành công'}), 200


@app.route('/api/customers/<customerId>', methods=['DELETE'])
def delete_customer(customerId):
    customer = Customer.query.get(customerId)
    if not customer:
        return jsonify({'success': False, 'message': 'Không tìm thấy khách hàng'}), 404

    if customer.bookings:
        return jsonify({'success': False, 'message': 'Không thể xóa khách hàng vì còn lịch'}), 400

    db.session.delete(customer)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Xóa khách hàng thành công'}), 200


# EMPLOYEE APIs

@app.route('/api/employees', methods=['POST'])
def create_employee():
    data = request.get_json()
    employee = Employee(
        employeeId=data['employeeId'],
        name=data['name'],
        role=data['role']
    )
    db.session.add(employee)
    db.session.commit()
    return jsonify({'success': True, 'message': "Tạo nhân viên thành công"}), 201


@app.route('/api/employees', methods=['GET'])
def get_employees():
    employees = Employee.query.all()
    data = [{
        'employeeId': e.employeeId,
        'name': e.name,
        'role': e.role
    } for e in employees]
    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/employees/<employeeId>', methods=['GET'])
def get_employee(employeeId):
    employee = Employee.query.get(employeeId)
    if not employee:
        return jsonify({'success': False, 'message': 'Không tìm thấy nhân viên'}), 404
    return jsonify({'success': True, 'data': {
        'employeeId': employee.employeeId,
        'name': employee.name,
        'role': employee.role
    }}), 200


@app.route('/api/employees/<employeeId>', methods=['PUT'])
def update_employee(employeeId):
    employee = Employee.query.get(employeeId)
    if not employee:
        return jsonify({'success': False, 'message': 'Không tìm thấy nhân viên'}), 404

    data = request.get_json()
    employee.name = data.get('name', employee.name)
    employee.role = data.get('role', employee.role)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Cập nhật nhân viên thành công'}), 200


@app.route('/api/employees/<employeeId>', methods=['DELETE'])
def delete_employee(employeeId):
    employee = Employee.query.get(employeeId)
    if not employee:
        return jsonify({'success': False, 'message': 'Không tìm thấy nhân viên'}), 404

    if employee.bookings:
        return jsonify({'success': False, 'message': 'Không thể xóa nhân viên vì còn lịch'}), 400

    db.session.delete(employee)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Xóa nhân viên thành công'}), 200


# SERVICE APIs ===================

@app.route('/api/services/form', methods=['GET'])
def get_service_form():
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
    data = request.get_json()

    if Service.query.get(data['servicesId']):
        return jsonify({'success': False, 'message': 'Mã dịch vụ đã tồn tại'}), 400

    d = int(data['durration'])
    if d < 15 or d > 120:
        return jsonify({'success': False, 'message': 'Thời lượng dịch vụ phải từ 15-120 phút'}), 400

    service = Service(
        servicesId=data['servicesId'],
        name=data['name'],
        durration=d,
        price=float(data['price']),
        note=data.get('note', '')
    )
    db.session.add(service)
    db.session.commit()

    return jsonify({'success': True, 'message': "Tạo dịch vụ thành công"}), 201


@app.route('/api/services', methods=['GET'])
def get_services():
    services = Service.query.all()
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
    service = Service.query.get(servicesId)
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
    service = Service.query.get(servicesId)
    if not service:
        return jsonify({'success': False, 'message': 'Không tìm thấy dịch vụ'}), 404

    data = request.get_json()
    if "durration" in data:
        d = int(data["durration"])
        if d < 15 or d > 120:
            return jsonify({'success': False, 'message': 'Thời lượng dịch vụ phải từ 15-120 phút'}), 400
        service.durration = d

    service.name = data.get('name', service.name)
    service.price = float(data.get('price', service.price))
    service.note = data.get('note', service.note)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Cập nhật dịch vụ thành công'}), 200


@app.route('/api/services/<servicesId>', methods=['DELETE'])
def delete_service(servicesId):
    service = Service.query.get(servicesId)
    if not service:
        return jsonify({'success': False, 'message': 'Không tìm thấy dịch vụ'}), 404

    if service.bookings:
        return jsonify({'success': False, 'message': 'Không thể xóa dịch vụ vì có lịch sử booking'}), 400

    db.session.delete(service)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Xóa dịch vụ thành công'}), 200


# BOOKING APIs

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    data = request.get_json()

    customer = Customer.query.get(data['customerId'])
    service = Service.query.get(data['servicesId'])
    employee = Employee.query.get(data['employeeId'])

    if not customer or not service or not employee:
        return jsonify({'success': False, 'message': 'Sai thông tin customer/service/employee'}), 404

    booking_time = datetime.fromisoformat(data['time'])
    end_time = booking_time + timedelta(minutes=service.durration)

    # Kiểm tra lịch trùng cho nhân viên
    conflicts = Booking.query.filter(
        Booking.employeeId == employee.employeeId,
        Booking.time < end_time
    ).all()

    for c in conflicts:
        c_end = c.time + timedelta(minutes=Service.query.get(c.servicesId).durration)
        if booking_time < c_end:
            return jsonify({'success': False, 'message': "Nhân viên đã có lịch trùng"}), 400

    # Kiểm tra giới hạn booking/ngày
    max_bookings = int(get_setting_value('max_bookings_per_day', '5'))
    day_start = booking_time.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    count = Booking.query.filter(
        Booking.employeeId == employee.employeeId,
        Booking.time >= day_start,
        Booking.time < day_end
    ).count()

    if count >= max_bookings:
        return jsonify({'success': False, 'message': f"Nhân viên đã đạt {max_bookings} lịch trong ngày"}), 400

    # Kiểm tra khách hàng có lịch trùng
    customer_conflicts = Booking.query.filter(
        Booking.customerId == customer.customerId,
        Booking.time < end_time
    ).all()

    for c in customer_conflicts:
        c_end = c.time + timedelta(minutes=Service.query.get(c.servicesId).durration)
        if booking_time < c_end:
            return jsonify({'success': False, 'message': "Khách hàng đã có lịch trùng"}), 400

    # Tạo booking
    booking = Booking(
        bookingId=data['bookingId'],
        time=booking_time,
        status=data.get('status', 'Đã xác nhận'),
        customerId=data['customerId'],
        servicesId=data['servicesId'],
        employeeId=data['employeeId']
    )

    db.session.add(booking)
    db.session.commit()

    return jsonify({'success': True, 'message': "Tạo lịch thành công"}), 201


@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    bookings = Booking.query.all()
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
    b = Booking.query.get(bookingId)
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
    booking = Booking.query.get(bookingId)
    if not booking:
        return jsonify({'success': False, 'message': 'Không tìm thấy lịch'}), 404

    data = request.get_json()

    if "time" in data:
        booking.time = datetime.fromisoformat(data['time'])

    booking.status = data.get('status', booking.status)

    db.session.commit()
    return jsonify({'success': True, 'message': "Cập nhật lịch thành công"}), 200


@app.route('/api/bookings/<bookingId>', methods=['DELETE'])
def delete_booking(bookingId):
    booking = Booking.query.get(bookingId)
    if not booking:
        return jsonify({'success': False, 'message': 'Không tìm thấy lịch'}), 404

    db.session.delete(booking)
    db.session.commit()
    return jsonify({'success': True, 'message': "Xóa lịch thành công"}), 200


# INVOICE APIs

@app.route('/api/invoices', methods=['POST'])
def create_invoice():
    """Tạo hóa đơn thanh toán cho booking"""
    data = request.get_json()

    booking = Booking.query.get(data['bookingId'])
    if not booking:
        return jsonify({'success': False, 'message': 'Không tìm thấy booking'}), 404

    if booking.invoiceId:
        return jsonify({'success': False, 'message': 'Booking đã có hóa đơn'}), 400

    if Invoice.query.get(data['invoiceId']):
        return jsonify({'success': False, 'message': 'Mã hóa đơn đã tồn tại'}), 400

    service = Service.query.get(booking.servicesId)

    # Lấy cấu hình từ settings
    vat_rate = float(get_setting_value('vat_rate', '10'))
    max_discount_rate = float(get_setting_value('max_discount', '20'))

    total = service.price

    discount_percent = float(data.get('discount', 0))
    if discount_percent < 0 or discount_percent > max_discount_rate:
        return jsonify({'success': False, 'message': f'Giảm giá tối đa {max_discount_rate}%'}), 400

    discount = total * discount_percent / 100
    subtotal = total - discount
    vat = subtotal * vat_rate / 100
    finalTotal = subtotal + vat

    invoice = Invoice(
        invoiceId=data['invoiceId'],
        customerId=booking.customerId,
        total=total,
        vat=vat,
        discount=discount,
        finalTotal=finalTotal
    )

    booking.invoiceId = data['invoiceId']

    db.session.add(invoice)
    db.session.commit()

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
    invoices = Invoice.query.all()
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
    invoice = Invoice.query.get(invoiceId)
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
    invoice = Invoice.query.get(invoiceId)
    if not invoice:
        return jsonify({'success': False, 'message': 'Không tìm thấy hóa đơn'}), 404

    data = request.get_json()

    booking = invoice.booking
    service = Service.query.get(booking.servicesId)
    total = service.price

    vat_rate = float(get_setting_value('vat_rate', '10'))
    max_discount_rate = float(get_setting_value('max_discount', '20'))

    discount_percent = float(data.get('discount', 0))
    if discount_percent < 0 or discount_percent > max_discount_rate:
        return jsonify({'success': False, 'message': f'Giảm giá tối đa {max_discount_rate}%'}), 400

    discount = total * discount_percent / 100
    subtotal = total - discount
    vat = subtotal * vat_rate / 100
    finalTotal = subtotal + vat

    invoice.total = total
    invoice.discount = discount
    invoice.vat = vat
    invoice.finalTotal = finalTotal

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Cập nhật hóa đơn thành công',
        'data': {
            'invoiceId': invoice.invoiceId,
            'total': invoice.total,
            'discount': invoice.discount,
            'vat': invoice.vat,
            'finalTotal': invoice.finalTotal
        }
    }), 200


@app.route('/api/invoices/<invoiceId>', methods=['DELETE'])
def delete_invoice(invoiceId):
    invoice = Invoice.query.get(invoiceId)
    if not invoice:
        return jsonify({'success': False, 'message': 'Không tìm thấy hóa đơn'}), 404

    if invoice.booking:
        invoice.booking.invoiceId = None

    db.session.delete(invoice)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Xóa hóa đơn thành công'}), 200


# SETTINGS APIs

@app.route('/api/settings', methods=['GET'])
def get_all_settings():
    settings = Settings.query.all()
    data = [{
        'settingId': s.settingId,
        'value': s.value,
        'description': s.description
    } for s in settings]

    return jsonify({'success': True, 'data': data}), 200


@app.route('/api/settings/<settingId>', methods=['GET'])
def get_setting(settingId):
    setting = Settings.query.get(settingId)
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
    setting = Settings.query.get(settingId)
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

    setting.value = new_value
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Cập nhật cài đặt thành công',
        'data': {
            'settingId': setting.settingId,
            'value': setting.value,
            'description': setting.description
        }
    }), 200


@app.route('/api/settings/service-price/<servicesId>', methods=['PUT'])
def update_service_price_via_settings(servicesId):
    service = Service.query.get(servicesId)
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


# REPORTS

@app.route('/api/reports/revenue', methods=['GET'])
def get_revenue_report():
    month = request.args.get('month')
    year = request.args.get('year')

    if not month or not year:
        return jsonify({'success': False, 'message': 'Thiếu tham số month hoặc year'}), 400

    try:
        month = int(month)
        year = int(year)
    except:
        return jsonify({'success': False, 'message': 'Tham số month/year không hợp lệ'}), 400

    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    bookings = Booking.query.filter(
        Booking.time >= start_date,
        Booking.time < end_date
    ).all()

    total_revenue = 0
    booking_count = len(bookings)

    for booking in bookings:
        service = Service.query.get(booking.servicesId)
        if service:
            total_revenue += service.price

    return jsonify({
        'success': True,
        'data': {
            'month': month,
            'year': year,
            'total_revenue': total_revenue,
            'booking_count': booking_count
        }
    }), 200


@app.route('/api/reports/service-frequency', methods=['GET'])
def get_service_frequency_report():
    month = request.args.get('month')
    year = request.args.get('year')

    if not month or not year:
        return jsonify({'success': False, 'message': 'Thiếu tham số month hoặc year'}), 400

    try:
        month = int(month)
        year = int(year)
    except:
        return jsonify({'success': False, 'message': 'Tham số month/year không hợp lệ'}), 400

    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    bookings = Booking.query.filter(
        Booking.time >= start_date,
        Booking.time < end_date
    ).all()

    service_frequency = {}
    for booking in bookings:
        service_id = booking.servicesId

        if service_id not in service_frequency:
            service = Service.query.get(service_id)
            service_frequency[service_id] = {
                'servicesId': service_id,
                'name': service.name if service else 'Unknown',
                'price': service.price if service else 0,
                'count': 0,
                'revenue': 0
            }

        service_frequency[service_id]['count'] += 1
        service_frequency[service_id]['revenue'] += service_frequency[service_id]['price']

    result = sorted(service_frequency.values(), key=lambda x: x['count'], reverse=True)

    return jsonify({
        'success': True,
        'data': {
            'month': month,
            'year': year,
            'services': result
        }
    }), 200


# RUN APP

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_default_settings()
    app.run(debug=True)