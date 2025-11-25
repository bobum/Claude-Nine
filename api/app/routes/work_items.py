from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from ..database import get_db
from ..models import WorkItem
from ..schemas import WorkItem as WorkItemSchema, WorkItemCreate, WorkItemUpdate

router = APIRouter()


@router.get("/", response_model=List[WorkItemSchema])
def list_work_items(
    skip: int = 0,
    limit: int = 100,
    team_id: Optional[UUID] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all work items with optional filters"""
    query = db.query(WorkItem)

    if team_id:
        query = query.filter(WorkItem.team_id == team_id)
    if status:
        query = query.filter(WorkItem.status == status)
    if source:
        query = query.filter(WorkItem.source == source)

    work_items = query.order_by(
        WorkItem.priority.desc(),
        WorkItem.assigned_at.asc()
    ).offset(skip).limit(limit).all()

    return work_items


@router.get("/{work_item_id}", response_model=WorkItemSchema)
def get_work_item(
    work_item_id: UUID,
    db: Session = Depends(get_db)
):
    """Get work item by ID"""
    work_item = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
    if not work_item:
        raise HTTPException(status_code=404, detail="Work item not found")
    return work_item


@router.post("/", response_model=WorkItemSchema, status_code=status.HTTP_201_CREATED)
def create_work_item(
    work_item: WorkItemCreate,
    db: Session = Depends(get_db)
):
    """Create a new work item"""
    # Check if work item with same source and external_id already exists
    existing = db.query(WorkItem).filter(
        WorkItem.source == work_item.source,
        WorkItem.external_id == work_item.external_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Work item {work_item.source}#{work_item.external_id} already exists"
        )

    db_work_item = WorkItem(**work_item.dict())
    db.add(db_work_item)
    db.commit()
    db.refresh(db_work_item)
    return db_work_item


@router.put("/{work_item_id}", response_model=WorkItemSchema)
def update_work_item(
    work_item_id: UUID,
    work_item_update: WorkItemUpdate,
    db: Session = Depends(get_db)
):
    """Update a work item"""
    db_work_item = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
    if not db_work_item:
        raise HTTPException(status_code=404, detail="Work item not found")

    # Update only provided fields
    for field, value in work_item_update.dict(exclude_unset=True).items():
        setattr(db_work_item, field, value)

    db.commit()
    db.refresh(db_work_item)
    return db_work_item


@router.delete("/{work_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_item(
    work_item_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a work item"""
    db_work_item = db.query(WorkItem).filter(WorkItem.id == work_item_id).first()
    if not db_work_item:
        raise HTTPException(status_code=404, detail="Work item not found")

    db.delete(db_work_item)
    db.commit()
    return None
