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

# Data yang dikirim frontend saat membuat aturan AI baru
class AIRuleCreate(BaseModel):
    name: str
    content: str

# Data lengkap yang dikembalikan oleh server
class AIRuleResponse(BaseModel):
    id: int
    name: str
    content: str
    created_at: datetime
    project_id: Optional[int] =  None  
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
    step_order: int
    title: str
    description: Optional[str] = None
    class Config:
        from_attributes = True
class UserJourneyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    project_id: int
class UserJourneyResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    project_id: int
    steps: List[JourneyStepResponse] = []
    class Config:
        from_attributes = True
