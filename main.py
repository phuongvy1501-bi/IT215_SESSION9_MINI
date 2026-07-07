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
        filtered_tasks = [task for task in tasks_db if task["status"] == status]

    return make_unified_response(
        status_code=status.HTTP_200_OK,
        message="Lấy danh sách công việc thành công!",
        data=filtered_tasks,
        path=request.url.path
    )

@app.post("/tasks")
def create_task(request: Request, task_in: TaskCreateSchema):
    """Chức năng 2: Tạo mới công việc nhóm (Chặn trùng title tự động)"""
    for task in tasks_db:
        if task["title"].strip().lower() == task_in.title.strip().lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ERR-TASK-01: Task conflict: Title field duplicates an existing record.::Lỗi: Tiêu đề công việc này đã tồn tại trong nhóm!"
            )

    max_id = max([task["id"] for task in tasks_db]) if tasks_db else 0
    new_task = {
        "id": max_id + 1,
        "title": task_in.title,
        "description": task_in.description,
        "assignee": task_in.assignee,
        "priority": task_in.priority,
        "status": "todo",
        "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    tasks_db.append(new_task)

    return make_unified_response(
        status_code=status.HTTP_201_CREATED,
        message="Khởi tạo công việc mới thành công!",
        data=new_task,
        path=request.url.path
    )

@app.put("/tasks/{task_id}")
def update_task_status(request: Request, task_id: int, status_in: TaskStatusUpdateSchema):
    """Chức năng 3: Cập nhật trạng thái tiến độ công việc"""
    target_task = None
    for task in tasks_db:
        if task["id"] == task_id:
            target_task = task
            break

    if not target_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ERR-TASK-03: Task not found.::Lỗi: Không tìm thấy ID công việc yêu cầu!"
        )

    if target_task["status"] == "done":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ERR-TASK-04: Cannot regress status of a completed task.::Lỗi: Công việc đã hoàn thành không được phép cập nhật lùi trạng thái!"
        )

    target_task["status"] = status_in.status
    return make_unified_response(
        status_code=status.HTTP_200_OK,
        message="Cập nhật tiến độ công việc thành công!",
        data=target_task,
        path=request.url.path
    )

@app.get("/tasks/analytics/dashboard")
def get_dashboard_analytics(request: Request):
    """Chức năng 4: Endpoint điều phối thống kê hiệu suất nhóm"""
    total_tasks, completed_tasks, completion_rate_percentage = calculate_team_metrics()

    dashboard_data = {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "completion_rate_percentage": completion_rate_percentage
    }

    return make_unified_response(
        status_code=status.HTTP_200_OK,
        message="Lấy số liệu thống kê hiệu suất nhóm thành công!",
        data=dashboard_data,
        path=request.url.path
    )