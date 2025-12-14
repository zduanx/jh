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
        UserInfo: Current user's email, name, and picture
    """
    return UserInfo(**current_user)
