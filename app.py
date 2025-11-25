from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

# APP CONFIG
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///spa_booking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False

db = SQLAlchemy(app)

# MODELS
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

class Booking(db.Model):
    __tablename__ = 'bookings'
    bookingId = db.Column(db.String(50), primary_key=True)
    time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='Đã xác nhận')
    customerId = db.Column(db.String(50), db.ForeignKey('customers.customerId'), nullable=False)
    servicesId = db.Column(db.String(50), db.ForeignKey('services.servicesId'), nullable=False)
    employeeId = db.Column(db.String(50), db.ForeignKey('employees.employeeId'), nullable=False)

# CUSTOMER
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

    # Kiểm tra lịch của khách hàng
    if customer.bookings:
        return jsonify({'success': False, 'message': 'Không thể xóa khách hàng vì còn lịch'}), 400

    db.session.delete(customer)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Xóa khách hàng thành công'}), 200

# EMPLOYEE
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

    # Kiểm tra lịch của nhân viên
    if employee.bookings:
        return jsonify({'success': False, 'message': 'Không thể xóa nhân viên vì còn lịch'}), 400

    db.session.delete(employee)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Xóa nhân viên thành công'}), 200

# SERVICE & SERVICE RECORD
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

    # Kiểm tra lịch sử dụng dịch vụ
    if service.bookings:
        return jsonify({'success': False, 'message': 'Không thể xóa dịch vụ vì có lịch sử booking'}), 400

    db.session.delete(service)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Xóa dịch vụ thành công'}), 200

# BOOKING
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

    # RULE 1: Kiểm tra lịch trùng cho nhân viên
    conflicts = Booking.query.filter(
        Booking.employeeId == employee.employeeId,
        Booking.time < end_time
    ).all()

    for c in conflicts:
        c_end = c.time + timedelta(minutes=Service.query.get(c.servicesId).durration)
        if booking_time < c_end:
            return jsonify({'success': False, 'message': "Nhân viên đã có lịch trùng"}), 400

    # RULE 2: Nhân viên tối đa 5 bookings/ngày
    day_start = booking_time.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    count = Booking.query.filter(
        Booking.employeeId == employee.employeeId,
        Booking.time >= day_start,
        Booking.time < day_end
    ).count()

    if count >= 5:
        return jsonify({'success': False, 'message': "Nhân viên đã đạt 5 lịch trong ngày"}), 400

    # RULE 3: Kiểm tra khách hàng có lịch trùng
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

# RUN APP
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

