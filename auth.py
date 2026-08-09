from datetime import datetime, timedelta, timezone
from typing import Union
from jose import jwt, JWTError
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials  # Diubah ke HTTPBearer
from sqlalchemy.orm import Session

import model
from database import get_db

SECRET_KEY = "MBGKOPDES"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

# Menggunakan HTTPBearer untuk mempermudah penempelan token di Swagger UI
security_scheme = HTTPBearer(auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Memverifikasi password menggunakan native bcrypt"""
    plain_pwd_bytes = plain_password.encode('utf-8')
    hashed_pwd_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_pwd_bytes, hashed_pwd_bytes)

def get_password_hash(password: str) -> str:
    """Mengenkripsi password menggunakan native bcrypt"""
    plain_pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(plain_pwd_bytes, salt)
    return hashed_password.decode('utf-8')

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    """Membuat token JWT dengan waktu kadaluarsa"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(security_scheme),  # Dependency diganti
    db: Session = Depends(get_db)
) -> model.User:
    """Dependency untuk mendapatkan data user yang login menggunakan token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid atau kedaluwarsa. Silakan login kembali.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        # Mengambil string token asli dari credentials
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(model.User).filter(model.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user