from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session
from typing import Optional

import model
import schemas
import auth
from database import get_db
from services.storage import upload_avatar  # <-- Impor helper upload MinIO kita

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
    """Mengubah info profil (nama lengkap)"""
    if profile_data.full_name is not None:
        current_user.full_name = profile_data.full_name
    if profile_data.avatar_url is not None:
        current_user.avatar_url = profile_data.avatar_url
        
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/avatar", response_model=schemas.UserResponse)
def upload_profile_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mengunggah foto profil ke MinIO dan memperbarui URL avatar di database"""
    # 1. Validasi tipe file (harus berupa gambar)
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File yang diunggah harus berupa gambar (JPG, PNG, GIF)"
        )
    
    try:
        # 2. Baca data biner dari file
        file_content = file.file.read()
        
        # 3. Buat nama file unik berdasarkan ID pengguna agar tidak saling tindih
        file_ext = file.filename.split(".")[-1]  # mengambil ekstensi seperti png/jpg
        unique_filename = f"user_{current_user.id}_avatar.{file_ext}"
        
        # 4. Kirim file ke MinIO menggunakan helper
        avatar_url = upload_avatar(
            file_data=file_content,
            file_name=unique_filename,
            content_type=file.content_type
        )
        
        # 5. Simpan URL publik hasil upload ke database user
        current_user.avatar_url = avatar_url
        db.commit()
        db.refresh(current_user)
        
        return current_user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengunggah foto profil: {str(e)}"
        )

@router.put("/change-password")
def change_password(
    password_data: schemas.PasswordUpdate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mengubah kata sandi akun"""
    # 1. Verifikasi apakah password lama cocok
    if not auth.verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi lama tidak sesuai"
        )
    
    # 2. Enkripsi dan simpan password baru
    current_user.hashed_password = auth.get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Kata sandi berhasil diubah"}