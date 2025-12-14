from pydantic import BaseModel, EmailStr


class GoogleTokenRequest(BaseModel):
    """Request model for Google OAuth token"""
    token: str


class TokenResponse(BaseModel):
    """Response model for JWT token"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    """User information from Google OAuth"""
    email: EmailStr
    name: str
    picture: str
