from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Price, StoreProduct, Product, Store, User, PriceVerification
from app.schemas.price import PriceSubmission, Price as PriceSchema

router = APIRouter(prefix="/submit", tags=["submissions"])


@router.post("/price", response_model=PriceSchema)
def submit_price(
    submission: PriceSubmission,
    user_id: int | None = None,  # Optional - can be anonymous
    db: Session = Depends(get_db)
):
    """Submit a price for a product at a store."""
    # Verify product and store exist
    product = db.query(Product).filter(Product.id == submission.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    store = db.query(Store).filter(Store.id == submission.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    # Get or create store product
    store_product = db.query(StoreProduct).filter(
        StoreProduct.product_id == submission.product_id,
        StoreProduct.store_id == submission.store_id
    ).first()

    if not store_product:
        store_product = StoreProduct(
            product_id=submission.product_id,
            store_id=submission.store_id,
            store_product_name=product.name
        )
        db.add(store_product)
        db.commit()
        db.refresh(store_product)

    # Create price entry
    new_price = Price(
        store_product_id=store_product.id,
        price=submission.price,
        was_price=submission.was_price,
        is_special=submission.is_special,
        special_type=submission.special_type,
        source="user",
        source_user_id=user_id
    )

    db.add(new_price)

    # Update user stats if logged in
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.submissions_count += 1
            user.reputation_score += 1  # Basic reputation for submission

    db.commit()
    db.refresh(new_price)

    return new_price


@router.post("/verify/{price_id}")
def verify_price(
    price_id: int,
    is_correct: bool,
    user_id: int | None = None,
    db: Session = Depends(get_db)
):
    """Verify a submitted price (upvote/downvote)."""
    price = db.query(Price).filter(Price.id == price_id).first()
    if not price:
        raise HTTPException(status_code=404, detail="Price not found")

    # Check if user already verified this price
    if user_id:
        existing = db.query(PriceVerification).filter(
            PriceVerification.price_id == price_id,
            PriceVerification.user_id == user_id
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="Already verified this price")

    # Create verification
    verification = PriceVerification(
        price_id=price_id,
        user_id=user_id,
        is_correct=is_correct
    )
    db.add(verification)

    # Update price verified count
    if is_correct:
        price.verified_count += 1
    else:
        price.verified_count -= 1

    # Update submitter reputation
    if price.source_user_id:
        submitter = db.query(User).filter(User.id == price.source_user_id).first()
        if submitter:
            if is_correct:
                submitter.reputation_score += 2
            else:
                submitter.reputation_score -= 1

    db.commit()

    return {"message": "Verification recorded", "new_verified_count": price.verified_count}


@router.get("/pending")
def get_pending_verifications(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get prices that need verification (low verified_count)."""
    prices = db.query(Price, StoreProduct, Product, Store).join(
        StoreProduct, Price.store_product_id == StoreProduct.id
    ).join(
        Product, StoreProduct.product_id == Product.id
    ).join(
        Store, StoreProduct.store_id == Store.id
    ).filter(
        Price.source == "user",
        Price.verified_count < 3  # Needs more verification
    ).order_by(Price.recorded_at.desc()).limit(limit).all()

    return [
        {
            "price_id": price.id,
            "product_name": product.name,
            "store_name": store.name,
            "price": float(price.price),
            "is_special": price.is_special,
            "verified_count": price.verified_count,
            "submitted_at": price.recorded_at
        }
        for price, sp, product, store in prices
    ]
