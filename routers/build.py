# routers/build.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import model
import schemas
import auth
from database import get_db
from services.ai import suggest_tech_stack, suggest_coding_guidelines, suggest_dev_plan

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
        if data.ui_layer is not None:
            tech_stack.ui_layer = data.ui_layer
        if data.app_layer is not None:
            tech_stack.app_layer = data.app_layer
        if data.data_layer is not None:
            tech_stack.data_layer = data.data_layer
        if data.integration_layer is not None:
            tech_stack.integration_layer = data.integration_layer
    else:
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


# ============ TAMBAHAN: AUTO-GENERATE SEMUANYA VIA AI ============
# Dipanggil otomatis begitu wizard project-setup selesai, supaya Build page sudah
# terisi draf awal (bukan kosong menunggu user isi manual). Best-effort: kalau AI
# gagal di salah satu bagian, bagian lain tetap dicoba disimpan.

@router.post("/{project_id}/generate-build-defaults", status_code=status.HTTP_201_CREATED)
def generate_build_defaults(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Generate draf awal Tech Stack, Coding Guidelines, dan Development Plan sekaligus via AI"""
    project = db.query(model.Project).filter(model.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan")

    results = {"tech_stack": False, "guidelines": False, "dev_plan": False, "errors": []}

    # 1. Tech Stack
    tech_stack_summary = ""
    try:
        ts = suggest_tech_stack(project.name, project.description or "", project.application_type or "")
        existing_ts = db.query(model.TechStack).filter(model.TechStack.project_id == project_id).first()
        if not existing_ts:
            db.add(model.TechStack(
                project_id=project_id,
                ui_layer=ts.ui_layer,
                app_layer=ts.app_layer,
                data_layer=ts.data_layer,
                integration_layer=ts.integration_layer,
            ))
            db.commit()
        results["tech_stack"] = True
        tech_stack_summary = f"UI: {ts.ui_layer}, Backend: {ts.app_layer}, Database: {ts.data_layer}, Integration: {ts.integration_layer}"
    except Exception as e:
        results["errors"].append(f"tech_stack: {str(e)}")

    # 2. Coding Guidelines (butuh tech stack summary dari langkah 1 kalau berhasil)
    try:
        if not tech_stack_summary:
            tech_stack_summary = f"{project.application_type or 'Web Application'}"
        gl = suggest_coding_guidelines(project.name, tech_stack_summary)
        existing_count = db.query(model.CodingGuideline).filter(model.CodingGuideline.project_id == project_id).count()
        if existing_count == 0:
            for item in gl.guidelines:
                db.add(model.CodingGuideline(project_id=project_id, title=item.title, content=item.content))
            db.commit()
        results["guidelines"] = True
    except Exception as e:
        results["errors"].append(f"guidelines: {str(e)}")

    # 3. Development Plan (satu task per Epic yang sudah ada)
    try:
        epics = db.query(model.Epic).filter(model.Epic.project_id == project_id).all()
        epic_names = [e.name for e in epics]
        dp = suggest_dev_plan(project.name, epic_names)
        existing_plan_count = db.query(model.DevelopmentPlan).filter(model.DevelopmentPlan.project_id == project_id).count()
        if existing_plan_count == 0:
            for item in dp.items:
                db.add(model.DevelopmentPlan(project_id=project_id, title=item.title, description=item.description, status="todo"))
            db.commit()
        results["dev_plan"] = True
    except Exception as e:
        results["errors"].append(f"dev_plan: {str(e)}")

    return results