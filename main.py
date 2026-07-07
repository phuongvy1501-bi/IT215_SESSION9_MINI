from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Tuple
from datetime import datetime

app = FastAPI(title="Team Task Management API")

tasks_db = [
    {
        "id": 1, 
        "title": "Thiet ke database Shop AI", 
        "description": "Xay dung bang va toi uu index", 
        "assignee": "QuyDev", 
        "priority": 1, 
        "status": "todo",
        "created_at": "2026-07-01T09:00:00Z"
    },
    {
        "id": 2, 
        "title": "Code bo API Authen", 
        "description": "Trien khai filter verify JWT token", 
        "assignee": "FixerQ", 
        "priority": 2, 
        "status": "done",
        "created_at": "2026-07-01T10:00:00Z"
    }
]

class TaskCreateSchema(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=1)
    assignee: str = Field(..., min_length=1)
    priority: int = Field(..., ge=1, le=5)

    class Config:
        anystr_strip_whitespace = True 

class TaskStatusUpdateSchema(BaseModel):
    status: str = Field(..., min_length=1)

def make_unified_response(
    status_code: int, 
    message: str, 
    data: Any = None, 
    error: Optional[str] = None, 
    path: str = ""
) -> JSONResponse:
    """Đóng gói dữ liệu đầu ra qua định dạng Unified Envelope JSON 6 trường bắt buộc"""
    payload = {
        "statusCode": status_code,
        "message": message,
        "data": data,
        "error": error,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "path": path
    }
    return JSONResponse(status_code=status_code, content=payload)

@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Bẫy lỗi dữ liệu đầu vào không hợp lệ từ Pydantic Field"""
    return make_unified_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Lỗi: Dữ liệu đầu vào không hợp lệ hoặc sai định dạng quy định!",
        error="ERR-VAL-422: Validation error at Request Body fields constraint layout.",
        path=request.url.path
    )

@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    """Bẫy các lỗi nghiệp vụ chủ động raise từ endpoint"""
    error_msg = str(exc.detail)
    return make_unified_response(
        status_code=exc.status_code,
        message=error_msg.split("::")[-1] if "::" in error_msg else error_msg,
        error=error_msg.split("::")[0] if "::" in error_msg else f"ERR-HTTP-{exc.status_code}",
        path=request.url.path
    )

@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    """Triệt tiêu hoàn toàn nguy cơ lộ mã nguồn Stack Trace thô ra Client"""
    return make_unified_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Lỗi hệ thống nghiêm trọng, vui lòng thử lại sau!",
        error=f"ERR-INTERNAL-500: {str(exc)}",
        path=request.url.path
    )

def calculate_team_metrics() -> Tuple[int, int, float]:
    """Hàm xử lý tính toán thuần túy, bắt buộc return Tuple 3 giá trị"""
    total_tasks = len(tasks_db)
    if total_tasks == 0:
        return (0, 0, 0.0)

    completed_tasks = sum(1 for task in tasks_db if task["status"] == "done")
    completion_rate = round((completed_tasks / total_tasks) * 100, 1)
    return (total_tasks, completed_tasks, completion_rate)

@app.get("/tasks")
def get_all_tasks(request: Request, status: Optional[str] = None):
    """Chức năng 1: Xem danh sách công việc hiện có (Hỗ trợ lọc & mảng rỗng)"""
    filtered_tasks = tasks_db
    if status: