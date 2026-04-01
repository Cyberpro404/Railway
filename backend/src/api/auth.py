"""
Authentication module for API security.
Implements JWT token-based authentication and role-based access control.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# Security configuration
SECRET_KEY = "gandiva-secret-key-prod"  # Change in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


class UserRole:
    """Role-based access levels"""
    VIEWER = "viewer"      # Can view data only
    OPERATOR = "operator"  # Can acknowledge alerts, view all data
    ADMIN = "admin"        # Full access including config changes


class TokenData(BaseModel):
    """JWT token payload"""
    username: Optional[str] = None
    roles: List[str] = []
    exp: Optional[datetime] = None


class User(BaseModel):
    """User model"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    roles: List[str] = []


class UserInDB(User):
    """User with hashed password"""
    hashed_password: str


# Simple user database (replace with real database in production)
USERS_DB = {
    "admin": {
        "username": "admin",
        "full_name": "System Administrator",
        "email": "admin@railway.com",
        "hashed_password": pwd_context.hash("admin123"),  # Change in production!
        "disabled": False,
        "roles": [UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER]
    },
    "operator": {
        "username": "operator",
        "full_name": "Operations Team",
        "email": "ops@railway.com",
        "hashed_password": pwd_context.hash("operator123"),  # Change in production!
        "disabled": False,
        "roles": [UserRole.OPERATOR, UserRole.VIEWER]
    },
    "viewer": {
        "username": "viewer",
        "full_name": "View Only User",
        "email": "viewer@railway.com",
        "hashed_password": pwd_context.hash("viewer123"),  # Change in production!
        "disabled": False,
        "roles": [UserRole.VIEWER]
    }
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def get_user(username: str) -> Optional[UserInDB]:
    """Get user from database"""
    if username in USERS_DB:
        user_dict = USERS_DB[username]
        return UserInDB(**user_dict)
    return None


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate user credentials"""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Extract and verify current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        roles: List[str] = payload.get("roles", [])
        
        if username is None:
            raise credentials_exception
        
        token_data = TokenData(username=username, roles=roles)
    except JWTError:
        raise credentials_exception
    
    user = get_user(token_data.username)
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Check user is active"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_role(required_role: str):
    """Dependency factory for role-based access control"""
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if required_role not in current_user.roles and UserRole.ADMIN not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        return current_user
    return role_checker


# Role-specific dependencies
require_admin = require_role(UserRole.ADMIN)
require_operator = require_role(UserRole.OPERATOR)
require_viewer = require_role(UserRole.VIEWER)
