"""
News controller — HTTP endpoint layer.

Endpoints:
- GET  /v1/news/topics                       : Catálogo de tópicos
- POST /v1/news/analyze-full                 : Inicia análisis async, retorna task_id
- GET  /v1/news/analyze/status/{task_id}     : Estado del análisis en background
- GET  /v1/news/analyzed                     : Noticias YA analizadas del usuario
- GET  /v1/news/latest_news                  : RSS feeds sin analizar
"""

import json
import logging
import os
import uuid
import asyncio
import threading
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.modules.news.dto import (
    TopicResponseDTO,
    NewsFullAnalysisResponseDTO,
    AnalyzedNewsListResponseDTO,
)
from app.modules.news.repository import NewsRepository
from app.modules.news.service import NewsService
from app.shared.background import task_manager
from app.shared.background_dto import TaskStatusResponse, TaskSubmitResponse
from app.shared.database import SessionLocal, get_db
from app.modules.users.entities import User
from app.shared.security.auth_middleware import get_current_user

router = APIRouter(prefix="/v1/news", tags=["News"])

logger = logging.getLogger(__name__)


def _get_news_service(db: Session = Depends(get_db)) -> NewsService:
    repository = NewsRepository(db)
    return NewsService(repository)


def _build_user_profile(user: User) -> dict:
    income_type_name = None
    if user.income_type_rel:
        income_type_name = user.income_type_rel.name
    topics = []
    if hasattr(user, "user_interests") and user.user_interests:
        topics = [ui.tag.name for ui in user.user_interests if hasattr(ui, "tag") and ui.tag]
    return {
        "user_id": str(user.user_id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "monthly_income": float(user.monthly_income),
        "monthly_expenses": float(user.monthly_expenses),
        "income_type_id": str(user.income_type_id) if user.income_type_id else None,
        "income_type_rel": {"name": income_type_name} if income_type_name else {},
        "birth_date": user.birth_date.isoformat() if user.birth_date else None,
        "topics": topics,
    }


@router.get(
    "/topics",
    response_model=list[TopicResponseDTO],
    summary="Obtener tópicos de noticias",
)
def get_news_topics(service: NewsService = Depends(_get_news_service)):
    topics = service.get_news_topics()
    return [
        TopicResponseDTO(id=t.tag_id, name=t.name, description=t.description or "")
        for t in topics
    ]


# ---------------------------------------------------------------------------
# Background async analysis
# ---------------------------------------------------------------------------


async def _run_news_analysis(
    user_profile: dict,
    threshold_for_search: int,
    db_session,
) -> dict:
    """Core news analysis logic — runs inside bg thread's own event loop."""
    from app.agent.news_agent import news_analysis_agent

    all_news_from_endpoint = (
        await news_analysis_agent.get_latest_rss_news(limit=15)
    ) or []

    user_categories = user_profile.get("topics", [])
    prioritized_news = news_analysis_agent._select_and_prioritize_news(
        all_news=all_news_from_endpoint,
        user_categories=user_categories,
        target_count=15,
    )

    matched_count = 0
    for news in prioritized_news:
        cat = news_analysis_agent._categorize_news(news)
        if cat in user_categories or any(
            uc in cat or cat in uc for uc in user_categories
        ):
            matched_count += 1

    chilean_news = []
    if matched_count < threshold_for_search:
        search_keywords = " ".join(user_categories[:3]) if user_categories else ""
        chilean_news = (
            await news_analysis_agent.search_chilean_news(
                user_categories=user_categories,
                keywords=search_keywords,
            )
        ) or []
        if chilean_news:
            logger.info("Encontradas %d noticias chilenas", len(chilean_news))
        else:
            logger.warning("No se encontraron noticias chilenas")

    combined_news = prioritized_news + chilean_news
    final_news = news_analysis_agent._select_and_prioritize_news(
        all_news=combined_news,
        user_categories=user_categories,
        target_count=10,
    )

    summary = {
        "monthly_income": user_profile["monthly_income"],
        "monthly_expenses": user_profile["monthly_expenses"],
        "savings_rate": (
            round(
                (user_profile["monthly_income"] - user_profile["monthly_expenses"])
                / user_profile["monthly_income"] * 100,
                1,
            )
            if user_profile["monthly_income"] > 0
            else 0
        ),
        "income_type": user_profile.get("income_type_rel", {}).get("name", "N/A"),
    }

    if not final_news:
        return {
            "success": True,
            "message": "No hay noticias para analizar",
            "analyzed_count": 0,
            "analyses": [],
            "user_profile_summary": summary,
        }

    analyses = await news_analysis_agent.analyze_and_save_news(
        news_items=final_news,
        user_profile=user_profile,
        db_session=db_session,
    )
    return {
        "success": True,
        "analyzed_count": len(analyses),
        "user_profile_summary": summary,
        "analyses": analyses,
    }


def _background_news_worker(task_id: str, user_profile: dict, threshold: int) -> None:
    """Runs news analysis in a dedicated thread with its own DB session and event loop."""
    from app.shared.database import SessionLocal

    db = SessionLocal()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _run_news_analysis(user_profile, threshold, db)
            )
        finally:
            loop.close()
        db.commit()
        task_manager.update_status(task_id, "completed", result=result)
    except Exception as e:
        db.rollback()
        logger.exception("Error en background news analysis")
        task_manager.update_status(task_id, "failed", error=str(e))
    finally:
        db.close()


@router.post(
    "/analyze-full",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Iniciar análisis de noticias en background",
    description="""
    Encola el análisis completo de noticias y retorna inmediatamente un task_id.
    
    El análisis incluye:
    1. Obtener RSS feeds
    2. Búsqueda en dominios .cl si es necesario
    3. Análisis con IA (Nvidia) según perfil financiero
    4. Guardado en base de datos
    
    Usa GET /v1/news/analyze/status/{task_id} para consultar el resultado.
    """,
    responses={
        202: {"description": "Análisis encolado"},
        401: {"description": "No autorizado"},
        404: {"description": "Usuario no encontrado"},
    },
)
async def analyze_full_background(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .options(joinedload(User.income_type_rel), joinedload(User.user_interests))
        .filter(User.user_id == current_user.user_id)
        .first()
    )
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    user_profile = _build_user_profile(user)
    threshold = int(os.getenv("MIN_NEWS_FOR_SEARCH", "5"))
    task_id = task_manager.create_task("news_analyze", str(user.user_id))

    thread = threading.Thread(
        target=_background_news_worker,
        args=(task_id, user_profile, threshold),
        daemon=True,
    )
    thread.start()

    return TaskSubmitResponse(
        task_id=task_id,
        status="pending",
        message="Análisis de noticias iniciado. Consulta GET /v1/news/analyze/status/{task_id} para resultados.",
    )


@router.get(
    "/analyze/status/{task_id}",
    response_model=TaskStatusResponse,
    summary="Consultar estado del análisis de noticias",
    description="Retorna el estado actual y resultado (si completó) de una tarea de análisis.",
    responses={404: {"description": "Task ID no encontrado"}},
)
def get_analyze_status(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Task no encontrada")
    return TaskStatusResponse(**task)


@router.get(
    "/analyzed",
    response_model=AnalyzedNewsListResponseDTO,
    summary="Obtener TODAS las noticias YA analizadas del usuario",
    description="""
    Retorna las noticias analizadas para este usuario.
    
    Si el usuario no tiene análisis personalizados aún (primera vez),
    retorna noticias por defecto precargadas en la base de datos.
    
    Cuando el análisis en background termine, las noticias reales
    aparecerán junto a las precargadas.
    """,
    responses={
        401: {"description": "No autorizado - se requiere JWT"},
        404: {"description": "Usuario no encontrado"},
    },
)
async def get_all_analyzed(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user = db.query(User).filter(User.user_id == current_user.user_id).first()
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

        user_id_str = str(user.user_id)

        from app.agent.news_agent import news_analysis_agent

        analyzed = await news_analysis_agent.get_all_analyzed_news(
            user_id=user_id_str, db_session=db,
        )

        # ── If user has no analyses yet, try seed news ─────────────────
        if not analyzed:
            from app.modules.news.entities import News, PersonalizedAnalysisNews

            seed_news = (
                db.query(News)
                .order_by(News.published_at.desc())
                .limit(5)
                .all()
            )

            for news in seed_news:
                analysis_record = PersonalizedAnalysisNews(
                    analysis_id=uuid.uuid4(),
                    news_id=news.news_id,
                    user_id=user.user_id,
                    analysis_text=json.dumps({
                        "analisis": f"Noticia precargada: {news.title}. Esta es información general. El análisis personalizado se generará en segundo plano.",
                        "impacto_personal": "Lee esta noticia para mantenerte informado. Pronto tendrás un análisis adaptado a tu perfil financiero.",
                        "recomendacion": "Mantente al día con las noticias económicas. Activa la generación de análisis desde la app para recibir recomendaciones personalizadas.",
                        "nivel_urgencia": "bajo",
                        "etiquetas": [],
                    }, ensure_ascii=False),
                    generated_at=datetime.utcnow(),
                )
                db.add(analysis_record)

            db.commit()

            analyzed = await news_analysis_agent.get_all_analyzed_news(
                user_id=user_id_str, db_session=db,
            )

        return {
            "success": True,
            "total_count": len(analyzed),
            "analyses": analyzed,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo noticias analizadas: {str(e)}",
        )


@router.get(
    "/latest_news",
    summary="Obtener últimas noticias (RSS)",
    description="Devuelve las últimas noticias de RSS feeds sin análisis.",
)
async def news(service: NewsService = Depends(_get_news_service)):
    return await service.get_latest_news()
