from fastapi import APIRouter, Depends
from auth.dependencies import get_current_user
from auth.models import UserInfo

router = APIRouter()


@router.get("/user", response_model=UserInfo)
async def get_user(current_user: dict = Depends(get_current_user)):
    """
    Get current user information (protected endpoint)

    Requires valid JWT token in Authorization header:
        Authorization: Bearer <jwt_token>

    Returns:
        UserInfo: Current user's email, name, picture, and last_login (all from JWT)

    Note: All data comes from JWT token, no database query needed (optimized)
    """
    # Return user data directly from JWT token (no DB query needed!)
    return UserInfo(**current_user)
