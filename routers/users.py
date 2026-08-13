# routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import model
import schemas
import auth
from database import get_db

router = APIRouter(prefix="/api/users", tags=["User Types & Personas"])

@router.get("/types", response_model=List[schemas.UserTypeResponse])
def get_user_types(project_id: int, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    return db.query(model.UserType).filter(model.UserType.project_id == project_id).all()

@router.post("/types", response_model=schemas.UserTypeResponse, status_code=status.HTTP_201_CREATED)
def create_user_type(data: schemas.UserTypeCreate, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    db_ut = model.UserType(name=data.name, description=data.description, project_id=data.project_id)
    db.add(db_ut)
    db.commit()
    db.refresh(db_ut)
    return db_ut

@router.delete("/types/{id}")
def delete_user_type(id: int, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    db_ut = db.query(model.UserType).filter(model.UserType.id == id).first()
    if not db_ut:
        raise HTTPException(status_code=404, detail="User type tidak ditemukan")
    db.delete(db_ut)
    db.commit()
    return {"message": "User type berhasil dihapus"}

@router.post("/personas", response_model=schemas.PersonaResponse, status_code=status.HTTP_201_CREATED)
def create_persona(data: schemas.PersonaCreate, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    db_persona = model.Persona(**data.model_dump())
    db.add(db_persona)
    db.commit()
    db.refresh(db_persona)
    return db_persona

@router.delete("/personas/{id}")
def delete_persona(id: int, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    db_persona = db.query(model.Persona).filter(model.Persona.id == id).first()
    if not db_persona:
        raise HTTPException(status_code=404, detail="Persona tidak ditemukan")
    db.delete(db_persona)
    db.commit()
    return {"message": "Persona berhasil dihapus"}