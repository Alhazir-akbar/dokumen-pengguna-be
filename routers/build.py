# routers/build.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import model
import schemas
import auth
from database import get_db

router = APIRouter(prefix="/api/projects", tags=["Build"])


# ============ TECH STACK ============

@router.get("/{project_id}/tech-stack", response_model=schemas.TechStackResponse)
def get_tech_stack(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mengambil konfigurasi technology stack sebuah proyek"""
    tech_stack = db.query(model.TechStack).filter(
        model.TechStack.project_id == project_id
    ).first()

    if not tech_stack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tech stack belum dikonfigurasi untuk proyek ini"
        )
    return tech_stack


@router.put("/{project_id}/tech-stack", response_model=schemas.TechStackResponse)
def upsert_tech_stack(
    project_id: int,
    data: schemas.TechStackUpdate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Membuat atau memperbarui konfigurasi technology stack"""
    tech_stack = db.query(model.TechStack).filter(
        model.TechStack.project_id == project_id
    ).first()

    if tech_stack:
        # Update jika sudah ada
        if data.ui_layer is not None:
            tech_stack.ui_layer = data.ui_layer
        if data.app_layer is not None:
            tech_stack.app_layer = data.app_layer
        if data.data_layer is not None:
            tech_stack.data_layer = data.data_layer
        if data.integration_layer is not None:
            tech_stack.integration_layer = data.integration_layer
    else:
        # Buat baru jika belum ada
        tech_stack = model.TechStack(
            project_id=project_id,
            ui_layer=data.ui_layer,
            app_layer=data.app_layer,
            data_layer=data.data_layer,
            integration_layer=data.integration_layer
        )
        db.add(tech_stack)

    db.commit()
    db.refresh(tech_stack)
    return tech_stack


# ============ CODING GUIDELINES ============

@router.get("/{project_id}/guidelines", response_model=List[schemas.CodingGuidelineResponse])
def get_guidelines(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mengambil semua coding guidelines sebuah proyek"""
    return db.query(model.CodingGuideline).filter(
        model.CodingGuideline.project_id == project_id
    ).all()


@router.post("/{project_id}/guidelines", response_model=schemas.CodingGuidelineResponse, status_code=status.HTTP_201_CREATED)
def create_guideline(
    project_id: int,
    data: schemas.CodingGuidelineCreate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Membuat coding guideline baru"""
    guideline = model.CodingGuideline(
        project_id=project_id,
        title=data.title,
        content=data.content
    )
    db.add(guideline)
    db.commit()
    db.refresh(guideline)
    return guideline


@router.put("/{project_id}/guidelines/{guideline_id}", response_model=schemas.CodingGuidelineResponse)
def update_guideline(
    project_id: int,
    guideline_id: int,
    data: schemas.CodingGuidelineUpdate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Memperbarui coding guideline"""
    guideline = db.query(model.CodingGuideline).filter(
        model.CodingGuideline.id == guideline_id,
        model.CodingGuideline.project_id == project_id
    ).first()

    if not guideline:
        raise HTTPException(status_code=404, detail="Guideline tidak ditemukan")

    if data.title is not None:
        guideline.title = data.title
    if data.content is not None:
        guideline.content = data.content

    db.commit()
    db.refresh(guideline)
    return guideline


@router.delete("/{project_id}/guidelines/{guideline_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_guideline(
    project_id: int,
    guideline_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Menghapus coding guideline"""
    guideline = db.query(model.CodingGuideline).filter(
        model.CodingGuideline.id == guideline_id,
        model.CodingGuideline.project_id == project_id
    ).first()

    if not guideline:
        raise HTTPException(status_code=404, detail="Guideline tidak ditemukan")

    db.delete(guideline)
    db.commit()


# ============ DEVELOPMENT PLANS ============

@router.get("/{project_id}/dev-plans", response_model=List[schemas.DevelopmentPlanResponse])
def get_dev_plans(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mengambil semua development plans sebuah proyek"""
    return db.query(model.DevelopmentPlan).filter(
        model.DevelopmentPlan.project_id == project_id
    ).all()


@router.post("/{project_id}/dev-plans", response_model=schemas.DevelopmentPlanResponse, status_code=status.HTTP_201_CREATED)
def create_dev_plan(
    project_id: int,
    data: schemas.DevelopmentPlanCreate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Membuat development plan baru"""
    plan = model.DevelopmentPlan(
        project_id=project_id,
        title=data.title,
        description=data.description,
        status=data.status or "todo"
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.put("/{project_id}/dev-plans/{plan_id}", response_model=schemas.DevelopmentPlanResponse)
def update_dev_plan(
    project_id: int,
    plan_id: int,
    data: schemas.DevelopmentPlanUpdate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Memperbarui development plan (termasuk mengubah status)"""
    plan = db.query(model.DevelopmentPlan).filter(
        model.DevelopmentPlan.id == plan_id,
        model.DevelopmentPlan.project_id == project_id
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Development plan tidak ditemukan")

    if data.title is not None:
        plan.title = data.title
    if data.description is not None:
        plan.description = data.description
    if data.status is not None:
        plan.status = data.status

    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{project_id}/dev-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dev_plan(
    project_id: int,
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Menghapus development plan"""
    plan = db.query(model.DevelopmentPlan).filter(
        model.DevelopmentPlan.id == plan_id,
        model.DevelopmentPlan.project_id == project_id
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Development plan tidak ditemukan")

    db.delete(plan)
    db.commit()