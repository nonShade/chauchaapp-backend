"""
News controller — HTTP endpoint layer.

Endpoints simplificados:
- POST /v1/news/analyze-full : TODO (RSS + Perfil + DB) en uno solo
- GET  /v1/news/analyzed     : Todas las noticias YA analizadas del usuario
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.modules.news.dto import (
    TopicResponseDTO,
    NewsFullAnalysisResponseDTO,
    AnalyzedNewsListResponseDTO,
)
from app.modules.news.repository import NewsRepository
from app.modules.news.service import NewsService
from app.shared.database import get_db
from app.modules.users.entities import User
from app.shared.security.auth_middleware import get_current_user

router = APIRouter(prefix="/v1/news", tags=["News"])


def _get_news_service(db: Session = Depends(get_db)) -> NewsService:
    """Dependency to build news service with its database repository."""
    repository = NewsRepository(db)
    return NewsService(repository)


def _build_user_profile(user: User) -> dict:
    """Construye el perfil completo del usuario para análisis."""
    income_type_name = None
    if user.income_type_rel:
        income_type_name = user.income_type_rel.name

    # Obtener nombres de categorías (topics) del usuario desde user_interests
    # IMPORTANTE: Devolvemos NOMBRES de categorías, no IDs
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
    description="Devuelve el catálogo de tópicos de noticias disponibles.",
)
def get_news_topics(service: NewsService = Depends(_get_news_service)):
    """Retrieve all available news tags (topics)."""
    topics = service.get_news_topics()
    return [
        TopicResponseDTO(
            id=t.tag_id,
            name=t.name,
            description=t.description or ""
        )
        for t in topics
    ]


@router.post(
    "/analyze-full",
    response_model=NewsFullAnalysisResponseDTO,
    summary="Analizar noticias RSS con perfil financiero y guardar en DB",
    description="""
    Realiza lo siguiente:
    
    1. Obtiene las últimas noticias desde endpoint interno /v1/news/latest_news
    2. Si insuficientes matches con categorías del usuario, busca en dominios .cl
    3. Obtiene el perfil financiero COMPLETO del usuario:
       - Ingresos, gastos, saldo, tasa de ahorro
       - Tipo de ingreso, nivel de deuda, estabilidad
       - Topics y top categories de interés
    4. Usa Tavily para búsqueda web de datos económicos actualizados
    5. Analiza con IA (modelo Nvidia) el impacto personalizado
    6. Guarda TODO en base de datos:
       - Noticias
       - Tags/categorías
       - Análisis personalizado vinculado al usuario
    7. Retorna las noticias analizadas
    
    """,
    responses={
        401: {"description": "No autorizado - se requiere JWT"},
        404: {"description": "Usuario no encontrado"},
        500: {"description": "Error en análisis/guardado"},
    },
)
async def analyze_full(
    current_user: User = Depends(get_current_user),
    service: NewsService = Depends(_get_news_service),
    db: Session = Depends(get_db),
):
    """
    Endpoint principal: Endpoint → Perfil → [Tavily] → IA → DB → Retorno.
    
    Flujo:
    1. Obtiene noticias del endpoint interno /v1/news/latest_news (OBLIGATORIO)
    2. Filtra por categorías del usuario
    3. Si < 5 matches, ejecuta búsqueda chilena (TavilyTools, dominios .cl)
    4. Analiza batch combinado
    5. Guarda en DB
    """
    import logging
    import os
    
    logger = logging.getLogger(__name__)
    threshold_for_search = int(os.getenv("MIN_NEWS_FOR_SEARCH", "5"))
    
    try:
        from sqlalchemy.orm import joinedload
        
        user = db.query(User).options(
            joinedload(User.income_type_rel),
            joinedload(User.user_interests)
        ).filter(User.user_id == current_user.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        # Construir perfil completo
        user_profile = _build_user_profile(user)

        from app.agent.news_agent import news_analysis_agent

        all_news_from_endpoint = await news_analysis_agent.get_latest_news_from_endpoint(limit=15)
        
        if not all_news_from_endpoint:
            all_news_from_endpoint = []

        user_categories = user_profile.get("topics", [])
        prioritized_news = news_analysis_agent._select_and_prioritize_news(
            all_news=all_news_from_endpoint,
            user_categories=user_categories,
            target_count=15
        )
        
        matched_count = 0
        for news in prioritized_news:
            cat = news_analysis_agent._categorize_news(news)
            if cat in user_categories or any(uc in cat or cat in uc for uc in user_categories):
                matched_count += 1
        
        chilean_news = []
        if matched_count < threshold_for_search:
            search_keywords = " ".join(user_categories[:3]) if user_categories else ""
            chilean_news = await news_analysis_agent.search_chilean_news(
                user_categories=user_categories,
                keywords=search_keywords
            )
            if chilean_news:
                logger.info(f"Encontradas {len(chilean_news)} noticias chilenas")
            else:
                logger.warning("No se encontraron noticias chilenas")
        
        combined_news = prioritized_news + chilean_news
        
        final_news = news_analysis_agent._select_and_prioritize_news(
            all_news=combined_news,
            user_categories=user_categories,
            target_count=10
        )
        
        if not final_news:
            return {
                "success": True,
                "message": "No hay noticias para analizar",
                "analyzed_count": 0,
                "analyses": [],
                "user_profile_summary": {
                    "monthly_income": user_profile["monthly_income"],
                    "monthly_expenses": user_profile["monthly_expenses"],
                    "savings_rate": round(
                        (user_profile["monthly_income"] - user_profile["monthly_expenses"]) 
                        / user_profile["monthly_income"] * 100, 1
                    ) if user_profile["monthly_income"] > 0 else 0,
                    "income_type": user_profile["income_type_rel"].get("name", "N/A"),
                }
            }

        analyses = await news_analysis_agent.analyze_and_save_news(
            news_items=final_news,
            user_profile=user_profile,
            db_session=db,
        )

        return {
            "success": True,
            "analyzed_count": len(analyses),
            "user_profile_summary": {
                "monthly_income": user_profile["monthly_income"],
                "monthly_expenses": user_profile["monthly_expenses"],
                "savings_rate": round(
                    (user_profile["monthly_income"] - user_profile["monthly_expenses"]) 
                    / user_profile["monthly_income"] * 100, 1
                ) if user_profile["monthly_income"] > 0 else 0,
                "income_type": user_profile["income_type_rel"].get("name", "N/A"),
            },
            "analyses": analyses,
        }

    except ValueError as e:
        logger.error(f"ValueError: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error en análisis completo: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en análisis completo: {str(e)}"
        )


@router.get(
    "/analyzed",
    response_model=AnalyzedNewsListResponseDTO,
    summary="Obtener TODAS las noticias YA analizadas del usuario",
    description="""
    Retorna todas las noticias que han sido previamente analizadas 
    y guardadas en base de datos para este usuario.
    
    Cada item incluye:
    - Datos de la noticia (título, fuente, fecha)
    - Análisis financiero completo
    - Impacto personalizado
    - Recomendación y nivel de urgencia
    - Fecha del análisis
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
    """
    Obtiene todas las noticias YA analizadas de la base de datos.
    """
    try:
        # Validar usuario
        user = db.query(User).filter(User.user_id == current_user.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        # Importar agente
        from app.agent.news_agent import news_analysis_agent

        analyzed = await news_analysis_agent.get_all_analyzed_news(
            user_id=str(user.user_id),
            db_session=db,
        )

        return {
            "success": True,
            "total_count": len(analyzed),
            "analyses": analyzed,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo noticias analizadas: {str(e)}"
        )


@router.get(
    "/latest_news",
    summary="Obtener últimas noticias (RSS)",
    description="Devuelve las últimas noticias de RSS feeds sin análisis.",
)
async def news(service: NewsService = Depends(_get_news_service)):
    return await service.get_latest_news()
