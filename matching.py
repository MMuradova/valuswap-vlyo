"""
ValuSwap-VLYO - Data Preparation / Matching Modulu (Gün 2)
"""
from typing import List
from sqlalchemy.orm import Session

from models import Product
from cache import get_cached_match, set_cached_match


def _keyword_overlap(a: str, b: str) -> float:
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _price_closeness(price_a: float, price_b: float) -> float:
    if price_a == 0 and price_b == 0:
        return 1.0
    diff = abs(price_a - price_b)
    avg = (price_a + price_b) / 2 or 1
    ratio = diff / avg
    return max(0.0, 1.0 - ratio)


def score_products(base: Product, candidate: Product) -> float:
    category_score = 1.0 if base.category.lower() == candidate.category.lower() else 0.0
    name_score = _keyword_overlap(base.name, candidate.name)
    price_score = _price_closeness(base.price_azn, candidate.price_azn)
    return (category_score * 0.5) + (price_score * 0.35) + (name_score * 0.15)


def find_matches(db: Session, product_id: int, limit: int = 5) -> List[dict]:
    """Verilmiş məhsul üçün ən uyğun (bənzər dəyərli) digər məhsulları tapır.
    Nəticələr Redis-də keşlənir (default 60 saniyə)."""

    cached = get_cached_match(product_id)
    if cached is not None:
        return cached

    base_product = db.query(Product).filter(Product.id == product_id).first()
    if not base_product:
        return []

    candidates = (
        db.query(Product)
        .filter(Product.id != product_id, Product.is_available == 1)
        .all()
    )

    scored = []
    for c in candidates:
        s = score_products(base_product, c)
        scored.append({
            "product_id": c.id,
            "name": c.name,
            "category": c.category,
            "price_azn": c.price_azn,
            "similarity_score": round(s, 3),
            "price_diff_azn": round(abs(base_product.price_azn - c.price_azn), 2),
        })

    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    top_matches = scored[:limit]

    set_cached_match(product_id, top_matches)
    return top_matches
