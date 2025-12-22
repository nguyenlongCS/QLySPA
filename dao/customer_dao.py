# dao/customer_dao.py
"""
Data Access Object cho Customer
"""
from __init__ import db
from models import Customer


def get_all_customers():
    """Lấy danh sách tất cả khách hàng"""
    return Customer.query.all()


def get_customer_by_id(customer_id):
    """Lấy thông tin khách hàng theo ID"""
    return Customer.query.get(customer_id)


def create_customer(data):
    """Tạo khách hàng mới"""
    customer = Customer(
        customerId=data['customerId'],
        name=data['name'],
        phone=data['phone'],
        email=data.get('email', '')
    )
    db.session.add(customer)
    db.session.commit()
    return customer


def update_customer(customer_id, data):
    """Cập nhật thông tin khách hàng"""
    customer = Customer.query.get(customer_id)
    if customer:
        customer.name = data.get('name', customer.name)
        customer.phone = data.get('phone', customer.phone)
        customer.email = data.get('email', customer.email)
        db.session.commit()
    return customer


def delete_customer(customer_id):
    """Xóa khách hàng"""
    customer = Customer.query.get(customer_id)
    if customer:
        db.session.delete(customer)
        db.session.commit()
        return True
    return False