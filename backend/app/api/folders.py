from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional
import uuid

from ..models.database import get_db
from ..models.chat import Folder, Document
from ..schemas.folder import FolderCreate, FolderUpdate, FolderMove, Folder as FolderSchema

router = APIRouter()

# TODO: Add proper user authentication when implemented
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get("/", response_model=List[FolderSchema])
async def get_folders(
    db: AsyncSession = Depends(get_db)
):
    """Get all folders for the current user, organized hierarchically"""
    # Get all folders for the user
    result = await db.execute(
        select(Folder).where(Folder.user_id == DEFAULT_USER_ID).order_by(Folder.name)
    )
    folders = result.scalars().all()

    # Get document counts for each folder
    folder_data = []
    for folder in folders:
        doc_count_result = await db.execute(
            select(func.count(Document.id)).where(
                and_(Document.folder_id == folder.id, Document.user_id == DEFAULT_USER_ID)
            )
        )
        doc_count = doc_count_result.scalar() or 0

        folder_schema = FolderSchema(
            id=folder.id,
            name=folder.name,
            description=folder.description,
            color=folder.color,
            parent_id=folder.parent_id,
            user_id=folder.user_id,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            children=[],
            document_count=doc_count
        )
        folder_data.append(folder_schema)

    # Build hierarchy
    folder_dict = {f.id: f for f in folder_data}
    root_folders = []

    for folder in folder_data:
        if folder.parent_id is None:
            root_folders.append(folder)
        else:
            parent = folder_dict.get(folder.parent_id)
            if parent:
                parent.children.append(folder)

    return root_folders


@router.post("/", response_model=FolderSchema)
async def create_folder(
    folder: FolderCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new folder"""
    # Check if parent exists and belongs to user
    if folder.parent_id:
        parent_result = await db.execute(
            select(Folder).where(
                and_(Folder.id == folder.parent_id, Folder.user_id == DEFAULT_USER_ID)
            )
        )
        parent_folder = parent_result.scalar_one_or_none()
        if not parent_folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent folder not found"
            )

    # Check for duplicate names in the same parent
    existing_result = await db.execute(
        select(Folder).where(
            and_(
                Folder.user_id == DEFAULT_USER_ID,
                Folder.parent_id == folder.parent_id,
                Folder.name == folder.name
            )
        )
    )
    existing_folder = existing_result.scalar_one_or_none()

    if existing_folder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Folder with this name already exists in the same parent folder"
        )

    # Create new folder
    db_folder = Folder(
        user_id=DEFAULT_USER_ID,
        name=folder.name,
        description=folder.description,
        color=folder.color,
        parent_id=folder.parent_id
    )

    db.add(db_folder)
    await db.commit()
    await db.refresh(db_folder)

    # Return folder with document count - manually create response to avoid lazy loading issues
    return FolderSchema(
        id=db_folder.id,
        name=db_folder.name,
        description=db_folder.description,
        color=db_folder.color,
        parent_id=db_folder.parent_id,
        user_id=db_folder.user_id,
        created_at=db_folder.created_at,
        updated_at=db_folder.updated_at,
        children=[],
        document_count=0
    )


@router.get("/{folder_id}", response_model=FolderSchema)
async def get_folder(
    folder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific folder"""
    result = await db.execute(
        select(Folder).where(
            and_(Folder.id == folder_id, Folder.user_id == DEFAULT_USER_ID)
        )
    )
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )

    # Get document count
    doc_count_result = await db.execute(
        select(func.count(Document.id)).where(
            and_(Document.folder_id == folder_id, Document.user_id == DEFAULT_USER_ID)
        )
    )
    doc_count = doc_count_result.scalar() or 0

    return FolderSchema(
        id=folder.id,
        name=folder.name,
        description=folder.description,
        color=folder.color,
        parent_id=folder.parent_id,
        user_id=folder.user_id,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        children=[],
        document_count=doc_count
    )


@router.put("/{folder_id}", response_model=FolderSchema)
async def update_folder(
    folder_id: uuid.UUID,
    folder_update: FolderUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a folder"""
    result = await db.execute(
        select(Folder).where(
            and_(Folder.id == folder_id, Folder.user_id == DEFAULT_USER_ID)
        )
    )
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )

    # Check if new parent exists and belongs to user (if provided)
    if folder_update.parent_id is not None:
        if folder_update.parent_id == folder_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Folder cannot be its own parent"
            )

        if folder_update.parent_id:
            parent_result = await db.execute(
                select(Folder).where(
                    and_(Folder.id == folder_update.parent_id, Folder.user_id == DEFAULT_USER_ID)
                )
            )
            parent_folder = parent_result.scalar_one_or_none()
            if not parent_folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent folder not found"
                )

    # Update folder fields
    update_data = folder_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(folder, field, value)

    await db.commit()
    await db.refresh(folder)

    # Get document count
    doc_count_result = await db.execute(
        select(func.count(Document.id)).where(
            and_(Document.folder_id == folder_id, Document.user_id == DEFAULT_USER_ID)
        )
    )
    doc_count = doc_count_result.scalar() or 0

    return FolderSchema(
        id=folder.id,
        name=folder.name,
        description=folder.description,
        color=folder.color,
        parent_id=folder.parent_id,
        user_id=folder.user_id,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        children=[],
        document_count=doc_count
    )


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a folder and move its contents to parent or root"""
    result = await db.execute(
        select(Folder).where(
            and_(Folder.id == folder_id, Folder.user_id == DEFAULT_USER_ID)
        )
    )
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )

    # Move all child folders to the parent of the deleted folder
    child_folders_result = await db.execute(
        select(Folder).where(
            and_(Folder.parent_id == folder_id, Folder.user_id == DEFAULT_USER_ID)
        )
    )
    child_folders = child_folders_result.scalars().all()

    for child in child_folders:
        child.parent_id = folder.parent_id

    # Move all documents to the parent of the deleted folder
    documents_result = await db.execute(
        select(Document).where(
            and_(Document.folder_id == folder_id, Document.user_id == DEFAULT_USER_ID)
        )
    )
    documents = documents_result.scalars().all()

    for doc in documents:
        doc.folder_id = folder.parent_id

    # Delete the folder
    await db.delete(folder)
    await db.commit()

    return {"message": "Folder deleted successfully"}


@router.put("/{folder_id}/move", response_model=FolderSchema)
async def move_folder(
    folder_id: uuid.UUID,
    move_data: FolderMove,
    db: AsyncSession = Depends(get_db)
):
    """Move a folder to a different parent"""
    result = await db.execute(
        select(Folder).where(
            and_(Folder.id == folder_id, Folder.user_id == DEFAULT_USER_ID)
        )
    )
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )

    # Check if new parent exists and belongs to user
    if move_data.parent_id:
        if move_data.parent_id == folder_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Folder cannot be its own parent"
            )

        parent_result = await db.execute(
            select(Folder).where(
                and_(Folder.id == move_data.parent_id, Folder.user_id == DEFAULT_USER_ID)
            )
        )
        parent_folder = parent_result.scalar_one_or_none()
        if not parent_folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent folder not found"
            )

    # Move folder
    folder.parent_id = move_data.parent_id
    await db.commit()
    await db.refresh(folder)

    # Get document count
    doc_count_result = await db.execute(
        select(func.count(Document.id)).where(
            and_(Document.folder_id == folder_id, Document.user_id == DEFAULT_USER_ID)
        )
    )
    doc_count = doc_count_result.scalar() or 0

    return FolderSchema(
        id=folder.id,
        name=folder.name,
        description=folder.description,
        color=folder.color,
        parent_id=folder.parent_id,
        user_id=folder.user_id,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        children=[],
        document_count=doc_count
    )