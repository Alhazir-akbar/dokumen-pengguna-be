import os
import json
from pydantic import BaseModel, Field
from typing import List
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Muat variabel environment dari .env
load_dotenv()

# ================= SKEMA OUTPUT TERSTRUKTUR UNTUK AI =================

class UserTypeSuggestion(BaseModel):
    name: str = Field(description="Nama tipe pengguna/persona (misal: Guest User, Admin, Pembeli)")
    description: str = Field(description="Penjelasan singkat siapa mereka dan apa peran mereka di aplikasi")

class EpicSuggestion(BaseModel):
    name: str = Field(description="Kategori fitur besar/modul aplikasi (misal: Autentikasi, Katalog Produk)")
    description: str = Field(description="Ringkasan modul/fitur apa saja yang berada di bawah Epic ini")

class UserStorySuggestion(BaseModel):
    epic_name: str = Field(description="Nama Epic tempat story ini bernaung (harus cocok dengan salah satu nama Epic di atas)")
    story_name: str = Field(description="Judul cerita pengguna (misal: Registrasi Akun, Cari Produk)")
    user_type: str = Field(description="Nama tipe pengguna yang melakukan aksi ini (harus cocok dengan salah satu User Type di atas)")
    description: str = Field(description="Format cerita: 'Sebagai [user_type], saya ingin [aksi] agar [manfaat/tujuan]'")
    acceptance_criteria: List[str] = Field(description="Daftar kriteria penerimaan/pengujian (AC) untuk story ini")

class NFRSuggestion(BaseModel):
    category: str = Field(description="Kategori NFR (misal: Performance, Security, Availability, Reliability)")
    description: str = Field(description="Detail kebutuhan non-fungsional tersebut")

class ProjectRequirementsOutput(BaseModel):
    user_types: List[UserTypeSuggestion]
    epics: List[EpicSuggestion]
    user_stories: List[UserStorySuggestion]
    nfrs: List[NFRSuggestion]

# ================= INISIALISASI GEMINI CLIENT =================

# SDK Google GenAI secara otomatis memuat GEMINI_API_KEY dari environment variable
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

def generate_project_requirements(
    project_name: str,
    project_description: str,
    application_type: str,
    domain_business: str,
    target_users: str,
    business_goals: str,
    ai_rules: List[str]
) -> ProjectRequirementsOutput:
    """
    Fungsi untuk memanggil Gemini API dan menghasilkan draf dokumentasi terstruktur.
    """
    # 1. Rangkai AI Rules jika ada
    rules_prompt = ""
    if ai_rules:
        rules_prompt = "\n".join([f"- {rule}" for rule in ai_rules])
    else:
        rules_prompt = "- Tidak ada aturan khusus. Tulis dengan standar profesional umum."

    # 2. Susun prompt instruksi utama
    prompt = f"""
    Anda adalah seorang Business Analyst dan System Analyst profesional. Tugas Anda adalah menganalisis detail proyek perangkat lunak berikut dan merancang dokumentasi kebutuhan awalnya:
    
    Nama Proyek: {project_name}
    Deskripsi: {project_description}
    Tipe Aplikasi: {application_type}
    Domain Bisnis: {domain_business}
    Target Pengguna: {target_users}
    Tujuan Bisnis: {business_goals}
    
    ATURAN KHUSUS AI (WAJIB DIPATUHI):
    {rules_prompt}
    
    Rancanglah data berikut secara lengkap dan saling terhubung sesuai dengan skema output JSON:
    1. User Types (Persona) berdasarkan target pengguna.
    2. Epics (modul utama) yang dibutuhkan untuk aplikasi tipe ini.
    3. User Stories untuk setiap Epic, terhubung ke User Type yang sesuai, lengkap dengan Acceptance Criteria (AC).
    4. Non-Functional Requirements (NFR) minimal untuk Performance, Security, dan Availability.
    """

    try:
        # 3. Panggil Gemini Model dengan konfigurasi JSON Schema
        response = client.models.generate_content(
            model='gemini-3.6-flash',  
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ProjectRequirementsOutput,
                temperature=0.2  # Nilai rendah agar hasil AI konsisten dan terarah
            )
        )
        
        # 4. Baca teks respon JSON dan konversi ke objek Pydantic kita
        result_json = json.loads(response.text)
        return ProjectRequirementsOutput(**result_json)
        
    except Exception as e:
        raise RuntimeError(f"Gagal memanggil Gemini API: {str(e)}")