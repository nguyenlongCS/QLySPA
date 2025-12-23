# dao/service_form_dao.py
"""
Data Access Object cho ServiceForm
"""
from datetime import datetime
from __init__ import db
from models import ServiceForm


def get_all_service_forms():
    """Lấy danh sách tất cả phiếu dịch vụ"""
    return ServiceForm.query.all()


def get_service_form_by_id(form_id):
    """Lấy phiếu dịch vụ theo ID"""
    return ServiceForm.query.get(form_id)


def get_service_forms_by_employee(employee_id):
    """Lấy danh sách phiếu dịch vụ của nhân viên"""
    return ServiceForm.query.filter_by(employeeId=employee_id).all()


def get_service_forms_by_booking(booking_id):
    """Lấy phiếu dịch vụ theo booking ID"""
    return ServiceForm.query.filter_by(bookingId=booking_id).all()


def create_service_form(data):
    """Tạo phiếu dịch vụ mới"""
    service_form = ServiceForm(
        formId=data['formId'],
        bookingId=data['bookingId'],
        employeeId=data['employeeId'],
        serviceName=data['serviceName'],
        serviceDuration=int(data['serviceDuration']),
        servicePrice=float(data['servicePrice']),
        serviceNote=data.get('serviceNote', ''),
        createdAt=datetime.now()
    )
    db.session.add(service_form)
    db.session.commit()
    return service_form


def update_service_form(form_id, data):
    """Cập nhật phiếu dịch vụ"""
    service_form = ServiceForm.query.get(form_id)
    if service_form:
        service_form.serviceName = data.get('serviceName', service_form.serviceName)
        service_form.serviceDuration = int(data.get('serviceDuration', service_form.serviceDuration))
        service_form.servicePrice = float(data.get('servicePrice', service_form.servicePrice))
        service_form.serviceNote = data.get('serviceNote', service_form.serviceNote)
        db.session.commit()
    return service_form


def delete_service_form(form_id):
    """Xóa phiếu dịch vụ"""
    service_form = ServiceForm.query.get(form_id)
    if service_form:
        db.session.delete(service_form)
        db.session.commit()
        return True
    return False


def check_service_form_exists(booking_id):
    """Kiểm tra đã có phiếu dịch vụ cho booking chưa"""
    return ServiceForm.query.filter_by(bookingId=booking_id).first() is not None