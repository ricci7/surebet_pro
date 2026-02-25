from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    plan = db.Column(db.String(50), default="free")
    daily_limit = db.Column(db.Integer, default=5)


class Calculation(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Guarda odds como texto simples: "2.10,1.95,3.40"
    odds = db.Column(db.String(200), nullable=False)

    investment = db.Column(db.Float, nullable=False)
    roi = db.Column(db.Float, nullable=False)
    profit = db.Column(db.Float, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)