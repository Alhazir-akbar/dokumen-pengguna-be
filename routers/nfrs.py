# routers/nfrs.py
#
# Mengikuti persis pola routers/stories.py yang sudah ada:
# - import model, schemas, auth
# - Depends(get_db) + Depends(auth.get_current_user)
# - model.NFR sudah ada di model.py kamu, tidak perlu diubah.
#
# PENTING soal 2 endpoint AI di bawah (ai-suggest-draft, ai-suggest-refine):
# Ini mengikuti pola PERSIS endpoint /api/stories/ai-suggest di routers/stories.py,
# yang manggil services.ai.suggest_story_refinement(). Untuk NFR, aku asumsikan
# ada (atau perlu kamu tambahkan) 2 fungsi setara di services/ai.py:
#
#   def suggest_nfr_draft(project_name, project_description, application_type,
#                          domain_business, existing_categories) -> object dengan
#                          atribut .category dan .description
#
#   def suggest_nfr_refinement(project_name, category, description) -> object
#                          dengan atribut .category dan .description
#
# Kalau services/ai.py kamu belum punya fungsi ini, share isinya biar aku bikinin
# yang match persis gaya suggest_story_refinement (prompt, parsing response, dll).
# Tanpa itu, dua endpoint AI di bawah akan error saat dipanggil (import gagal).

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import model
import schemas
import auth
from database import get_db
from services.ai import suggest_nfr_draft, suggest_nfr_refinement

router = APIRouter(prefix="/api/nfrs", tags=["Non-Functional Requirements"])


@router.get("", response_model=List[schemas.NFRResponse])
def get_nfrs(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user),
):
    return db.query(model.NFR).filter(model.NFR.project_id == project_id).all()


@router.post("", response_model=schemas.NFRResponse, status_code=status.HTTP_201_CREATED)
def create_nfr(
    data: schemas.NFRCreate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user),
):
    db_nfr = model.NFR(
        category=data.category,
        description=data.description,
        project_id=data.project_id,
    )
    db.add(db_nfr)
    db.commit()
    db.refresh(db_nfr)
    return db_nfr


@router.put("/{id}", response_model=schemas.NFRResponse)
def update_nfr(
    id: int,
    data: schemas.NFRUpdate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user),
):
    db_nfr = db.query(model.NFR).filter(model.NFR.id == id).first()
    if not db_nfr:
        raise HTTPException(status_code=404, detail="NFR tidak ditemukan")

    if data.category is not None:
        db_nfr.category = data.category
    if data.description is not None:
        db_nfr.description = data.description

    db.commit()
    db.refresh(db_nfr)
    return db_nfr


@router.delete("/{id}")
def delete_nfr(
    id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user),
):
    db_nfr = db.query(model.NFR).filter(model.NFR.id == id).first()
    if not db_nfr:
        raise HTTPException(status_code=404, detail="NFR tidak ditemukan")
    db.delete(db_nfr)
    db.commit()
    return {"message": "NFR berhasil dihapus"}


# ================= AI: DRAFT & REFINE (lihat catatan di atas) =================

@router.post("/ai-suggest-draft", response_model=schemas.SuggestNFRDraftResponse)
def ai_suggest_nfr_draft(
    data: schemas.SuggestNFRDraftRequest,
    current_user: model.User = Depends(auth.get_current_user),
):
    try:
        suggestion = suggest_nfr_draft(
            project_name=data.project_name,
            project_description=data.project_description or "",
            application_type=data.application_type or "",
            domain_business=data.domain_business or "",
            existing_categories=data.existing_categories or [],
        )
        return schemas.SuggestNFRDraftResponse(
            category=suggestion.category,
            description=suggestion.description,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai-suggest-refine", response_model=schemas.SuggestNFRRefineResponse)
def ai_suggest_nfr_refine(
    data: schemas.SuggestNFRRefineRequest,
    current_user: model.User = Depends(auth.get_current_user),
):
    try:
        suggestion = suggest_nfr_refinement(
            project_name=data.project_name or "",
            category=data.category,
            description=data.description or "",
        )
        return schemas.SuggestNFRRefineResponse(
            category=suggestion.category,
            description=suggestion.description,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# TAMBAHKAN ke schemas.py (dekat NFRCreate/NFRResponse) -- belum ada, dipakai
# oleh endpoint PUT di atas:
#
# class NFRUpdate(BaseModel):
#     category: Optional[str] = None
#     description: Optional[str] = None
# ---------------------------------------------------------------------------