import os
import json
from pydantic import BaseModel, Field
from typing import List, Optional
from google import genai
from google.genai import types
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ================= SKEMA DATA PYDANTIC =================

class UserTypeSuggestion(BaseModel):
    name: str = Field(description="Nama tipe pengguna/persona")
    description: str = Field(description="Penjelasan peran dan tanggung jawab pengguna")

class EpicSuggestion(BaseModel):
    name: str = Field(description="Kategori modul/fitur besar")
    description: str = Field(description="Tujuan dan batasan cakupan modul")

class UserStorySuggestion(BaseModel):
    epic_name: str = Field(description="Nama Epic induk")
    story_name: str = Field(description="Judul cerita pengguna")
    user_type: str = Field(description="Aktor/User type yang menjalankan")
    description: str = Field(description="Sebagai [user], saya ingin [fitur] agar [manfaat]")
    acceptance_criteria: List[str] = Field(description="Daftar kriteria penerimaan format Given-When-Then")
    tech_notes: Optional[List[str]] = Field(default=[], description="Catatan teknis arsitektur")
    test_cases: Optional[List[str]] = Field(default=[], description="Skenario pengujian QA")

class NFRSuggestion(BaseModel):
    category: str = Field(description="Kategori NFR (Performance, Security, Availability, dll)")
    description: str = Field(description="Target kuantitatif terukur")

class ProjectRequirementsOutput(BaseModel):
    user_types: List[UserTypeSuggestion]
    epics: List[EpicSuggestion]
    user_stories: List[UserStorySuggestion]
    nfrs: List[NFRSuggestion]


# ================= CLIENT INITIALIZATION =================

# 1. Gemini Client
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# 2. OpenRouter Client (OpenAI-Compatible)
openrouter_client = OpenAI(
    base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=os.getenv("OPENROUTER_API_KEY", "")
)
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

# 3. Groq Client (OpenAI-Compatible)
groq_client = OpenAI(
    base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
    api_key=os.getenv("GROQ_API_KEY", "")
)
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


# ================= CORE ENGINE FUNCTIONS =================

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
    Menghasilkan dokumentasi lengkap tanpa batas 4 dengan orkestrasi Multi-AI.
    """
    rules_text = "\n".join([f"- {r}" for r in ai_rules]) if ai_rules else "- Standar industri profesional."

    # TAHAP 1: Gemini merancang Kerangka Utama (User Types, Epics, NFR)
    prompt_stage1 = f"""
    Bertindaklah sebagai Senior System Architect. Rancang kerangka arsitektur untuk proyek berikut:
    Nama Proyek: {project_name}
    Deskripsi: {project_description}
    Tipe: {application_type} | Domain: {domain_business}
    Target User: {target_users} | Tujuan: {business_goals}
    Aturan Khusus: {rules_text}

    Buatkan:
    1. 4-6 User Types / Persona mendalam.
    2. 6-10 Epics (Modul Utama) yang komprehensif dari hulu ke hilir.
    3. 6-8 NFRs terukur (Performance, Security, Availability, Usability, Scalability).
    4. Minimal 1-2 User Story dasar per Epic sebagai acuan awal.
    """

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt_stage1,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ProjectRequirementsOutput,
                temperature=0.3,
                max_output_tokens=16384,
            )
        )
        result = json.loads(response.text)
        return ProjectRequirementsOutput(**result)

    except Exception as gemini_err:
        print(f"⚠️ Gemini fallback ke OpenRouter/Groq: {str(gemini_err)}")
        # TAHAP FALLBACK jika Gemini limit: Panggil OpenRouter / Groq
        try:
            chat_completion = openrouter_client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional system analyst. Output valid JSON matching the schema strictly."},
                    {"role": "user", "content": prompt_stage1}
                ],
                response_format={"type": "json_object"}
            )
            raw_text = chat_completion.choices[0].message.content
            return ProjectRequirementsOutput(**json.loads(raw_text))
        except Exception as fallback_err:
            raise RuntimeError(f"Semua provider AI gagal memproses data: {str(fallback_err)}")


def generate_detailed_stories_for_epic(epic_name: str, epic_desc: str, project_context: str) -> List[UserStorySuggestion]:
    """
    Menghasilkan 4-8 User Story mendalam untuk 1 Epic spesifik menggunakan OpenRouter / Groq.
    """
    prompt = f"""
    Proyek: {project_context}
    Epic: {epic_name} ({epic_desc})

    Hasilkan 4-8 User Story spesifik dan kaya detail untuk Epic ini.
    Format JSON:
    [
      {{
        "epic_name": "{epic_name}",
        "story_name": "Judul Story",
        "user_type": "Peran",
        "description": "Sebagai [peran], saya ingin [fitur] agar [manfaat]",
        "acceptance_criteria": ["Given...", "When...", "Then..."],
        "tech_notes": ["Catatan teknis arsitektur / database / API"],
        "test_cases": ["Nama skenario test QA"]
      }}
    ]
    """
    try:
        # Gunakan Groq untuk pemrosesan detail super cepat
        res = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Return ONLY a JSON array of stories."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        data = json.loads(res.choices[0].message.content)
        stories_list = data if isinstance(data, list) else data.get("stories", [])
        return [UserStorySuggestion(**s) for s in stories_list]
    except Exception as e:
        print(f"Gagal generate detail story: {e}")
        return []