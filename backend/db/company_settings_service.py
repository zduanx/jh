"""Company settings service layer - CRUD operations for user company settings."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from models.user_company_settings import UserCompanySettings
from extractors.config import TitleFilters


def get_user_settings(db: Session, user_id: int) -> list[UserCompanySettings]:
    """
    Get all company settings for a user.

    Args:
        db: Database session
        user_id: User's ID

    Returns:
        List of UserCompanySettings for this user
    """
    return db.query(UserCompanySettings).filter(
        UserCompanySettings.user_id == user_id
    ).all()


def get_setting_by_id(db: Session, setting_id: int) -> Optional[UserCompanySettings]:
    """
    Get a specific setting by ID.

    Args:
        db: Database session
        setting_id: Setting's ID

    Returns:
        UserCompanySettings if found, None otherwise
    """
    return db.query(UserCompanySettings).filter(
        UserCompanySettings.id == setting_id
    ).first()


def get_setting_by_company(
    db: Session,
    user_id: int,
    company_name: str
) -> Optional[UserCompanySettings]:
    """
    Get setting for a specific user+company combination.

    Args:
        db: Database session
        user_id: User's ID
        company_name: Company name (extractor key)

    Returns:
        UserCompanySettings if found, None otherwise
    """
    return db.query(UserCompanySettings).filter(
        UserCompanySettings.user_id == user_id,
        UserCompanySettings.company_name == company_name
    ).first()


def create_setting(
    db: Session,
    user_id: int,
    company_name: str,
    title_filters: Optional[dict] = None,
    is_enabled: bool = True
) -> UserCompanySettings:
    """
    Create a new company setting for a user.

    Args:
        db: Database session
        user_id: User's ID
        company_name: Company name (extractor key)
        title_filters: Filter configuration {"include": [...], "exclude": [...]}
        is_enabled: Whether this company is enabled

    Returns:
        Created UserCompanySettings

    Raises:
        IntegrityError: If setting for user+company already exists
        ValueError: If title_filters structure is invalid
    """
    # Validate and normalize via TitleFilters dataclass
    validated = TitleFilters.from_dict(title_filters)

    setting = UserCompanySettings(
        user_id=user_id,
        company_name=company_name,
        title_filters=validated.to_dict(),
        is_enabled=is_enabled
    )

    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def update_setting(
    db: Session,
    setting_id: int,
    title_filters: Optional[dict] = None,
    is_enabled: Optional[bool] = None
) -> Optional[UserCompanySettings]:
    """
    Update an existing company setting.

    Args:
        db: Database session
        setting_id: Setting's ID
        title_filters: New filter configuration (optional)
        is_enabled: New enabled state (optional)

    Returns:
        Updated UserCompanySettings if found, None otherwise

    Raises:
        ValueError: If title_filters structure is invalid
    """
    setting = get_setting_by_id(db, setting_id)
    if not setting:
        return None

    if title_filters is not None:
        validated = TitleFilters.from_dict(title_filters)
        setting.title_filters = validated.to_dict()
    if is_enabled is not None:
        setting.is_enabled = is_enabled

    setting.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(setting)
    return setting


def upsert_setting(
    db: Session,
    user_id: int,
    company_name: str,
    title_filters: Optional[dict] = None,
    is_enabled: bool = True
) -> UserCompanySettings:
    """
    Create or update a company setting (upsert).

    Uses PostgreSQL ON CONFLICT for atomic upsert.

    Args:
        db: Database session
        user_id: User's ID
        company_name: Company name (extractor key)
        title_filters: Filter configuration {"include": [...], "exclude": [...]}
        is_enabled: Whether this company is enabled

    Returns:
        Created or updated UserCompanySettings

    Raises:
        ValueError: If title_filters structure is invalid
    """
    now = datetime.now(timezone.utc)
    validated = TitleFilters.from_dict(title_filters)
    filters = validated.to_dict()

    stmt = insert(UserCompanySettings).values(
        user_id=user_id,
        company_name=company_name,
        title_filters=filters,
        is_enabled=is_enabled,
        created_at=now,
        updated_at=now
    )

    stmt = stmt.on_conflict_do_update(
        constraint='uq_user_company',
        set_={
            'title_filters': filters,
            'is_enabled': is_enabled,
            'updated_at': now
        }
    )

    db.execute(stmt)
    db.commit()

    # Fetch the result
    return get_setting_by_company(db, user_id, company_name)


def delete_setting(db: Session, setting_id: int, user_id: int) -> bool:
    """
    Delete a company setting.

    Verifies ownership before deletion.

    Args:
        db: Database session
        setting_id: Setting's ID
        user_id: User's ID (for ownership verification)

    Returns:
        True if deleted, False if not found or not owned
    """
    setting = db.query(UserCompanySettings).filter(
        UserCompanySettings.id == setting_id,
        UserCompanySettings.user_id == user_id
    ).first()

    if not setting:
        return False

    db.delete(setting)
    db.commit()
    return True


def get_enabled_settings(db: Session, user_id: int) -> list[UserCompanySettings]:
    """
    Get only enabled company settings for a user.

    Args:
        db: Database session
        user_id: User's ID

    Returns:
        List of enabled UserCompanySettings for this user
    """
    return db.query(UserCompanySettings).filter(
        UserCompanySettings.user_id == user_id,
        UserCompanySettings.is_enabled == True
    ).all()


def batch_operations(
    db: Session,
    user_id: int,
    operations: list[dict]
) -> list[dict]:
    """
    Execute batch operations on company settings.

    Each operation has an 'op' field: 'upsert' or 'delete'.

    Args:
        db: Database session
        user_id: User's ID
        operations: List of operations, each with:
            - op: 'upsert' or 'delete'
            - company_name: Company identifier
            - title_filters: (upsert only) Filter config
            - is_enabled: (upsert only) Enabled state

    Returns:
        List of operation results, each with:
            - op: The operation type
            - success: Boolean
            - company_name: Company identifier
            - id: (upsert only) Setting ID
            - updated_at: (upsert only) Timestamp
            - error: (on failure) Error message
    """
    now = datetime.now(timezone.utc)
    results = []

    for op_data in operations:
        op_type = op_data.get('op')
        company_name = op_data.get('company_name')

        try:
            if op_type == 'upsert':
                validated = TitleFilters.from_dict(op_data.get('title_filters'))
                filters = validated.to_dict()
                is_enabled = op_data.get('is_enabled', True)

                stmt = insert(UserCompanySettings).values(
                    user_id=user_id,
                    company_name=company_name,
                    title_filters=filters,
                    is_enabled=is_enabled,
                    created_at=now,
                    updated_at=now
                )

                stmt = stmt.on_conflict_do_update(
                    constraint='uq_user_company',
                    set_={
                        'title_filters': filters,
                        'is_enabled': is_enabled,
                        'updated_at': now
                    }
                )

                db.execute(stmt)
                db.flush()  # Flush to get the ID

                # Fetch the setting to get the ID
                setting = get_setting_by_company(db, user_id, company_name)
                results.append({
                    'op': 'upsert',
                    'success': True,
                    'company_name': company_name,
                    'id': setting.id,
                    'updated_at': setting.updated_at.isoformat(),
                })

            elif op_type == 'delete':
                deleted_count = db.query(UserCompanySettings).filter(
                    UserCompanySettings.user_id == user_id,
                    UserCompanySettings.company_name == company_name
                ).delete(synchronize_session=False)

                results.append({
                    'op': 'delete',
                    'success': deleted_count > 0,
                    'company_name': company_name,
                })

            else:
                results.append({
                    'op': op_type,
                    'success': False,
                    'company_name': company_name,
                    'error': f"Unknown operation: {op_type}",
                })

        except ValueError as e:
            results.append({
                'op': op_type,
                'success': False,
                'company_name': company_name,
                'error': str(e),
            })

    db.commit()
    return results
