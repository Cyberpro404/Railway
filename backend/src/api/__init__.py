# API module - FastAPI application and authentication
from .main import app, lifespan
from .auth import (
    create_access_token,
    authenticate_user,
    get_current_user,
    get_current_active_user,
    require_admin,
    require_operator,
    require_viewer,
    UserRole
)

__all__ = [
    'app',
    'lifespan',
    'create_access_token',
    'authenticate_user',
    'get_current_user',
    'get_current_active_user',
    'require_admin',
    'require_operator',
    'require_viewer',
    'UserRole'
]
