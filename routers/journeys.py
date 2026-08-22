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

# ================= TAMBAHAN: UPDATE JOURNEY (name/description) =================
@router.put("/{id}", response_model=schemas.UserJourneyResponse)
def update_journey(
    id: int,
    data: schemas.UserJourneyUpdate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    db_journey = db.query(model.UserJourney).filter(model.UserJourney.id == id).first()
    if not db_journey:
        raise HTTPException(status_code=404, detail="Journey tidak ditemukan")

    db_journey.name = data.name
    db_journey.description = data.description
    db.commit()
    db.refresh(db_journey)
    return db_journey

# ================= TAMBAHAN: HAPUS JOURNEY =================
@router.delete("/{id}")
def delete_journey(id: int, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    db_journey = db.query(model.UserJourney).filter(model.UserJourney.id == id).first()
    if not db_journey:
        raise HTTPException(status_code=404, detail="Journey tidak ditemukan")
    db.delete(db_journey)
    db.commit()
    return {"message": "Journey berhasil dihapus"}

# ================= TAMBAHAN: SIMPAN ULANG SELURUH STEPS SEKALIGUS =================
# Pendekatan "replace all": hapus semua step lama milik journey ini, lalu buat baru
# sesuai urutan yang dikirim frontend. Ini paling simpel untuk mendukung UI drag/edit/
# add/delete step tanpa perlu endpoint terpisah untuk tiap operasi step.
@router.put("/{id}/steps", response_model=schemas.UserJourneyResponse)
def replace_journey_steps(
    id: int,
    data: schemas.JourneyStepsBulkUpdate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    db_journey = db.query(model.UserJourney).filter(model.UserJourney.id == id).first()
    if not db_journey:
        raise HTTPException(status_code=404, detail="Journey tidak ditemukan")

    # Hapus seluruh step lama
    db.query(model.JourneyStep).filter(model.JourneyStep.user_journey_id == id).delete()

    # Buat step baru sesuai urutan yang dikirim
    for step_data in data.steps:
        db_step = model.JourneyStep(
            user_journey_id=id,
            persona_id=step_data.persona_id,
            step_order=step_data.step_order,
            title=step_data.title,
            description=step_data.description,
        )
        db.add(db_step)

    db.commit()
    db.refresh(db_journey)
    return db_journey