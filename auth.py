from datetime import datetime, timedelta, timezone
from typing import Union
from jose import jwt
import bcrypt  # Menggunakan library bcrypt langsung (tanpa passlib)

SECRET_KEY = "MBGKOPDES"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

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