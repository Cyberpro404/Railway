"""
Gandiva Error Handling Module

Defines a hierarchy of custom exceptions for the Gandiva application.
"""
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, TypeVar, cast

from fastapi import HTTPException, status
from pydantic import BaseModel

T = TypeVar('T', bound='GandivaError')

class GandivaError(Exception):
    """Base exception for all Gandiva application errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "internal_error",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """Initialize Gandiva error.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            status_code: HTTP status code
            details: Additional error details
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON responses."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
        }

    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=self.status_code,
            detail=self.to_dict()
        )

    @classmethod
    def from_exception(
        cls: Type[T],
        exc: Exception,
        message: Optional[str] = None,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        **details: Any
    ) -> T:
        """Create a GandivaError from another exception."""
        return cls(
            message=message or str(exc),
            code=code or "internal_error",
            status_code=status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            cause=exc
        )


class GandivaConfigError(GandivaError):
    """Raised when there is a configuration error."""
    def __init__(self, message: str, **details: Any):
        super().__init__(
            message=message,
            code="config_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class GandivaValidationError(GandivaError):
    """Raised when data validation fails."""
    def __init__(self, message: str, errors: Optional[list] = None, **details: Any):
        details = details or {}
        if errors:
            details["errors"] = errors
        super().__init__(
            message=message,
            code="validation_error",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class SensorError(GandivaError):
    """Raised when there is an error communicating with the sensor."""
    def __init__(self, message: str, **details: Any):
        super().__init__(
            message=message,
            code="sensor_error",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class ModelError(GandivaError):
    """Raised when there is an error with the ML model."""
    def __init__(self, message: str, **details: Any):
        super().__init__(
            message=message,
            code="model_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class DatabaseError(GandivaError):
    """Raised when there is a database error."""
    def __init__(self, message: str, **details: Any):
        super().__init__(
            message=message,
            code="database_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class APIError(GandivaError):
    """Base class for API-related errors."""
    def __init__(
        self,
        message: str,
        code: str = "api_error",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        **details: Any
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details
        )


class NotFoundError(APIError):
    """Raised when a requested resource is not found."""
    def __init__(self, resource: str, resource_id: Any, **details: Any):
        super().__init__(
            message=f"{resource} with id {resource_id} not found",
            code="not_found",
            status_code=status.HTTP_404_NOT_FOUND,
            resource=resource,
            resource_id=resource_id,
            **details
        )


def error_handler(
    error_class: Type[GandivaError] = GandivaError,
    message: Optional[str] = None,
    code: Optional[str] = None,
    status_code: Optional[int] = None,
    **default_details: Any
):
    """Decorator for consistent error handling in API endpoints.
    
    Args:
        error_class: The error class to use for wrapping exceptions
        message: Default error message (can use {exception} placeholder)
        code: Default error code
        status_code: Default HTTP status code
        **default_details: Default details to include in the error
    
    Example:
        @router.get("/items/{item_id}")
        @error_handler(APIError, "Failed to get item {item_id}", "item_fetch_error")
        async def get_item(item_id: str):
            item = await get_item_from_db(item_id)
            if not item:
                raise NotFoundError("Item", item_id)
            return item
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except GandivaError as e:
                # Re-raise GandivaErrors as-is
                raise e
            except HTTPException as e:
                # Re-raise FastAPI HTTPExceptions as-is
                raise e
            except Exception as e:
                # Format the error message with the exception details
                error_message = message or str(e)
                if "{exception}" in error_message:
                    error_message = error_message.format(exception=str(e))
                
                # Create and raise the error
                raise error_class(
                    message=error_message,
                    code=code or "internal_error",
                    status_code=status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
                    **default_details
                ) from e
        return wrapper
    return decorator


def handle_errors():
    """FastAPI dependency that can be used to handle errors in a dependency.
    
    Example:
        @router.get("/some-route")
        async def some_endpoint(deps = Depends(handle_errors)):
            # Your route logic here
            return {"status": "success"}
    """
    try:
        yield
    except GandivaError as e:
        raise e.to_http_exception()
    except Exception as e:
        error = GandivaError.from_exception(e)
        raise error.to_http_exception()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON responses."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "status_code": self.status_code,
                **self.details
            }
        }


class SensorError(GandivaError):
    """Base exception for sensor-related errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code="sensor_error",
            status_code=503,  # Service Unavailable
            details=details,
            cause=cause
        )


class ModelError(GandivaError):
    """Base exception for model-related errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code="model_error",
            status_code=500,
            details=details,
            cause=cause
        )


class ConfigurationError(GandivaError):
    """Raised when there is a configuration error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code="configuration_error",
            status_code=500,
            details=details,
            cause=cause
        )


class ValidationError(GandivaError):
    """Raised when input validation fails."""
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None, 
                 details: Optional[Dict[str, Any]] = None):
        if details is None:
            details = {}
        if field is not None:
            details["field"] = field
        if value is not None:
            details["value"] = value
            
        super().__init__(
            message=message,
            code="validation_error",
            status_code=400,  # Bad Request
            details=details
        )


class ResourceNotFoundError(GandivaError):
    """Raised when a requested resource is not found."""
    def __init__(self, resource_type: str, resource_id: Any, details: Optional[Dict[str, Any]] = None):
        if details is None:
            details = {}
        details["resource_type"] = resource_type
        details["resource_id"] = resource_id
        
        super().__init__(
            message=f"{resource_type} with id {resource_id} not found",
            code="not_found",
            status_code=404,
            details=details
        )


def error_handler(error: Exception) -> tuple[dict, int]:
    ""
    Convert exceptions to JSON responses.
    
    This should be registered with FastAPI's exception handlers.
    """
    if isinstance(error, GandivaError):
        return error.to_dict(), error.status_code
    
    # Handle unexpected errors
    return {
        "error": {
            "code": "internal_server_error",
            "message": "An unexpected error occurred",
            "details": {
                "type": error.__class__.__name__,
                "message": str(error)
            }
        }
    }, 500
