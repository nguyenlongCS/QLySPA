# dao/account_dao.py
"""
Data Access Object cho Account
"""
from datetime import datetime
from __init__ import db
from models import Account, Customer, Employee


def get_account_by_username(username):
    """Lấy tài khoản theo username"""
    return Account.query.filter_by(username=username).first()


def create_account(account_data, customer_id=None):
    """Tạo tài khoản mới"""
    account = Account(
        accountId=account_data['accountId'],
        username=account_data['username'],
        passwordHash=account_data['passwordHash'],
        role=account_data['role'],
        fullName=account_data.get('fullName'),
        phone=account_data.get('phone'),
        email=account_data.get('email'),
        customerId=customer_id,
        createdAt=datetime.now()
    )
    db.session.add(account)
    db.session.commit()
    return account


def update_account_password(username, new_password_hash):
    """Cập nhật mật khẩu tài khoản"""
    account = Account.query.filter_by(username=username).first()
    if account:
        account.passwordHash = new_password_hash
        db.session.commit()
        return True
    return False


def get_all_accounts():
    """Lấy tất cả tài khoản"""
    return Account.query.all()


def update_account_role(username, new_role):
    """Cập nhật role tài khoản"""
    account = Account.query.filter_by(username=username).first()
    if account:
        account.role = new_role
        db.session.commit()
        return True
    return False


def get_account_info_by_role(account):
    """Lấy thông tin account theo role với data từ account table"""
    base_info = {
        'accountId': account.accountId,
        'username': account.username,
        'role': account.role,
        'name': account.fullName,
        'phone': account.phone,
        'email': account.email,
        'createdAt': account.createdAt.isoformat()
    }
    
    if account.role == 'Customer' and account.customer and account.customer.active:
        base_info['customerId'] = account.customer.customerId
        base_info['loyaltyPoints'] = account.customer.loyaltyPoints
        base_info['membershipLevel'] = account.customer.membershipLevel
    elif account.role == 'Employee' and account.employee and account.employee.active:
        base_info['employeeId'] = account.employee.employeeId
        base_info['position'] = account.employee.position
        base_info['department'] = account.employee.department
    elif account.role == 'Cashier' and account.employee and account.employee.active:
        base_info['employeeId'] = account.employee.employeeId
        base_info['position'] = 'Thu ngân'
    
    return base_info
