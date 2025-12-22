# dao/account_dao.py
"""
Data Access Object cho Account
"""
from datetime import datetime
from __init__ import db
from models import Account


def get_account_by_username(username):
    """Lấy tài khoản theo username"""
    return Account.query.filter_by(username=username).first()


def create_account(account_data, customer_id):
    """Tạo tài khoản mới"""
    account = Account(
        accountId=account_data['accountId'],
        username=account_data['username'],
        passwordHash=account_data['passwordHash'],
        role=account_data['role'],
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