"""
Controlador para Daily Tips endpoints.

Routes:
    - GET  /tips/today            - Obtener los tips del dia
    - GET  /tips/all              - Obtener todos los tips activos
    - POST /tips/generate         - Iniciar generación en background
    - GET  /tips/tasks/{task_id}  - Estado de la generación
    - GET  /tips/latest-generation - Fecha de última generación
"""

import threading
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.shared.background import task_manager
from app.shared.background_dto import TaskStatusResponse, TaskSubmitResponse
from app.shared.database import SessionLocal, get_db
from app.modules.daily_tips.service import DailyTipService
from app.modules.daily_tips.dto import (
    DailyTipCreate,
    DailyTipResponse,
    DailyTipBatchResponse,
)
from app.agent.daily_tips_agent import daily_tips_agent

router = APIRouter(prefix="/tips", tags=["daily-tips"])


def _background_tips_worker(task_id: str) -> None:
    """Generate and save tips batch in background thread."""
    db = SessionLocal()
    try:
        task_manager.update_status(task_id, "processing")
        tips_data = daily_tips_agent.generate_weekly_tips_batch()

        tips_create = [
            DailyTipCreate(
                title=tip.titulo,
                text=tip.texto,
                category=tip.categoria,
                day_of_week=tip.day_of_week if tip.day_of_week is not None else 0,
            )
            for tip in tips_data
        ]

        service = DailyTipService(db)
        batch = service.create_batch(tips_create)

        task_manager.update_status(
            task_id, "completed", result=batch.model_dump(mode="json")
        )
    except Exception as e:
        task_manager.update_status(task_id, "failed", error=str(e))
    finally:
        db.close()


@router.get(
    "/today",
    response_model=DailyTipResponse,
    summary="Obtener el consejo financiero de hoy",
)
def get_today_tip(db: Session = Depends(get_db)) -> DailyTipResponse:
    service = DailyTipService(db)
    today_day = date.today().weekday()
    tip = service.get_today_tip(today_day)
    if not tip:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="No hay consejo disponible para hoy. Por favor genera un nuevo lote.",
        )
    return tip


@router.get(
    "/all",
    response_model=DailyTipBatchResponse,
    summary="Obtener todos los consejos activos",
)
def get_all_tips(db: Session = Depends(get_db)) -> DailyTipBatchResponse:
    service = DailyTipService(db)
    batch = service.get_all_active()
    if batch.total_count == 0:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="No hay consejos disponibles. Por favor genera un nuevo lote.",
        )
    return batch


@router.post(
    "/generate",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Iniciar generación de consejos en background",
    description="Encola la generación de 7 consejos y retorna task_id. Consulta GET /tips/tasks/{task_id} para el resultado.",
)
def generate_tips_batch():
    task_id = task_manager.create_task("tips_generate")
    thread = threading.Thread(
        target=_background_tips_worker, args=(task_id,), daemon=True
    )
    thread.start()
    return TaskSubmitResponse(
        task_id=task_id,
        status="pending",
        message="Generación de consejos iniciada. Consulta GET /tips/tasks/{task_id} para resultados.",
    )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
    summary="Consultar estado de generación de consejos",
)
def get_tips_task_status(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Task no encontrada")
    return TaskStatusResponse(**task)


@router.get(
    "/latest-generation",
    response_model=dict,
    summary="Obtener la fecha de la última generación",
)
def get_latest_generation(db: Session = Depends(get_db)) -> dict:
    service = DailyTipService(db)
    generation_date = service.get_latest_generation_date()
    if not generation_date:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Aún no se ha generado ningún lote.",
        )
    return {
        "generated_at": generation_date,
        "days_since_generation": (datetime.utcnow() - generation_date).days,
    }
