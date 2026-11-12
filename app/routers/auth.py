from fastapi import APIRouter, HTTPException
from ..auth import create_token, hash_password, verify_password
from ..db import get_connection
from ..dependencies import clean
from ..schemas import Credentials
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/register", status_code=201)
def register(payload: Credentials):
    username = clean(payload.username)
    if not username:
        raise HTTPException(400, detail={"code": "VALIDATION_ERROR", "message": "username must not be empty"})
    with get_connection() as conn:
        if conn.execute("SELECT 1 FROM users WHERE username=? COLLATE NOCASE", (username,)).fetchone():
            raise HTTPException(409, detail={"code": "USERNAME_EXISTS", "message": "Username already exists"})
        cursor = conn.execute("INSERT INTO users(username,password_hash) VALUES(?,?)", (username, hash_password(payload.password)))
        row = conn.execute("SELECT id,username,created_at FROM users WHERE id=?", (cursor.lastrowid,)).fetchone()
    return dict(row)

@router.post("/login")
def login(payload: Credentials):
    with get_connection() as conn:
        user = conn.execute("SELECT id,password_hash FROM users WHERE username=? COLLATE NOCASE", (clean(payload.username),)).fetchone()
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(401, detail={"code": "INVALID_CREDENTIALS", "message": "Invalid username or password"})
    return {"access_token": create_token(user["id"]), "token_type": "Bearer", "expires_in": 3600}
