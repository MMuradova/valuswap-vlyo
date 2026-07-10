"""
ValuSwap-VLYO - Pydantic Sxemləri
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from models import ProductType, TradeStatus


# --------------------------------------------------------------------------
# USER
# --------------------------------------------------------------------------
class UserCreate(BaseModel):
    telegram_id: str
    username: Optional[str] = None
    full_name: Optional[str] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    rating: float
    created_at: datetime


# --------------------------------------------------------------------------
# PRODUCT
# --------------------------------------------------------------------------
class ProductCreate(BaseModel):
    """Claude Vision-un JSON çıxışı (name/category/condition/price_azn) +
    n8n-dən gələn owner_telegram_id birbaşa buraya map olunur"""
    owner_telegram_id: str
    name: str = Field(..., max_length=256)
    category: str = Field(..., max_length=128)
    condition: Optional[str] = None
    price_azn: float = Field(ge=0)
    description: Optional[str] = None
    image_url: Optional[str] = None
    type: ProductType = ProductType.generic


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    category: str
    condition: Optional[str] = None
    price_azn: float
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_available: int
    type: ProductType
    created_at: datetime


# --------------------------------------------------------------------------
# TRADE
# --------------------------------------------------------------------------
class TradeOfferCreate(BaseModel):
    proposer_product_id: int
    target_product_id: int


class TradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    proposer_product_id: int
    target_product_id: int
    status: TradeStatus
    price_diff_azn: float
    created_at: datetime


# --------------------------------------------------------------------------
# MATCH
# --------------------------------------------------------------------------
class MatchResult(BaseModel):
    product_id: int
    name: str
    category: str
    price_azn: float
    similarity_score: float
    price_diff_azn: float