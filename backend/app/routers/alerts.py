"""
Alerts router for managing price watch alerts and notifications.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from decimal import Decimal

from ..database import get_db
from .auth import get_current_user, require_premium
from ..models import Alert, Notification, Product, User

router = APIRouter(prefix="/alerts", tags=["alerts"])


# Schemas
class AlertCreate(BaseModel):
    product_id: int
    alert_type: str = "price_drop"  # 'price_drop', 'special', 'threshold'
    threshold_price: Optional[float] = None
    notify_any_drop: bool = True
    notify_special: bool = True


class AlertUpdate(BaseModel):
    threshold_price: Optional[float] = None
    notify_any_drop: Optional[bool] = None
    notify_special: Optional[bool] = None
    is_active: Optional[bool] = None


class AlertResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_brand: Optional[str]
    alert_type: str
    threshold_price: Optional[float]
    notify_any_drop: bool
    notify_special: bool
    is_active: bool
    last_price_seen: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    message: Optional[str]
    data: Optional[dict]
    read_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# Alert Endpoints
@router.get("", response_model=list[AlertResponse])
async def get_my_alerts(
    active_only: bool = Query(True, description="Only return active alerts"),
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db)
):
    """Get all alerts for the current user. Premium feature."""
    query = db.query(Alert).filter(Alert.user_id == current_user.id)

    if active_only:
        query = query.filter(Alert.is_active == True)

    alerts = query.options(joinedload(Alert.product)).order_by(desc(Alert.created_at)).all()

    return [
        AlertResponse(
            id=alert.id,
            product_id=alert.product_id,
            product_name=alert.product.name,
            product_brand=alert.product.brand,
            alert_type=alert.alert_type,
            threshold_price=float(alert.threshold_price) if alert.threshold_price else None,
            notify_any_drop=alert.notify_any_drop,
            notify_special=alert.notify_special,
            is_active=alert.is_active,
            last_price_seen=float(alert.last_price_seen) if alert.last_price_seen else None,
            created_at=alert.created_at
        )
        for alert in alerts
    ]


@router.post("", response_model=AlertResponse)
async def create_alert(
    alert_data: AlertCreate,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db)
):
    """Create a new price alert for a product. Premium feature."""
    # Check if product exists
    product = db.query(Product).filter(Product.id == alert_data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if alert already exists for this product
    existing = db.query(Alert).filter(
        Alert.user_id == current_user.id,
        Alert.product_id == alert_data.product_id,
        Alert.is_active == True
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Alert already exists for this product")

    # Create alert
    alert = Alert(
        user_id=current_user.id,
        product_id=alert_data.product_id,
        alert_type=alert_data.alert_type,
        threshold_price=Decimal(str(alert_data.threshold_price)) if alert_data.threshold_price else None,
        notify_any_drop=alert_data.notify_any_drop,
        notify_special=alert_data.notify_special
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return AlertResponse(
        id=alert.id,
        product_id=alert.product_id,
        product_name=product.name,
        product_brand=product.brand,
        alert_type=alert.alert_type,
        threshold_price=float(alert.threshold_price) if alert.threshold_price else None,
        notify_any_drop=alert.notify_any_drop,
        notify_special=alert.notify_special,
        is_active=alert.is_active,
        last_price_seen=None,
        created_at=alert.created_at
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db)
):
    """Get a specific alert."""
    alert = db.query(Alert).options(joinedload(Alert.product)).filter(
        Alert.id == alert_id,
        Alert.user_id == current_user.id
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return AlertResponse(
        id=alert.id,
        product_id=alert.product_id,
        product_name=alert.product.name,
        product_brand=alert.product.brand,
        alert_type=alert.alert_type,
        threshold_price=float(alert.threshold_price) if alert.threshold_price else None,
        notify_any_drop=alert.notify_any_drop,
        notify_special=alert.notify_special,
        is_active=alert.is_active,
        last_price_seen=float(alert.last_price_seen) if alert.last_price_seen else None,
        created_at=alert.created_at
    )


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    alert_data: AlertUpdate,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db)
):
    """Update an alert's settings."""
    alert = db.query(Alert).options(joinedload(Alert.product)).filter(
        Alert.id == alert_id,
        Alert.user_id == current_user.id
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Update fields
    if alert_data.threshold_price is not None:
        alert.threshold_price = Decimal(str(alert_data.threshold_price))
    if alert_data.notify_any_drop is not None:
        alert.notify_any_drop = alert_data.notify_any_drop
    if alert_data.notify_special is not None:
        alert.notify_special = alert_data.notify_special
    if alert_data.is_active is not None:
        alert.is_active = alert_data.is_active

    db.commit()
    db.refresh(alert)

    return AlertResponse(
        id=alert.id,
        product_id=alert.product_id,
        product_name=alert.product.name,
        product_brand=alert.product.brand,
        alert_type=alert.alert_type,
        threshold_price=float(alert.threshold_price) if alert.threshold_price else None,
        notify_any_drop=alert.notify_any_drop,
        notify_special=alert.notify_special,
        is_active=alert.is_active,
        last_price_seen=float(alert.last_price_seen) if alert.last_price_seen else None,
        created_at=alert.created_at
    )


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db)
):
    """Delete an alert."""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == current_user.id
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    db.delete(alert)
    db.commit()

    return {"status": "deleted"}


# Quick Watch Endpoint (simplified alert creation)
@router.post("/watch/{product_id}")
async def quick_watch_product(
    product_id: int,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db)
):
    """Quick watch a product for any price drops. Premium feature."""
    # Check if product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if already watching
    existing = db.query(Alert).filter(
        Alert.user_id == current_user.id,
        Alert.product_id == product_id,
        Alert.is_active == True
    ).first()

    if existing:
        # Toggle off - deactivate
        existing.is_active = False
        db.commit()
        return {"watching": False, "product_id": product_id}

    # Create new watch
    alert = Alert(
        user_id=current_user.id,
        product_id=product_id,
        alert_type="price_drop",
        notify_any_drop=True,
        notify_special=True
    )

    db.add(alert)
    db.commit()

    return {"watching": True, "product_id": product_id, "alert_id": alert.id}


@router.get("/watch/{product_id}")
async def check_watch_status(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if a product is being watched."""
    alert = db.query(Alert).filter(
        Alert.user_id == current_user.id,
        Alert.product_id == product_id,
        Alert.is_active == True
    ).first()

    return {"watching": alert is not None, "alert_id": alert.id if alert else None}


# Notification Endpoints
@router.get("/notifications", response_model=list[NotificationResponse])
async def get_notifications(
    limit: int = Query(20, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notifications for the current user."""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.read_at == None)

    notifications = query.order_by(desc(Notification.created_at)).limit(limit).all()

    return [
        NotificationResponse(
            id=n.id,
            type=n.type,
            title=n.title,
            message=n.message,
            data=n.data,
            read_at=n.read_at,
            created_at=n.created_at
        )
        for n in notifications
    ]


@router.get("/notifications/count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get count of unread notifications."""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.read_at == None
    ).count()

    return {"unread_count": count}


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.read_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "read"}


@router.post("/notifications/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.read_at == None
    ).update({"read_at": datetime.now(timezone.utc)})

    db.commit()

    return {"status": "all_read"}
