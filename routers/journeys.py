from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from services import ai  
import model
import schemas
import auth
from database import get_db

router = APIRouter(prefix="/api/journeys", tags=["User Journeys"])

@router.get("", response_model=List[schemas.UserJourneyResponse])
def get_user_journeys(project_id: int, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    return db.query(model.UserJourney).filter(model.UserJourney.project_id == project_id).all()

@router.post("", response_model=schemas.UserJourneyResponse, status_code=status.HTTP_201_CREATED)
def create_journey(
    data: schemas.UserJourneyCreate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    db_journey = model.UserJourney(name=data.name, description=data.description, project_id=data.project_id)
    db.add(db_journey)
    db.commit()
    db.refresh(db_journey)

    for idx, step_data in enumerate(data.steps):
        db_step = model.JourneyStep(
            user_journey_id=db_journey.id,
            persona_id=step_data.persona_id,
            step_order=step_data.step_order or (idx + 1),
            title=step_data.title,
            description=step_data.description,
        )
        db.add(db_step)

    if data.steps:
        db.commit()
        db.refresh(db_journey)

    return db_journey

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

@router.delete("/{id}")
def delete_journey(id: int, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    db_journey = db.query(model.UserJourney).filter(model.UserJourney.id == id).first()
    if not db_journey:
        raise HTTPException(status_code=404, detail="Journey tidak ditemukan")
    db.delete(db_journey)
    db.commit()
    return {"message": "Journey berhasil dihapus"}

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

    db.query(model.JourneyStep).filter(model.JourneyStep.user_journey_id == id).delete()
    db.flush()

    for step_data in data.steps:
        db_step = model.JourneyStep(
            user_journey_id=id,
            persona_id=step_data.persona_id,
            step_order=step_data.step_order,
            title=step_data.title,
            description=step_data.description,
            # assigned_persona DIHAPUS -- kolom itu gak ada di model, bikin crash
        )
        db.add(db_step)

    db.commit()

    result = db.query(model.UserJourney).filter(model.UserJourney.id == id).first()
    return result


@router.post("/{id}/generate-ai-steps", response_model=schemas.UserJourneyResponse)
def generate_journey_steps(
    id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    db_journey = db.query(model.UserJourney).filter(model.UserJourney.id == id).first()
    if not db_journey:
        raise HTTPException(status_code=404, detail="Journey tidak ditemukan")

    project = db.query(model.Project).filter(model.Project.id == db_journey.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")

    # Ambil semua persona lintas UserType di project ini
    personas = (
        db.query(model.Persona)
        .join(model.UserType, model.Persona.user_type_id == model.UserType.id)
        .filter(model.UserType.project_id == project.id)
        .all()
    )

    if not personas:
        raise HTTPException(
            status_code=400,
            detail="Belum ada Persona di project ini. Buat User Type & Persona dulu sebelum generate AI journey."
        )

    persona_payload = [
        {"name": p.name, "user_type": p.user_type.name, "about": p.about or ""}
        for p in personas
    ]

    try:
        ai_result = ai.suggest_user_journey(
            project_name=project.name,
            project_description=project.description or "",
            personas=persona_payload,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Mapping nama persona hasil AI -> persona_id asli (case-insensitive)
    name_to_id = {p.name.strip().lower(): p.id for p in personas}

    db.query(model.JourneyStep).filter(model.JourneyStep.user_journey_id == id).delete()
    db.flush()

    for idx, step_data in enumerate(ai_result.steps):
        matched_persona_id = name_to_id.get((step_data.persona_name or "").strip().lower())
        db_step = model.JourneyStep(
            user_journey_id=id,
            persona_id=matched_persona_id,
            step_order=idx + 1,
            title=step_data.title,
            description=step_data.description,
        )
        db.add(db_step)

    if not db_journey.description or db_journey.description == 'Deskripsi user journey baru...':
        db_journey.description = ai_result.narrative

    db.commit()

    result = db.query(model.UserJourney).filter(model.UserJourney.id == id).first()
    return result