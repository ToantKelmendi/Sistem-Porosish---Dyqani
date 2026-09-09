"""Modeli i domenit të inventarit — një entitet i vetëm, Product."""

from sqlalchemy import Column, Float, Integer, String

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    price = Column(Float, nullable=False)
    quantity_in_stock = Column(Integer, nullable=False, default=0)
