# api/tracking.py
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.order import Order, OrderStatus
from app.schemas.tracking import GPSUpdate
from app.services.tracking_service import update_driver_location, get_live_location, clear_tracking
from app.api.deps import require_verified_driver
from app.core.users import current_active_user
from app.core.ws_manager import tracking_manager
from app.database import get_db

router = APIRouter(prefix="/tracking", tags=["tracking"])

CHAT_ALLOWED_STATUSES = {
    OrderStatus.ACCEPTED,
    OrderStatus.PICKED_UP,
    OrderStatus.IN_TRANSIT,
}


@router.post("/update")
async def push_gps(
    data: GPSUpdate,
    user: User = Depends(require_verified_driver()),
):
    return await update_driver_location(data, str(user.id))


@router.get("/live/{order_id}")
async def get_tracking(order_id: str, user: User = Depends(current_active_user)):
    return await get_live_location(order_id)


@router.delete("/live/{order_id}")
async def stop_tracking(order_id: str, user: User = Depends(require_verified_driver())):
    return await clear_tracking(order_id)


@router.websocket("/ws/{order_id}")
async def tracking_websocket(websocket: WebSocket, order_id: str):
    """
    Sender connects here to receive live driver location.
    No auth on WebSocket — waybill number is the access control.
    Anyone with the order_id can watch the delivery.
    """
    await tracking_manager.connect(order_id, websocket)
    try:
        while True:
            # We don't expect messages from sender
            # but we must keep listening to detect disconnection
            await websocket.receive_text()
    except WebSocketDisconnect:
        tracking_manager.disconnect(order_id, websocket)


@router.websocket("/chat/{order_id}")
async def chat_websocket(
    websocket: WebSocket,
    order_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Sender and driver connect here to chat during active delivery.
    
    Auth via query param: /tracking/chat/{order_id}?token=JWT_TOKEN
    
    Message format sent by client:
    {"text": "I am at the park now"}
    
    Message format received by client:
    {"type": "message", "user_id": "...", "first_name": "...", 
     "role": "sender|driver", "text": "...", "timestamp": "..."}
    """
    await websocket.accept()

    token = websocket.query_params.get("token")
    if not token:
        await websocket.send_json({"type": "error", "message": "Missing token"})
        await websocket.close(code=4001, reason="Missing token")
        return

    try:
        from jose import jwt, JWTError
        from app.config import get_settings
        settings = get_settings()

        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            audience="fastapi-users:auth",
        )
        user_id = payload.get("sub")
        if not user_id:
            await websocket.send_json({"type": "error", "message": "Invalid token"})
            await websocket.close(code=4001, reason="Invalid token")
            return

    except Exception as e:
        print(f"[CHAT WS] Token decode failed: {e}")
        await websocket.send_json({"type": "error", "message": "Invalid token"})
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Fetch user from DB
    import uuid
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        await websocket.close(code=4001, reason="Invalid user ID")
        return

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        await websocket.send_json({"type": "error", "message": "User not found"})
        await websocket.close(code=4001, reason="User not found")
        return

    print(f"[CHAT WS] User authenticated: {user.email} role={user.role}")

    # Fetch order
    try:
        oid = uuid.UUID(order_id)
    except ValueError:
        await websocket.send_json({"type": "error", "message": "Invalid order ID"})
        await websocket.close(code=4004, reason="Invalid order ID")
        return

    result = await db.execute(select(Order).where(Order.id == oid))
    order = result.scalar_one_or_none()

    if not order:
        await websocket.send_json({"type": "error", "message": "Order not found"})
        await websocket.close(code=4004, reason="Order not found")
        return

    print(f"[CHAT WS] Order found: {order.waybill_number} status={order.status}")

    # Check order is active
    if order.status not in CHAT_ALLOWED_STATUSES:
        await websocket.send_json({
            "type": "chat_closed",
            "reason": f"Chat not available. Order status is {order.status.value}"
        })
        await websocket.close(code=4003, reason="Order not active")
        return

    # Check authorisation
    from app.models.user import UserRole
    is_sender = order.sender_id == uid
    is_driver = order.driver_id == uid

    if not is_sender and not is_driver and user.role != UserRole.ADMIN:
        await websocket.send_json({"type": "error", "message": "Not authorised for this order"})
        await websocket.close(code=4003, reason="Not authorised")
        return

    print(f"[CHAT WS] All checks passed — connecting to chat room {order_id}")

    # Connect to chat room
    await tracking_manager.chat_connect(
        order_id=str(oid),
        websocket=websocket,
        user_id=str(user.id),
        role=user.role.value,
    )

    try:
        while True:
            data = await websocket.receive_json()
            text = data.get("text", "").strip()

            if not text:
                continue

            if len(text) > 500:
                await websocket.send_json({
                    "type": "error",
                    "message": "Message too long. Max 500 characters."
                })
                continue

            # Re-check order is still active
            await db.refresh(order)
            if order.status not in CHAT_ALLOWED_STATUSES:
                await tracking_manager.close_chat(str(oid))
                break

            await tracking_manager.send_message(
                order_id=str(oid),
                user_id=str(user.id),
                first_name=user.first_name,
                role=user.role.value,
                text=text,
            )

    except WebSocketDisconnect:
        print(f"[CHAT WS] Client disconnected: {user.email}")
        tracking_manager.chat_disconnect(str(oid), websocket)
    except Exception as e:
        print(f"[CHAT WS] Error: {e}")
        tracking_manager.chat_disconnect(str(oid), websocket)
