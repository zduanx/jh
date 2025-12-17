"""User database service layer"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.user import User


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Get user by email address.

    Args:
        db: Database session
        email: User's email address

    Returns:
        User object if found, None otherwise
    """
    return db.query(User).filter(User.email == email.lower()).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    Get user by user_id.

    Args:
        db: Database session
        user_id: User's ID

    Returns:
        User object if found, None otherwise
    """
    return db.query(User).filter(User.user_id == user_id).first()


def create_user(db: Session, email: str, name: str, picture_url: Optional[str] = None) -> User:
    """
    Create a new user record.

    Args:
        db: Database session
        email: User's email address
        name: User's full name from Google
        picture_url: User's profile picture URL from Google (optional)

    Returns:
        Created User object

    Raises:
        IntegrityError: If user with email already exists
    """
    now = datetime.now(timezone.utc)

    user = User(
        email=email.lower(),
        name=name,
        picture_url=picture_url,
        created_at=now,
        last_login=now
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_profile(
    db: Session,
    user_id: int,
    name: Optional[str] = None,
    picture_url: Optional[str] = None
) -> Optional[User]:
    """
    Update user's profile data (name, picture_url) and last_login timestamp.

    Args:
        db: Database session
        user_id: User's ID
        name: Updated name (optional)
        picture_url: Updated profile picture URL (optional)

    Returns:
        Updated User object if found, None otherwise
    """
    user = get_user_by_id(db, user_id)
    if not user:
        return None

    # Update profile fields if provided
    if name is not None:
        user.name = name
    if picture_url is not None:
        user.picture_url = picture_url

    # Always update last_login
    user.last_login = datetime.now(timezone.utc)

    db.commit()
    db.refresh(user)
    return user


def get_or_create_user(
    db: Session,
    email: str,
    name: str,
    picture_url: Optional[str] = None
) -> tuple[User, bool]:
    """
    Get existing user or create new one.

    This is the main function used during authentication flow.
    - If user exists: updates profile data and last_login (optimized - no extra query)
    - If user is new: creates user record

    Args:
        db: Database session
        email: User's email address
        name: User's full name from Google
        picture_url: User's profile picture URL from Google (optional)

    Returns:
        Tuple of (User object, is_new_user boolean)
    """
    # Try to get existing user
    user = get_user_by_email(db, email)

    if user:
        # Existing user - update profile and last_login directly (optimized)
        user.name = name
        if picture_url is not None:
            user.picture_url = picture_url
        user.last_login = datetime.now(timezone.utc)

        db.commit()
        db.refresh(user)
        return user, False
    else:
        # New user - create record
        user = create_user(db, email, name, picture_url)
        return user, True
