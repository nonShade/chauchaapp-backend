"""
Financial planning controller.

Endpoints:
    - GET /v1/financial-planning
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.modules.financial_data.dto import (
    FinancialPlanningTipsBatchResponseDTO,
    FinancialPlanningTipsResponseDTO,
)
from app.modules.financial_data.service import FinancialPlanningService
from app.shared.database import get_db

router = APIRouter(prefix="/v1/financial-planning", tags=["Financial Planning"])


def _get_financial_planning_service(
    db: Session = Depends(get_db),
) -> FinancialPlanningService:
    return FinancialPlanningService(db=db)


@router.post(
    "/generate",
    response_model=FinancialPlanningTipsBatchResponseDTO,
    summary="Generar planificaciones financieras",
    description="Genera tips de planificacion financiera y guarda un nuevo lote activo.",
    status_code=status.HTTP_201_CREATED,
)
def generate_financial_planning_tips(
    service: FinancialPlanningService = Depends(_get_financial_planning_service),
) -> FinancialPlanningTipsBatchResponseDTO:
    try:
        tips = service.generate_and_save_tips()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando planificaciones: {str(exc)}",
        )

    generated_at = service.get_latest_generation_date()
    return {
        "financialPlanningTips": [tip.model_dump() for tip in tips],
        "totalCount": len(tips),
        "generatedAt": generated_at.isoformat() if generated_at else "",
    }


@router.get(
    "",
    response_model=FinancialPlanningTipsResponseDTO,
    summary="Obtener planificaciones financieras",
    description="Devuelve el lote activo de tips de planificacion financiera.",
)
def get_financial_planning_tips(
    service: FinancialPlanningService = Depends(_get_financial_planning_service),
) -> FinancialPlanningTipsResponseDTO:
    tips = service.get_active_tips()
    return {
        "financialPlanningTips": [tip.model_dump() for tip in tips],
    }
