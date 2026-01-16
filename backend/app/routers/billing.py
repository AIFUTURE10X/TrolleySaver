"""
Billing router for Stripe subscription management.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..config import get_settings
from .auth import get_current_user
from ..services import stripe_service
from ..models.user import User

router = APIRouter(prefix="/billing", tags=["billing"])
settings = get_settings()


class CheckoutRequest(BaseModel):
    plan: str  # 'monthly' or 'yearly'


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


@router.post("/create-checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a Stripe Checkout session for subscription."""
    if request.plan not in ["monthly", "yearly"]:
        raise HTTPException(status_code=400, detail="Invalid plan. Must be 'monthly' or 'yearly'")

    # Check if Stripe is configured
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=503,
            detail="Payment processing is not configured. Please try again later."
        )

    try:
        success_url = f"{settings.frontend_url}/pricing?success=true"
        cancel_url = f"{settings.frontend_url}/pricing?cancelled=true"

        checkout_url = stripe_service.create_checkout_session(
            user=current_user,
            plan=request.plan,
            success_url=success_url,
            cancel_url=cancel_url
        )

        # Update user's stripe_customer_id if it was just created
        if not current_user.stripe_customer_id:
            db.refresh(current_user)

        return CheckoutResponse(checkout_url=checkout_url)

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        print(f"Checkout error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/customer-portal", response_model=PortalResponse)
async def create_customer_portal(
    current_user: User = Depends(get_current_user)
):
    """Create a Stripe Customer Portal session for subscription management."""
    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No subscription found. Please subscribe first."
        )

    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=503,
            detail="Payment processing is not configured."
        )

    try:
        return_url = f"{settings.frontend_url}/pricing"
        portal_url = stripe_service.create_portal_session(
            customer_id=current_user.stripe_customer_id,
            return_url=return_url
        )
        return PortalResponse(portal_url=portal_url)

    except Exception as e:
        print(f"Portal error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create portal session")


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db)
):
    """Handle Stripe webhook events."""
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook not configured")

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    payload = await request.body()

    try:
        event = stripe_service.verify_webhook_signature(payload, stripe_signature)
    except Exception as e:
        print(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})

    try:
        if event_type == "checkout.session.completed":
            stripe_service.handle_checkout_completed(data, db)

        elif event_type == "customer.subscription.updated":
            stripe_service.handle_subscription_updated(data, db)

        elif event_type == "customer.subscription.deleted":
            stripe_service.handle_subscription_deleted(data, db)

        elif event_type == "invoice.payment_succeeded":
            # Subscription renewed successfully
            subscription_id = data.get("subscription")
            if subscription_id:
                import stripe
                subscription = stripe.Subscription.retrieve(subscription_id)
                stripe_service.handle_subscription_updated(subscription, db)

        elif event_type == "invoice.payment_failed":
            # Payment failed - update status
            subscription_id = data.get("subscription")
            if subscription_id:
                import stripe
                subscription = stripe.Subscription.retrieve(subscription_id)
                stripe_service.handle_subscription_updated(subscription, db)

    except Exception as e:
        print(f"Error handling webhook {event_type}: {e}")
        # Don't fail the webhook, just log the error
        pass

    return {"status": "ok"}


@router.get("/subscription-status")
async def get_subscription_status(
    current_user: User = Depends(get_current_user)
):
    """Get current user's subscription status."""
    return {
        "status": current_user.subscription_status,
        "ends_at": current_user.subscription_ends_at.isoformat() if current_user.subscription_ends_at else None,
        "is_premium": current_user.subscription_status == "active"
    }
