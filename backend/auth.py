from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import secrets
import random

from database import get_user_by_id, get_user_by_phone, get_user_by_email
from utils import utc_now

# Security
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    # Generate a persistent key for development only
    import logging
    logger = logging.getLogger(__name__)
    SECRET_KEY = secrets.token_urlsafe(32)
    logger.warning("SECRET_KEY not set in environment. Using temporary key. This will invalidate tokens on restart!")
    logger.warning("For production, set SECRET_KEY environment variable.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 days

# Development mode flag for OTP exposure
DEV_MODE = os.environ.get('DEV_MODE', 'true').lower() == 'true'

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = utc_now() + expires_delta
    else:
        expire = utc_now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user

def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))

async def authenticate_user(phone_or_email: str, password: str):
    """Authenticate user with phone/email and password"""
    user = None
    if '@' in phone_or_email:
        user = await get_user_by_email(phone_or_email)
    else:
        user = await get_user_by_phone(phone_or_email)
    
    if not user:
        return False
    if not user.get('hashed_password'):
        return False
    if not verify_password(password, user['hashed_password']):
        return False
    return user
