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

c# Data yang dikirim frontend saat membuat aturan AI baru
class AIRuleCreate(BaseModel):
    name: str
    content: str

# Data lengkap yang dikembalikan oleh server
class AIRuleResponse(BaseModel):
    id: int
    name: str
    content: str
    created_at: datetime
    project_id: int

    class Config:
        from_attributes = True
