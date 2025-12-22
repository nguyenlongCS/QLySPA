# __init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Khởi tạo SQLAlchemy
db = SQLAlchemy()


def create_app():
    """Tạo và cấu hình Flask application"""
    app = Flask(__name__)

    # Cấu hình app
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///spa_booking.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_AS_ASCII'] = False

    # Khởi tạo database với app
    db.init_app(app)

    return app