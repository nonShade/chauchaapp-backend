"""
Financial planning controller.

Endpoints:
    - POST /v1/financial-planning/generate   : Iniciar generación en background
    - GET  /v1/financial-planning/tasks/{task_id} : Estado de generación
    - GET  /v1/financial-planning             : Lote activo
"""

import threading
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.modules.financial_data.dto import (
    FinancialPlanningTipsBatchResponseDTO,
    FinancialPlanningTipsResponseDTO,
)
from app.modules.financial_data.service import FinancialPlanningService
from app.shared.background import task_manager
from app.shared.background_dto import TaskStatusResponse, TaskSubmitResponse
from app.shared.database import SessionLocal, get_db

router = APIRouter(prefix="/v1/financial-planning", tags=["Financial Planning"])


def _get_financial_planning_service(
    db: Session = Depends(get_db),
) -> FinancialPlanningService:
    return FinancialPlanningService(db=db)


def _background_fp_worker(task_id: str) -> None:
    """Generate financial planning tips in background thread."""
    db = SessionLocal()
    try:
        task_manager.update_status(task_id, "processing")
        service = FinancialPlanningService(db=db)
        tips = service.generate_and_save_tips()
        generated_at = service.get_latest_generation_date()
        result = {
            "financialPlanningTips": [tip.model_dump() for tip in tips],
            "totalCount": len(tips),
            "generatedAt": generated_at.isoformat() if generated_at else None,
        }
        task_manager.update_status(task_id, "completed", result=result)
    except Exception as e:
        task_manager.update_status(task_id, "failed", error=str(e))
    finally:
        db.close()


@router.post(
    "/generate",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Iniciar generación de planificaciones en background",
    description="Encola la generación de tips y retorna task_id. Consulta GET /v1/financial-planning/tasks/{task_id} para resultados.",
)
def generate_financial_planning_tips():
    task_id = task_manager.create_task("financial_planning_generate")
    thread = threading.Thread(
        target=_background_fp_worker, args=(task_id,), daemon=True
    )
    thread.start()
    return TaskSubmitResponse(
        task_id=task_id,
        status="pending",
        message="Generación de planificaciones iniciada. Consulta GET /v1/financial-planning/tasks/{task_id} para resultados.",
    )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
    summary="Consultar estado de generación de planificaciones",
)
def get_fp_task_status(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Task no encontrada")
    return TaskStatusResponse(**task)


@router.get(
    "",
    response_model=FinancialPlanningTipsResponseDTO,
    summary="Obtener planificaciones financieras activas",
)
def get_financial_planning_tips(
    service: FinancialPlanningService = Depends(_get_financial_planning_service),
) -> FinancialPlanningTipsResponseDTO:
    tips = service.get_active_tips()
    return {"financialPlanningTips": [tip.model_dump() for tip in tips]}
