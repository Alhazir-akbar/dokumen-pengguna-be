from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta

import model  # Mengimpor model.py (singular)
import schemas
import auth
from database import engine, get_db

# Membuat tabel di database SQLite jika belum ada saat backend dijalankan
model.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Userdoc Backend API")

# Mengonfigurasi CORS agar Frontend Next.js (port 3000) bisa mengakses API ini
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # 1. Periksa apakah email sudah terdaftar
    db_user_email = db.query(model.User).filter(model.User.email == user.email).first()
    if db_user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sudah terdaftar"
        )
    
    # 2. Periksa apakah username sudah terdaftar
    db_user_username = db.query(model.User).filter(model.User.username == user.username).first()
    if db_user_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username sudah terdaftar"
        )
    
    # 3. Hash password dan simpan user baru
    hashed_password = auth.get_password_hash(user.password)
    new_user = model.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/auth/login", response_model=schemas.Token)
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    # 1. Cari user berdasarkan email
    user = db.query(model.User).filter(model.User.email == user_credentials.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah"
        )
    
    # 2. Verifikasi password
    if not auth.verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah"
        )
    
    # 3. Buat token akses JWT
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

# Endpoint testing untuk memastikan API berjalan
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "message": "Backend FastAPI siap digunakan!"}