# Add New API Endpoint

Scaffold a new FastAPI endpoint following project conventions.

## Project Patterns

Before creating an endpoint, understand these patterns:

### Route Organization
- Routes live in `api/app/routes/`
- Each domain has its own file (teams.py, work_items.py, etc.)
- Routers are included in `main.py`

### Standard CRUD Structure
```python
GET    /resource/          # List with filters
GET    /resource/{id}      # Get single by UUID
POST   /resource/          # Create (returns 201)
PUT    /resource/{id}      # Update (partial)
DELETE /resource/{id}      # Delete (returns 204)
```

## Step-by-Step Guide

### 1. Create or Update Route File

```python
# api/app/routes/your_resource.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from ..database import get_db
from .. import models, schemas

router = APIRouter()


@router.get("/", response_model=list[schemas.YourResource])
def list_resources(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all resources with optional filtering."""
    query = db.query(models.YourResource)
    if status:
        query = query.filter(models.YourResource.status == status)
    return query.offset(skip).limit(limit).all()


@router.get("/{resource_id}", response_model=schemas.YourResource)
def get_resource(resource_id: UUID, db: Session = Depends(get_db)):
    """Get a single resource by ID."""
    resource = db.query(models.YourResource).filter(
        models.YourResource.id == resource_id
    ).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource


@router.post("/", response_model=schemas.YourResource, status_code=201)
def create_resource(
    resource: schemas.YourResourceCreate,
    db: Session = Depends(get_db)
):
    """Create a new resource."""
    db_resource = models.YourResource(**resource.model_dump())
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    return db_resource


@router.put("/{resource_id}", response_model=schemas.YourResource)
def update_resource(
    resource_id: UUID,
    resource: schemas.YourResourceUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing resource."""
    db_resource = db.query(models.YourResource).filter(
        models.YourResource.id == resource_id
    ).first()
    if not db_resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    for key, value in resource.model_dump(exclude_unset=True).items():
        setattr(db_resource, key, value)

    db.commit()
    db.refresh(db_resource)
    return db_resource


@router.delete("/{resource_id}", status_code=204)
def delete_resource(resource_id: UUID, db: Session = Depends(get_db)):
    """Delete a resource."""
    db_resource = db.query(models.YourResource).filter(
        models.YourResource.id == resource_id
    ).first()
    if not db_resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    db.delete(db_resource)
    db.commit()
```

### 2. Add Pydantic Schemas

```python
# api/app/schemas.py (add to existing file)
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum


class YourResourceStatus(str, Enum):
    active = "active"
    inactive = "inactive"


class YourResourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class YourResourceCreate(YourResourceBase):
    pass


class YourResourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[YourResourceStatus] = None


class YourResource(YourResourceBase):
    id: UUID
    status: YourResourceStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### 3. Add Database Model (if needed)

```python
# api/app/models.py (add to existing file)
from sqlalchemy import Column, String, DateTime, CheckConstraint, func
from .database import Base, GUID
import uuid


class YourResource(Base):
    __tablename__ = "your_resources"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    status = Column(String(50), default="active")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            status.in_(['active', 'inactive']),
            name='your_resource_status_check'
        ),
    )
```

### 4. Register Router in main.py

```python
# api/app/main.py (add import and include_router)
from .routes import your_resource

app.include_router(
    your_resource.router,
    prefix="/api/your-resources",
    tags=["your-resources"]
)
```

### 5. Create Database Migration

```bash
# Reset database to apply new model
cd api
python reset_db.py
```

### 6. Test the Endpoint

```bash
# Create
curl -X POST http://localhost:8000/api/your-resources/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Resource"}'

# List
curl http://localhost:8000/api/your-resources/

# Get by ID
curl http://localhost:8000/api/your-resources/UUID_HERE

# Update
curl -X PUT http://localhost:8000/api/your-resources/UUID_HERE \
  -H "Content-Type: application/json" \
  -d '{"status": "inactive"}'

# Delete
curl -X DELETE http://localhost:8000/api/your-resources/UUID_HERE
```

## Checklist

- [ ] Route file created in `api/app/routes/`
- [ ] Pydantic schemas added to `schemas.py`
- [ ] Database model added to `models.py` (if needed)
- [ ] Router registered in `main.py`
- [ ] Database reset to apply model changes
- [ ] Endpoints tested with curl
- [ ] OpenAPI docs updated (automatic): http://localhost:8000/docs
