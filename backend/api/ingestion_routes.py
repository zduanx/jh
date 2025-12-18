"""
API routes for ingestion workflow - Stage 1 (company settings configuration).

Endpoints:
- GET  /api/ingestion/companies       List available companies from extractor registry
- GET  /api/ingestion/settings        Get user's configured company settings
- POST /api/ingestion/settings        Create or update company setting (upsert)
- DELETE /api/ingestion/settings/:id  Delete company setting

Interactive API docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Running locally:
    cd backend
    uvicorn main:app --reload
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from typing import Optional, Literal
from datetime import datetime
from sqlalchemy.orm import Session
from auth.dependencies import get_current_user
from db.session import get_db
from db.company_settings_service import (
    get_user_settings,
    batch_operations,
)
from extractors.registry import list_companies

router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================

class CompanyInfo(BaseModel):
    """Company information for frontend display."""
    name: str
    display_name: str
    logo_url: Optional[str] = None


class CompanySettingResponse(BaseModel):
    """Response model for a single company setting."""
    id: int
    company_name: str
    title_filters: dict
    is_enabled: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


class SettingOperation(BaseModel):
    """A single operation in a batch request."""
    op: Literal['upsert', 'delete']
    company_name: str
    title_filters: Optional[dict] = None
    is_enabled: bool = True

    @field_validator('company_name')
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        """Validate company name exists in registry."""
        available = list_companies()
        if v.lower() not in available:
            raise ValueError(f"Company '{v}' not found. Available: {', '.join(available)}")
        return v.lower()


class OperationResult(BaseModel):
    """Result of a single operation."""
    op: str
    success: bool
    company_name: str
    id: Optional[int] = None
    updated_at: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# Company Metadata (static config)
# =============================================================================

# Display names and logos for companies
# Using Google's favicon service (reliable, works for all domains)
# Format: https://www.google.com/s2/favicons?domain={domain}&sz=128
COMPANY_METADATA = {
    "google": {"display_name": "Google", "logo_url": "https://www.google.com/s2/favicons?domain=google.com&sz=128"},
    "amazon": {"display_name": "Amazon", "logo_url": "https://www.google.com/s2/favicons?domain=amazon.com&sz=128"},
    "anthropic": {"display_name": "Anthropic", "logo_url": "https://www.google.com/s2/favicons?domain=anthropic.com&sz=128"},
    "tiktok": {"display_name": "TikTok", "logo_url": "https://www.google.com/s2/favicons?domain=tiktok.com&sz=128"},
    "roblox": {"display_name": "Roblox", "logo_url": "https://www.google.com/s2/favicons?domain=roblox.com&sz=128"},
    "netflix": {"display_name": "Netflix", "logo_url": "https://www.google.com/s2/favicons?domain=netflix.com&sz=128"},
}


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/companies", response_model=list[CompanyInfo])
async def get_available_companies():
    """
    List available companies from extractor registry.

    Returns company names with display metadata for frontend cards.
    No authentication required (public endpoint).

    Returns:
        List of CompanyInfo objects

    Example:
        GET /api/ingestion/companies

        Response:
        [
            {"name": "google", "display_name": "Google", "logo_url": "https://www.google.com/s2/favicons?domain=google.com&sz=128"},
            {"name": "anthropic", "display_name": "Anthropic", "logo_url": "https://www.google.com/s2/favicons?domain=anthropic.com&sz=128"},
            ...
        ]
    """
    companies = list_companies()
    return [
        CompanyInfo(
            name=name,
            display_name=COMPANY_METADATA.get(name, {}).get("display_name", name.title()),
            logo_url=COMPANY_METADATA.get(name, {}).get("logo_url"),
        )
        for name in companies
    ]


@router.get("/settings", response_model=list[CompanySettingResponse])
async def get_settings(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get user's configured company settings.

    Returns all company settings for the authenticated user.
    Auth: JWT required

    Returns:
        List of CompanySettingResponse objects

    Example:
        GET /api/ingestion/settings
        Authorization: Bearer <jwt_token>

        Response:
        [
            {
                "id": 1,
                "company_name": "anthropic",
                "title_filters": {"include": ["engineer"], "exclude": ["intern"]},
                "is_enabled": true
            },
            ...
        ]
    """
    user_id = current_user["user_id"]
    settings = get_user_settings(db, user_id)
    return settings


@router.post("/settings", response_model=list[OperationResult])
async def batch_update_settings(
    operations: list[SettingOperation],
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Batch create, update, or delete company settings.

    Accepts an array of operations, each with an 'op' field ('upsert' or 'delete').
    Returns an array of results confirming each operation's success.
    Auth: JWT required

    Args:
        operations: List of SettingOperation objects

    Returns:
        List of OperationResult objects

    Example:
        POST /api/ingestion/settings
        Authorization: Bearer <jwt_token>
        [
            {"op": "upsert", "company_name": "google", "title_filters": {"include": ["engineer"]}, "is_enabled": true},
            {"op": "upsert", "company_name": "amazon", "title_filters": {}, "is_enabled": false},
            {"op": "delete", "company_name": "netflix"}
        ]

        Response:
        [
            {"op": "upsert", "success": true, "company_name": "google", "id": 1, "updated_at": "2025-12-18T..."},
            {"op": "upsert", "success": true, "company_name": "amazon", "id": 2, "updated_at": "2025-12-18T..."},
            {"op": "delete", "success": true, "company_name": "netflix"}
        ]
    """
    user_id = current_user["user_id"]

    # Convert Pydantic models to dicts for service layer
    ops_data = [op.model_dump() for op in operations]

    results = batch_operations(db, user_id, ops_data)

    return results
