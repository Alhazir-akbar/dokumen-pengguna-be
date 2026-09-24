from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from services.ai import suggest_story_refinement, suggest_epic_draft, suggest_nfr_draft

import model
import schemas
import auth
from database import get_db
import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form

router = APIRouter(prefix="/api/stories", tags=["Epics & User Stories"])
UPLOAD_DIR = "static/story_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
def update_story(
    id: int, 
    data: schemas.UserStoryUpdate, 
    db: Session = Depends(get_db), 
    current_user: model.User = Depends(auth.get_current_user)
):
    db_story = db.query(model.UserStory).filter(model.UserStory.id == id).first()
    if not db_story:
        raise HTTPException(status_code=404, detail="User Story tidak ditemukan")

    if data.as_a is not None:
        db_story.as_a = data.as_a
    if data.i_want is not None:
        db_story.i_want = data.i_want
    if data.so_that is not None:
        db_story.so_that = data.so_that
    if data.status is not None:
        db_story.status = data.status
    if data.code is not None:
        db_story.code = data.code

    # Sinkronisasi Acceptance Criteria ke tabel database
    if data.acceptance_criteria is not None:
        db.query(model.AcceptanceCriteria).filter(model.AcceptanceCriteria.user_story_id == id).delete()
        for ac_desc in data.acceptance_criteria:
            if ac_desc and str(ac_desc).strip():
                db.add(model.AcceptanceCriteria(user_story_id=id, description=str(ac_desc).strip()))

    # Sinkronisasi Tech Notes ke tabel database
    if data.tech_notes is not None:
        db.query(model.TechNote).filter(model.TechNote.user_story_id == id).delete()
        for note_content in data.tech_notes:
            if note_content and str(note_content).strip():
                db.add(model.TechNote(user_story_id=id, content=str(note_content).strip()))

    # Sinkronisasi Test Cases ke tabel database
    if data.test_cases is not None:
        db.query(model.TestCase).filter(model.TestCase.user_story_id == id).delete()
        for tc in data.test_cases:
            if tc:
                db.add(model.TestCase(
                    user_story_id=id,
                    action=tc.action if hasattr(tc, 'action') else getattr(tc, 'description', str(tc)),
                    expected_result=tc.expected_result if hasattr(tc, 'expected_result') else "",
                ))

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

# ================= TAMBAHAN: SEED EXAMPLE STORY (AiChoice -> "No, not at this stage") =================
@router.post("/seed-example", status_code=status.HTTP_201_CREATED)
def seed_example_story(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """
    Membuat 1 Epic + 1 User Story contoh (lengkap dengan Acceptance Criteria)
    untuk project yang baru dibuat, supaya dashboard Stories tidak kosong total
    saat user memilih 'No, not at this stage' di step AiChoice.

    Idempotent: kalau project ini sudah punya epic (misal user klik lagi atau
    reload), tidak akan bikin duplikat -- langsung return tanpa insert baru.
    """
    existing_epic = db.query(model.Epic).filter(model.Epic.project_id == project_id).first()
    if existing_epic:
        return {"message": "Project sudah memiliki data, seed dilewati.", "epic_id": existing_epic.id}

    db_epic = model.Epic(
        name="Getting Started",
        description="Contoh Epic bawaan untuk membantu kamu memahami struktur Userdoc.",
        project_id=project_id,
    )
    db.add(db_epic)
    db.commit()
    db.refresh(db_epic)

    db_story = model.UserStory(
        epic_id=db_epic.id,
        code="US-1.1",
        as_a="Customer",
        i_want="to create my first user story",
        so_that="I can describe the requirements of my system in a language everyone can understand",
        status="draft",
        project_id=project_id,
    )
    db.add(db_story)
    db.commit()
    db.refresh(db_story)

    example_criteria = [
        'Use acceptance criteria to capture what needs to happen for this story to be "done"',
        "It should be clear and concise",
        "Able to be understood by everyone",
        "Focus on the user's perspective",
        "Testable, meaning it can be used for defining, implementing, and testing a story",
        "You can link to other user stories by typing hash '#' and then the name of the story",
        "This helps you build a navigable map of your system",
        "You can also add resource links to each story in the 'Resources' panel on the right hand",
        "You can add images to your stories for better visualization of requirements or design mockups",
        "Images can be referenced directly within your descriptions and acceptance criteria",
        "This helps stakeholders understand the visual aspects of requirements",
    ]

    for desc in example_criteria:
        db.add(model.AcceptanceCriteria(user_story_id=db_story.id, description=desc))

    db.commit()

    return {"message": "Example story berhasil dibuat.", "epic_id": db_epic.id, "story_id": db_story.id}


# ================= TAMBAHAN: BATCH SAVE DARI WIZARD =================
@router.post("/batch", status_code=status.HTTP_201_CREATED)
def save_wizard_stories_batch(
    project_id: int, 
    data: schemas.WizardBatchCreateSchema, 
    db: Session = Depends(get_db), 
    current_user: model.User = Depends(auth.get_current_user)
):
    """Menyimpan seluruh Epics dan User Stories hasil wizard frontend secara sekaligus"""

    for epic_data in data.epics:
        db_epic = model.Epic(
            name=epic_data.name,
            description=epic_data.description,
            project_id=project_id
        )
        db.add(db_epic)
        db.commit()
        db.refresh(db_epic)

        # Simpan stories yang terikat ke epic ini.
        # model.UserStory TIDAK punya field storyName/userType/description —
        # field itu perlu di-mapping ke i_want / as_a / so_that.
        for story_data in epic_data.stories:
            # Cari UserType yang namanya cocok di project ini (kalau ada),
            # supaya story bisa terhubung ke user_type_id yang benar.
            user_type = db.query(model.UserType).filter(
                model.UserType.project_id == project_id,
                model.UserType.name == story_data.userType
            ).first()

            db_story = model.UserStory(
                epic_id=db_epic.id,
                user_type_id=user_type.id if user_type else None,
                as_a=story_data.userType,
                i_want=story_data.storyName,
                so_that=story_data.description,
                status="draft",
                project_id=project_id
            )
            db.add(db_story)

    db.commit()
    return {"message": "Semua data wizard berhasil disimpan ke database!"}

# ================= TAMBAHAN: ENDPOINT AI REGENERATE USER STORY =================
@router.post("/ai-suggest", response_model=schemas.StoryAiSuggestResponse)
def ai_suggest_user_story(
    data: schemas.StoryAiSuggestRequest,
    current_user: model.User = Depends(auth.get_current_user)
):
    """Menyempurnakan dan men-generate kelengkapan User Story menggunakan AI"""
    try:
        suggestion = suggest_story_refinement(
            as_a=data.as_a or "",
            i_want=data.i_want or "",
            so_that=data.so_that or "",
            epic_name=data.epic_name or "",
            project_name=data.project_name or ""
        )
        return schemas.StoryAiSuggestResponse(
            as_a=suggestion.as_a,
            i_want=suggestion.i_want,
            so_that=suggestion.so_that,
            acceptance_criteria=suggestion.acceptance_criteria,
            tech_notes=suggestion.tech_notes,
            test_cases=suggestion.test_cases
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ================= NON-FUNCTIONAL REQUIREMENTS (NFR) =================

@router.get("/nfrs", response_model=List[schemas.NFRResponse])
def get_nfrs(project_id: int, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    return db.query(model.NFR).filter(model.NFR.project_id == project_id).all()

@router.post("/nfrs", response_model=schemas.NFRResponse, status_code=status.HTTP_201_CREATED)
def create_nfr(data: schemas.NFRCreate, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    db_nfr = model.NFR(category=data.category, description=data.description, project_id=data.project_id)
    db.add(db_nfr)
    db.commit()
    db.refresh(db_nfr)
    return db_nfr

@router.put("/nfrs/{id}", response_model=schemas.NFRResponse)
def update_nfr(
    id: int,
    data: schemas.NFRCreate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    db_nfr = db.query(model.NFR).filter(model.NFR.id == id).first()
    if not db_nfr:
        raise HTTPException(status_code=404, detail="NFR tidak ditemukan")
    db_nfr.category = data.category
    db_nfr.description = data.description
    db.commit()
    db.refresh(db_nfr)
    return db_nfr

@router.delete("/nfrs/{id}")
def delete_nfr(id: int, db: Session = Depends(get_db), current_user: model.User = Depends(auth.get_current_user)):
    db_nfr = db.query(model.NFR).filter(model.NFR.id == id).first()
    if not db_nfr:
        raise HTTPException(status_code=404, detail="NFR tidak ditemukan")
    db.delete(db_nfr)
    db.commit()
    return {"message": "NFR berhasil dihapus"}


# ================= AI-SUGGEST: EPIC & NFR =================

@router.post("/epics/ai-suggest", response_model=schemas.SuggestEpicDraftResponse)
def ai_suggest_epic(
    data: schemas.SuggestEpicDraftRequest,
    current_user: model.User = Depends(auth.get_current_user)
):
    try:
        suggestion = suggest_epic_draft(
            project_name=data.project_name,
            project_description=data.project_description or "",
            application_type=data.application_type or "",
            domain_business=data.domain_business or "",
            existing_epics=data.existing_epics,
        )
        return schemas.SuggestEpicDraftResponse(title=suggestion.title, description=suggestion.description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/nfrs/ai-suggest", response_model=schemas.SuggestNFRDraftResponse)
def ai_suggest_nfr(
    data: schemas.SuggestNFRDraftRequest,
    current_user: model.User = Depends(auth.get_current_user)
):
    try:
        suggestion = suggest_nfr_draft(
            project_name=data.project_name,
            project_description=data.project_description or "",
            application_type=data.application_type or "",
            domain_business=data.domain_business or "",
            existing_categories=data.existing_categories,
        )
        return schemas.SuggestNFRDraftResponse(category=suggestion.category, description=suggestion.description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ================= TAMBAHAN: STORY IMAGES / WIREFRAMES =================

@router.post("/{id}/images/upload", response_model=schemas.StoryImageResponse, status_code=status.HTTP_201_CREATED)
def upload_story_image(
    id: int,
    file: UploadFile = File(...),
    caption: str = Form(None),
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Upload file gambar lokal untuk sebuah User Story."""
    db_story = db.query(model.UserStory).filter(model.UserStory.id == id).first()
    if not db_story:
        raise HTTPException(status_code=404, detail="User Story tidak ditemukan")

    ext = os.path.splitext(file.filename or "")[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    image_url = f"/static/story_images/{filename}"
    db_image = model.StoryImage(user_story_id=id, url=image_url, caption=caption)
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return db_image


@router.post("/{id}/images", response_model=schemas.StoryImageResponse, status_code=status.HTTP_201_CREATED)
def add_story_image_url(
    id: int,
    data: schemas.StoryImageCreate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Tambah gambar via URL eksternal (bukan upload file)."""
    db_story = db.query(model.UserStory).filter(model.UserStory.id == id).first()
    if not db_story:
        raise HTTPException(status_code=404, detail="User Story tidak ditemukan")

    db_image = model.StoryImage(user_story_id=id, url=data.url, caption=data.caption)
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return db_image


@router.delete("/images/{image_id}")
def delete_story_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    db_image = db.query(model.StoryImage).filter(model.StoryImage.id == image_id).first()
    if not db_image:
        raise HTTPException(status_code=404, detail="Gambar tidak ditemukan")

    # Hapus file fisik dari disk kalau itu file upload lokal (bukan URL eksternal)
    if db_image.url.startswith("/static/"):
        filepath = db_image.url.lstrip("/")
        if os.path.exists(filepath):
            os.remove(filepath)

    db.delete(db_image)
    db.commit()
    return {"message": "Gambar berhasil dihapus"}