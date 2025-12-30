# dao/customer_dao.py
"""
Data Access Object cho Customer
"""
from __init__ import db
from models import Customer, Account


def get_all_customers():
    """Lấy danh sách tất cả khách hàng active với thông tin từ account"""
    customers = Customer.query.filter_by(active=True).all()
    return customers


def get_customer_by_id(customer_id):
    """Lấy thông tin khách hàng theo ID"""
    return Customer.query.filter_by(customerId=customer_id, active=True).first()


def create_customer(data):
    """Tạo khách hàng mới"""
    customer = Customer(
        customerId=data['customerId'],
        loyaltyPoints=data.get('loyaltyPoints', 0),
        membershipLevel=data.get('membershipLevel', 'Basic'),
        active=True
    )
    db.session.add(customer)
    db.session.commit()
    return customer


def update_customer(customer_id, data):
    """Cập nhật thông tin khách hàng - cập nhật vào account"""
    customer = Customer.query.filter_by(customerId=customer_id, active=True).first()
    if customer and customer.account:
        account = customer.account
        if 'name' in data:
            account.fullName = data['name']
        if 'phone' in data:
            account.phone = data['phone']
        if 'email' in data:
            account.email = data['email']

        # Cập nhật thông tin đặc thù customer
        if 'loyaltyPoints' in data:
            customer.loyaltyPoints = data['loyaltyPoints']
        if 'membershipLevel' in data:
            customer.membershipLevel = data['membershipLevel']

        db.session.commit()
    return customer


def delete_customer(customer_id):
    """Soft delete khách hàng"""
    customer = Customer.query.get(customer_id)
    if customer:
        customer.active = False
        db.session.commit()
        return True
    return False