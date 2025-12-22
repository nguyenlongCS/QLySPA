# models.py
from datetime import datetime
from __init__ import db


class Settings(db.Model):
    """Model cho bảng cài đặt hệ thống"""
    __tablename__ = 'settings'
    settingId = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))


class Account(db.Model):
    """Model cho bảng tài khoản"""
    __tablename__ = 'accounts'
    accountId = db.Column(db.String(50), primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    passwordHash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='Customer')  # Customer, Employee, Admin
    customerId = db.Column(db.String(50), db.ForeignKey('customers.customerId'))
    employeeId = db.Column(db.String(50), db.ForeignKey('employees.employeeId'))
    createdAt = db.Column(db.DateTime, default=datetime.now)

    customer = db.relationship('Customer', backref='account', uselist=False, lazy=True)
    employee = db.relationship('Employee', backref='account', uselist=False, lazy=True)


class Customer(db.Model):
    """Model cho bảng khách hàng"""
    __tablename__ = 'customers'
    customerId = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100))
    bookings = db.relationship('Booking', backref='customer', lazy=True)


class Service(db.Model):
    """Model cho bảng dịch vụ"""
    __tablename__ = 'services'
    servicesId = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    durration = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(200))
    bookings = db.relationship('Booking', backref='service', lazy=True)


class Employee(db.Model):
    """Model cho bảng nhân viên"""
    __tablename__ = 'employees'
    employeeId = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    bookings = db.relationship('Booking', backref='employee', lazy=True)


class Invoice(db.Model):
    """Model cho bảng hóa đơn"""
    __tablename__ = 'invoices'
    invoiceId = db.Column(db.String(50), primary_key=True)
    customerId = db.Column(db.String(50), db.ForeignKey('customers.customerId'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    vat = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0)
    finalTotal = db.Column(db.Float, nullable=False)
    customer = db.relationship('Customer', backref='invoices', lazy=True)
    booking = db.relationship('Booking', backref='invoice', uselist=False, lazy=True)


class Booking(db.Model):
    """Model cho bảng đặt lịch"""
    __tablename__ = 'bookings'
    bookingId = db.Column(db.String(50), primary_key=True)
    time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='Đã xác nhận')
    customerId = db.Column(db.String(50), db.ForeignKey('customers.customerId'), nullable=False)
    servicesId = db.Column(db.String(50), db.ForeignKey('services.servicesId'), nullable=False)
    employeeId = db.Column(db.String(50), db.ForeignKey('employees.employeeId'), nullable=False)
    invoiceId = db.Column(db.String(50), db.ForeignKey('invoices.invoiceId'))