# dao/utils.py
"""
Các hàm tiện ích và helper functions
"""
import secrets
from __init__ import db
from models import Settings


def get_setting_value(setting_id, default_value):
    """Lấy giá trị cài đặt từ database"""
    setting = Settings.query.get(setting_id)
    if setting:
        return setting.value
    return default_value


def init_default_settings():
    """Khởi tạo các cài đặt mặc định"""
    default_settings = [
        {'settingId': 'vat_rate', 'value': '10', 'description': 'Mức VAT (%)'},
        {'settingId': 'max_bookings_per_day', 'value': '5',
         'description': 'Số lượng booking tối đa mỗi nhân viên mỗi ngày'},
        {'settingId': 'max_discount', 'value': '20', 'description': 'Phần trăm giảm giá tối đa (%)'}
    ]

    for setting in default_settings:
        if not Settings.query.get(setting['settingId']):
            new_setting = Settings(
                settingId=setting['settingId'],
                value=setting['value'],
                description=setting['description']
            )
            db.session.add(new_setting)

    db.session.commit()


def generate_account_id():
    """Tạo mã tài khoản tự động"""
    return 'ACC' + secrets.token_hex(4).upper()


def generate_customer_id():
    """Tạo mã khách hàng tự động"""
    return 'C' + secrets.token_hex(4).upper()