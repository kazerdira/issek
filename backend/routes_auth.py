from fastapi import APIRouter, HTTPException, status, Depends, Request
from datetime import datetime, timedelta
import uuid
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

from models import (
    UserCreate, UserLogin, UserResponse, Token,
    OTPRequest, OTPVerify, User
)
from auth import (
    get_password_hash, create_access_token, authenticate_user,
    generate_otp, get_current_user
)
from database import (
    Database, get_user_by_phone, get_user_by_email,
    get_user_by_username, create_user, update_user
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate):
    """Register a new user"""
    db = Database.get_db()
    
    # Check if user already exists
    if user_data.phone_number:
        existing = await get_user_by_phone(user_data.phone_number)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
    
    if user_data.email:
        existing = await get_user_by_email(user_data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    existing = await get_user_by_username(user_data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user
    user_id = str(uuid.uuid4())
    user_dict = user_data.dict()
    
    # Hash password if provided
    if user_dict.get('password'):
        user_dict['hashed_password'] = get_password_hash(user_dict['password'])
        del user_dict['password']
    
    user_dict.update({
        'id': user_id,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'is_online': True,
        'contacts': [],
        'blocked_users': []
    })
    
    await create_user(user_dict)
    
    # Create access token
    access_token = create_access_token(data={"sub": user_id})
    
    user_response = UserResponse(
        id=user_id,
        phone_number=user_data.phone_number,
        email=user_data.email,
        username=user_data.username,
        display_name=user_data.display_name,
        bio=user_data.bio,
        avatar=user_data.avatar,
        role=user_data.role,
        is_online=True,
        created_at=datetime.utcnow()
    )
    
    return Token(access_token=access_token, user=user_response)

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, login_data: UserLogin):
    """Login with phone/email and password"""
    if not login_data.phone_number and not login_data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number or email required"
        )
    
    if not login_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password required"
        )
    
    identifier = login_data.phone_number or login_data.email
    user = await authenticate_user(identifier, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials"
        )
    
    # Update user status
    await update_user(user['id'], {'is_online': True, 'last_seen': datetime.utcnow()})
    
    # Create access token
    access_token = create_access_token(data={"sub": user['id']})
    
    user_response = UserResponse(
        id=user['id'],
        phone_number=user.get('phone_number'),
        email=user.get('email'),
        username=user['username'],
        display_name=user['display_name'],
        bio=user.get('bio'),
        avatar=user.get('avatar'),
        role=user.get('role', 'regular'),
        is_online=True,
        last_seen=user.get('last_seen'),
        created_at=user['created_at']
    )
    
    return Token(access_token=access_token, user=user_response)

@router.post("/request-otp")
@limiter.limit("3/hour")
async def request_otp(request: Request, otp_request: OTPRequest):
    """Request OTP for phone number verification"""
    db = Database.get_db()
    
    # Generate OTP
    otp_code = generate_otp()
    
    # Store OTP in database
    otp_data = {
        'phone_number': otp_request.phone_number,
        'otp': otp_code,
        'created_at': datetime.utcnow(),
        'expires_at': datetime.utcnow() + timedelta(minutes=10),
        'verified': False
    }
    
    # Delete old OTPs for this phone number
    await db.otps.delete_many({'phone_number': otp_request.phone_number})
    
    # Insert new OTP
    await db.otps.insert_one(otp_data)
    
    # In production, send OTP via SMS (Twilio, etc.)
    logger.info(f"OTP for {otp_request.phone_number}: {otp_code}")
    
    # Only expose OTP in development mode
    from auth import DEV_MODE
    response = {"message": "OTP sent successfully"}
    if DEV_MODE:
        response["otp"] = otp_code
        logger.warning("DEV_MODE: Exposing OTP in API response")
    
    return response

@router.post("/verify-otp", response_model=Token)
async def verify_otp(otp_verify: OTPVerify):
    """Verify OTP and create/login user"""
    db = Database.get_db()
    
    # Find OTP
    otp_record = await db.otps.find_one({
        'phone_number': otp_verify.phone_number,
        'otp': otp_verify.otp,
        'verified': False
    })
    
    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )
    
    # Check if OTP expired
    if otp_record['expires_at'] < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP expired"
        )
    
    # Mark OTP as verified
    await db.otps.update_one(
        {'_id': otp_record['_id']},
        {'$set': {'verified': True}}
    )
    
    # Check if user exists
    user = await get_user_by_phone(otp_verify.phone_number)
    
    if not user:
        # Create new user
        user_id = str(uuid.uuid4())
        username = f"user_{otp_verify.phone_number[-6:]}"  # Generate username from phone
        
        user_dict = {
            'id': user_id,
            'phone_number': otp_verify.phone_number,
            'username': username,
            'display_name': username,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'is_online': True,
            'role': 'regular',
            'contacts': [],
            'blocked_users': []
        }
        
        await create_user(user_dict)
        user = user_dict
    else:
        # Update existing user
        await update_user(user['id'], {'is_online': True, 'last_seen': datetime.utcnow()})
    
    # Create access token
    access_token = create_access_token(data={"sub": user['id']})
    
    user_response = UserResponse(
        id=user['id'],
        phone_number=user.get('phone_number'),
        email=user.get('email'),
        username=user['username'],
        display_name=user['display_name'],
        bio=user.get('bio'),
        avatar=user.get('avatar'),
        role=user.get('role', 'regular'),
        is_online=True,
        created_at=user['created_at']
    )
    
    return Token(access_token=access_token, user=user_response)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    return UserResponse(
        id=current_user['id'],
        phone_number=current_user.get('phone_number'),
        email=current_user.get('email'),
        username=current_user['username'],
        display_name=current_user['display_name'],
        bio=current_user.get('bio'),
        avatar=current_user.get('avatar'),
        role=current_user.get('role', 'regular'),
        is_online=current_user.get('is_online', False),
        last_seen=current_user.get('last_seen'),
        created_at=current_user['created_at']
    )

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    display_name: str = None,
    bio: str = None,
    avatar: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Update user profile"""
    update_data = {}
    
    if display_name is not None:
        update_data['display_name'] = display_name
    if bio is not None:
        update_data['bio'] = bio
    if avatar is not None:
        update_data['avatar'] = avatar
    
    if update_data:
        await update_user(current_user['id'], update_data)
        current_user.update(update_data)
    
    return UserResponse(
        id=current_user['id'],
        phone_number=current_user.get('phone_number'),
        email=current_user.get('email'),
        username=current_user['username'],
        display_name=current_user['display_name'],
        bio=current_user.get('bio'),
        avatar=current_user.get('avatar'),
        role=current_user.get('role', 'regular'),
        is_online=current_user.get('is_online', False),
        last_seen=current_user.get('last_seen'),
        created_at=current_user['created_at']
    )
