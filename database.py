import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Muat variabel environment dari .env
load_dotenv()

# Baca DATABASE_URL dari .env (Otomatis membaca Supabase PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./userdoc.db")

# Jika URI diawali postgres://, ubah ke postgresql:// agar dikenali SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Konfigurasi engine koneksi
if "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
else:
    # Untuk Supabase PostgreSQL
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()