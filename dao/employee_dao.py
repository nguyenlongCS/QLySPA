# dao/employee_dao.py
"""
Data Access Object cho Employee
"""
from __init__ import db
from models import Employee


def get_all_employees():
    """Lấy danh sách tất cả nhân viên"""
    return Employee.query.all()


def get_employee_by_id(employee_id):
    """Lấy thông tin nhân viên theo ID"""
    return Employee.query.get(employee_id)


# Cập nhật dao/employee_dao.py

def create_employee(data):
    """Tạo nhân viên mới"""
    employee = Employee(
        employeeId=data['employeeId'],
        name=data['name'],
        role=data['role'],
        phone=data.get('phone', ''),  # THÊM PHONE
        email=data.get('email', '')   # THÊM EMAIL
    )
    db.session.add(employee)
    db.session.commit()
    return employee


def update_employee(employee_id, data):
    """Cập nhật thông tin nhân viên"""
    employee = Employee.query.get(employee_id)
    if employee:
        employee.name = data.get('name', employee.name)
        employee.role = data.get('role', employee.role)
        employee.phone = data.get('phone', employee.phone)  # THÊM PHONE
        employee.email = data.get('email', employee.email)  # THÊM EMAIL
        db.session.commit()
    return employee


def delete_employee(employee_id):
    """Xóa nhân viên"""
    employee = Employee.query.get(employee_id)
    if employee:
        db.session.delete(employee)
        db.session.commit()
        return True
    return False