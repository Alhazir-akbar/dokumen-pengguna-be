from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timezone
import os

import model
import auth
from database import get_db

router = APIRouter(prefix="/api/tokens", tags=["Token Usage"])

MONTHLY_DEFAULT_QUOTA = 500_000  # Kuota 500.000 token per bulan per akun

@router.get("/usage")
def get_user_token_usage(
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mengambil ringkasan kuota dan riwayat pemakaian token AI pengguna"""
    
    # Ambil awal bulan ini (UTC)
    now = datetime.now(timezone.utc)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    # 1. Total token bulan ini
    monthly_used = db.query(func.sum(model.AiTokenUsage.total_tokens)).filter(
        model.AiTokenUsage.user_id == current_user.id,
        model.AiTokenUsage.created_at >= start_of_month
    ).scalar() or 0

    remaining = max(0, MONTHLY_DEFAULT_QUOTA - monthly_used)
    percentage = min(100.0, round((monthly_used / MONTHLY_DEFAULT_QUOTA) * 100, 1))

    # 2. Breakdown per Provider
    providers = ["gemini", "openrouter", "groq"]
    usage_by_provider = {}
    for p in providers:
        toks = db.query(func.sum(model.AiTokenUsage.total_tokens)).filter(
            model.AiTokenUsage.user_id == current_user.id,
            model.AiTokenUsage.provider == p
        ).scalar() or 0
        usage_by_provider[p] = toks

    # 3. Breakdown per Fitur
    features_raw = db.query(
        model.AiTokenUsage.feature,
        func.sum(model.AiTokenUsage.total_tokens)
    ).filter(
        model.AiTokenUsage.user_id == current_user.id
    ).group_by(model.AiTokenUsage.feature).all()
    
    usage_by_feature = {f: toks for f, toks in features_raw}

    # 4. Riwayat 15 request terakhir
    recent_query = db.query(model.AiTokenUsage).filter(
        model.AiTokenUsage.user_id == current_user.id
    )
    if project_id:
        recent_query = recent_query.filter(model.AiTokenUsage.project_id == project_id)
    
    recent_records = recent_query.order_by(model.AiTokenUsage.created_at.desc()).limit(15).all()

    history = [
        {
            "id": r.id,
            "feature": r.feature,
            "provider": r.provider,
            "model_name": r.model_name,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "total_tokens": r.total_tokens,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in recent_records
    ]

    # 5. Informasi Provider Aktif dari Environment
    providers_info = [
        {
            "name": "Google Gemini",
            "provider_key": "gemini",
            "model": os.getenv("GEMINI_MODEL_NAME") or os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            "status": "Ready" if os.getenv("GEMINI_API_KEY") else "Not Configured"
        },
        {
            "name": "OpenRouter AI",
            "provider_key": "openrouter",
            "model": os.getenv("OPENROUTER_MODEL_NAME", "meta-llama/llama-3.3-70b-instruct:free"),
            "status": "Ready" if os.getenv("OPENROUTER_API_KEY") else "Not Configured"
        },
        {
            "name": "Groq Cloud LPU",
            "provider_key": "groq",
            "model": os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile"),
            "status": "Ready" if os.getenv("GROQ_API_KEY") else "Not Configured"
        }
    ]

    return {
        "monthly_quota": MONTHLY_DEFAULT_QUOTA,
        "monthly_used": monthly_used,
        "remaining_tokens": remaining,
        "usage_percentage": percentage,
        "usage_by_provider": usage_by_provider,
        "usage_by_feature": usage_by_feature,
        "providers_info": providers_info,
        "history": history
    }