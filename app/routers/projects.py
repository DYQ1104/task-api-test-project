from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from ..db import get_connection
from ..dependencies import clean, current_user, project_owned
from ..schemas import ProjectIn, ProjectPatch
router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

@router.post("", status_code=201)
def create_project(payload: ProjectIn, user_id: int = Depends(current_user)):
    name = clean(payload.name)
    if not name:
        raise HTTPException(400, detail={"code":"VALIDATION_ERROR","message":"name must not be empty"})
    with get_connection() as conn:
        cursor = conn.execute("INSERT INTO projects(name,description,owner_id) VALUES(?,?,?)", (name, clean(payload.description), user_id))
        return dict(conn.execute("SELECT * FROM projects WHERE id=?", (cursor.lastrowid,)).fetchone())

@router.get("")
def list_projects(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user_id: int = Depends(current_user)):
    with get_connection() as conn:
        total = conn.execute("SELECT count(*) n FROM projects WHERE owner_id=?", (user_id,)).fetchone()["n"]
        rows = conn.execute("SELECT * FROM projects WHERE owner_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?", (user_id, page_size, (page-1)*page_size)).fetchall()
    return {"items":[dict(row) for row in rows],"page":page,"page_size":page_size,"total":total}

@router.get("/{project_id}")
def get_project(project_id: int, user_id: int = Depends(current_user)):
    with get_connection() as conn:
        return dict(project_owned(conn, project_id, user_id))

@router.patch("/{project_id}")
def patch_project(project_id: int, payload: ProjectPatch, user_id: int = Depends(current_user)):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(400, detail={"code":"VALIDATION_ERROR","message":"No fields supplied"})
    if "name" in data:
        data["name"] = clean(data["name"])
        if not data["name"]:
            raise HTTPException(400, detail={"code":"VALIDATION_ERROR","message":"name must not be empty"})
    with get_connection() as conn:
        project_owned(conn, project_id, user_id)
        columns = ",".join(f"{key}=?" for key in data)
        conn.execute(f"UPDATE projects SET {columns},updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?", [*data.values(), project_id])
        return dict(project_owned(conn, project_id, user_id))

@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, user_id: int = Depends(current_user)):
    with get_connection() as conn:
        project_owned(conn, project_id, user_id)
        conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
