"""
Stripe service for handling subscription payments.
"""
from typing import Optional
import stripe
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..config import get_settings
from ..models.user import User

settings = get_settings()

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key


def create_customer(user: User) -> str:
    """Create a Stripe customer for a user."""
    if not stripe.api_key:
        raise ValueError("Stripe is not configured")

    customer = stripe.Customer.create(
        email=user.email,
        name=user.display_name,
        metadata={"user_id": str(user.id)}
    )
    return customer.id


def create_checkout_session(
    user: User,
    plan: str,  # 'monthly' or 'yearly'
    success_url: str,
    cancel_url: str
) -> str:
    """Create a Stripe Checkout session for subscription."""
    if not stripe.api_key:
        raise ValueError("Stripe is not configured")

    # Get the price ID based on plan
    price_id = (
        settings.stripe_price_monthly if plan == "monthly"
        else settings.stripe_price_yearly
    )

    if not price_id:
        raise ValueError(f"Price ID for {plan} plan is not configured")

    # Create or get customer
    customer_id = user.stripe_customer_id
    if not customer_id:
        customer_id = create_customer(user)

    # Create checkout session
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{
            "price": price_id,
            "quantity": 1,
        }],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": str(user.id)},
        subscription_data={
            "metadata": {"user_id": str(user.id)}
        }
    )

    return session.url


def create_portal_session(customer_id: str, return_url: str) -> str:
    """Create a Stripe Customer Portal session."""
    if not stripe.api_key:
        raise ValueError("Stripe is not configured")

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


def handle_checkout_completed(session: dict, db: Session) -> None:
    """Handle successful checkout completion."""
    user_id = session.get("metadata", {}).get("user_id")
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    if not user_id:
        return

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        return

    # Update user with Stripe customer ID
    user.stripe_customer_id = customer_id

    # Get subscription details
    if subscription_id:
        subscription = stripe.Subscription.retrieve(subscription_id)
        user.subscription_status = "active"

        # Set subscription end date
        current_period_end = subscription.get("current_period_end")
        if current_period_end:
            user.subscription_ends_at = datetime.fromtimestamp(
                current_period_end, tz=timezone.utc
            )

    db.commit()


def handle_subscription_updated(subscription: dict, db: Session) -> None:
    """Handle subscription updates (renewal, cancellation, etc.)."""
    customer_id = subscription.get("customer")
    status = subscription.get("status")

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return

    # Map Stripe status to our status
    status_map = {
        "active": "active",
        "past_due": "past_due",
        "canceled": "cancelled",
        "unpaid": "past_due",
        "incomplete": "free",
        "incomplete_expired": "free",
        "trialing": "active",
    }

    user.subscription_status = status_map.get(status, "free")

    # Update end date
    current_period_end = subscription.get("current_period_end")
    if current_period_end:
        user.subscription_ends_at = datetime.fromtimestamp(
            current_period_end, tz=timezone.utc
        )

    db.commit()


def handle_subscription_deleted(subscription: dict, db: Session) -> None:
    """Handle subscription cancellation/deletion."""
    customer_id = subscription.get("customer")

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return

    user.subscription_status = "cancelled"
    db.commit()


def verify_webhook_signature(payload: bytes, signature: str) -> dict:
    """Verify webhook signature and return event."""
    if not settings.stripe_webhook_secret:
        raise ValueError("Stripe webhook secret is not configured")

    event = stripe.Webhook.construct_event(
        payload,
        signature,
        settings.stripe_webhook_secret
    )
    return event
