from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth.utils import decode_access_token
from auth.models import UserInfo

security = HTTPBearer()


def get_current_user_from_token(token: str) -> dict:
    """
    Get user info from a raw JWT token string.

    This is used for SSE endpoints where the token is passed as a query param
    (EventSource API cannot send Authorization headers).

    Args:
        token: Raw JWT token string

    Returns:
        dict: User information from JWT token

    Raises:
        HTTPException: If token is invalid
    """
    payload = decode_access_token(token)

    user_id = payload.get("user_id")
    email = payload.get("email")
    if email is None or user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    return {
        "user_id": user_id,
        "email": payload.get("email"),
        "name": payload.get("name"),
        "picture": payload.get("picture"),
        "last_login": payload.get("last_login"),
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Dependency to get current authenticated user from JWT token

    Usage in route:
        @app.get("/api/user")
        async def get_user(current_user: dict = Depends(get_current_user)):
            return current_user

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        dict: User information from JWT token

    Raises:
        HTTPException: If token is missing or invalid
    """
    token = credentials.credentials

    # Decode and verify the JWT token
    payload = decode_access_token(token)

    # Extract user info from token
    user_id = payload.get("user_id")
    email = payload.get("email")
    if email is None or user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "user_id": user_id,
        "email": payload.get("email"),
        "name": payload.get("name"),
        "picture": payload.get("picture"),
        "last_login": payload.get("last_login"),  # Include last_login from JWT
    }
