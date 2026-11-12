from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .db import init_db
from .routers import auth, projects, tasks

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Task Management API", version="1.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)

@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code":"HTTP_ERROR","message":str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, headers=exc.headers, content={"error":{"code":detail.get("code","HTTP_ERROR"),"message":detail.get("message",str(exc.detail)),"details":detail.get("details",[])}})

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    details = [{"field":".".join(str(part) for part in item["loc"][1:]),"reason":item["msg"]} for item in exc.errors()]
    return JSONResponse(status_code=400, content={"error":{"code":"VALIDATION_ERROR","message":"Request validation failed","details":details}})

@app.get("/health")
def health():
    return {"status":"ok"}
