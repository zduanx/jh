from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth.utils import decode_access_token
from auth.models import UserInfo

security = HTTPBearer()


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
    email = payload.get("email")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "email": payload.get("email"),
        "name": payload.get("name"),
        "picture": payload.get("picture"),
    }
