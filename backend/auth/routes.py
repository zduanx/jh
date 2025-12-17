from datetime import timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from auth.models import GoogleTokenRequest, TokenResponse
from auth.utils import verify_google_token, create_access_token
from config.settings import settings
from db.session import get_db
from db.user_service import get_or_create_user

router = APIRouter()


@router.post("/google", response_model=TokenResponse)
async def google_auth(request: GoogleTokenRequest, db: Session = Depends(get_db)):
    """
    Authenticate with Google OAuth token and return JWT

    Flow:
    1. Frontend sends Google ID token
    2. Backend verifies token with Google
    3. Get or create user record in database
    4. Backend creates our own JWT with user_id
    5. Frontend stores JWT for subsequent requests
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

    # Get or create user record
    # - New users: creates record with profile data
    # - Returning users: updates profile data (name, picture_url) and last_login
    user, is_new_user = get_or_create_user(
        db=db,
        email=user_email,
        name=user_info["name"],
        picture_url=user_info.get("picture")
    )

    # Create our own JWT with user information including user_id and last_login
    access_token = create_access_token(
        data={
            "sub": user_email,  # Standard JWT claim for subject
            "user_id": user.user_id,  # Our database user ID
            "email": user_email,
            "name": user_info["name"],
            "picture": user_info.get("picture"),
            "last_login": user.last_login.isoformat(),  # Include last_login to avoid DB query
        },
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
    )
