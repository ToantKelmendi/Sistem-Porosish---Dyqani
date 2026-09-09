"""Kontratat e hyrjes dhe daljes (Pydantic v2).

Validimi ndodh para se të prekim bazën: EmailStr refuzon email të pavlefshëm,
dhe kufijtë e sasisë/çmimit refuzojnë vlera absurde me 422 — kjo është pjesa e
parë e "cilësisë së të dhënave".
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=1000)
    unit_price: float = Field(gt=0)


class OrderItemOut(OrderItemCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=2, max_length=120)
    customer_email: EmailStr
    items: List[OrderItemCreate] = Field(min_length=1)


class OrderOut(BaseModel):
    id: int
    status: str
    created_at: datetime
    items: List[OrderItemOut]

    model_config = ConfigDict(from_attributes=True)
