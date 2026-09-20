from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from services.ai import suggest_story_refinement

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
            db.add(model.AcceptanceCriteria(user_story_id=id, description=ac_desc))

    # Sinkronisasi Tech Notes ke tabel database
    if data.tech_notes is not None:
        db.query(model.TechNote).filter(model.TechNote.user_story_id == id).delete()
        for note_content in data.tech_notes:
            db.add(model.TechNote(user_story_id=id, content=note_content))

    # Sinkronisasi Test Cases ke tabel database
    if data.test_cases is not None:
        db.query(model.TestCase).filter(model.TestCase.user_story_id == id).delete()
        for tc_desc in data.test_cases:
            db.add(model.TestCase(user_story_id=id, description=tc_desc))

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