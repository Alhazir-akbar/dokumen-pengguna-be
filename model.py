from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timezone

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)  # Hanya menyimpan password terenkripsi
    full_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    last_login = Column(DateTime, nullable=True)

    # Relasi
    workspaces_owned = relationship("Workspace", back_populates="owner")
    workspace_memberships = relationship("WorkspaceMember", back_populates="user")
    projects_created = relationship("Project", back_populates="creator")

class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relasi
    owner = relationship("User", back_populates="workspaces_owned")
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="workspace", cascade="all, delete-orphan")
    ai_rules = relationship("AIRule", back_populates="workspace", cascade="all, delete-orphan")

# Rapat ke kiri (tidak menjorok di dalam kelas Workspace)
class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, default="viewer")  # "owner", "editor", "viewer"
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relasi
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="workspace_memberships")

# Rapat ke kiri (tidak menjorok di dalam kelas Workspace)
class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    application_type = Column(String, nullable=True)  # Dieja benar: application_type
    domain_business = Column(String, nullable=True)
    target_users = Column(String, nullable=True)
    business_goals = Column(String, nullable=True)
    repo_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relasi
    workspace = relationship("Workspace", back_populates="projects")
    creator = relationship("User", back_populates="projects_created")
    ai_rules = relationship("AIRule", back_populates="project", cascade="all, delete-orphan")

class AIRule(Base):
    __tablename__ = "ai_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)

    # Relasi
    project = relationship("Project", back_populates="ai_rules")
    workspace = relationship("Workspace", back_populates="ai_rules")