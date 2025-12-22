# dao/service_dao.py
"""
Data Access Object cho Service
"""
from __init__ import db
from models import Service


def get_all_services():
    """Lấy danh sách tất cả dịch vụ"""
    return Service.query.all()


def get_service_by_id(service_id):
    """Lấy thông tin dịch vụ theo ID"""
    return Service.query.get(service_id)


def create_service(data):
    """Tạo dịch vụ mới"""
    service = Service(
        servicesId=data['servicesId'],
        name=data['name'],
        durration=int(data['durration']),
        price=float(data['price']),
        note=data.get('note', '')
    )
    db.session.add(service)
    db.session.commit()
    return service


def update_service(service_id, data):
    """Cập nhật thông tin dịch vụ"""
    service = Service.query.get(service_id)
    if service:
        if "durration" in data:
            service.durration = int(data["durration"])
        service.name = data.get('name', service.name)
        service.price = float(data.get('price', service.price))
        service.note = data.get('note', service.note)
        db.session.commit()
    return service


def delete_service(service_id):
    """Xóa dịch vụ"""
    service = Service.query.get(service_id)
    if service:
        db.session.delete(service)
        db.session.commit()
        return True
    return False