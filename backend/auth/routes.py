from datetime import timedelta
from fastapi import APIRouter, HTTPException, status
from auth.models import GoogleTokenRequest, TokenResponse
from auth.utils import verify_google_token, create_access_token
from config.settings import settings

router = APIRouter()


@router.post("/google", response_model=TokenResponse)
async def google_auth(request: GoogleTokenRequest):
    """
    Authenticate with Google OAuth token and return JWT

    Flow:
    1. Frontend sends Google ID token
    2. Backend verifies token with Google
    3. Backend creates our own JWT
    4. Frontend stores JWT for subsequent requests
    """
    # Verify the Google token
    user_info = verify_google_token(request.token)

    # Check if email is allowed
    allowed_emails = settings.get_allowed_emails()
    user_email = user_info["email"].lower()

    if user_email not in allowed_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Your email ({user_info['email']}) is not authorized to use this application."
        )

    # Create our own JWT with user information
    access_token = create_access_token(
        data={
            "sub": user_info["email"],
            "email": user_info["email"],
            "name": user_info["name"],
            "picture": user_info["picture"],
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
    )
