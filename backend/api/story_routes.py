"""
API routes for behavioral interview stories (Phase 5).

Endpoints:
- GET    /api/stories              List all stories for current user
- GET    /api/stories/{story_id}   Get single story
- POST   /api/stories              Create new story
- PATCH  /api/stories/{story_id}   Update story
- DELETE /api/stories/{story_id}   Delete story
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from auth.dependencies import get_current_user
from db.session import get_db
from models.story import Story

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================

class StoryBase(BaseModel):
    """Base story fields."""
    question: str
    type: Optional[str] = None
    tags: Optional[list[str]] = []
    situation: Optional[str] = None
    task: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None


class StoryCreate(StoryBase):
    """Request for POST /api/stories."""
    pass


class StoryUpdate(BaseModel):
    """Request for PATCH /api/stories/{story_id}."""
    question: Optional[str] = None
    type: Optional[str] = None
    tags: Optional[list[str]] = None
    situation: Optional[str] = None
    task: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None


class StoryResponse(StoryBase):
    """Response for story endpoints."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StoriesListResponse(BaseModel):
    """Response for GET /api/stories."""
    stories: list[StoryResponse]


# =============================================================================
# Routes
# =============================================================================

@router.get("/stories", response_model=StoriesListResponse)
async def list_stories(
    type: Optional[str] = None,
    tag: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all stories for current user.

    Optional filters:
    - type: Filter by question type
    - tag: Filter by tag (partial match)
    """
    query = db.query(Story).filter(Story.user_id == current_user["user_id"])

    if type:
        query = query.filter(Story.type == type)

    if tag:
        # PostgreSQL array contains
        query = query.filter(Story.tags.contains([tag]))

    stories = query.order_by(desc(Story.updated_at)).all()

    return StoriesListResponse(stories=stories)


@router.get("/stories/{story_id}", response_model=StoryResponse)
async def get_story(
    story_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single story by ID."""
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == current_user["user_id"]
    ).first()

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )

    return story


@router.post("/stories", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
async def create_story(
    request: StoryCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new story."""
    user_id = current_user["user_id"]
    story = Story(
        user_id=user_id,
        question=request.question,
        type=request.type,
        tags=request.tags or [],
        situation=request.situation,
        task=request.task,
        action=request.action,
        result=request.result,
    )

    db.add(story)
    db.commit()
    db.refresh(story)

    logger.info(f"Created story {story.id} for user {user_id}")

    return story


@router.patch("/stories/{story_id}", response_model=StoryResponse)
async def update_story(
    story_id: int,
    request: StoryUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing story."""
    user_id = current_user["user_id"]
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == user_id
    ).first()

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )

    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(story, field, value)

    story.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(story)

    logger.info(f"Updated story {story_id} for user {user_id}")

    return story


@router.delete("/stories/{story_id}")
async def delete_story(
    story_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a story."""
    user_id = current_user["user_id"]
    story = db.query(Story).filter(
        Story.id == story_id,
        Story.user_id == user_id
    ).first()

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found"
        )

    db.delete(story)
    db.commit()

    logger.info(f"Deleted story {story_id} for user {user_id}")

    return {"success": True}
