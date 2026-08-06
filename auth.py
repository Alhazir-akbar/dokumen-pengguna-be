from datetime import datetime, timedelta, timezone
from typing import Union
from jose import jwt
from passlib.context import CryptContext

SECRET_KEY = ""
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """memverifikasi apakah password yang dimasukkan cocok dengan hash di database"""
    return pwd_context.verify(plain_password, hashed_password)
def get_password_hash(password: str) -> str:
    """Mengubah Password plain menjadi hash acak"""
    return pwd_context.hash(password)
def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    """membuat token jwt dengan waktu kadaluarsa"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)