"""
ValuSwap-VLYO - FastAPI Backend
n8n (Telegram) və Gradio bu API-yə qoşulur.

İşə salmaq:
    uvicorn app.main:app --reload --port 8000

Sənədləşmə (Swagger):
    http://localhost:8000/docs
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import get_db, init_db
from models import User, Product, Trade, TradeStatus
import schemas
from matching import find_matches
from cache import invalidate_match_cache

app = FastAPI(
    title="ValuSwap-VLYO API",
    description="Dəyərə əsaslanan barter platforması üçün backend",
    version="1.0.0",
)

# CORS: Swagger UI, Gradio/Streamlit UI və brauzerdən gələn sorğulara icazə
# MVP mərhələsində hamısına açıq saxlanılır; production-da domenləri məhdudlaşdır
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def health_check():
    return {"status": "ok", "service": "ValuSwap-VLYO API"}


# --------------------------------------------------------------------------
# USERS
# --------------------------------------------------------------------------
def get_or_create_user(db: Session, telegram_id: str, username: str | None = None,
                        full_name: str | None = None) -> User:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if user:
        return user
    user = User(telegram_id=telegram_id, username=username, full_name=full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/users", response_model=schemas.UserOut)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    return get_or_create_user(db, payload.telegram_id, payload.username, payload.full_name)


# --------------------------------------------------------------------------
# PRODUCTS
# --------------------------------------------------------------------------
@app.post("/products", response_model=schemas.ProductOut)
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db)):
    """
    n8n Claude Vision node-undan gələn JSON (name/category/condition/price_azn)
    birbaşa bu endpoint-ə göndərilir. owner_telegram_id Telegram Trigger-dən gəlir.
    """
    owner = get_or_create_user(db, payload.owner_telegram_id)

    product = Product(
        owner_id=owner.id,
        name=payload.name,
        category=payload.category,
        condition=payload.condition,
        price_azn=payload.price_azn,
        description=payload.description,
        image_url=payload.image_url,
        type=payload.type,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.get("/products", response_model=list[schemas.ProductOut])
def list_products(category: str | None = None, available_only: bool = True,
                   db: Session = Depends(get_db)):
    query = db.query(Product)
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    if available_only:
        query = query.filter(Product.is_available == 1)
    return query.order_by(Product.created_at.desc()).all()


@app.get("/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Məhsul tapılmadı")
    return product


# --------------------------------------------------------------------------
# MATCH (Gün 2)
# --------------------------------------------------------------------------
@app.get("/match/{product_id}", response_model=list[schemas.MatchResult])
def match_product(product_id: int, limit: int = 5, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Məhsul tapılmadı")
    return find_matches(db, product_id, limit=limit)


# --------------------------------------------------------------------------
# TRADE OFFERS
# --------------------------------------------------------------------------
@app.post("/trade-offer", response_model=schemas.TradeOut)
def create_trade_offer(payload: schemas.TradeOfferCreate, db: Session = Depends(get_db)):
    proposer = db.query(Product).filter(Product.id == payload.proposer_product_id).first()
    target = db.query(Product).filter(Product.id == payload.target_product_id).first()

    if not proposer or not target:
        raise HTTPException(status_code=404, detail="Məhsullardan biri tapılmadı")
    if proposer.is_available == 0 or target.is_available == 0:
        raise HTTPException(status_code=400, detail="Məhsullardan biri artıq mövcud deyil")

    trade = Trade(
        proposer_product_id=proposer.id,
        target_product_id=target.id,
        status=TradeStatus.pending,
        price_diff_azn=abs(proposer.price_azn - target.price_azn),
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


@app.post("/trade-offer/{trade_id}/accept", response_model=schemas.TradeOut)
def accept_trade(trade_id: int, db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Təklif tapılmadı")
    trade.accept()
    db.commit()
    db.refresh(trade)
    return trade


@app.post("/trade-offer/{trade_id}/complete", response_model=schemas.TradeOut)
def complete_trade(trade_id: int, db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Təklif tapılmadı")
    trade.complete()
    db.commit()
    db.refresh(trade)

    # Məhsullar artıq mövcud olmadığı üçün onların keşini təmizlə
    invalidate_match_cache(trade.proposer_product_id)
    invalidate_match_cache(trade.target_product_id)
    return trade