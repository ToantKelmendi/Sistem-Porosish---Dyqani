"""Modeli i domenit të porosive.

Customer 1—N Order 1—N OrderItem. Artikujt fshihen bashkë me porosinë
(delete-orphan), sepse nuk kanë kuptim jashtë saj.

Vini re: nuk ka tabelë Product këtu. Produkti i përket domenit të inventarit
dhe referencohet vetëm me product_id — kjo është ndarja sipas domenit.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    # Emaili është identifikuesi natyror i klientit — unique parandalon dublikatat.
    email = Column(String, nullable=False, unique=True, index=True)

    orders = relationship("Order", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    # pending -> reserved | failed | returned
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="orders")
    items = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    # Referencë logjike ndaj domenit të inventarit (pa foreign key ndër-bazë).
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    # Çmimi ruhet në momentin e porosisë; ndryshimi i mëvonshëm nuk e prek historikun.
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
