from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import model
import schemas
import auth
from database import get_db

router = APIRouter(prefix="/api/profile", tags=["Profile"])

@router.get("", response_model=schemas.UserResponse)
def get_profile(current_user: model.User = Depends(auth.get_current_user)):
    """Mendapatkan informasi profil user yang sedang login"""
    return current_user

@router.put("", response_model=schemas.UserResponse)
def update_profile(
    profile_data: schemas.ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mengubah info profil (nama lengkap / foto profil)"""
    if profile_data.full_name is not None:
        current_user.full_name = profile_data.full_name
    if profile_data.avatar_url is not None:
        current_user.avatar_url = profile_data.avatar_url
        
    db.commit()
    db.refresh(current_user)
    return current_user

@router.put("/change-password")
def change_password(
    password_data: schemas.PasswordUpdate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mengubah kata sandi akun"""
    # 1. Verifikasi apakah password lama cocok (menggunakan current_password sesuai skema)
    if not auth.verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi lama tidak sesuai"
        )
    
    # 2. Enkripsi dan simpan password baru
    current_user.hashed_password = auth.get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Kata sandi berhasil diubah"}