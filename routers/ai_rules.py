from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import model
import schemas
import auth
from database import get_db
from routers.projects import check_workspace_access

router = APIRouter(tags=["AI Rules"])

# ATURAN AI TINGKAT PROYEK
@router.POST("/api/projects/{priject_id}/ai-rules", response_model=schemas.AIRuleResponse,
status_code=status.HTTP_201_CREATED)
def create_project_ai_rule(
    project_id: int,
    rule_data: schemas.AIRuleCreate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Menambahkan aturan AI baru untuk proyek tertentu (Hanya Owner dan Editor)"""
    project = db.query(model.Project).filter(model.Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyek tidak ditemukan"
        )
    check_workspace_access(
        workspace_id=project.workspace_id,
        user_id=current_user.id,
        db=db,
        required_roles=["owner","editor"]
    )

    new_rule = model.AIRule(
        name=rule_data.name,
        content=rule_data.content,
        project_id=project_id,
        workspace_id=None
    )

    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    return new_rule

@router.get("/api/projects/{project_id}/ai-rules",
response_model=List[schemas.AIRuleResponse])
def get_project_ai_rules(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mendapatkan daftar seluruh aturan AI pada sebuah proyek"""
    project = db.query(model.Project).filter(model.Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyek tidak ditemukan"
        )
    check_workspace_access(
        workspace_id=project.workspace_id,
        user_id=current_user.id,
        db=db
    )

    rules = db.query(model.AIRule).filter(model.AIRule.project_id == project_id).all()
    return rules


# ATURANAI TINGKAT TIM / WORKSPACE

@router.post("/api/workspace/{workspace_id}/ai_rules", response_model=schemas.AIRuleResponse, status_code=status.HTTP_201_CREATED)
def create_workspace_ai_rule(
    workspace_id: int,
    rule_data: schemas.AIRuleCreate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Menambahkan aturan AI baru di tingkat Workspace (hanya Owner dan Editor)"""
    check_workspace_access(
        workspace_id=workspace_id,
        user_id=current_user.id,
        db=db,
        required_roles=["owner", "editor"]
    )
    new_rule = model.AIRule(
        name=rule_data.name,
        content=rule_data.content,
        project_id=None,
        workspace_id=workspace_id
    )
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    return new_rule
@router.get("/api/workspaces/{workspace_id}/ai-rules", response_model=List[schemas.AIRuleResponse])
def get_workspace_ai_rules(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mendapatkan seluruh aturan AI di tingkat Workspace"""
    # 1. Pastikan user adalah anggota workspace
    check_workspace_access(
        workspace_id=workspace_id,
        user_id=current_user.id,
        db=db
    )
    
    # 2. Ambil seluruh aturan AI yang terikat ke workspace ini (dan tidak terikat ke project tertentu)
    rules = db.query(model.AIRule).filter(
        model.AIRule.workspace_id == workspace_id,
        model.AIRule.project_id == None
    ).all()
    return rules
# ================= PENGHAPUSAN ATURAN AI (UMUM) =================
@router.delete("/api/ai-rules/{id}")
def delete_ai_rule(
    id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Menghapus aturan AI (Tingkat Proyek maupun Workspace)"""
    rule = db.query(model.AIRule).filter(model.AIRule.id == id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aturan AI tidak ditemukan"
        )
    
    # Deteksi secara dinamis ID Workspace untuk verifikasi hak akses
    if rule.project_id:
        project = db.query(model.Project).filter(model.Project.id == rule.project_id).first()
        workspace_id = project.workspace_id
    else:
        workspace_id = rule.workspace_id
        
    check_workspace_access(
        workspace_id=workspace_id,
        user_id=current_user.id,
        db=db,
        required_roles=["owner", "editor"]
    )
    
    db.delete(rule)
    db.commit()
    return {"message": "Aturan AI berhasil dihapus"}