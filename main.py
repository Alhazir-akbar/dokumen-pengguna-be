from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from routers.users import router as users_router
from routers.stories import router as stories_router
from routers.journeys import router as journeys_router
from routers.build import router as build_router
from routers.tokens import router as tokens_router

import model
from database import engine

# Impor router modular kita dari folder routers
from routers.auth import router as auth_router
from routers.workspaces import router as workspaces_router
from routers.projects import router as projects_router
from routers.ai_rules import router as ai_rules_router
from routers.profile import router as profile_router
from routers import nfrs

# Membuat seluruh tabel baru di database jika belum ada
try:
    model.Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Notice: DB metadata.create_all skipped/safe: {e}")

app = FastAPI(title="Userdoc Backend API")

# Folder untuk menyimpan file upload (gambar story) secara lokal.
# TODO migrasi ke S3/cloud storage: ganti bagian upload di routers/stories.py
# supaya upload ke bucket, lalu simpan URL bucket-nya ke kolom StoryImage.url
# (struktur kolomnya sudah generic, jadi migrasi nanti nggak perlu ubah schema).
os.makedirs("static/story_images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mengonfigurasi CORS agar Frontend Next.js (Lokal & Vercel Production) bisa mengakses API ini
frontend_url = os.getenv("FRONTEND_URL")
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if frontend_url:
    allowed_origins.append(frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mendaftarkan router modular ke dalam aplikasi FastAPI
app.include_router(auth_router)
app.include_router(build_router)
app.include_router(workspaces_router)
app.include_router(projects_router)
app.include_router(ai_rules_router)
app.include_router(profile_router)
app.include_router(users_router)
app.include_router(stories_router)
app.include_router(journeys_router)
app.include_router(tokens_router)
app.include_router(nfrs.router)

# Endpoint testing status
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "message": "Backend FastAPI berjalan dengan baik"}