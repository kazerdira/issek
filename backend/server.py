from fastapi import FastAPI, APIRouter, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import logging
from pathlib import Path
import socketio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import database and socket manager
from database import Database
from socket_manager import socket_manager

# Import routes
from routes_auth import router as auth_router, limiter as auth_limiter
from routes_chat import router as chat_router
from routes_users import router as users_router

# Create the main app
app = FastAPI(title="ChatApp API", version="1.0.0")

# Add rate limiter state and exception handler
app.state.limiter = auth_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Health check endpoint
@api_router.get("/")
async def root():
    return {"message": "ChatApp API is running", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy"}

# Include all routers
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(users_router)

# Include the API router in the main app
app.include_router(api_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Socket.IO
socket_app = socketio.ASGIApp(
    socket_manager.sio,
    other_asgi_app=app,
    socketio_path='/socket.io'
)

@app.on_event("startup")
async def startup_event():
    """Initialize database indexes on startup"""
    logger.info("Starting up ChatApp API...")
    await Database.create_indexes()
    logger.info("Database indexes created successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    logger.info("Shutting down ChatApp API...")
    await Database.close_db()
    logger.info("Database connection closed")

# Export the socket_app as the main ASGI app
app = socket_app
