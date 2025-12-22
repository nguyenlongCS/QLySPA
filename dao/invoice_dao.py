# dao/invoice_dao.py
"""
Data Access Object cho Invoice
"""
from __init__ import db
from models import Invoice, Booking


def get_all_invoices():
    """Lấy danh sách tất cả hóa đơn"""
    return Invoice.query.all()


def get_invoice_by_id(invoice_id):
    """Lấy thông tin hóa đơn theo ID"""
    return Invoice.query.get(invoice_id)


def create_invoice(invoice_data, booking_id):
    """Tạo hóa đơn mới"""
    invoice = Invoice(
        invoiceId=invoice_data['invoiceId'],
        customerId=invoice_data['customerId'],
        total=invoice_data['total'],
        vat=invoice_data['vat'],
        discount=invoice_data['discount'],
        finalTotal=invoice_data['finalTotal']
    )

    booking = Booking.query.get(booking_id)
    if booking:
        booking.invoiceId = invoice_data['invoiceId']

    db.session.add(invoice)
    db.session.commit()
    return invoice


def update_invoice(invoice_id, invoice_data):
    """Cập nhật thông tin hóa đơn"""
    invoice = Invoice.query.get(invoice_id)
    if invoice:
        invoice.total = invoice_data['total']
        invoice.discount = invoice_data['discount']
        invoice.vat = invoice_data['vat']
        invoice.finalTotal = invoice_data['finalTotal']
        db.session.commit()
    return invoice


def delete_invoice(invoice_id):
    """Xóa hóa đơn"""
    invoice = Invoice.query.get(invoice_id)
    if invoice:
        if invoice.booking:
            invoice.booking.invoiceId = None
        db.session.delete(invoice)
        db.session.commit()
        return True
    return False