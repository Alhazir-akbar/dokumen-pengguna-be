import os
import json
from pydantic import BaseModel, Field
from typing import List
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# ================= SKEMA OUTPUT TERSTRUKTUR UNTUK AI =================

class UserTypeSuggestion(BaseModel):
    name: str = Field(description="Nama tipe pengguna/persona (misal: Guest User, Admin, Operator)")
    description: str = Field(
        description=(
            "Penjelasan rinci (8-15 kalimat) siapa mereka, apa peran/tanggung jawab mereka "
            "di aplikasi, dan hak akses tingkat tinggi apa yang mereka miliki dibanding tipe user lain. "
            "Sebutkan juga contoh tujuan utama mereka menggunakan sistem ini."
        )
    )

class EpicSuggestion(BaseModel):
    name: str = Field(description="Kategori fitur besar/modul aplikasi (misal: Autentikasi & Manajemen Akun, Dashboard Analitik)")
    description: str = Field(
        description=(
            "Ringkasan modul/fitur yang berada di bawah Epic ini (8-15 kalimat), termasuk tujuan "
            "bisnisnya, dan batasan cakupan eksplisit (apa yang termasuk dan tidak termasuk dalam epic ini) "
            "supaya tidak tumpang tindih dengan Epic lain."
        )
    )

class UserStorySuggestion(BaseModel):
    epic_name: str = Field(description="Nama Epic tempat story ini bernaung (harus cocok persis dengan salah satu nama Epic di atas)")
    story_name: str = Field(description="Judul singkat cerita pengguna (misal: Registrasi Akun Pengguna Baru, Filter Data Berdasarkan Kategori)")
    user_type: str = Field(description="Nama tipe pengguna yang melakukan aksi ini (harus cocok persis dengan salah satu User Type di atas)")
    description: str = Field(
        description=(
            "Deskripsi lengkap minimal 8-12 kalimat dengan struktur berikut dalam satu paragraf naratif:\n"
            "(1) Format inti: 'Sebagai [user_type], saya ingin [aksi spesifik], agar [manfaat/tujuan bisnis]'.\n"
            "(2) Alur utama (main flow) langkah demi langkah dari awal sampai selesai.\n"
            "(3) Kondisi khusus/edge case yang relevan dan perilaku sistem.\n"
            "(4) Prasyarat atau ketergantungan sistem."
        )
    )
    acceptance_criteria: List[str] = Field(
        description=(
            "Minimal 6 dan maksimal 10 kriteria penerimaan yang spesifik dan terukur dalam format 'Given [kondisi], When [aksi], Then [hasil]'. "
            "Wajib mencakup kombinasi happy path dan skenario validasi error handling dengan batasan angka konkret."
        )
    )
    tech_notes: List[str] = Field(
        description=(
            "Minimal 6 dan maksimal 10 catatan teknis pertimbangan implementasi developer (struktur database, endpoint API, aturan validasi, keamanan, performa)."
        )
    )
    test_cases: List[str] = Field(
        description=(
            "Minimal 6 dan maksimal 10 skenario pengujian QA dengan format '[Nama skenario]: Langkah = [...], Hasil = [...]'."
        )
    )

class NFRSuggestion(BaseModel):
    category: str = Field(
        description="Kategori NFR (Performance, Security, Availability, Usability, Scalability, Compliance)."
    )
    description: str = Field(
        description="Detail kebutuhan non-fungsional dengan target kuantitatif/terukur yang jelas beserta standar verifikasinya."
    )

class ProjectRequirementsOutput(BaseModel):
    user_types: List[UserTypeSuggestion]
    epics: List[EpicSuggestion]
    user_stories: List[UserStorySuggestion]
    nfrs: List[NFRSuggestion]

# ================= INISIALISASI GEMINI CLIENT =================

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


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
    Memanggil Gemini API untuk menghasilkan draf dokumentasi kebutuhan software dengan tingkat kedalaman tinggi.
    """
    if ai_rules:
        rules_prompt = "\n".join([f"- {rule}" for rule in ai_rules])
    else:
        rules_prompt = "- Tidak ada aturan khusus. Tulis dengan standar profesional umum."

    prompt = f"""
    Anda adalah seorang Senior Business Analyst dan System Analyst profesional dengan pengalaman lebih dari 10 tahun. 
    Buatlah dokumentasi kebutuhan software yang sangat detail, mendalam, dan siap pakai untuk tim engineering profesional.

    DETAIL PROYEK:
    Nama Proyek: {project_name}
    Deskripsi: {project_description}
    Tipe Aplikasi: {application_type}
    Domain Bisnis: {domain_business}
    Target Pengguna: {target_users}
    Tujuan Bisnis: {business_goals}

    ATURAN KHUSUS AI (WAJIB DIPATUHI):
    {rules_prompt}

    INSTRUKSI PENYUSUNAN (DETAIL & KOMPREHENSIF):

    1. USER TYPES
       - Identifikasi 4-6 tipe pengguna utama yang relevan secara komprehensif.
       - Jelaskan peran, tanggung jawab, dan tingkat akses masing-masing secara mendalam.
       - Setiap tipe pengguna harus memiliki deskripsi rinci (8-15 kalimat) yang mencakup tujuan utama mereka menggunakan sistem.
       - Pastikan tidak ada tumpang tindih hak akses antar tipe pengguna.
       - Gunakan istilah yang konsisten untuk nama tipe pengguna di seluruh dokumen.
       - Setiap tipe pengguna harus memiliki contoh alur kerja utama yang mereka lakukan di sistem.
       - Sertakan pertimbangan keamanan dan privasi yang relevan untuk setiap tipe pengguna.
       - Pastikan deskripsi mencakup skenario penggunaan nyata dan konteks bisnis yang jelas.
       - Gunakan bahasa yang profesional, jelas, dan mudah dipahami oleh tim pengembang dan pemangku kepentingan bisnis.
       - Setiap tipe pengguna harus memiliki contoh tujuan bisnis yang spesifik dan terukur.
       - Pastikan setiap deskripsi mencakup interaksi dengan fitur utama sistem dan bagaimana mereka berkontribusi pada tujuan bisnis secara keseluruhan.

    2. EPICS
       - Susun **4 hingga 6 Epic utama** yang mencakup seluruh arsitektur sistem dari hulu ke hilir (autentikasi, manajemen data, fitur utama sesuai domain bisnis, laporan/analitik, pengaturan sistem, dll).
       - Pastikan cakupan setiap Epic jelas dan tidak tumpang tindih.
       - Setiap Epic harus memiliki deskripsi rinci (8-15 kalimat) yang mencakup tujuan bisnis, batasan cakupan, dan alur kerja utama.
       - Gunakan istilah yang konsisten untuk nama Epic di seluruh dokumen.
       - Setiap Epic harus mencakup pertimbangan teknis dan non-teknis yang relevan, termasuk integrasi dengan sistem lain jika diperlukan.
       - Pastikan setiap Epic mencakup skenario penggunaan nyata dan konteks bisnis yang jelas.
       - Gunakan bahasa yang profesional, jelas, dan mudah dipahami oleh tim pengembang dan pemangku kepentingan bisnis.
       - Setiap Epic harus memiliki contoh tujuan bisnis yang spesifik dan terukur.
       - Pastikan setiap deskripsi mencakup interaksi dengan fitur utama sistem dan bagaimana mereka berkontribusi pada tujuan bisnis secara keseluruhan.

    3. USER STORIES
       3. USER STORIES
    - Setiap Epic wajib memiliki **2 hingga 3 User Story** yang saling melengkapi.
    - Setiap User Story harus memiliki deskripsi singkat padat (3-5 kalimat).
    - Setiap User Story wajib memiliki **3 hingga 5** acceptance criteria spesifik dalam format Given-When-Then.
    - Setiap User Story wajib memiliki **3 hingga 5** tech notes ringkas untuk developer.
    - Setiap User Story wajib memiliki **3 hingga 5** test cases untuk pengujian QA.

    4. NON-FUNCTIONAL REQUIREMENTS (NFR)
       - Wajib mencakup kategori: Performance, Security, Availability, Usability, Scalability, dan Compliance.
       - Setiap NFR harus dijelaskan secara rinci dengan target kuantitatif yang jelas (misal: response time < 2 detik, uptime 99.9%, enkripsi AES-256, dsb).
       - Setiap NFR harus memiliki target angka terukur (kuantitatif).
       - Setiap NFR harus mencakup standar verifikasi yang jelas (misal: metode pengujian, alat ukur, atau prosedur audit).
       - Pastikan setiap NFR relevan dengan domain bisnis dan tujuan proyek.
       - Gunakan bahasa yang profesional, jelas, dan mudah dipahami oleh tim pengembang dan pemangku kepentingan bisnis.
       - Setiap NFR harus mencakup pertimbangan teknis dan non-teknis yang relevan, termasuk integrasi dengan sistem lain jika diperlukan.
       - Pastikan setiap NFR mencakup skenario penggunaan nyata dan konteks bisnis yang jelas.

    5. FORMAT OUTPUT
       - Gunakan format JSON yang valid dan sesuai skema yang telah ditentukan. Jangan menambahkan teks pengantar atau penutup di luar struktur JSON.
       - Pastikan semua field diisi sesuai batas minimal yang ditentukan tanpa diringkas.
       - Gunakan istilah yang konsisten di seluruh dokumen untuk nama tipe pengguna, Epic, dan User Story.
       - Pastikan JSON dapat di-parse tanpa error dan sesuai dengan struktur yang telah ditentukan.
       - Gunakan bahasa yang profesional, jelas, dan mudah dipahami oleh tim pengembang dan pemangku kepentingan bisnis.
       - Pastikan setiap field diisi sesuai batas minimal yang ditentukan tanpa diringkas.
       - Pastikan JSON dapat di-parse tanpa error dan sesuai dengan struktur yang telah ditentukan.
    """

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ProjectRequirementsOutput,
                temperature=0.3,
                max_output_tokens=16384,  # Memastikan token maksimal agar output mendalam tidak terpotong
            )
        )

        result_json = json.loads(response.text)
        return ProjectRequirementsOutput(**result_json)

    except Exception as e:
        raise RuntimeError(f"Gagal memanggil Gemini API: {str(e)}")


def suggest_project_description(project_name: str, platform_type: str) -> str:
    """Menghasilkan draf deskripsi proyek singkat berdasarkan nama & tipe platform"""
    prompt = f"""
Kamu adalah asisten business analyst berpengalaman.
Buatkan draf deskripsi proyek software singkat (2-4 kalimat) berdasarkan detail berikut:

- Nama proyek: {project_name}
- Tipe platform: {platform_type}

Deskripsi harus menjelaskan tujuan utama aplikasi, target penggunanya, dan gambaran fitur inti secara umum.
Tulis dalam Bahasa Indonesia, gaya natural dan profesional, tanpa markdown, tanpa tanda kutip di awal/akhir.
""".strip()

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        description = (response.text or "").strip()
    except Exception as e:
        raise RuntimeError(f"Gagal memanggil Gemini API: {str(e)}")

    if not description:
        raise ValueError("AI tidak menghasilkan deskripsi")

    return description