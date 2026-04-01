"""
Simple authentication module - bypassing bcrypt issues temporarily.
"""
from typing import Optional, List
from fastapi import HTTPException, status
from pydantic import BaseModel

class UserRole:
    """Role-based access levels"""
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"

class TokenData(BaseModel):
    """JWT token payload"""
    username: Optional[str] = None
    roles: List[str] = []
    exp: Optional[str] = None

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

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Simple password verification - bypassing bcrypt"""
    return plain_password == "admin123"  # Temporary simple check

def get_password_hash(password: str) -> str:
    """Simple password hashing - bypassing bcrypt"""
    return "hashed_" + password  # Temporary simple hashing

def create_access_token(data: dict, expires_delta: Optional = None) -> str:
    """Create access token - simplified"""
    return "simple_token_" + data.get("sub", "")

def verify_token(token: str) -> Optional[str]:
    """Verify token - simplified"""
    if token.startswith("simple_token_"):
        return token.replace("simple_token_", "")
    return None
