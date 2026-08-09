from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

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
    # 1. Validasi akses user ke workspace (Harus Owner atau Editor)
    check_workspace_access(
        workspace_id=project_data.workspace_id,
        user_id=current_user.id,
        db=db,
        required_roles=["owner", "editor"]
    )

    # 2. Buat proyek baru
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
    # 1. Validasi akses user ke workspace
    check_workspace_access(
        workspace_id=workspace_id,
        user_id=current_user.id,
        db=db
    )

    # 2. Ambil seluruh proyek
    projects = db.query(model.Project).filter(model.Project.workspace_id == workspace_id).all()
    return projects

@router.get("/{id}", response_model=schemas.ProjectResponse)
def get_project_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mendapatkan detail dari sebuah proyek"""
    # 1. Cari proyek
    project = db.query(model.Project).filter(model.Project.id == id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyek tidak ditemukan"
        )

    # 2. Validasi akses user ke workspace proyek tersebut
    check_workspace_access(
        workspace_id=project.workspace_id,
        user_id=current_user.id,
        db=db
    )

    return project

@router.put("/{id}", response_model=schemas.ProjectResponse)
def update_project(
    id: int,
    project_data: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mengubah info proyek (Hanya Owner dan Editor yang diizinkan)"""
    # 1. Cari proyek
    project = db.query(model.Project).filter(model.Project.id == id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyek tidak ditemukan"
        )

    # 2. Validasi akses user ke workspace proyek tersebut (Harus Owner atau Editor)
    check_workspace_access(
        workspace_id=project.workspace_id,
        user_id=current_user.id,
        db=db,
        required_roles=["owner", "editor"]
    )

    # 3. Update data yang dikirim saja
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
    # 1. Cari proyek
    project = db.query(model.Project).filter(model.Project.id == id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyek tidak ditemukan"
        )

    # 2. Validasi akses user ke workspace proyek tersebut (Harus Owner)
    check_workspace_access(
        workspace_id=project.workspace_id,
        user_id=current_user.id,
        db=db,
        required_roles=["owner"]
    )

    db.delete(project)
    db.commit()
    
    return {"message": "Proyek berhasil dihapus"}