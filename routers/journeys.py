# routers/journeys.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import model
import schemas
import auth
from database import get_db

router = APIRouter(prefix="/api/journeys", tags=["User Journeys"])

@router.get("", response_model=List[schemas.UserJourneyResponse])
def get_user_journeys(project_id: int, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    return db.query(model.UserJourney).filter(model.UserJourney.project_id == project_id).all()

@router.post("", response_model=schemas.UserJourneyResponse, status_code=status.HTTP_201_CREATED)
def create_journey(data: schemas.UserJourneyCreate, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    db_journey = model.UserJourney(name=data.name, description=data.description, project_id=data.project_id)
    db.add(db_journey)
    db.commit()
    db.refresh(db_journey)
    return db_journey