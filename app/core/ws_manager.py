from fastapi import WebSocket
from datetime import datetime


class TrackingManager:
    def __init__(self):
        # Senders watching a delivery
        # { order_id: [websocket1, websocket2] }
        self.active_connections: dict[str, list[WebSocket]] = {}

        # Latest GPS per order — so if sender connects mid-delivery
        # they immediately get current position instead of waiting
        # { order_id: {lat, lng, ...} }
        self.latest_positions: dict[str, dict] = {}

        # Messaging
        # { order_id: [websocket, ...] }
        self.chat_connections: dict[str, list[WebSocket]] = {}
        # { order_id: [{sender, message, timestamp}, ...] }
        self.chat_history: dict[str, list[dict]] = {}

    async def connect(self, order_id: str, websocket: WebSocket):
        await websocket.accept()

        if order_id not in self.active_connections:
            self.active_connections[order_id] = []
        self.active_connections[order_id].append(websocket)

        # Send current position immediately if driver already started
        if order_id in self.latest_positions:
            await websocket.send_json(self.latest_positions[order_id])

    def disconnect(self, order_id: str, websocket: WebSocket):
        if order_id in self.active_connections:
            self.active_connections[order_id].remove(websocket)
            if not self.active_connections[order_id]:
                del self.active_connections[order_id]

    async def broadcast(self, order_id: str, location: dict):
        # Store latest
        self.latest_positions[order_id] = location

        # Push to all senders watching this order
        dead = []
        for ws in self.active_connections.get(order_id, []):
            try:
                await ws.send_json(location)
            except Exception:
                dead.append(ws)

        # Clean up broken connections
        for ws in dead:
            self.active_connections[order_id].remove(ws)
    
    async def chat_connect(
        self,
        order_id: str,
        websocket: WebSocket,
        user_id: str,
        role: str,
    ):
        #await websocket.accept()

        if order_id not in self.chat_connections:
            self.chat_connections[order_id] = []
        self.chat_connections[order_id].append(websocket)

        # Send chat history so user sees previous messages in this trip
        history = self.chat_history.get(order_id, [])
        if history:
            await websocket.send_json({
                "type": "history",
                "messages": history,
            })

    def chat_disconnect(self, order_id: str, websocket: WebSocket):
        if order_id in self.chat_connections:
            try:
                self.chat_connections[order_id].remove(websocket)
            except ValueError:
                pass
            if not self.chat_connections[order_id]:
                del self.chat_connections[order_id]

    async def send_message(
        self,
        order_id: str,
        user_id: str,
        first_name: str,
        role: str,
        text: str,
    ):
        message = {
            "type": "message",
            "user_id": user_id,
            "first_name": first_name,
            "role": role,          # "sender" or "driver"
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Store in memory
        if order_id not in self.chat_history:
            self.chat_history[order_id] = []
        self.chat_history[order_id].append(message)

        # Broadcast to all connected chat participants
        dead = []
        for ws in self.chat_connections.get(order_id, []):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.chat_connections[order_id].remove(ws)

    async def close_chat(self, order_id: str):
        """
        Called when order is delivered or cancelled.
        Notifies all connected clients then clears everything.
        """
        # Tell everyone chat is closing
        for ws in self.chat_connections.get(order_id, []):
            try:
                await ws.send_json({
                    "type": "chat_closed",
                    "reason": "Delivery completed. Chat is no longer available.",
                })
                await ws.close()
            except Exception:
                pass

        # Clear everything
        self.chat_connections.pop(order_id, None)
        self.chat_history.pop(order_id, None)


    def clear(self, order_id: str):
        self.latest_positions.pop(order_id, None)
        self.active_connections.pop(order_id, None)


tracking_manager = TrackingManager()