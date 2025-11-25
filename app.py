# app.py - File chính chứa toàn bộ ứng dụng Flask với CRUD đầy đủ và nghiệp vụ đặt lịch

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

# Khởi tạo Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///spa_booking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False

# Khởi tạo database
db = SQLAlchemy(app)


# Model Customer - Khách hàng
class Customer(db.Model):
    __tablename__ = 'customers'

    customerId = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100))

    bookings = db.relationship('Booking', backref='customer', lazy=True)


# Model Service - Dịch vụ
class Service(db.Model):
    __tablename__ = 'services'

    servicesId = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    durration = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(200))

    bookings = db.relationship('Booking', backref='service', lazy=True)


# Model Employee - Nhân viên
class Employee(db.Model):
    __tablename__ = 'employees'

    employeeId = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)

    bookings = db.relationship('Booking', backref='employee', lazy=True)


# Model Booking - Đặt lịch
class Booking(db.Model):
    __tablename__ = 'bookings'

    bookingId = db.Column(db.String(50), primary_key=True)
    time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='Đã xác nhận')

    customerId = db.Column(db.String(50), db.ForeignKey('customers.customerId'), nullable=False)
    servicesId = db.Column(db.String(50), db.ForeignKey('services.servicesId'), nullable=False)
    employeeId = db.Column(db.String(50), db.ForeignKey('employees.employeeId'), nullable=False)


# ==================== API BOOKING ====================

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    """Tạo đặt lịch mới với kiểm tra nghiệp vụ"""
    data = request.get_json()

    # Kiểm tra customer, service, employee có tồn tại
    customer = Customer.query.get(data['customerId'])
    if not customer:
        return jsonify({'success': False, 'message': 'Không tìm thấy khách hàng'}), 404

    service = Service.query.get(data['servicesId'])
    if not service:
        return jsonify({'success': False, 'message': 'Không tìm thấy dịch vụ'}), 404

    employee = Employee.query.get(data['employeeId'])
    if not employee:
        return jsonify({'success': False, 'message': 'Không tìm thấy nhân viên'}), 404

    booking_time = datetime.fromisoformat(data['time'])

    # Nghiệp vụ 1: Kiểm tra trùng lịch (nhân viên không thể nhận 2 booking cùng lúc)
    end_time = booking_time + timedelta(minutes=service.durration)

    conflicts = Booking.query.filter(
        Booking.employeeId == data['employeeId'],
        Booking.time < end_time
    ).all()

    for conflict in conflicts:
        conflict_service = Service.query.get(conflict.servicesId)
        conflict_end = conflict.time + timedelta(minutes=conflict_service.durration)

        # Kiểm tra trùng giờ
        if booking_time < conflict_end:
            return jsonify({
                'success': False,
                'message': 'Nhân viên đã có lịch trong khoảng thời gian này'
            }), 400

    # Nghiệp vụ 2: Giới hạn 5 booking/ngày cho mỗi nhân viên
    start_of_day = booking_time.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    bookings_count = Booking.query.filter(
        Booking.employeeId == data['employeeId'],
        Booking.time >= start_of_day,
        Booking.time < end_of_day
    ).count()

    if bookings_count >= 5:
        return jsonify({
            'success': False,
            'message': 'Nhân viên đã đạt giới hạn 5 khách/ngày'
        }), 400

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

    # Gửi thông báo xác nhận
    notification = f'Đặt lịch thành công cho {customer.name} - Dịch vụ {service.name} lúc {booking_time.strftime("%H:%M %d/%m/%Y")}'

    return jsonify({
        'success': True,
        'data': {
            'bookingId': booking.bookingId,
            'time': booking.time.isoformat(),
            'status': booking.status,
            'customer': {'customerId': customer.customerId, 'name': customer.name},
            'service': {'servicesId': service.servicesId, 'name': service.name},
            'employee': {'employeeId': employee.employeeId, 'name': employee.name}
        },
        'notification': notification
    }), 201


@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    """Lấy danh sách tất cả đặt lịch"""
    bookings = Booking.query.all()

    result = []
    for booking in bookings:
        result.append({
            'bookingId': booking.bookingId,
            'time': booking.time.isoformat(),
            'status': booking.status,
            'customer': {'customerId': booking.customer.customerId, 'name': booking.customer.name},
            'service': {'servicesId': booking.service.servicesId, 'name': booking.service.name},
            'employee': {'employeeId': booking.employee.employeeId, 'name': booking.employee.name}
        })

    return jsonify({'success': True, 'data': result, 'total': len(result)}), 200


@app.route('/api/bookings/<string:booking_id>', methods=['GET'])
def get_booking(booking_id):
    """Lấy chi tiết một đặt lịch"""
    booking = Booking.query.get(booking_id)

    if not booking:
        return jsonify({'success': False, 'message': 'Không tìm thấy đặt lịch'}), 404

    return jsonify({
        'success': True,
        'data': {
            'bookingId': booking.bookingId,
            'time': booking.time.isoformat(),
            'status': booking.status,
            'customer': {
                'customerId': booking.customer.customerId,
                'name': booking.customer.name,
                'phone': booking.customer.phone,
                'email': booking.customer.email
            },
            'service': {
                'servicesId': booking.service.servicesId,
                'name': booking.service.name,
                'durration': booking.service.durration,
                'price': booking.service.price,
                'note': booking.service.note
            },
            'employee': {
                'employeeId': booking.employee.employeeId,
                'name': booking.employee.name,
                'role': booking.employee.role
            }
        }
    }), 200


@app.route('/api/bookings/<string:booking_id>', methods=['PUT'])
def update_booking(booking_id):
    """Cập nhật thông tin đặt lịch"""
    booking = Booking.query.get(booking_id)

    if not booking:
        return jsonify({'success': False, 'message': 'Không tìm thấy đặt lịch'}), 404

    data = request.get_json()

    # Cập nhật thông tin
    if 'time' in data:
        booking.time = datetime.fromisoformat(data['time'])
    if 'status' in data:
        booking.status = data['status']
    if 'customerId' in data:
        booking.customerId = data['customerId']
    if 'servicesId' in data:
        booking.servicesId = data['servicesId']
    if 'employeeId' in data:
        booking.employeeId = data['employeeId']

    db.session.commit()

    return jsonify({'success': True, 'message': 'Cập nhật thành công'}), 200


@app.route('/api/bookings/<string:booking_id>', methods=['DELETE'])
def delete_booking(booking_id):
    """Xóa đặt lịch"""
    booking = Booking.query.get(booking_id)

    if not booking:
        return jsonify({'success': False, 'message': 'Không tìm thấy đặt lịch'}), 404

    db.session.delete(booking)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Xóa đặt lịch thành công'}), 200


# ==================== API CUSTOMER ====================

@app.route('/api/customers', methods=['POST'])
def create_customer():
    """Tạo khách hàng mới"""
    data = request.get_json()

    customer = Customer(
        customerId=data['customerId'],
        name=data['name'],
        phone=data['phone'],
        email=data.get('email', '')
    )

    db.session.add(customer)
    db.session.commit()

    return jsonify({
        'success': True,
        'data': {
            'customerId': customer.customerId,
            'name': customer.name,
            'phone': customer.phone,
            'email': customer.email
        }
    }), 201


@app.route('/api/customers', methods=['GET'])
def get_customers():
    """Lấy danh sách khách hàng"""
    customers = Customer.query.all()

    result = []
    for customer in customers:
        result.append({
            'customerId': customer.customerId,
            'name': customer.name,
            'phone': customer.phone,
            'email': customer.email
        })

    return jsonify({'success': True, 'data': result, 'total': len(result)}), 200


@app.route('/api/customers/<string:customer_id>', methods=['GET'])
def get_customer(customer_id):
    """Lấy chi tiết khách hàng"""
    customer = Customer.query.get(customer_id)

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


@app.route('/api/customers/<string:customer_id>', methods=['PUT'])
def update_customer(customer_id):
    """Cập nhật thông tin khách hàng"""
    customer = Customer.query.get(customer_id)

    if not customer:
        return jsonify({'success': False, 'message': 'Không tìm thấy khách hàng'}), 404

    data = request.get_json()

    if 'name' in data:
        customer.name = data['name']
    if 'phone' in data:
        customer.phone = data['phone']
    if 'email' in data:
        customer.email = data['email']

    db.session.commit()

    return jsonify({'success': True, 'message': 'Cập nhật thành công'}), 200


@app.route('/api/customers/<string:customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    """Xóa khách hàng"""
    customer = Customer.query.get(customer_id)

    if not customer:
        return jsonify({'success': False, 'message': 'Không tìm thấy khách hàng'}), 404

    db.session.delete(customer)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Xóa khách hàng thành công'}), 200


# ==================== API SERVICE ====================

@app.route('/api/services', methods=['POST'])
def create_service():
    """Tạo dịch vụ mới"""
    data = request.get_json()

    service = Service(
        servicesId=data['servicesId'],
        name=data['name'],
        durration=data['durration'],
        price=data['price'],
        note=data.get('note', '')
    )

    db.session.add(service)
    db.session.commit()

    return jsonify({
        'success': True,
        'data': {
            'servicesId': service.servicesId,
            'name': service.name,
            'durration': service.durration,
            'price': service.price,
            'note': service.note
        }
    }), 201


@app.route('/api/services', methods=['GET'])
def get_services():
    """Lấy danh sách dịch vụ"""
    services = Service.query.all()

    result = []
    for service in services:
        result.append({
            'servicesId': service.servicesId,
            'name': service.name,
            'durration': service.durration,
            'price': service.price,
            'note': service.note
        })

    return jsonify({'success': True, 'data': result, 'total': len(result)}), 200


@app.route('/api/services/<string:service_id>', methods=['GET'])
def get_service(service_id):
    """Lấy chi tiết dịch vụ"""
    service = Service.query.get(service_id)

    if not service:
        return jsonify({'success': False, 'message': 'Không tìm thấy dịch vụ'}), 404

    return jsonify({
        'success': True,
        'data': {
            'servicesId': service.servicesId,
            'name': service.name,
            'durration': service.durration,
            'price': service.price,
            'note': service.note
        }
    }), 200


@app.route('/api/services/<string:service_id>', methods=['PUT'])
def update_service(service_id):
    """Cập nhật thông tin dịch vụ"""
    service = Service.query.get(service_id)

    if not service:
        return jsonify({'success': False, 'message': 'Không tìm thấy dịch vụ'}), 404

    data = request.get_json()

    if 'name' in data:
        service.name = data['name']
    if 'durration' in data:
        service.durration = data['durration']
    if 'price' in data:
        service.price = data['price']
    if 'note' in data:
        service.note = data['note']

    db.session.commit()

    return jsonify({'success': True, 'message': 'Cập nhật thành công'}), 200


@app.route('/api/services/<string:service_id>', methods=['DELETE'])
def delete_service(service_id):
    """Xóa dịch vụ"""
    service = Service.query.get(service_id)

    if not service:
        return jsonify({'success': False, 'message': 'Không tìm thấy dịch vụ'}), 404

    db.session.delete(service)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Xóa dịch vụ thành công'}), 200


# ==================== API EMPLOYEE ====================

@app.route('/api/employees', methods=['POST'])
def create_employee():
    """Tạo nhân viên mới"""
    data = request.get_json()

    employee = Employee(
        employeeId=data['employeeId'],
        name=data['name'],
        role=data['role']
    )

    db.session.add(employee)
    db.session.commit()

    return jsonify({
        'success': True,
        'data': {
            'employeeId': employee.employeeId,
            'name': employee.name,
            'role': employee.role
        }
    }), 201


@app.route('/api/employees', methods=['GET'])
def get_employees():
    """Lấy danh sách nhân viên"""
    employees = Employee.query.all()

    result = []
    for employee in employees:
        result.append({
            'employeeId': employee.employeeId,
            'name': employee.name,
            'role': employee.role
        })

    return jsonify({'success': True, 'data': result, 'total': len(result)}), 200


@app.route('/api/employees/<string:employee_id>', methods=['GET'])
def get_employee(employee_id):
    """Lấy chi tiết nhân viên"""
    employee = Employee.query.get(employee_id)

    if not employee:
        return jsonify({'success': False, 'message': 'Không tìm thấy nhân viên'}), 404

    return jsonify({
        'success': True,
        'data': {
            'employeeId': employee.employeeId,
            'name': employee.name,
            'role': employee.role
        }
    }), 200


@app.route('/api/employees/<string:employee_id>', methods=['PUT'])
def update_employee(employee_id):
    """Cập nhật thông tin nhân viên"""
    employee = Employee.query.get(employee_id)

    if not employee:
        return jsonify({'success': False, 'message': 'Không tìm thấy nhân viên'}), 404

    data = request.get_json()

    if 'name' in data:
        employee.name = data['name']
    if 'role' in data:
        employee.role = data['role']

    db.session.commit()

    return jsonify({'success': True, 'message': 'Cập nhật thành công'}), 200


@app.route('/api/employees/<string:employee_id>', methods=['DELETE'])
def delete_employee(employee_id):
    """Xóa nhân viên"""
    employee = Employee.query.get(employee_id)

    if not employee:
        return jsonify({'success': False, 'message': 'Không tìm thấy nhân viên'}), 404

    db.session.delete(employee)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Xóa nhân viên thành công'}), 200


# Khởi chạy ứng dụng
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)