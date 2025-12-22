# dao/settings_dao.py
"""
Data Access Object cho Settings
"""
from __init__ import db
from models import Settings


def get_all_settings():
    """Lấy tất cả cài đặt"""
    return Settings.query.all()


def get_setting_by_id(setting_id):
    """Lấy cài đặt theo ID"""
    return Settings.query.get(setting_id)


def update_setting(setting_id, new_value):
    """Cập nhật giá trị cài đặt"""
    setting = Settings.query.get(setting_id)
    if setting:
        setting.value = new_value
        db.session.commit()
        return True
    return False