from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime
import json
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load env variables
load_dotenv()

app = FastAPI(title="RealTime Chat Hub", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")
client = AsyncIOMotorClient(MONGO_URI)
db = client["chat_db"]
messages_collection = db["messages"]

class Message(BaseModel):
    client_id: str
    content: str
    timestamp: str

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        await self.broadcast(f"System: {client_id} has joined the chat.")

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

    async def add_to_history(self, message: Message):
        await messages_collection.insert_one(message.dict())

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def get():
    with open("static/wbindex.html", "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content, status_code=200)

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(client_id, websocket)
    try:
        # Send previous messages
        cursor = messages_collection.find().sort("timestamp", 1).limit(100)
        async for doc in cursor:
            await manager.send_personal_message(json.dumps(doc, default=str), client_id)

        # Handle new messages
        while True:
            data = await websocket.receive_text()
            message = Message(
                client_id=client_id,
                content=data,
                timestamp=datetime.now().isoformat()
            )
            await manager.add_to_history(message)
            await manager.broadcast(json.dumps(message.dict()))
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await manager.broadcast(f"System: {client_id} has left the chat")
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {str(e)}")

@app.get("/history", response_model=List[Message])
async def get_message_history():
    cursor = messages_collection.find().sort("timestamp", -1).limit(100)
    history = []
    async for doc in cursor:
        history.append(Message(**doc))
    history.reverse()
    return history

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {"detail": str(exc.detail), "status_code": exc.status_code}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)


# from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
# from fastapi.responses import HTMLResponse
# from fastapi.staticfiles import StaticFiles
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from typing import List, Dict
# from datetime import datetime
# import json
# import logging
# from motor.motor_asyncio import AsyncIOMotorClient
# from pymongo import MongoClient
# import os
# # import motor.motor_asyncio

# app = FastAPI(title="RealTime Chat Hub", version="1.0.0")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# app.mount("/static", StaticFiles(directory="static"), name="static")

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
# # latest
# # MONGO_URI="mongodb+srv://kalkeeshjami:6FQPsB6WflpW7GsW@chatroomcluster.jblk7g1.mongodb.net/?retryWrites=true&w=majority&appName=chatroomCluster"
# MONGO_URI = os.getenv("MONGO_URI")
# client = AsyncIOMotorClient(MONGO_URI)
# db = client["chat_db"]
# messages_collection = db["messages"]
# # Async MongoDB setup (Motor) — now commented out
# # MONGO_URL = "mongodb://localhost:27017"
# # client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
# # db = client["chat_db"]
# # messages_collection = db["messages"]

# class Message(BaseModel):
#     client_id: str
#     content: str
#     timestamp: str

# class ConnectionManager:
#     def __init__(self):
#         self.active_connections: Dict[str, WebSocket] = {}

#     async def connect(self, client_id: str, websocket: WebSocket):
#         await websocket.accept()
#         self.active_connections[client_id] = websocket
#         await self.broadcast(f"System: {client_id} has joined the chat.")

#     def disconnect(self, client_id: str):
#         self.active_connections.pop(client_id, None)

#     async def send_personal_message(self, message: str, client_id: str):
#         if client_id in self.active_connections:
#             await self.active_connections[client_id].send_text(message)

#     async def broadcast(self, message: str):
#         for connection in self.active_connections.values():
#             await connection.send_text(message)

#     def add_to_history(self, message: Message):
#         messages_collection.insert_one(message.dict())

# manager = ConnectionManager()

# @app.get("/", response_class=HTMLResponse)
# async def get():
#     with open("static/wbindex.html", "r") as file:
#         html_content = file.read()
#     return HTMLResponse(content=html_content, status_code=200)

# @app.websocket("/ws/{client_id}")
# async def websocket_endpoint(websocket: WebSocket, client_id: str):
#     await manager.connect(client_id, websocket)
#     try:
#         # Send previous messages
#         cursor = messages_collection.find().sort("timestamp", 1).limit(100)
#         for doc in cursor:
#             await manager.send_personal_message(json.dumps(doc, default=str), client_id)

#         # Handle new messages
#         while True:
#             data = await websocket.receive_text()
#             message = Message(
#                 client_id=client_id,
#                 content=data,
#                 timestamp=datetime.now().isoformat()
#             )
#             manager.add_to_history(message)
#             await manager.broadcast(json.dumps(message.dict()))
#     except WebSocketDisconnect:
#         manager.disconnect(client_id)
#         await manager.broadcast(f"System: {client_id} has left the chat")
#     except Exception as e:
#         logger.error(f"Error in WebSocket connection: {str(e)}")

# @app.get("/history", response_model=List[Message])
# async def get_message_history():
#     cursor = messages_collection.find().sort("timestamp", -1).limit(100)
#     history = [Message(**doc) for doc in reversed(list(cursor))]
#     return history

# @app.exception_handler(HTTPException)
# async def http_exception_handler(request, exc):
#     return {"detail": str(exc.detail), "status_code": exc.status_code}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=10000)
