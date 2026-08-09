from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import model
import schemas
import auth
from database import get_db

router = APIRouter(prefix="/api/workspaces", tags=["Workspaces"])

@router.post("", response_model=schemas.WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    workspace_data: schemas.WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    # 1. Buat data workspace baru
    new_workspace = model.Workspace(
        name=workspace_data.name,
        owner_id=current_user.id
    )
    db.add(new_workspace)
    db.commit()
    db.refresh(new_workspace)

    # 2. Otomatis daftarkan pembuatnya sebagai anggota pertama dengan peran "owner"
    member_link = model.WorkspaceMember(
        workspace_id=new_workspace.id,
        user_id=current_user.id,
        role="owner"
    )
    db.add(member_link)
    db.commit()

    return new_workspace

@router.get("", response_model=List[schemas.WorkspaceResponse])
def get_my_workspaces(
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mendapatkan daftar seluruh workspace yang diikuti oleh user"""
    memberships = db.query(model.WorkspaceMember).filter(model.WorkspaceMember.user_id == current_user.id).all()
    workspace_ids = [m.workspace_id for m in memberships]
    
    workspaces = db.query(model.Workspace).filter(model.Workspace.id.in_(workspace_ids)).all()
    return workspaces

@router.get("/{id}/members", response_model=List[schemas.WorkspaceMemberResponse])
def get_workspace_members(
    id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mendapatkan daftar seluruh anggota tim di dalam suatu workspace (Hanya untuk anggota workspace)"""
    # Pastikan user yang me-request adalah anggota dari workspace ini
    membership = db.query(model.WorkspaceMember).filter(
        model.WorkspaceMember.workspace_id == id,
        model.WorkspaceMember.user_id == current_user.id
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak memiliki akses ke ruang kerja ini"
        )
    
    members = db.query(model.WorkspaceMember).filter(model.WorkspaceMember.workspace_id == id).all()
    
    response_data = []
    for member in members:
        user_info = db.query(model.User).filter(model.User.id == member.user_id).first()
        response_data.append({
            "user_id": member.user_id,
            "username": user_info.username,
            "email": user_info.email,
            "role": member.role,
            "joined_at": member.joined_at
        })
    
    return response_data

@router.post("/{id}/members", status_code=status.HTTP_201_CREATED)
def add_workspace_member(
    id: int,
    email: str,
    role: str,  # "owner", "editor", "viewer"
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mengundang/menambahkan anggota baru ke workspace (Hanya Owner yang diizinkan)"""
    workspace = db.query(model.Workspace).filter(model.Workspace.id == id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ruang kerja tidak ditemukan"
        )

    # Cek apakah user yang login memiliki peran 'owner' di workspace ini
    current_user_membership = db.query(model.WorkspaceMember).filter(
        model.WorkspaceMember.workspace_id == id,
        model.WorkspaceMember.user_id == current_user.id
    ).first()
    
    if not current_user_membership or current_user_membership.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya Owner ruang kerja yang dapat mengundang anggota baru"
        )

    # Validasi role
    if role not in ["owner", "editor", "viewer"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role tidak valid. Gunakan 'owner', 'editor', atau 'viewer'"
        )

    # Cari target user berdasarkan email
    target_user = db.query(model.User).filter(model.User.email == email).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pengguna dengan email tersebut belum terdaftar di sistem"
        )

    # Cek jika target user sudah tergabung di workspace ini
    existing_member = db.query(model.WorkspaceMember).filter(
        model.WorkspaceMember.workspace_id == id,
        model.WorkspaceMember.user_id == target_user.id
    ).first()
    
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pengguna tersebut sudah menjadi anggota ruang kerja ini"
        )

    # Tambahkan anggota baru
    new_member = model.WorkspaceMember(
        workspace_id=id,
        user_id=target_user.id,
        role=role
    )
    db.add(new_member)
    db.commit()
    
    return {"message": f"Berhasil menambahkan {email} ke ruang kerja sebagai {role}"}

@router.delete("/{id}/members/{user_id}")
def remove_workspace_member(
    id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: model.User = Depends(auth.get_current_user)
):
    """Mengeluarkan anggota dari workspace (Hanya Owner yang diizinkan)"""
    # Cek apakah user yang login memiliki peran 'owner'
    current_user_membership = db.query(model.WorkspaceMember).filter(
        model.WorkspaceMember.workspace_id == id,
        model.WorkspaceMember.user_id == current_user.id
    ).first()
    
    if not current_user_membership or current_user_membership.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya Owner ruang kerja yang dapat mengeluarkan anggota"
        )

    target_member = db.query(model.WorkspaceMember).filter(
        model.WorkspaceMember.workspace_id == id,
        model.WorkspaceMember.user_id == user_id
    ).first()
    
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anggota tidak ditemukan di ruang kerja ini"
        )

    # Cegah menghapus diri sendiri jika merupakan owner satu-satunya
    if user_id == current_user.id:
        owner_count = db.query(model.WorkspaceMember).filter(
            model.WorkspaceMember.workspace_id == id,
            model.WorkspaceMember.role == "owner"
        ).count()
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Anda adalah satu-satunya Owner. Tunjuk Owner baru terlebih dahulu sebelum keluar."
            )

    db.delete(target_member)
    db.commit()
    
    return {"message": "Anggota berhasil dikeluarkan dari ruang kerja"}