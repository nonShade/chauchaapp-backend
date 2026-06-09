from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any


class TaskStatusResponse(BaseModel):
    task_id: str = Field(..., description="ID de la tarea")
    status: str = Field(..., description="Estado: pending, processing, completed, failed")
    task_type: str = Field(..., description="Tipo de tarea")
    created_at: datetime = Field(..., description="Fecha de creación")
    completed_at: datetime | None = Field(None, description="Fecha de finalización")
    result: Any = Field(None, description="Resultado (si status=completed)")
    error: str | None = Field(None, description="Error (si status=failed)")


class TaskSubmitResponse(BaseModel):
    task_id: str = Field(..., description="ID de la tarea para consultar estado")
    status: str = Field("pending", description="Estado inicial")
    message: str = Field(..., description="Mensaje informativo")
