from pydantic import BaseModel, Field, RootModel
from typing import List, Optional
from fastapi import WebSocket
from Manager.app.models import Order
from Manager.app.models.db import Drinks, Orders
import json, socket

class JSONList(RootModel):
    root: List[str]

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string")
            
        if not isinstance(value, List):
            raise ValueError("JSON data must be a list")
        
        if not value:
            return cls(root = [])
        
        return [str(item) for item in value]
    
class FormData(BaseModel):
    selectedDrinkIDs: JSONList = Field(default_factory = lambda: JSONList(root = []))
    selectedItemIndex: Optional[int] = None

class PydanticORM:
    @staticmethod
    def readDrinksORM(drinks: Drinks) -> dict:
        out = drinks.__dict__
        if out['options']:
            out['options'] = out['options'].split(',')
        else:
            out['options'] = []
        
        return out
    
    @staticmethod
    def readOrdersORM(orders: Orders) -> Order:
        return Order(**{
            'orderID': orders.orderID,
            'customer': orders.customer,
            'dateReceived': orders.dateReceived,
            'timeReceived': orders.timeReceived,
            'timeComplete': orders.timeComplete,
            'drinks': [PydanticORM.readDrinksORM(d) for d in (orders.drinks or [])]
        })

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_text(message)

class Utils:
    @staticmethod
    def getAddress() -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ipv4_address = s.getsockname()[0]
        finally:
            s.close()
        return ipv4_address