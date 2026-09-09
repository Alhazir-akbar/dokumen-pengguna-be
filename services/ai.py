import os
import re
import json
import threading
import itertools
from typing import List, Optional, Type, TypeVar

from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

T = TypeVar("T", bound=BaseModel)

# ================= SKEMA OUTPUT TERSTRUKTUR UNTUK AI =================

class PersonaSuggestion(BaseModel):
    name: str = Field(description="Nama lengkap persona fiktif yang representatif (misal: Sarah Wijaya)")
    age: int = Field(description="Usia persona yang masuk akal untuk tipe pengguna ini")
    location: str = Field(description="Kota/lokasi tempat tinggal persona (contoh: Jakarta, Indonesia)")
    family_status: str = Field(description="Status keluarga singkat (misal: Menikah, punya 1 anak / Lajang)")
    job_title: str = Field(description="Jabatan/pekerjaan persona yang relevan dengan tipe pengguna ini")
    about: str = Field(description="Deskripsi singkat 2-3 kalimat tentang latar belakang dan keseharian persona ini")
    goals: str = Field(description="Tujuan spesifik persona ini saat menggunakan aplikasi, 1-2 kalimat")
    frustrations: str = Field(description="Hal yang membuat persona ini frustrasi jika kebutuhannya tidak terpenuhi, 1-2 kalimat")


class UserTypeSuggestion(BaseModel):
    name: str = Field(description="Nama tipe pengguna/persona (misal: Guest User, Admin, Pembeli)")
    description: str = Field(
        description=(
            "Penjelasan singkat dan padat, MAKSIMAL 3 kalimat (jangan lebih panjang dari itu): "
            "siapa mereka, apa peran utama mereka di aplikasi, dan tingkat akses mereka dibanding "
            "tipe user lain. Ini hanya ringkasan identitas — tujuan/motivasi detail mereka akan "
            "digali terpisah di tahap lain, jadi tidak perlu dijelaskan panjang lebar di sini."
        )
    )
    personas: List[PersonaSuggestion] = Field(
        min_length=1,
        max_length=1,
        description=(
            "WAJIB berisi TEPAT 1 contoh persona fiktif yang representatif untuk tipe pengguna ini "
            "(array ini TIDAK BOLEH kosong), supaya tim punya gambaran konkret siapa yang sebenarnya "
            "memakai fitur ini (bukan sekadar kategori abstrak). Buat persona yang realistis dan "
            "spesifik, bukan generik."
        )
    )

class EpicSuggestion(BaseModel):
    name: str = Field(description="Kategori fitur besar/modul aplikasi (misal: Autentikasi, Katalog Produk)")
    description: str = Field(
        description=(
            "Deskripsi lengkap 4-6 kalimat yang mencakup: (1) tujuan bisnis epic ini secara jelas, "
            "(2) daftar konkret fitur/kemampuan utama yang termasuk di dalamnya (sebutkan beberapa "
            "nama fitur/layar spesifik, bukan cuma kategori umum), (3) batasan cakupan eksplisit — "
            "apa yang TIDAK termasuk di epic ini supaya tidak tumpang tindih dengan epic lain, dan "
            "(4) siapa saja user type yang akan berinteraksi dengan modul ini. Epic adalah unit kerja "
            "besar yang akan dipecah developer jadi banyak task, jadi harus cukup jelas cakupannya."
        )
    )

class UserStorySuggestion(BaseModel):
    epic_name: str = Field(description="Nama Epic tempat story ini bernaung (harus cocok persis dengan salah satu nama Epic di atas)")
    story_name: str = Field(description="Judul singkat cerita pengguna (misal: Registrasi Akun, Cari Produk Berdasarkan Kategori)")
    user_type: str = Field(description="Nama tipe pengguna yang melakukan aksi ini (harus cocok persis dengan salah satu User Type di atas)")
    description: str = Field(
        description=(
            "Deskripsi lengkap minimal 4-6 kalimat dengan struktur berikut, semua dalam satu paragraf "
            "naratif (bukan bullet list):\n"
            "(1) Format inti: 'Sebagai [user_type], saya ingin [aksi spesifik], agar [manfaat/tujuan bisnis "
            "yang jelas dan terukur]'.\n"
            "(2) Alur utama (main flow): jelaskan langkah demi langkah yang dilalui user dari mulai sampai "
            "selesai (misal: user membuka halaman X, mengisi form Y, menekan tombol Z, sistem memvalidasi, "
            "sistem menampilkan konfirmasi).\n"
            "(3) Minimal 1-2 kondisi khusus/edge case yang relevan dan bagaimana sistem seharusnya "
            "berperilaku (misal: input tidak valid, data kosong, koneksi gagal, duplikasi data, batas "
            "kuota tercapai, permission ditolak).\n"
            "(4) Ketergantungan/prasyarat jika ada (misal: 'story ini membutuhkan user sudah login' atau "
            "'membutuhkan data dari story lain terlebih dahulu')."
        )
    )
    acceptance_criteria: List[str] = Field(
        description=(
            "Minimal 3 dan maksimal 4 kriteria penerimaan yang SPESIFIK dan TERUKUR/TESTABLE. Tulis "
            "masing-masing dalam format 'Given [kondisi awal], When [aksi user], Then [hasil yang "
            "diharapkan]'. Setiap kriteria harus bisa langsung dijadikan test case tanpa tafsir tambahan. "
            "WAJIB mencakup: (1) minimal 1 skenario normal/happy path, (2) minimal 1 skenario validasi "
            "input atau error handling, (3) minimal 1 batasan data/aturan bisnis dengan angka konkret "
            "(contoh: 'Given user mengisi password kurang dari 8 karakter, When user menekan submit, "
            "Then sistem menampilkan pesan error \\\"Password minimal 8 karakter\\\" dan form tidak terkirim'). "
            "Hindari kriteria generik seperti 'Sistem harus berfungsi dengan baik'."
        )
    )
    tech_notes: List[str] = Field(
        description=(
            "Minimal 2 dan maksimal 3 catatan teknis yang membantu developer memahami PERTIMBANGAN "
            "IMPLEMENTASI sebelum coding, bukan pengulangan acceptance criteria. Contoh hal yang wajib "
            "dipertimbangkan dan disebutkan jika relevan: struktur data/field yang perlu disimpan di "
            "database, endpoint API yang kemungkinan dibutuhkan (method + tujuan singkatnya), aturan "
            "validasi di sisi backend vs frontend, kebutuhan keamanan spesifik (misal enkripsi, rate "
            "limiting, otorisasi berdasarkan role), potensi dampak performa (misal butuh pagination, "
            "caching, indexing), atau ketergantungan ke layanan/pihak ketiga (payment gateway, email "
            "service, storage, dsb). Setiap catatan harus actionable, bukan generik seperti 'harus "
            "diimplementasikan dengan baik'."
        )
    )
    test_cases: List[str] = Field(
        description=(
            "Minimal 3 dan maksimal 4 skenario pengujian (test case) untuk tim QA, yang BERBEDA dari "
            "acceptance criteria — acceptance criteria menyatakan syarat diterimanya fitur, sedangkan "
            "test case ini adalah skenario uji konkret yang bisa langsung dieksekusi manual/otomatis. "
            "Tulis dalam format: '[Nama skenario]: Langkah = [langkah-langkah uji], Hasil yang diharapkan "
            "= [hasil]'. WAJIB mencakup kombinasi: uji fungsional normal, uji dengan data invalid/kosong/"
            "melebihi batas, dan minimal 1 uji kondisi negatif (misal koneksi terputus di tengah proses, "
            "submit ganda/double-click)."
        )
    )

class NFRSuggestion(BaseModel):
    category: str = Field(
        description=(
            "Kategori NFR. WAJIB mencakup minimal: Performance, Security, Availability, Usability, dan "
            "Scalability — tambahkan kategori lain jika relevan dengan tipe aplikasi (misal: Compliance, "
            "Maintainability, Compatibility, Data Integrity)."
        )
    )
    description: str = Field(
        description=(
            "Detail kebutuhan non-fungsional dengan TARGET KUANTITATIF/TERUKUR yang jelas (contoh: "
            "'Waktu respons API tidak boleh lebih dari 2 detik untuk 95% request pada beban normal', "
            "'Sistem harus mendukung minimal 500 pengguna aktif bersamaan tanpa penurunan performa "
            "signifikan', 'Data sensitif harus dienkripsi menggunakan AES-256 saat disimpan dan TLS 1.2+ "
            "saat transit', 'Uptime sistem minimal 99.5% per bulan'). Sebutkan juga bagaimana requirement "
            "ini idealnya diverifikasi/diukur. Hindari deskripsi generik seperti 'harus cepat' atau "
            "'harus aman' tanpa angka atau standar yang jelas."
        )
    )

class ProjectRequirementsOutput(BaseModel):
    user_types: List[UserTypeSuggestion]
    epics: List[EpicSuggestion]
    user_stories: List[UserStorySuggestion]
    nfrs: List[NFRSuggestion]

# ================= TAMBAHAN: SARAN GOALS & FRUSTRATIONS PER USER TYPE =================

class UserGoalsSuggestion(BaseModel):
    goals: str = Field(
        description=(
            "Tujuan utama tipe pengguna ini saat memakai aplikasi, ditulis 2-3 kalimat yang "
            "spesifik dan kontekstual terhadap nama proyek serta peran user tersebut — bukan "
            "kalimat generik yang bisa berlaku untuk aplikasi apa saja."
        )
    )
    frustrations: str = Field(
        description=(
            "Hal-hal yang membuat tipe pengguna ini frustrasi saat memakai aplikasi sejenis, "
            "ditulis 2-3 kalimat yang spesifik dan kontekstual terhadap peran user tersebut — "
            "bukan kalimat generik seperti 'UI membingungkan' tanpa konteks."
        )
    )


class UserJourneyStepSuggestion(BaseModel):
    title: str = Field(description="Judul singkat tahapan ini (misal: 'Membuka Halaman Utama', 'Mengisi Formulir Pendaftaran')")
    description: str = Field(
        description=(
            "Penjelasan detail 2-3 kalimat mengenai aksi konkret yang dilakukan pengguna pada tahap ini. "
            "Sebutkan halaman, komponen UI, atau tombol spesifik yang diklik, serta bagaimana sistem merespons "
            "aksi tersebut (misal: 'Pengguna menekan tombol Masuk di pojok kanan atas, lalu sistem memunculkan "
            "modal popup formulir autentikasi')."
        )
    )


class UserJourneySuggestion(BaseModel):
    narrative: str = Field(
        description=(
            "Satu paragraf naratif (5-7 kalimat) yang menggambarkan keseluruhan alur pengalaman pengguna "
            "secara profesional dan mengalir dari awal penggunaan hingga tujuan tercapai. Fokuskan pada "
            "proses operasional sistem dan interaksi fungsional, hindari penggunaan nama orang atau fiksi."
        )
    )
    steps: List[UserJourneyStepSuggestion] = Field(
        description=(
            "5-7 tahapan berurutan dari awal (start) sampai akhir (end) yang menyusun journey ini. "
            "Setiap tahapan harus menjelaskan langkah operasional nyata secara kronologis tanpa menggunakan "
            "perumpamaan nama tokoh fiktif."
        )
    )


class TechStackSuggestion(BaseModel):
    ui_layer: str = Field(description="Framework/teknologi UI yang paling cocok (contoh: 'Next.js (React)')")
    app_layer: str = Field(description="Framework/teknologi backend yang paling cocok (contoh: 'FastAPI (Python)')")
    data_layer: str = Field(description="Database yang paling cocok (contoh: 'PostgreSQL')")
    integration_layer: str = Field(description="Protokol/pola integrasi yang paling cocok (contoh: 'REST API')")


class GuidelineSuggestion(BaseModel):
    title: str = Field(description="Judul singkat guideline (contoh: 'Struktur Folder & Penamaan File')")
    content: str = Field(
        description=(
            "Isi guideline 3-5 kalimat yang actionable dan spesifik terhadap tech stack proyek "
            "ini -- bukan saran generik yang berlaku untuk semua bahasa pemrograman."
        )
    )


class CodingGuidelinesSuggestion(BaseModel):
    guidelines: List[GuidelineSuggestion] = Field(
        description="3-5 coding guideline paling penting untuk proyek ini, spesifik terhadap tech stack yang dipakai."
    )


class DevPlanItemSuggestion(BaseModel):
    title: str = Field(description="Judul task pengembangan (contoh: 'Implementasi Autentikasi & Registrasi')")
    description: str = Field(description="Deskripsi singkat 1-2 kalimat cakupan task ini")


class DevPlanSuggestion(BaseModel):
    items: List[DevPlanItemSuggestion] = Field(
        description="Daftar task pengembangan awal, satu task per Epic yang diberikan, dengan urutan prioritas logis (fondasi/autentikasi duluan)."
    )


# ================= KONFIGURASI 3 PROVIDER AI =================
# Tiga provider dipakai bergiliran (round-robin) untuk generate, supaya beban tidak
# numpuk di satu API key/model saja dan lebih tahan terhadap rate limit.
#
# 1. Gemini        -> pakai SDK resmi google-genai, support response_schema native.
# 2. OpenRouter     -> OpenAI-compatible, dipanggil lewat SDK `openai` dengan base_url custom.
# 3. Groq Cloud     -> OpenAI-compatible juga, sama caranya dengan OpenRouter.

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME") or os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL_NAME", "meta-llama/llama-3.3-70b-instruct:free")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")

# Client dibuat sekali di level modul. Kalau salah satu API key tidak diset,
# client-nya jadi None dan provider itu otomatis dilewati saat giliran (bukan crash).
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
openrouter_client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL) if OPENROUTER_API_KEY else None
groq_client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL) if GROQ_API_KEY else None

_PROVIDER_NAMES = ["gemini", "openrouter", "groq"]
_provider_cycle = itertools.cycle(_PROVIDER_NAMES)
_cycle_lock = threading.Lock()


def _next_provider_order() -> List[str]:
    """
    Ambil urutan provider yang akan dicoba untuk satu kali panggilan generate.
    Provider "giliran" (hasil round-robin) dicoba duluan, lalu 2 provider lain
    dipakai sebagai fallback berurutan kalau yang giliran gagal/limit/error.
    Dengan lock supaya aman kalau ada beberapa request generate bersamaan.
    """
    with _cycle_lock:
        start = next(_provider_cycle)
    idx = _PROVIDER_NAMES.index(start)
    return _PROVIDER_NAMES[idx:] + _PROVIDER_NAMES[:idx]


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json_object(text: str) -> str:
    """Bersihkan output model non-Gemini yang kadang membungkus JSON dengan
    code fence atau menambahkan kalimat pembuka/penutup di luar JSON."""
    candidate = _strip_json_fence(text)
    try:
        json.loads(candidate)
        return candidate
    except json.JSONDecodeError:
        pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        return candidate[start:end + 1]
    return candidate


def _call_gemini(prompt: str, schema: Type[T], temperature: float, max_output_tokens: Optional[int] = None) -> T:
    if gemini_client is None:
        raise RuntimeError("GEMINI_API_KEY tidak diset di .env")

    config_kwargs = dict(
        response_mime_type="application/json",
        response_schema=schema,
        temperature=temperature,
    )
    if max_output_tokens:
        config_kwargs["max_output_tokens"] = max_output_tokens

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )

    finish_reason = None
    try:
        finish_reason = response.candidates[0].finish_reason
    except Exception:
        pass
    if finish_reason is not None and str(finish_reason).upper().find("MAX_TOKENS") != -1:
        raise RuntimeError("Respons Gemini terpotong karena melebihi batas token maksimum.")

    result_json = json.loads(response.text)
    return schema(**result_json)


def _call_openai_compatible(
    client: Optional[OpenAI],
    model: str,
    prompt: str,
    schema: Type[T],
    temperature: float,
    max_tokens: Optional[int] = None,
) -> T:
    if client is None:
        raise RuntimeError(f"API key untuk model '{model}' tidak diset di .env")

    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
    system_msg = (
        "Kamu adalah asisten yang WAJIB membalas HANYA dengan satu objek JSON valid yang "
        "sesuai skema berikut, tanpa teks pembuka, tanpa penjelasan, tanpa markdown code fence:\n\n"
        f"{schema_json}"
    )

    create_kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )
    if max_tokens:
        create_kwargs["max_tokens"] = max_tokens

    try:
        response = client.chat.completions.create(response_format={"type": "json_object"}, **create_kwargs)
    except Exception:
        # Sebagian model/provider (terutama model gratis) belum tentu mendukung
        # response_format json_object -> fallback ke request biasa, tetap mengandalkan
        # instruksi di system prompt supaya outputnya JSON.
        response = client.chat.completions.create(**create_kwargs)

    choice = response.choices[0]
    if getattr(choice, "finish_reason", None) == "length":
        raise RuntimeError(f"Respons dari model '{model}' terpotong karena melebihi batas token maksimum.")

    raw_text = choice.message.content or ""
    candidate = _extract_json_object(raw_text)
    result_json = json.loads(candidate)
    return schema(**result_json)


def _generate_structured(prompt: str, schema: Type[T], temperature: float = 0.3, max_tokens: Optional[int] = None) -> T:
    """
    Dispatcher utama untuk semua generate yang butuh output terstruktur (JSON -> Pydantic).
    Urutan provider mengikuti round-robin (_next_provider_order), dengan fallback otomatis
    ke provider berikutnya kalau salah satu gagal (limit, error jaringan, output terpotong,
    atau JSON tidak valid).
    """
    errors: List[str] = []
    for provider in _next_provider_order():
        try:
            if provider == "gemini":
                return _call_gemini(prompt, schema, temperature, max_output_tokens=max_tokens)
            elif provider == "openrouter":
                return _call_openai_compatible(
                    openrouter_client, OPENROUTER_MODEL, prompt, schema, temperature, max_tokens=max_tokens
                )
            elif provider == "groq":
                return _call_openai_compatible(
                    groq_client, GROQ_MODEL, prompt, schema, temperature, max_tokens=max_tokens
                )
        except Exception as e:
            errors.append(f"[{provider}] {e}")
            continue

    raise RuntimeError(
        "Semua provider AI (Gemini, OpenRouter, Groq) gagal merespons secara bergiliran. "
        "Detail per provider: " + " || ".join(errors)
    )


def _generate_text(prompt: str, temperature: float = 0.5) -> str:
    """Dispatcher untuk generate teks bebas (non-JSON), dengan round-robin + fallback yang sama."""
    errors: List[str] = []
    for provider in _next_provider_order():
        try:
            if provider == "gemini":
                if gemini_client is None:
                    raise RuntimeError("GEMINI_API_KEY tidak diset di .env")
                response = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
                text = (response.text or "").strip()
            else:
                client = openrouter_client if provider == "openrouter" else groq_client
                model = OPENROUTER_MODEL if provider == "openrouter" else GROQ_MODEL
                if client is None:
                    raise RuntimeError(f"API key untuk provider '{provider}' tidak diset di .env")
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                )
                text = (response.choices[0].message.content or "").strip()

            if not text:
                raise RuntimeError(f"Respons kosong dari provider '{provider}'")
            return text
        except Exception as e:
            errors.append(f"[{provider}] {e}")
            continue

    raise RuntimeError(
        "Semua provider AI (Gemini, OpenRouter, Groq) gagal merespons secara bergiliran. "
        "Detail per provider: " + " || ".join(errors)
    )


# ================= FUNGSI-FUNGSI GENERATE (PUBLIC API - TIDAK BERUBAH SIGNATURE-NYA) =================

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
    Menghasilkan draf dokumentasi kebutuhan software yang detail dan siap dipakai
    developer — mencakup user types, epics, user stories (dengan acceptance criteria,
    tech notes, dan test cases), serta NFR. Provider dipilih bergiliran (round-robin)
    dengan fallback otomatis kalau salah satu provider gagal/limit/output terpotong.
    """
    if ai_rules:
        rules_prompt = "\n".join([f"- {rule}" for rule in ai_rules])
    else:
        rules_prompt = "- Tidak ada aturan khusus. Tulis dengan standar profesional umum."

    prompt = f"""
    Anda adalah seorang Senior Business Analyst dan System Analyst dengan pengalaman lebih dari
    10 tahun menulis dokumentasi kebutuhan software untuk tim engineering profesional. Dokumen
    yang Anda hasilkan akan LANGSUNG dipakai developer untuk membangun sistem tanpa sesi
    klarifikasi tambahan dengan stakeholder — jadi setiap requirement HARUS cukup jelas, spesifik,
    dan lengkap sehingga tidak ada ruang untuk salah tafsir. Requirement yang terlalu singkat atau
    generik akan menyebabkan developer salah membangun fitur, itu adalah kegagalan dokumen ini.

    DETAIL PROYEK:
    Nama Proyek: {project_name}
    Deskripsi: {project_description}
    Tipe Aplikasi: {application_type}
    Domain Bisnis: {domain_business}
    Target Pengguna: {target_users}
    Tujuan Bisnis: {business_goals}

    ATURAN KHUSUS AI (WAJIB DIPATUHI):
    {rules_prompt}

    INSTRUKSI PENYUSUNAN (WAJIB DIIKUTI SECARA KETAT, JANGAN DIRINGKAS):

    1. USER TYPES
        - Identifikasi seluruh tipe pengguna relevan berdasarkan target pengguna dan domain bisnis.
        - Deskripsi tiap tipe CUKUP SINGKAT (maksimal 3 kalimat) — cukup identitas, peran, dan tingkat
          akses. JANGAN dibuat panjang; kedalaman requirement difokuskan ke Epic dan User Story di
          bawah, bukan di sini.
        - Setiap User Type WAJIB disertai TEPAT 1 contoh persona fiktif yang konkret (nama, usia,
          lokasi, pekerjaan, latar belakang singkat, goals, frustrations) — lihat skema PersonaSuggestion.

    2. EPICS
        - Susun 3-5 Epic (tidak perlu lebih) yang mencakup fungsi utama aplikasi, termasuk minimal:
          autentikasi/manajemen akun dan fitur inti sesuai domain bisnis.
        - Setiap Epic harus DETAIL dan KONKRET (lihat definisi field description pada skema): sebutkan
          fitur/layar spesifik yang termasuk di dalamnya, bukan cuma nama kategori umum. Epic yang
          kabur/generik akan membuat developer salah estimasi cakupan kerja.
        - Setiap Epic harus punya cakupan yang jelas dan tidak tumpang tindih dengan Epic lain.

    3. USER STORIES
        - Setiap Epic memiliki 2-3 User Story PALING PENTING/PALING INTI saja (bukan mencoba
          mencakup semua kemungkinan aksi) — kualitas dan kedalaman tiap story jauh lebih penting
          daripada kuantitas. Lebih baik sedikit story yang sangat detail daripada banyak story
          yang dangkal.
        - User Story adalah bagian PALING PENTING dari dokumen ini — inilah yang langsung dipakai
          developer untuk membangun fitur. WAJIB memenuhi seluruh sub-field berikut secara lengkap
          dan detail (lihat definisi masing-masing field pada skema): description (naratif lengkap
          dengan main flow dan edge case), acceptance_criteria (format Given-When-Then, terukur),
          tech_notes (pertimbangan implementasi teknis konkret), dan test_cases (skenario uji QA
          konkret, berbeda isinya dari acceptance_criteria).
        - Terhubung ke Epic dan User Type yang sesuai (nama harus persis sama dengan yang
          didefinisikan di atas, huruf besar/kecil dan ejaan harus identik).

    4. NON-FUNCTIONAL REQUIREMENTS (NFR)
        - Wajib mencakup minimal kategori: Performance, Security, Availability, Usability, Scalability.
        - Setiap NFR harus punya target kuantitatif/terukur, bukan pernyataan kualitatif yang samar.

    5. KUALITAS & KEDALAMAN
        - Gunakan Bahasa Indonesia yang jelas dan profesional.
        - JANGAN membuat requirement singkat/generik hanya demi menghemat panjang output. Kedalaman
          dan kejelasan lebih penting daripada keringkasan. Bayangkan seorang developer junior yang
          belum pernah bicara dengan stakeholder harus bisa membangun fitur dengan benar HANYA dari
          membaca dokumen ini, tanpa bertanya lagi.
        - Pastikan konsistensi penamaan (epic_name, user_type) di seluruh story agar validasi data
          tidak gagal.

    Hasilkan output sesuai skema JSON yang telah ditentukan.
    """

    try:
        # max_tokens digenerelisir ke seluruh provider (bukan cuma Gemini) karena
        # output requirement ini memang berat -- kalau provider yang lagi giliran
        # tidak sanggup (output kepotong / limit), dispatcher akan otomatis coba
        # provider berikutnya.
        return _generate_structured(prompt, ProjectRequirementsOutput, temperature=0.3, max_tokens=32768)
    except Exception as e:
        raise RuntimeError(f"Gagal generate project requirements: {str(e)}") from e


def suggest_project_description(project_name: str, platform_type: str) -> str:
    """Menghasilkan draf deskripsi proyek singkat (2-4 kalimat) berdasarkan nama & platform"""
    prompt = f"""
    Kamu adalah asisten business analyst berpengalaman.
    Buatkan draf deskripsi proyek software singkat (2-4 kalimat) berdasarkan detail berikut:

    - Nama proyek: {project_name}
    - Tipe platform: {platform_type}

    Deskripsi harus menjelaskan tujuan utama aplikasi, target penggunanya, dan gambaran fitur inti secara umum.
    Tulis dalam Bahasa Indonesia, gaya natural dan profesional, tanpa markdown, tanpa tanda kutip di awal/akhir.
    """.strip()

    try:
        description = _generate_text(prompt, temperature=0.6)
    except Exception as e:
        raise RuntimeError(f"Gagal memanggil AI: {str(e)}")

    if not description:
        raise ValueError("AI tidak menghasilkan deskripsi")

    return description


def suggest_user_goals(project_name: str, user_type_name: str, user_type_description: str) -> UserGoalsSuggestion:
    """Menghasilkan saran goals & frustrations untuk satu tipe pengguna, dipakai di step UserTypeGoals wizard"""
    context_line = (
        f"Deskripsi tipe pengguna ini: {user_type_description}"
        if user_type_description
        else "Tidak ada deskripsi tambahan untuk tipe pengguna ini."
    )

    prompt = f"""
Kamu adalah UX researcher berpengalaman yang membantu menyusun user persona untuk sebuah proyek software.

Nama Proyek: {project_name}
Tipe Pengguna: {user_type_name}
{context_line}

Tugasmu: tuliskan (1) goals — apa yang ingin dicapai tipe pengguna ini saat memakai aplikasi
"{project_name}", dan (2) frustrations — hal-hal yang membuat mereka frustrasi jika aplikasi
ini tidak memenuhi kebutuhan mereka. Keduanya harus spesifik terhadap peran "{user_type_name}"
dan konteks proyek ini, bukan kalimat generik yang bisa dipakai untuk aplikasi apa saja.

Tulis dalam Bahasa Indonesia, gaya natural dan profesional.
""".strip()

    try:
        return _generate_structured(prompt, UserGoalsSuggestion, temperature=0.4)
    except Exception as e:
        raise RuntimeError(f"Gagal memanggil AI: {str(e)}")


def suggest_user_journey(project_name: str, project_description: str, user_types: List[str]) -> UserJourneySuggestion:
    """Menghasilkan draf narasi DAN langkah-langkah user journey terstruktur dari awal sampai akhir secara detail tanpa nama fiktif."""
    user_types_line = (
        f"Tipe pengguna yang terlibat: {', '.join(user_types)}."
        if user_types
        else "Tidak ada informasi tipe pengguna spesifik."
    )

    prompt = f"""
Kamu adalah UX researcher dan system analyst profesional. Buatlah draf user journey yang komprehensif, logis, dan detail untuk aplikasi ini dari awal (start) sampai selesai (end).

Nama Proyek: {project_name}
Deskripsi Proyek: {project_description or 'Tidak ada deskripsi.'}
{user_types_line}

ATURAN KETAT:
1. JANGAN menggunakan perumpamaan nama fiktif/tokoh (misalnya: hindari kalimat seperti "Budi membuka aplikasi..."). Gunakan sudut pandang objektif atau sebut langsung peran penggunanya (misalnya: "Pengguna", "Admin", atau "Sistem").
2. Buat alur dari awal titik masuk (start) hingga mencapai tujuan akhir (end) secara runtut.
3. Hasilkan dalam dua bentuk:
   (1) narrative: paragraf ringkasan alur secara utuh, profesional, dan operasional.
   (2) steps: 5 hingga 7 tahapan berurutan dari awal sampai akhir, di mana setiap tahapan menjelaskan aksi sistem/pengguna secara spesifik dan teknis.

Tulis dalam Bahasa Indonesia, gaya natural dan profesional.
""".strip()

    try:
        return _generate_structured(prompt, UserJourneySuggestion, temperature=0.4)
    except Exception as e:
        raise RuntimeError(f"Gagal memanggil AI: {str(e)}")


def suggest_tech_stack(project_name: str, project_description: str, application_type: str) -> TechStackSuggestion:
    """Menyarankan technology stack awal berdasarkan konteks proyek"""
    prompt = f"""
Kamu adalah Solutions Architect berpengalaman. Berdasarkan detail proyek berikut, sarankan
technology stack yang paling sesuai untuk 4 lapisan arsitektur: UI, Application, Data, dan
Integration. Pilih teknologi yang umum, stabil, dan sesuai skala proyek ini -- bukan pilihan
eksotis tanpa alasan kuat.

Nama Proyek: {project_name}
Deskripsi: {project_description or 'Tidak ada deskripsi.'}
Tipe Aplikasi: {application_type or 'Tidak disebutkan'}

Tulis dalam Bahasa Indonesia untuk penjelasan jika ada, tapi nama teknologi tetap istilah asli
(contoh: "Next.js", "FastAPI", "PostgreSQL").
""".strip()

    try:
        return _generate_structured(prompt, TechStackSuggestion, temperature=0.3)
    except Exception as e:
        raise RuntimeError(f"Gagal memanggil AI: {str(e)}")


def suggest_coding_guidelines(project_name: str, tech_stack_summary: str) -> CodingGuidelinesSuggestion:
    """Menyarankan draf coding guidelines awal berdasarkan tech stack proyek"""
    prompt = f"""
Kamu adalah Tech Lead berpengalaman yang menyusun coding guidelines untuk tim developer baru.

Nama Proyek: {project_name}
Tech Stack: {tech_stack_summary}

Susun 3-5 coding guideline paling penting dan actionable untuk stack ini (contoh topik: struktur
folder, konvensi penamaan, penanganan error, testing, keamanan dasar) -- sesuaikan dengan
teknologi yang disebutkan, jangan generik.

Tulis dalam Bahasa Indonesia.
""".strip()

    try:
        return _generate_structured(prompt, CodingGuidelinesSuggestion, temperature=0.3)
    except Exception as e:
        raise RuntimeError(f"Gagal memanggil AI: {str(e)}")


def suggest_dev_plan(project_name: str, epic_names: List[str]) -> DevPlanSuggestion:
    """Menyusun draf development plan awal berdasarkan daftar Epic yang sudah di-generate"""
    epics_line = ", ".join(epic_names) if epic_names else "Tidak ada epic yang terdaftar."

    prompt = f"""
Kamu adalah Project Manager teknis yang menyusun rencana pengembangan awal (development plan)
untuk sebuah proyek software, berdasarkan modul-modul (Epic) yang sudah didefinisikan.

Nama Proyek: {project_name}
Daftar Epic: {epics_line}

Buat satu task development untuk MASING-MASING epic di atas (jumlah task = jumlah epic),
diurutkan berdasarkan prioritas logis (fondasi seperti autentikasi/setup lebih dulu). Judul
task boleh mengikuti nama epic-nya, deskripsi singkat 1-2 kalimat cakupan kerjanya.

Tulis dalam Bahasa Indonesia.
""".strip()

    try:
        return _generate_structured(prompt, DevPlanSuggestion, temperature=0.3)
    except Exception as e:
        raise RuntimeError(f"Gagal memanggil AI: {str(e)}")