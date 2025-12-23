# admin.py
from flask import redirect, url_for, request, flash
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import Select2Widget
from werkzeug.security import check_password_hash
from wtforms import SelectField, TextAreaField, PasswordField
from wtforms.validators import DataRequired, Length, Email, Optional
from __init__ import db
from models import Customer, Service, Employee, Booking, Invoice, Account, Settings


class SecureAdminIndexView(AdminIndexView):
    """Trang chủ admin có bảo mật"""

    @expose('/')
    def index(self):
        # Kiểm tra đăng nhập admin
        admin_user = request.args.get('admin')
        if not admin_user:
            flash('Vui lòng đăng nhập admin', 'error')
            return redirect('/login')

        # Thống kê cơ bản
        stats = {
            'total_customers': Customer.query.filter_by(active=True).count(),
            'total_services': Service.query.count(),
            'total_employees': Employee.query.filter_by(active=True).count(),
            'total_bookings': Booking.query.count(),
            'pending_bookings': Booking.query.filter_by(status='Đang chờ').count(),
            'total_invoices': Invoice.query.count()
        }

        return self.render('admin/index.html', stats=stats)

    def is_accessible(self):
        # Kiểm tra quyền truy cập
        admin_user = request.args.get('admin')
        if admin_user:
            from dao import get_account_by_username
            account = get_account_by_username(admin_user)
            return account and account.role == 'Admin'
        return False


class SecureModelView(ModelView):
    """Base ModelView với bảo mật"""

    def is_accessible(self):
        admin_user = request.args.get('admin')
        if admin_user:
            from dao import get_account_by_username
            account = get_account_by_username(admin_user)
            return account and account.role == 'Admin'
        return False

    def inaccessible_callback(self, name, **kwargs):
        return redirect('/login')


class CustomerAdmin(SecureModelView):
    """Quản lý khách hàng"""

    # Cột hiển thị - sử dụng relationship với account
    column_list = ('customerId', 'account.fullName', 'account.phone', 'account.email', 'loyaltyPoints', 'membershipLevel')
    column_searchable_list = ('customerId', 'account.fullName', 'account.phone')
    column_filters = ('loyaltyPoints', 'membershipLevel', 'active')
    column_labels = {
        'customerId': 'Mã KH',
        'account.fullName': 'Tên khách hàng',
        'account.phone': 'Điện thoại',
        'account.email': 'Email',
        'loyaltyPoints': 'Điểm tích lũy',
        'membershipLevel': 'Hạng thành viên'
    }

    # Form tạo/sửa - chỉ các field trong Customer model
    form_columns = ('customerId', 'loyaltyPoints', 'membershipLevel', 'active')
    form_args = {
        'customerId': {'validators': [DataRequired()], 'render_kw': {'placeholder': 'Mã khách hàng'}},
        'loyaltyPoints': {'validators': [Optional()], 'render_kw': {'placeholder': 'Điểm tích lũy'}},
        'membershipLevel': {'validators': [Optional()], 'render_kw': {'placeholder': 'Hạng thành viên'}},
    }

    # Phân trang
    page_size = 20

    # Query chỉ lấy customer active
    def get_query(self):
        return self.session.query(self.model).filter_by(active=True)

    def create_model(self, form):
        # Tạo mã khách hàng tự động nếu chưa có
        if not form.customerId.data:
            import secrets
            form.customerId.data = 'C' + secrets.token_hex(4).upper()
        return super().create_model(form)


class ServiceAdmin(SecureModelView):
    """Quản lý dịch vụ"""

    column_list = ('servicesId', 'name', 'durration', 'price', 'note')
    column_searchable_list = ('name', 'servicesId')
    column_filters = ('price', 'durration')
    column_labels = {
        'servicesId': 'Mã dịch vụ',
        'name': 'Tên dịch vụ',
        'durration': 'Thời lượng (phút)',
        'price': 'Giá (VNĐ)',
        'note': 'Ghi chú'
    }

    # Định dạng cột
    column_formatters = {
        'price': lambda v, c, m, p: f"{m.price:,.0f}đ",
        'durration': lambda v, c, m, p: f"{m.durration} phút"
    }

    form_columns = ('servicesId', 'name', 'durration', 'price', 'note')
    form_args = {
        'servicesId': {'validators': [DataRequired()]},
        'name': {'validators': [DataRequired()]},
        'durration': {'validators': [DataRequired()]},
        'price': {'validators': [DataRequired()]},
    }

    # Widget tùy chỉnh
    form_overrides = {
        'note': TextAreaField
    }

    def create_model(self, form):
        # Tạo mã dịch vụ tự động theo format SVXXXXXXXX
        if not form.servicesId.data:
            import secrets
            form.servicesId.data = 'SV' + secrets.token_hex(4).upper()
        return super().create_model(form)


class EmployeeAdmin(SecureModelView):
    """Quản lý nhân viên"""

    # Cột hiển thị - sử dụng relationship với account
    column_list = ('employeeId', 'account.fullName', 'position', 'department', 'account.phone', 'account.email')
    column_searchable_list = ('employeeId', 'account.fullName', 'position')
    column_filters = ('position', 'department', 'active')
    column_labels = {
        'employeeId': 'Mã NV',
        'account.fullName': 'Tên nhân viên',
        'position': 'Vị trí',
        'department': 'Phòng ban',
        'account.phone': 'Điện thoại',
        'account.email': 'Email'
    }

    # Form tạo/sửa - chỉ các field trong Employee model
    form_columns = ('employeeId', 'position', 'department', 'active')
    form_args = {
        'employeeId': {'validators': [DataRequired()]},
        'position': {'validators': [DataRequired()]},
        'department': {'validators': [DataRequired()]},
    }

    # Query chỉ lấy employee active
    def get_query(self):
        return self.session.query(self.model).filter_by(active=True)

    def create_model(self, form):
        if not form.employeeId.data:
            import secrets
            form.employeeId.data = 'E' + secrets.token_hex(4).upper()
        return super().create_model(form)


class BookingAdmin(SecureModelView):
    """Quản lý đặt lịch"""

    column_list = ('bookingId', 'customer.account.fullName', 'service.name', 'employee.account.fullName', 'time', 'status')
    column_searchable_list = ('bookingId',)
    column_filters = ('status', 'time')
    column_labels = {
        'bookingId': 'Mã booking',
        'customer.account.fullName': 'Khách hàng',
        'service.name': 'Dịch vụ',
        'employee.account.fullName': 'Nhân viên',
        'time': 'Thời gian',
        'status': 'Trạng thái'
    }

    # Định dạng cột
    column_formatters = {
        'time': lambda v, c, m, p: m.time.strftime('%d/%m/%Y %H:%M') if m.time else ''
    }

    form_columns = ('bookingId', 'customerId', 'servicesId', 'employeeId', 'time', 'status')

    # Dropdown cho status
    form_overrides = {
        'status': SelectField
    }

    form_args = {
        'status': {
            'choices': [
                ('Đang chờ', 'Đang chờ'),
                ('Chấp nhận', 'Chấp nhận'),
                ('Từ chối', 'Từ chối'),
                ('Đã hủy', 'Đã hủy')
            ]
        }
    }

    # Sắp xếp mặc định
    column_default_sort = ('time', True)  # True = DESC


class InvoiceAdmin(SecureModelView):
    """Quản lý hóa đơn"""

    column_list = ('invoiceId', 'customer.account.fullName', 'total', 'discount', 'vat', 'finalTotal')
    column_searchable_list = ('invoiceId',)
    column_filters = ('finalTotal',)
    column_labels = {
        'invoiceId': 'Mã hóa đơn',
        'customer.account.fullName': 'Khách hàng',
        'total': 'Tổng tiền',
        'discount': 'Giảm giá',
        'vat': 'VAT',
        'finalTotal': 'Thành tiền'
    }

    # Định dạng tiền tệ
    column_formatters = {
        'total': lambda v, c, m, p: f"{m.total:,.0f}đ",
        'discount': lambda v, c, m, p: f"{m.discount:,.0f}đ",
        'vat': lambda v, c, m, p: f"{m.vat:,.0f}đ",
        'finalTotal': lambda v, c, m, p: f"{m.finalTotal:,.0f}đ"
    }

    # Chỉ cho phép xem và xóa, không cho phép tạo/sửa
    can_create = False
    can_edit = False


class AccountAdmin(SecureModelView):
    """Quản lý tài khoản"""

    column_list = ('accountId', 'username', 'role', 'fullName', 'phone', 'email', 'createdAt')
    column_searchable_list = ('username', 'accountId', 'fullName')
    column_filters = ('role', 'createdAt')
    column_labels = {
        'accountId': 'Mã tài khoản',
        'username': 'Tên đăng nhập',
        'role': 'Vai trò',
        'fullName': 'Họ tên',
        'phone': 'Điện thoại',
        'email': 'Email',
        'createdAt': 'Ngày tạo'
    }

    # Ẩn cột password
    column_exclude_list = ('passwordHash',)

    form_columns = ('accountId', 'username', 'role', 'fullName', 'phone', 'email')

    form_overrides = {
        'role': SelectField
    }

    form_args = {
        'role': {
            'choices': [
                ('Customer', 'Khách hàng'),
                ('Employee', 'Nhân viên'),
                ('Cashier', 'Thu ngân'),
                ('Admin', 'Quản trị')
            ]
        }
    }

    # Định dạng ngày
    column_formatters = {
        'createdAt': lambda v, c, m, p: m.createdAt.strftime('%d/%m/%Y %H:%M') if m.createdAt else ''
    }

    # Không cho phép tạo account từ admin (dùng API register)
    can_create = False


class SettingsAdmin(SecureModelView):
    """Quản lý cài đặt hệ thống"""

    column_list = ('settingId', 'value', 'description')
    column_searchable_list = ('settingId', 'description')
    column_labels = {
        'settingId': 'Mã cài đặt',
        'value': 'Giá trị',
        'description': 'Mô tả'
    }

    form_columns = ('settingId', 'value', 'description')

    # Không cho phép xóa settings
    can_delete = False


def init_admin(app):
    """Khởi tạo Flask-Admin"""

    # Tạo admin với custom index view
    admin = Admin(
        app,
        name='OU Spa Admin',
        index_view=SecureAdminIndexView()
    )

    # Thêm các model views
    admin.add_view(CustomerAdmin(Customer, db.session, name='Khách hàng'))
    admin.add_view(ServiceAdmin(Service, db.session, name='Dịch vụ'))
    admin.add_view(EmployeeAdmin(Employee, db.session, name='Nhân viên'))
    admin.add_view(BookingAdmin(Booking, db.session, name='Đặt lịch'))
    admin.add_view(InvoiceAdmin(Invoice, db.session, name='Hóa đơn'))
    admin.add_view(AccountAdmin(Account, db.session, name='Tài khoản'))
    admin.add_view(SettingsAdmin(Settings, db.session, name='Cài đặt'))

    return admin


# Tạo custom templates (tùy chọn)
def create_admin_templates():
    """Tạo templates tùy chỉnh cho admin"""

    # admin/index.html
    index_template = """
    {% extends 'admin/master.html' %}

    {% block body %}
    <div class="row">
        <div class="col-md-12">
            <h1>OU Spa - Admin Dashboard</h1>
            <p>Chào mừng đến trang quản trị OU Spa</p>
        </div>
    </div>

    <div class="row">
        <div class="col-md-3">
            <div class="panel panel-info">
                <div class="panel-heading">Khách hàng</div>
                <div class="panel-body text-center">
                    <h2>{{ stats.total_customers }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="panel panel-success">
                <div class="panel-heading">Dịch vụ</div>
                <div class="panel-body text-center">
                    <h2>{{ stats.total_services }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="panel panel-warning">
                <div class="panel-heading">Nhân viên</div>
                <div class="panel-body text-center">
                    <h2>{{ stats.total_employees }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="panel panel-primary">
                <div class="panel-heading">Booking</div>
                <div class="panel-body text-center">
                    <h2>{{ stats.total_bookings }}</h2>
                    <small>{{ stats.pending_bookings }} đang chờ</small>
                </div>
            </div>
        </div>
    </div>
    {% endblock %}
    """

    return {
        'admin/index.html': index_template
    }
