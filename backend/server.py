from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
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

# Create global rate limiter
limiter = Limiter(key_func=get_remote_address)

# Import database and socket manager
from database import Database
from socket_manager import socket_manager

# Import routes
from routes_auth import router as auth_router
from routes_chat import router as chat_router
from routes_users import router as users_router
from routes_media import router as media_router
from routes_friends import router as friends_router

# Create the main app
app = FastAPI(title="ChatApp API", version="1.0.0")

# Add rate limiter state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch all unhandled exceptions, log them securely, and return sanitized error responses
    to prevent information leakage in production
    """
    # Log the full error details (including stack trace) securely
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_host": request.client.host if request.client else "unknown"
        }
    )
    
    # Check if we're in development mode
    dev_mode = os.getenv('DEV_MODE', 'false').lower() == 'true'
    
    # Return sanitized error response (hide implementation details in production)
    if dev_mode:
        # In development, expose error details for debugging
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "dev_mode": True
            }
        )
    else:
        # In production, return generic error message
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal server error occurred. Please try again later.",
                "error_id": f"{request.url.path}-{id(exc)}"  # Correlation ID for support
            }
        )

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
api_router.include_router(media_router)
api_router.include_router(friends_router)

# Include the API router in the main app
app.include_router(api_router)

# Configure CORS with environment-based allowed origins
ALLOWED_ORIGINS = os.getenv(
    'CORS_ORIGINS', 
    'http://localhost:19006,http://localhost:8081,http://localhost:3000'
).split(',')

logger.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# Add SlowAPI middleware for rate limiting
app.add_middleware(SlowAPIMiddleware)

# Add GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Custom middleware to limit request body size (10MB)
@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    MAX_SIZE = 10 * 1024 * 1024  # 10MB
    
    # Check Content-Length header if present
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_SIZE:
        return JSONResponse(
            status_code=413,
            content={
                "detail": f"Request body too large. Maximum size is 10MB, got {int(content_length) / (1024*1024):.2f}MB"
            }
        )
    
    response = await call_next(request)
    return response

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
    
    # Check database health before proceeding
    if not await Database.health_check():
        logger.critical("Database health check failed during startup!")
        raise RuntimeError("Cannot start server: database is not accessible")
    
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
