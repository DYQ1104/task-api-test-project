from fastapi import Depends, Header, HTTPException
from .auth import verify_token
from .db import get_connection

def current_user(authorization: str = Header(default="")) -> int:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, detail={"code": "UNAUTHORIZED", "message": "Bearer token required"})
    user_id = verify_token(authorization[7:])
    if user_id is None:
        raise HTTPException(401, detail={"code": "UNAUTHORIZED", "message": "Invalid or expired token"})
    with get_connection() as conn:
        user = conn.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        raise HTTPException(401, detail={"code": "UNAUTHORIZED", "message": "Invalid token subject"})
    return user_id

def clean(value):
    return value.strip() if isinstance(value, str) else value

def project_owned(conn, project_id: int, user_id: int):
    row = conn.execute("SELECT * FROM projects WHERE id=? AND owner_id=?", (project_id, user_id)).fetchone()
    if not row:
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Resource not found"})
    return row

def task_owned(conn, task_id: int, user_id: int):
    row = conn.execute("SELECT t.* FROM tasks t JOIN projects p ON p.id=t.project_id WHERE t.id=? AND p.owner_id=?", (task_id, user_id)).fetchone()
    if not row:
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Resource not found"})
    return row
