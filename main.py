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

# Membuat seluruh tabel baru di database SQLite jika belum ada
model.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Userdoc Backend API")

# Folder untuk menyimpan file upload (gambar story) secara lokal.
# TODO migrasi ke S3/cloud storage: ganti bagian upload di routers/stories.py
# supaya upload ke bucket, lalu simpan URL bucket-nya ke kolom StoryImage.url
# (struktur kolomnya sudah generic, jadi migrasi nanti nggak perlu ubah schema).
os.makedirs("static/story_images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mengonfigurasi CORS agar Frontend Next.js (port 3000) bisa mengakses API ini
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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