from pydantic import BaseModel, Field, RootModel
from typing import List, Optional
from fastapi import WebSocket, WebSocketDisconnect
import json

class JSONList(RootModel):
    root: List[int]

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
        
        return [int(item) for item in value]
    
class FormData(BaseModel):
    selectedDrinkIDs: JSONList = Field(default_factory = lambda: JSONList(root = []))
    selectedItemIndex: Optional[int] = None

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