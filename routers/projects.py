from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from services.ai import ProjectRequirementsOutput, generate_project_requirements, suggest_project_description

import model
import schemas
import auth
from database import get_db

router = APIRouter(prefix="/api/projects", tags=["Projects"])


def check_workspace_access(workspace_id: int, user_id: int, db: Session, required_roles: List[str] = None):
    """Helper untuk memverifikasi apakah user adalah anggota workspace dengan role tertentu"""
    membership = db.query(model.WorkspaceMember).filter(
        model.WorkspaceMember.workspace_id == workspace_id,
        model.WorkspaceMember.user_id == user_id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses ke ruang kerja ini"
        )

    if required_roles and membership.role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tindakan ini memerlukan peran: {', '.join(required_roles)}"
        )

    return membership


@router.post("", response_model=schemas.ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Membuat proyek baru di dalam workspace (Hanya Owner dan Editor yang diizinkan)"""
    check_workspace_access(
        workspace_id=project_data.workspace_id,
        user_id=current_user.id,
        db=db,
        required_roles=["owner", "editor"]
    )

    new_project = model.Project(
        name=project_data.name,
        description=project_data.description,
        application_type=project_data.application_type,
        domain_business=project_data.domain_business,
        target_users=project_data.target_users,
        business_goals=project_data.business_goals,
        repo_url=project_data.repo_url,
        workspace_id=project_data.workspace_id,
        creator_id=current_user.id
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


@router.get("", response_model=List[schemas.ProjectResponse])
def get_projects(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mendapatkan seluruh proyek dalam suatu workspace (Semua anggota workspace bisa akses)"""
    check_workspace_access(workspace_id=workspace_id, user_id=current_user.id, db=db)
    projects = db.query(model.Project).filter(model.Project.workspace_id == workspace_id).all()
    return projects


@router.get("/{id}", response_model=schemas.ProjectResponse)
def get_project_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mendapatkan detail dari sebuah proyek"""
    project = db.query(model.Project).filter(model.Project.id == id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyek tidak ditemukan")

    check_workspace_access(workspace_id=project.workspace_id, user_id=current_user.id, db=db)
    return project


@router.put("/{id}", response_model=schemas.ProjectResponse)
def update_project(
    id: int,
    project_data: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mengubah info proyek (Hanya Owner dan Editor yang diizinkan)"""
    project = db.query(model.Project).filter(model.Project.id == id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyek tidak ditemukan")

    check_workspace_access(
        workspace_id=project.workspace_id,
        user_id=current_user.id,
        db=db,
        required_roles=["owner", "editor"]
    )

    update_data = project_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{id}")
def delete_project(
    id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Menghapus proyek secara permanen (Hanya Owner yang diizinkan)"""
    project = db.query(model.Project).filter(model.Project.id == id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyek tidak ditemukan")

    check_workspace_access(
        workspace_id=project.workspace_id,
        user_id=current_user.id,
        db=db,
        required_roles=["owner"]
    )

    db.delete(project)
    db.commit()
    return {"message": "Proyek berhasil dihapus"}


@router.post("/suggest-description", response_model=schemas.SuggestDescriptionResponse)
def suggest_description(
    payload: schemas.SuggestDescriptionRequest,
    current_user: model.User = Depends(auth.get_current_user)
):
    """Memanggil AI untuk memberikan draf deskripsi proyek singkat, dipakai di step DescribeProject wizard"""
    try:
        description = suggest_project_description(
            project_name=payload.project_name,
            platform_type=payload.platform_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI gagal memberikan saran deskripsi: {str(e)}"
        )

    return schemas.SuggestDescriptionResponse(description=description)


@router.post("/{id}/generate-requirements")
def generate_requirements(
    id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Memanggil Gemini AI untuk menghasilkan draf kebutuhan proyek secara otomatis"""
    project = db.query(model.Project).filter(model.Project.id == id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyek tidak ditemukan")

    check_workspace_access(
        workspace_id=project.workspace_id,
        user_id=current_user.id,
        db=db,
        required_roles=["owner", "editor"]
    )

    project_rules = db.query(model.AIRule).filter(model.AIRule.project_id == id).all()
    workspace_rules = db.query(model.AIRule).filter(
        model.AIRule.workspace_id == project.workspace_id,
        model.AIRule.project_id == None
    ).all()

    all_rules_text = [rule.content for rule in project_rules] + [rule.content for rule in workspace_rules]

    try:
        requirements_draft = generate_project_requirements(
            project_name=project.name,
            project_description=project.description or "",
            application_type=project.application_type or "",
            domain_business=project.domain_business or "",
            target_users=project.target_users or "",
            business_goals=project.business_goals or "",
            ai_rules=all_rules_text
        )
        return requirements_draft

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI gagal memproses data: {str(e)}"
        )


@router.post("/{id}/save-requirements", status_code=status.HTTP_201_CREATED)
def save_project_requirements(
    id: int,
    requirements: ProjectRequirementsOutput,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Menyimpan draf kebutuhan proyek (User Types, Epics, Stories + AC + Tech Notes +
    Test Cases, NFRs) hasil generate AI ke database"""
    project = db.query(model.Project).filter(model.Project.id == id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyek tidak ditemukan")

    check_workspace_access(
        workspace_id=project.workspace_id,
        user_id=current_user.id,
        db=db,
        required_roles=["owner", "editor"]
    )

    # 1. Simpan User Types
    user_type_map = {}
    for ut_data in requirements.user_types:
        db_ut = model.UserType(
            name=ut_data.name,
            description=ut_data.description,
            project_id=id
        )
        db.add(db_ut)
        db.commit()
        db.refresh(db_ut)
        user_type_map[ut_data.name] = db_ut.id

    # 2. Simpan Epics
    epic_map = {}
    for epic_data in requirements.epics:
        db_epic = model.Epic(
            name=epic_data.name,
            description=epic_data.description,
            project_id=id
        )
        db.add(db_epic)
        db.commit()
        db.refresh(db_epic)
        epic_map[epic_data.name] = db_epic.id

    # 3. Simpan User Stories + Acceptance Criteria + Tech Notes + Test Cases
    for story_data in requirements.user_stories:
        epic_id = epic_map.get(story_data.epic_name)
        user_type_id = user_type_map.get(story_data.user_type)

        db_story = model.UserStory(
            epic_id=epic_id,
            user_type_id=user_type_id,
            as_a=story_data.user_type,
            i_want=story_data.story_name,
            so_that=story_data.description,
            status="draft",
            project_id=id
        )
        db.add(db_story)
        db.commit()
        db.refresh(db_story)

        for ac_desc in story_data.acceptance_criteria:
            db_ac = model.AcceptanceCriteria(
                user_story_id=db_story.id,
                description=ac_desc
            )
            db.add(db_ac)

        # TAMBAHAN: simpan tech notes
        for note in story_data.tech_notes:
            db_note = model.TechNote(
                user_story_id=db_story.id,
                content=note
            )
            db.add(db_note)

        # TAMBAHAN: simpan test cases
        for tc in story_data.test_cases:
            db_tc = model.TestCase(
                user_story_id=db_story.id,
                description=tc
            )
            db.add(db_tc)

    # 4. Simpan NFRs
    for nfr_data in requirements.nfrs:
        db_nfr = model.NFR(
            category=nfr_data.category,
            description=nfr_data.description,
            project_id=id
        )
        db.add(db_nfr)

    db.commit()
    return {"message": "Draf kebutuhan proyek berhasil disimpan ke database"}