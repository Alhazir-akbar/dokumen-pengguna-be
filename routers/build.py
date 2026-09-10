# routers/build.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

import model
import schemas
import auth
from database import get_db
from services.ai import (
    suggest_tech_stack,
    suggest_guideline_by_category,
    suggest_dev_plan_for_epic,
    GUIDELINE_CATEGORY_LABELS,
)

router = APIRouter(prefix="/api/projects", tags=["Build"])

GUIDELINE_CATEGORIES = list(GUIDELINE_CATEGORY_LABELS.keys())


def _get_project_or_404(db: Session, project_id: int) -> model.Project:
    project = db.query(model.Project).filter(model.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan")
    return project


def _tech_stack_summary(ts: Optional[model.TechStack]) -> str:
    """Ringkasan tech stack dalam satu baris teks, dipakai sebagai konteks untuk prompt AI
    (generate coding guidelines & dev plan) supaya hasilnya spesifik terhadap stack proyek."""
    if not ts:
        return ""
    parts = []
    if ts.ui_framework or ts.ui_language:
        parts.append(f"UI: {ts.ui_framework or ''} ({ts.ui_language or ''})".strip())
    if ts.app_framework or ts.app_language:
        parts.append(f"Backend: {ts.app_framework or ''} ({ts.app_language or ''})".strip())
    if ts.data_layer:
        parts.append(f"Database: {ts.data_layer}")
    if ts.integration_layer:
        parts.append(f"Integration: {ts.integration_layer}")
    return ", ".join(parts)


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
    _get_project_or_404(db, project_id)
    tech_stack = db.query(model.TechStack).filter(
        model.TechStack.project_id == project_id
    ).first()

    update_fields = data.model_dump(exclude_unset=True)

    if tech_stack:
        for field, value in update_fields.items():
            setattr(tech_stack, field, value)
    else:
        tech_stack = model.TechStack(project_id=project_id, **update_fields)
        db.add(tech_stack)

    db.commit()
    db.refresh(tech_stack)
    return tech_stack


@router.post("/{project_id}/tech-stack/generate", response_model=schemas.TechStackResponse)
def generate_tech_stack(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Generate saran Technology Stack lengkap via AI, lalu langsung disimpan (upsert)."""
    project = _get_project_or_404(db, project_id)
    try:
        ts = suggest_tech_stack(project.name, project.description or "", project.application_type or "")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gagal generate tech stack: {str(e)}")

    tech_stack = db.query(model.TechStack).filter(
        model.TechStack.project_id == project_id
    ).first()

    values = dict(
        target_users=ts.target_users,
        scale=ts.scale,
        platform=ts.platform,
        ui_language=ts.ui_language,
        ui_framework=ts.ui_framework,
        ui_library=ts.ui_library,
        app_language=ts.app_language,
        app_framework=ts.app_framework,
        data_layer=ts.data_layer,
        integration_layer=ts.integration_layer,
    )

    if tech_stack:
        for field, value in values.items():
            setattr(tech_stack, field, value)
    else:
        tech_stack = model.TechStack(project_id=project_id, **values)
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
    """Mengambil semua coding guidelines sebuah proyek (5 kategori tetap + custom)"""
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
    """Membuat coding guideline baru (custom, atau kategori tetap kalau belum ada)"""
    guideline = model.CodingGuideline(
        project_id=project_id,
        title=data.title,
        content=data.content,
        category=data.category,
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
    if data.category is not None:
        guideline.category = data.category

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


@router.post("/{project_id}/guidelines/generate", response_model=schemas.CodingGuidelineResponse)
def generate_guideline(
    project_id: int,
    data: schemas.GenerateGuidelineRequest,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Generate (atau regenerate) satu coding guideline untuk kategori tetap tertentu via AI."""
    if data.category not in GUIDELINE_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Kategori tidak dikenal: {data.category}")

    project = _get_project_or_404(db, project_id)
    tech_stack = db.query(model.TechStack).filter(model.TechStack.project_id == project_id).first()
    summary = _tech_stack_summary(tech_stack) or (project.application_type or "")

    try:
        suggestion = suggest_guideline_by_category(project.name, summary, data.category)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    guideline = db.query(model.CodingGuideline).filter(
        model.CodingGuideline.project_id == project_id,
        model.CodingGuideline.category == data.category,
    ).first()

    if guideline:
        guideline.title = suggestion.title
        guideline.content = suggestion.content
    else:
        guideline = model.CodingGuideline(
            project_id=project_id,
            category=data.category,
            title=suggestion.title,
            content=suggestion.content,
        )
        db.add(guideline)

    db.commit()
    db.refresh(guideline)
    return guideline


@router.post("/{project_id}/guidelines/generate-all", response_model=schemas.GenerateGuidelinesAllResponse)
def generate_all_guidelines(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Generate kelima kategori coding guideline tetap sekaligus. Best-effort per kategori
    -- kalau satu kategori gagal, kategori lain tetap dicoba & dilaporkan di 'errors'."""
    project = _get_project_or_404(db, project_id)
    tech_stack = db.query(model.TechStack).filter(model.TechStack.project_id == project_id).first()
    summary = _tech_stack_summary(tech_stack) or (project.application_type or "")

    results: List[model.CodingGuideline] = []
    errors: List[str] = []

    for category in GUIDELINE_CATEGORIES:
        try:
            suggestion = suggest_guideline_by_category(project.name, summary, category)
        except Exception as e:
            errors.append(f"{GUIDELINE_CATEGORY_LABELS[category]}: {str(e)}")
            continue

        guideline = db.query(model.CodingGuideline).filter(
            model.CodingGuideline.project_id == project_id,
            model.CodingGuideline.category == category,
        ).first()

        if guideline:
            guideline.title = suggestion.title
            guideline.content = suggestion.content
        else:
            guideline = model.CodingGuideline(
                project_id=project_id,
                category=category,
                title=suggestion.title,
                content=suggestion.content,
            )
            db.add(guideline)

        db.commit()
        db.refresh(guideline)
        results.append(guideline)

    return schemas.GenerateGuidelinesAllResponse(guidelines=results, errors=errors)


# ============ DEVELOPMENT PLANS ============

@router.get("/{project_id}/epics-options", response_model=List[schemas.EpicOptionResponse])
def get_epic_options(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Daftar ringkas Epic (id + nama) proyek, dipakai dropdown 'pilih requirement' saat membuat Dev Plan."""
    return db.query(model.Epic).filter(model.Epic.project_id == project_id).all()


@router.get("/{project_id}/dev-plans", response_model=List[schemas.DevelopmentPlanResponse])
def get_dev_plans(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mengambil semua development plans sebuah proyek"""
    return db.query(model.DevelopmentPlan).filter(
        model.DevelopmentPlan.project_id == project_id
    ).order_by(model.DevelopmentPlan.created_at.desc()).all()


@router.post("/{project_id}/dev-plans", response_model=schemas.DevelopmentPlanResponse, status_code=status.HTTP_201_CREATED)
def create_dev_plan(
    project_id: int,
    data: schemas.DevelopmentPlanCreate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Membuat development plan baru (manual)"""
    plan = model.DevelopmentPlan(
        project_id=project_id,
        title=data.title,
        description=data.description,
        status=data.status or "todo",
        epic_id=data.epic_id,
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
    if data.epic_id is not None:
        plan.epic_id = data.epic_id

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


@router.post("/{project_id}/dev-plans/generate", response_model=schemas.DevelopmentPlanResponse, status_code=status.HTTP_201_CREATED)
def generate_dev_plan(
    project_id: int,
    data: schemas.GenerateDevPlanRequest,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Generate satu Development Plan detail via AI berdasarkan Epic/requirement yang dipilih."""
    project = _get_project_or_404(db, project_id)
    epic = db.query(model.Epic).filter(
        model.Epic.id == data.epic_id,
        model.Epic.project_id == project_id
    ).first()
    if not epic:
        raise HTTPException(status_code=404, detail="Epic tidak ditemukan")

    tech_stack = db.query(model.TechStack).filter(model.TechStack.project_id == project_id).first()
    tech_summary = _tech_stack_summary(tech_stack)

    guidelines = db.query(model.CodingGuideline).filter(model.CodingGuideline.project_id == project_id).all()
    guidelines_summary = "; ".join([g.title for g in guidelines]) if guidelines else ""

    try:
        suggestion = suggest_dev_plan_for_epic(
            project.name, epic.name, epic.description or "", tech_summary, guidelines_summary
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    plan = model.DevelopmentPlan(
        project_id=project_id,
        epic_id=epic.id,
        title=suggestion.title,
        description=suggestion.description,
        status="draft",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


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
    """Generate draf awal Tech Stack, Coding Guidelines (5 kategori tetap), dan
    Development Plan (satu per Epic) sekaligus via AI."""
    project = _get_project_or_404(db, project_id)

    results = {"tech_stack": False, "guidelines": False, "dev_plan": False, "errors": []}

    # 1. Tech Stack
    tech_stack_summary = ""
    existing_ts = db.query(model.TechStack).filter(model.TechStack.project_id == project_id).first()
    try:
        if not existing_ts:
            ts = suggest_tech_stack(project.name, project.description or "", project.application_type or "")
            existing_ts = model.TechStack(
                project_id=project_id,
                target_users=ts.target_users,
                scale=ts.scale,
                platform=ts.platform,
                ui_language=ts.ui_language,
                ui_framework=ts.ui_framework,
                ui_library=ts.ui_library,
                app_language=ts.app_language,
                app_framework=ts.app_framework,
                data_layer=ts.data_layer,
                integration_layer=ts.integration_layer,
            )
            db.add(existing_ts)
            db.commit()
            db.refresh(existing_ts)
        results["tech_stack"] = True
        tech_stack_summary = _tech_stack_summary(existing_ts)
    except Exception as e:
        results["errors"].append(f"tech_stack: {str(e)}")

    # 2. Coding Guidelines (5 kategori tetap, skip kategori yang sudah ada isinya)
    try:
        existing_categories = {
            g.category for g in db.query(model.CodingGuideline).filter(
                model.CodingGuideline.project_id == project_id
            ).all()
        }
        for category in GUIDELINE_CATEGORIES:
            if category in existing_categories:
                continue
            try:
                suggestion = suggest_guideline_by_category(
                    project.name, tech_stack_summary or (project.application_type or ""), category
                )
                db.add(model.CodingGuideline(
                    project_id=project_id,
                    category=category,
                    title=suggestion.title,
                    content=suggestion.content,
                ))
                db.commit()
            except Exception as inner_e:
                results["errors"].append(f"guidelines[{category}]: {str(inner_e)}")
        results["guidelines"] = True
    except Exception as e:
        results["errors"].append(f"guidelines: {str(e)}")

    # 3. Development Plan (satu draft per Epic yang sudah ada, hanya kalau belum ada plan sama sekali)
    try:
        epics = db.query(model.Epic).filter(model.Epic.project_id == project_id).all()
        existing_plan_count = db.query(model.DevelopmentPlan).filter(
            model.DevelopmentPlan.project_id == project_id
        ).count()
        if existing_plan_count == 0:
            guidelines = db.query(model.CodingGuideline).filter(model.CodingGuideline.project_id == project_id).all()
            guidelines_summary = "; ".join([g.title for g in guidelines]) if guidelines else ""
            for epic in epics:
                try:
                    suggestion = suggest_dev_plan_for_epic(
                        project.name, epic.name, epic.description or "", tech_stack_summary, guidelines_summary
                    )
                    db.add(model.DevelopmentPlan(
                        project_id=project_id,
                        epic_id=epic.id,
                        title=suggestion.title,
                        description=suggestion.description,
                        status="draft",
                    ))
                    db.commit()
                except Exception as inner_e:
                    results["errors"].append(f"dev_plan[{epic.name}]: {str(inner_e)}")
        results["dev_plan"] = True
    except Exception as e:
        results["errors"].append(f"dev_plan: {str(e)}")

    return results