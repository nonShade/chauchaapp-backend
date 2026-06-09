"""
Education controller — HTTP endpoint layer.

Endpoints:
    - POST /v1/education/modules/generate           : Iniciar generación en background
    - GET  /v1/education/modules/tasks/{task_id}    : Estado de generación
    - GET  /v1/education/modules
    - GET  /v1/education/modules/{slug}
    - POST /v1/education/modules/{module_id}/progress/start
    - PATCH /v1/education/modules/{module_id}/progress/sections
    - POST /v1/education/modules/{module_id}/quiz/attempts
"""

import threading

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.modules.education.dto import (
    GenerateModulesRequestDTO,
    ModuleDetailResponseDTO,
    ModulesListResponseDTO,
    SubmitQuizAttemptRequestDTO,
    SubmitQuizAttemptResponseDTO,
    UpdateModuleProgressRequestDTO,
    UserModuleProgressDTO,
)
from app.modules.education.repository import EducationRepository
from app.modules.education.service import EducationService
from app.shared.background import task_manager
from app.shared.background_dto import TaskStatusResponse, TaskSubmitResponse
from app.shared.database import SessionLocal, get_db

router = APIRouter(prefix="/v1/education", tags=["Education"])


def _background_education_worker(task_id: str, items: list[dict]) -> None:
    """Generate education modules in background thread."""
    from app.modules.education.repository import EducationRepository
    from app.modules.education.service import EducationService

    db = SessionLocal()
    try:
        task_manager.update_status(task_id, "processing")
        repo = EducationRepository(db)
        service = EducationService(repository=repo)
        modules = service.generate_modules(items=items)
        result = {
            "items": [
                {
                    "module": service.get_module_detail_payload(m),
                    "progress": service.get_progress_for_module(
                        module_id=m.id, user_id=None
                    ),
                }
                for m in modules
            ]
        }
        task_manager.update_status(task_id, "completed", result=result)
    except Exception as e:
        task_manager.update_status(task_id, "failed", error=str(e))
    finally:
        db.close()


def _get_education_service(db: Session = Depends(get_db)) -> EducationService:
    repository = EducationRepository(db)
    return EducationService(repository=repository)


def _raise_service_error(exc: ValueError) -> None:
    detail = str(exc)
    status_code = (
        status.HTTP_404_NOT_FOUND
        if "not found" in detail.lower()
        else status.HTTP_400_BAD_REQUEST
    )
    raise HTTPException(status_code=status_code, detail=detail)


@router.get(
    "/modules",
    response_model=ModulesListResponseDTO,
    summary="Listar modulos educativos",
    description="Devuelve el catalogo de modulos educativos disponibles.",
)
def list_modules(
    service: EducationService = Depends(_get_education_service),
) -> ModulesListResponseDTO:
    modules = service.list_modules()
    return {
        "totalCount": len(modules),
        "modules": service.get_module_card_payload(modules),
    }


@router.post(
    "/modules/generate",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Iniciar generación de módulo educativo en background",
    description="Encola la generación de módulos y retorna task_id. Consulta GET /v1/education/modules/tasks/{task_id} para resultados.",
)
def generate_module_background(
    payload: GenerateModulesRequestDTO,
):
    items_data = [item.model_dump() for item in payload.items]
    task_id = task_manager.create_task("education_generate")
    thread = threading.Thread(
        target=_background_education_worker,
        args=(task_id, items_data),
        daemon=True,
    )
    thread.start()
    return TaskSubmitResponse(
        task_id=task_id,
        status="pending",
        message="Generación de módulo iniciada. Consulta GET /v1/education/modules/tasks/{task_id} para resultados.",
    )


@router.get(
    "/modules/tasks/{task_id}",
    response_model=TaskStatusResponse,
    summary="Consultar estado de generación de módulo educativo",
)
def get_education_task_status(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Task no encontrada")
    return TaskStatusResponse(**task)


@router.get(
    "/modules/{slug}",
    response_model=ModuleDetailResponseDTO,
    summary="Obtener detalle de modulo educativo",
    description="Devuelve el contenido completo del modulo y progreso del usuario.",
    responses={
        404: {"description": "Modulo no encontrado"},
    },
)
def get_module_detail(
    slug: str,
    user_id: str | None = Query(default=None, description="ID del usuario"),
    service: EducationService = Depends(_get_education_service),
) -> ModuleDetailResponseDTO:
    module = service.get_module_by_slug(slug)
    if module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Modulo no encontrado",
        )

    try:
        progress = service.get_progress_for_module(
            module_id=module.id, user_id=user_id
        )
    except ValueError as exc:
        _raise_service_error(exc)

    return {
        "module": service.get_module_detail_payload(module),
        "progress": progress,
    }


@router.post(
    "/modules/{module_id}/progress/start",
    response_model=UserModuleProgressDTO,
    summary="Iniciar progreso de modulo",
    description="Crea o reactiva el progreso del usuario para un modulo.",
)
def start_module_progress(
    module_id: str,
    user_id: str = Query(..., description="ID del usuario"),
    service: EducationService = Depends(_get_education_service),
) -> UserModuleProgressDTO:
    try:
        return service.start_progress(module_id=module_id, user_id=user_id)
    except ValueError as exc:
        _raise_service_error(exc)


@router.patch(
    "/modules/{module_id}/progress/sections",
    response_model=UserModuleProgressDTO,
    summary="Actualizar progreso por seccion",
    description="Marca una seccion como completada y recalcula el progreso.",
)
def update_module_progress(
    module_id: str,
    payload: UpdateModuleProgressRequestDTO,
    user_id: str = Query(..., description="ID del usuario"),
    service: EducationService = Depends(_get_education_service),
) -> UserModuleProgressDTO:
    try:
        return service.update_section_progress(
            module_id=module_id,
            user_id=user_id,
            payload=payload,
        )
    except ValueError as exc:
        _raise_service_error(exc)


@router.post(
    "/modules/{module_id}/quiz/attempts",
    response_model=SubmitQuizAttemptResponseDTO,
    summary="Registrar intento de quiz",
    description="Guarda el intento del quiz y completa el modulo si aprueba.",
)
def submit_quiz_attempt(
    module_id: str,
    payload: SubmitQuizAttemptRequestDTO,
    user_id: str = Query(..., description="ID del usuario"),
    service: EducationService = Depends(_get_education_service),
) -> SubmitQuizAttemptResponseDTO:
    try:
        return service.submit_quiz_attempt(
            module_id=module_id,
            user_id=user_id,
            payload=payload,
        )
    except ValueError as exc:
        _raise_service_error(exc)
