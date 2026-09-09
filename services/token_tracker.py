import math
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import model

def estimate_tokens(text: str) -> int:
    """Estimasi jumlah token (1 token ~= 3.8 - 4 karakter)"""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 3.8))

def record_token_usage(
    db: Session,
    user_id: int,
    provider: str,
    model_name: str,
    feature: str,
    prompt_text: str = "",
    response_text: str = "",
    project_id: int = None,
    workspace_id: int = None,
    actual_prompt_tokens: int = None,
    actual_completion_tokens: int = None,
):
    """Mencatat konsumsi token AI ke database Supabase"""
    prompt_toks = actual_prompt_tokens if actual_prompt_tokens is not None else estimate_tokens(prompt_text)
    comp_toks = actual_completion_tokens if actual_completion_tokens is not None else estimate_tokens(response_text)
    total_toks = prompt_toks + comp_toks

    usage_entry = model.AiTokenUsage(
        user_id=user_id,
        workspace_id=workspace_id,
        project_id=project_id,
        provider=provider,
        model_name=model_name,
        feature=feature,
        prompt_tokens=prompt_toks,
        completion_tokens=comp_toks,
        total_tokens=total_toks,
        created_at=datetime.now(timezone.utc)
    )
    db.add(usage_entry)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️ Gagal mencatat token usage: {e}")