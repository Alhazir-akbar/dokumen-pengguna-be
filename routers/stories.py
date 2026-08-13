# routers/stories.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import model
import schemas
import auth
from database import get_db

router = APIRouter(prefix="/api/stories", tags=["Epics & User Stories"])

@router.get("/epics", response_model=List[schemas.EpicResponse])
def get_epics(project_id: int, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    return db.query(model.Epic).filter(model.Epic.project_id == project_id).all()

@router.post("/epics", response_model=schemas.EpicResponse, status_code=status.HTTP_201_CREATED)
def create_epic(data: schemas.EpicCreate, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    db_epic = model.Epic(name=data.name, description=data.description, project_id=data.project_id)
    db.add(db_epic)
    db.commit()
    db.refresh(db_epic)
    return db_epic

@router.get("", response_model=List[schemas.UserStoryResponse])
def get_stories(project_id: int, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    return db.query(model.UserStory).filter(model.UserStory.project_id == project_id).all()

@router.post("", response_model=schemas.UserStoryResponse, status_code=status.HTTP_201_CREATED)
def create_story(data: schemas.UserStoryCreate, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    db_story = model.UserStory(**data.model_dump())
    db.add(db_story)
    db.commit()
    db.refresh(db_story)
    return db_story

@router.put("/{id}", response_model=schemas.UserStoryResponse)
def update_story(id: int, data: schemas.UserStoryCreate, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    db_story = db.query(model.UserStory).filter(model.UserStory.id == id).first()
    if not db_story:
        raise HTTPException(status_code=404, detail="User Story tidak ditemukan")
    
    for key, value in data.model_dump().items():
        setattr(db_story, key, value)
        
    db.commit()
    db.refresh(db_story)
    return db_story

@router.delete("/{id}")
def delete_story(id: int, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    db_story = db.query(model.UserStory).filter(model.UserStory.id == id).first()
    if not db_story:
        raise HTTPException(status_code=404, detail="User Story tidak ditemukan")
    db.delete(db_story)
    db.commit()
    return {"message": "User story berhasil dihapus"}