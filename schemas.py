from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# AUTHENTICATION DAN USER

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# PROFILE SETTINGS

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str

# WORKSPACE

class WorkspaceCreate(BaseModel):
    name: str

class WorkspaceResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    owner_id: int

    class Config:
        from_attributes = True

class WorkspaceMemberResponse(BaseModel):
    user_id: int
    username: str
    email: str
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True

# PROJECT

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    application_type: Optional[str] = None
    domain_business: Optional[str] = None
    target_users: Optional[str] = None
    business_goals: Optional[str] = None
    repo_url: Optional[str] = None
    workspace_id: int

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    application_type: Optional[str] = None
    domain_business: Optional[str] = None
    target_users: Optional[str] = None
    business_goals: Optional[str] = None
    repo_url: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    application_type: Optional[str] = None
    domain_business: Optional[str] = None
    target_users: Optional[str] = None
    business_goals: Optional[str] = None
    repo_url: Optional[str] = None
    created_at: datetime
    workspace_id: int
    creator_id: int

    class Config:
        from_attributes = True

# AI RULES

class AIRuleCreate(BaseModel):
    name: str
    content: str

class AIRuleSuggestionItem(BaseModel):
    name: str
    content: str

class AIRuleSuggestionsResponse(BaseModel):
    suggestions: List[AIRuleSuggestionItem] = []
    
class AIRuleResponse(BaseModel):
    id: int
    name: str
    content: str
    created_at: datetime
    project_id: Optional[int] = None
    workspace_id: Optional[int] = None

    class Config:
        from_attributes = True

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class PersonaCreate(BaseModel):
    name: str
    avatar_url: Optional[str] = None
    age: Optional[int] = None
    location: Optional[str] = None
    family_status: Optional[str] = None
    job_title: Optional[str] = None
    about: Optional[str] = None
    goals: Optional[str] = None
    frustrations: Optional[str] = None
    user_type_id: int

class PersonaResponse(BaseModel):
    id: int
    name: str
    avatar_url: Optional[str] = None
    age: Optional[int] = None
    location: Optional[str] = None
    family_status: Optional[str] = None
    job_title: Optional[str] = None
    about: Optional[str] = None
    goals: Optional[str] = None
    frustrations: Optional[str] = None
    user_type_id: int

    class Config:
        from_attributes = True

class UserTypeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    project_id: int

class UserTypeResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    project_id: int
    personas: List[PersonaResponse] = []

    class Config:
        from_attributes = True

class EpicCreate(BaseModel):
    name: str
    description: Optional[str] = None
    project_id: int

class EpicResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    project_id: int

    class Config:
        from_attributes = True

class AcceptanceCriteriaCreate(BaseModel):
    description: str
    user_story_id: int

class AcceptanceCriteriaResponse(BaseModel):
    id: int
    description: str
    user_story_id: int

    class Config:
        from_attributes = True

# ================= TECH NOTES & TEST CASES =================

class TechNoteResponse(BaseModel):
    id: int
    content: str
    user_story_id: int

    class Config:
        from_attributes = True

class TestCaseResponse(BaseModel):
    id: int
    description: str
    user_story_id: int

    class Config:
        from_attributes = True

class UserStoryCreate(BaseModel):
    epic_id: int
    user_type_id: Optional[int] = None
    code: Optional[str] = None
    as_a: Optional[str] = None
    i_want: str
    so_that: Optional[str] = None
    status: Optional[str] = "draft"
    project_id: int

class UserStoryResponse(BaseModel):
    id: int
    epic_id: int
    user_type_id: Optional[int] = None
    code: Optional[str] = None
    as_a: Optional[str] = None
    i_want: str
    so_that: Optional[str] = None
    status: str
    project_id: int
    created_at: datetime
    acceptance_criteria: List[AcceptanceCriteriaResponse] = []
    tech_notes: List[TechNoteResponse] = []
    test_cases: List[TestCaseResponse] = []

    class Config:
        from_attributes = True

class NFRCreate(BaseModel):
    category: str
    description: str
    project_id: int

class NFRResponse(BaseModel):
    id: int
    category: str
    description: str
    project_id: int

    class Config:
        from_attributes = True

# ================= JOURNEYS =================

# ================= JOURNEYS =================

class JourneyStepBulkItem(BaseModel):
    title: str
    description: Optional[str] = None
    step_order: int
    persona_id: Optional[int] = None

class JourneyStepCreate(BaseModel):
    user_journey_id: int
    persona_id: Optional[int] = None
    step_order: int
    title: str
    description: Optional[str] = None

class JourneyStepResponse(BaseModel):
    id: int
    user_journey_id: int
    persona_id: Optional[int] = None
    persona: Optional[PersonaResponse] = None
    step_order: int
    title: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class UserJourneyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    project_id: int
    steps: List[JourneyStepBulkItem] = []   # <- sekarang aman, JourneyStepBulkItem udah didefinisikan di atas

class UserJourneyUpdate(BaseModel):
    name: str
    description: Optional[str] = None

class JourneyStepsBulkUpdate(BaseModel):
    steps: List[JourneyStepBulkItem] = []

class UserJourneyResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    project_id: int
    steps: List[JourneyStepResponse] = []

    class Config:
        from_attributes = True

# ================= BUILD MODULE (FR007) =================

class TechStackUpdate(BaseModel):
    target_users: Optional[str] = None
    scale: Optional[str] = None
    platform: Optional[str] = None
    ui_language: Optional[str] = None
    ui_framework: Optional[str] = None
    ui_library: Optional[str] = None
    app_language: Optional[str] = None
    app_framework: Optional[str] = None
    data_layer: Optional[str] = None
    integration_layer: Optional[str] = None

class TechStackResponse(BaseModel):
    id: int
    project_id: int
    target_users: Optional[str] = None
    scale: Optional[str] = None
    platform: Optional[str] = None
    ui_language: Optional[str] = None
    ui_framework: Optional[str] = None
    ui_library: Optional[str] = None
    app_language: Optional[str] = None
    app_framework: Optional[str] = None
    data_layer: Optional[str] = None
    integration_layer: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True

# TAMBAHAN: field "category" untuk 5 kategori tetap (project_structure, security,
# frontend, backend, database). None berarti guideline custom buatan user.
class CodingGuidelineCreate(BaseModel):
    title: str
    content: str
    category: Optional[str] = None

class CodingGuidelineUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None

class CodingGuidelineResponse(BaseModel):
    id: int
    project_id: int
    category: Optional[str] = None
    title: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class GenerateGuidelineRequest(BaseModel):
    category: str  # project_structure | security | frontend | backend | database

class GenerateGuidelinesAllResponse(BaseModel):
    guidelines: List[CodingGuidelineResponse]
    errors: List[str] = []

# TAMBAHAN: status "completed" menggantikan "done", dan status baru "draft" untuk
# hasil AI generate yang belum direview. epic_id untuk menghubungkan plan ke requirement.
class DevelopmentPlanCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "todo"  # draft | todo | in_progress | completed
    epic_id: Optional[int] = None

class DevelopmentPlanUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    epic_id: Optional[int] = None

class DevelopmentPlanResponse(BaseModel):
    id: int
    project_id: int
    epic_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class GenerateDevPlanRequest(BaseModel):
    epic_id: int

class EpicOptionResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

# --- Tambahan Skema untuk Batch Wizard ---

class WizardStoryItemCreate(BaseModel):
    storyName: str
    userType: str
    description: Optional[str] = None

class WizardEpicItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    stories: List[WizardStoryItemCreate] = []

class WizardBatchCreateSchema(BaseModel):
    epics: List[WizardEpicItemCreate] = []
    userStories: List[WizardStoryItemCreate] = []

class SuggestDescriptionRequest(BaseModel):
    project_name: str
    platform_type: str

class SuggestDescriptionResponse(BaseModel):
    description: str

class SuggestUserGoalsRequest(BaseModel):
    project_name: str
    user_type_name: str
    user_type_description: Optional[str] = None

class SuggestUserGoalsResponse(BaseModel):
    goals: str
    frustrations: str

class SuggestUserJourneyPersonaItem(BaseModel):
    name: str
    user_type: Optional[str] = None
    about: Optional[str] = None

class SuggestUserJourneyRequest(BaseModel):
    project_name: str
    project_description: Optional[str] = None
    personas: List[SuggestUserJourneyPersonaItem] = []  

class SuggestUserJourneyStepItem(BaseModel):
    title: str
    description: str
    persona_name: Optional[str] = None  

class SuggestUserJourneyResponse(BaseModel):
    journey: str
    steps: List[SuggestUserJourneyStepItem] = []

# ================= TAMBAHAN: SKEMA KHUSUS UNTUK SAVE-REQUIREMENTS =================

class SavePersonaItem(BaseModel):
    name: str
    age: Optional[int] = None
    location: Optional[str] = None
    family_status: Optional[str] = None
    job_title: Optional[str] = None
    about: Optional[str] = None
    goals: Optional[str] = None
    frustrations: Optional[str] = None

class SaveUserTypeItem(BaseModel):
    name: str
    description: Optional[str] = None
    personas: List[SavePersonaItem] = []

class SaveEpicItem(BaseModel):
    name: str
    description: Optional[str] = None

class SaveUserStoryItem(BaseModel):
    epic_name: str
    story_name: str
    user_type: str
    description: Optional[str] = None
    acceptance_criteria: List[str] = []
    tech_notes: List[str] = []
    test_cases: List[str] = []

class SaveNFRItem(BaseModel):
    category: str
    description: str

class SaveRequirementsPayload(BaseModel):
    user_types: List[SaveUserTypeItem] = []
    epics: List[SaveEpicItem] = []
    user_stories: List[SaveUserStoryItem] = []
    nfrs: List[SaveNFRItem] = []

class SuggestUserTypeDescriptionRequest(BaseModel):
    project_name: str
    user_type_name: str
    project_description: Optional[str] = None

class SuggestUserTypeDescriptionResponse(BaseModel):
    description: str

