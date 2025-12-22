# dao/booking_dao.py
"""
Data Access Object cho Booking
"""
from datetime import datetime, timedelta
from __init__ import db
from models import Booking, Service


def get_all_bookings():
    """Lấy danh sách tất cả booking"""
    return Booking.query.all()


def get_booking_by_id(booking_id):
    """Lấy thông tin booking theo ID"""
    return Booking.query.get(booking_id)


def create_booking(data):
    """Tạo booking mới"""
    booking = Booking(
        bookingId=data['bookingId'],
        time=datetime.fromisoformat(data['time']),
        status=data.get('status', 'Đã xác nhận'),
        customerId=data['customerId'],
        servicesId=data['servicesId'],
        employeeId=data['employeeId']
    )
    db.session.add(booking)
    db.session.commit()
    return booking


def update_booking(booking_id, data):
    """Cập nhật thông tin booking"""
    booking = Booking.query.get(booking_id)
    if booking:
        if "time" in data:
            booking.time = datetime.fromisoformat(data['time'])
        booking.status = data.get('status', booking.status)
        db.session.commit()
    return booking


def delete_booking(booking_id):
    """Xóa booking"""
    booking = Booking.query.get(booking_id)
    if booking:
        db.session.delete(booking)
        db.session.commit()
        return True
    return False


def check_employee_booking_conflicts(employee_id, booking_time, service_duration):
    """Kiểm tra lịch trùng cho nhân viên"""
    end_time = booking_time + timedelta(minutes=service_duration)

    conflicts = Booking.query.filter(
        Booking.employeeId == employee_id,
        Booking.time < end_time
    ).all()

    for c in conflicts:
        c_service = Service.query.get(c.servicesId)
        c_end = c.time + timedelta(minutes=c_service.durration)
        if booking_time < c_end:
            return True
    return False


def check_customer_booking_conflicts(customer_id, booking_time, service_duration):
    """Kiểm tra khách hàng có lịch trùng"""
    end_time = booking_time + timedelta(minutes=service_duration)

    customer_conflicts = Booking.query.filter(
        Booking.customerId == customer_id,
        Booking.time < end_time
    ).all()

    for c in customer_conflicts:
        c_service = Service.query.get(c.servicesId)
        c_end = c.time + timedelta(minutes=c_service.durration)
        if booking_time < c_end:
            return True
    return False


def count_employee_bookings_on_date(employee_id, booking_date):
    """Đếm số lượng booking của nhân viên trong ngày"""
    day_start = booking_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    count = Booking.query.filter(
        Booking.employeeId == employee_id,
        Booking.time >= day_start,
        Booking.time < day_end
    ).count()

    return count


def get_bookings_by_month(month, year):
    """Lấy các booking trong tháng"""
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    bookings = Booking.query.filter(
        Booking.time >= start_date,
        Booking.time < end_date
    ).all()

    return bookings