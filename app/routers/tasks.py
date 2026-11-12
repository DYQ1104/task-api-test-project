from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from ..db import get_connection
from ..dependencies import clean, current_user, project_owned, task_owned
from ..schemas import TaskIn, TaskPatch
router = APIRouter(tags=["tasks"])
VALID_STATUS = {"todo", "doing", "done"}

@router.post("/api/v1/projects/{project_id}/tasks", status_code=201)
def create_task(project_id: int, payload: TaskIn, user_id: int = Depends(current_user)):
    title = clean(payload.title)
    if not title or payload.status not in VALID_STATUS:
        raise HTTPException(400, detail={"code":"VALIDATION_ERROR","message":"Invalid title or status"})
    with get_connection() as conn:
        project_owned(conn, project_id, user_id)
        cursor = conn.execute("INSERT INTO tasks(project_id,title,description,status) VALUES(?,?,?,?)", (project_id,title,clean(payload.description),payload.status))
        return dict(conn.execute("SELECT * FROM tasks WHERE id=?", (cursor.lastrowid,)).fetchone())

@router.get("/api/v1/projects/{project_id}/tasks")
def list_tasks(project_id: int, status: Optional[str] = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user_id: int = Depends(current_user)):
    if status is not None and status not in VALID_STATUS:
        raise HTTPException(400, detail={"code":"VALIDATION_ERROR","message":"Invalid status"})
    with get_connection() as conn:
        project_owned(conn, project_id, user_id)
        where = "project_id=?"; args = [project_id]
        if status:
            where += " AND status=?"; args.append(status)
        total = conn.execute(f"SELECT count(*) n FROM tasks WHERE {where}", args).fetchone()["n"]
        rows = conn.execute(f"SELECT * FROM tasks WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?", [*args,page_size,(page-1)*page_size]).fetchall()
    return {"items":[dict(row) for row in rows],"page":page,"page_size":page_size,"total":total}

@router.get("/api/v1/tasks/{task_id}")
def get_task(task_id: int, user_id: int = Depends(current_user)):
    with get_connection() as conn:
        return dict(task_owned(conn, task_id, user_id))

@router.patch("/api/v1/tasks/{task_id}")
def patch_task(task_id: int, payload: TaskPatch, user_id: int = Depends(current_user)):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(400, detail={"code":"VALIDATION_ERROR","message":"No fields supplied"})
    if "title" in data:
        data["title"] = clean(data["title"])
        if not data["title"]:
            raise HTTPException(400, detail={"code":"VALIDATION_ERROR","message":"Invalid title"})
    if data.get("status") is not None and data["status"] not in VALID_STATUS:
        raise HTTPException(400, detail={"code":"VALIDATION_ERROR","message":"Invalid status"})
    with get_connection() as conn:
        task_owned(conn, task_id, user_id)
        columns = ",".join(f"{key}=?" for key in data)
        conn.execute(f"UPDATE tasks SET {columns},updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?", [*data.values(), task_id])
        return dict(task_owned(conn, task_id, user_id))

@router.delete("/api/v1/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, user_id: int = Depends(current_user)):
    with get_connection() as conn:
        task_owned(conn, task_id, user_id)
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
