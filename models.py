"""
ValuSwap-VLYO - OOP Modelləri
User, Product (baza class) -> Electronics / Clothing (alt-classlar), Trade
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
)
from sqlalchemy.orm import relationship

from database import Base


# --------------------------------------------------------------------------
# USER
# --------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String(64), unique=True, index=True, nullable=False)
    username = Column(String(128), nullable=True)
    full_name = Column(String(128), nullable=True)
    rating = Column(Float, default=5.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="owner")

    def __repr__(self):
        return f"<User id={self.id} username={self.username}>"


# --------------------------------------------------------------------------
# PRODUCT (baza class) + Electronics / Clothing (alt-classlar)
# Single Table Inheritance: bütün məhsul növləri eyni cədvəldə saxlanılır,
# `type` sütunu ilə fərqləndirilir.
# --------------------------------------------------------------------------
class ProductType(str, enum.Enum):
    generic = "product"
    electronics = "electronics"
    clothing = "clothing"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String(256), nullable=False)
    category = Column(String(128), nullable=False)
    condition = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)

    price_azn = Column(Float, nullable=False, default=0.0)

    image_url = Column(String(512), nullable=True)
    is_available = Column(Integer, default=1)  # 1=aktiv, 0=dəyişilib/deaktiv
    created_at = Column(DateTime, default=datetime.utcnow)

    type = Column(Enum(ProductType), default=ProductType.generic)

    owner = relationship("User", back_populates="products")

    __mapper_args__ = {
        "polymorphic_identity": ProductType.generic,
        "polymorphic_on": type,
    }

    def similarity_key(self) -> str:
        cond = self.condition or ""
        return f"{self.category} {self.name} {cond}".lower()

    def __repr__(self):
        return f"<Product id={self.id} name={self.name} price={self.price_azn}>"


class Electronics(Product):
    __mapper_args__ = {"polymorphic_identity": ProductType.electronics}

    def estimated_lifespan_years(self) -> int:
        return 5


class Clothing(Product):
    __mapper_args__ = {"polymorphic_identity": ProductType.clothing}

    def size_hint(self) -> str:
        return "Ölçü təsvirdə qeyd olunmalıdır"


# --------------------------------------------------------------------------
# TRADE (dəyişmə təklifi) - state machine
# --------------------------------------------------------------------------
class TradeStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    completed = "completed"


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)

    proposer_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    target_product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    status = Column(Enum(TradeStatus), default=TradeStatus.pending)
    price_diff_azn = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    proposer_product = relationship("Product", foreign_keys=[proposer_product_id])
    target_product = relationship("Product", foreign_keys=[target_product_id])

    def accept(self):
        self.status = TradeStatus.accepted

    def reject(self):
        self.status = TradeStatus.rejected

    def complete(self):
        self.status = TradeStatus.completed
        self.proposer_product.is_available = 0
        self.target_product.is_available = 0

    def __repr__(self):
        return f"<Trade id={self.id} status={self.status}>"