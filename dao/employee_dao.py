# dao/employee_dao.py
"""
Data Access Object cho Employee
"""
from __init__ import db
from models import Employee, Account


def get_all_employees():
    """Lấy danh sách tất cả nhân viên active (không bao gồm cashier)"""
    # Lấy employees active và join với account để lọc bỏ cashier
    employees = db.session.query(Employee).join(Account).filter(
        Employee.active == True,
        Account.role == 'Employee'
    ).all()
    return employees


def get_employee_by_id(employee_id):
    """Lấy thông tin nhân viên theo ID"""
    return Employee.query.filter_by(employeeId=employee_id, active=True).first()


def create_employee(data):
    """Tạo nhân viên mới"""
    employee = Employee(
        employeeId=data['employeeId'],
        position=data.get('position', 'Kỹ thuật viên'),
        department=data.get('department', 'Dịch vụ'),
        active=True
    )
    db.session.add(employee)
    db.session.commit()
    return employee


def update_employee(employee_id, data):
    """Cập nhật thông tin nhân viên - cập nhật vào account"""
    employee = Employee.query.filter_by(employeeId=employee_id, active=True).first()
    if employee and employee.account:
        account = employee.account
        if 'name' in data:
            account.fullName = data['name']
        if 'phone' in data:
            account.phone = data['phone']
        if 'email' in data:
            account.email = data['email']
        
        # Cập nhật thông tin đặc thù employee
        if 'position' in data:
            employee.position = data['position']
        if 'department' in data:
            employee.department = data['department']
            
        db.session.commit()
    return employee


def delete_employee(employee_id):
    """Soft delete nhân viên"""
    employee = Employee.query.get(employee_id)
    if employee:
        employee.active = False
        db.session.commit()
        return True
    return False
