import os
import asyncio
import time
import json as json_module
import hashlib
from typing import Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.nvidia import Nvidia
from agno.tools.tavily import TavilyTools
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class NewsAnalysis(BaseModel):
    """Modelo para el análisis de una noticia individual."""
    titulo: str = Field(..., description="Título de la noticia")
    resumen: str = Field(..., description="Resumen detallado de la noticia")
    analisis: str = Field(..., description="Análisis financiero basado en el perfil del usuario")
    impacto_personal: str = Field(..., description="Impacto personalizado según situación financiera")
    recomendacion: str = Field(..., description="Recomendación de acción concreta")
    nivel_urgencia: str = Field(..., description="Nivel de urgencia: 'bajo', 'medio' o 'alto'")
    etiquetas: list[str] = Field(..., description="Lista de categorías/etiquetas relevantes (MÁXIMO 3)")
    fuente_url: Optional[str] = Field(None, description="URL de la fuente original")

class NewsAnalysisBatch(BaseModel):
    """Modelo para un lote de análisis de noticias."""
    analisis: list[NewsAnalysis] = Field(
        ...,
        description="Lista de análisis de noticias (máximo 3 por llamada)"
    )

    def __init__(self, **data):
        super().__init__(**data)
        if len(self.analisis) > 3:
            raise ValueError(
                f"Se permiten máximo 3 análisis por llamada, se recibieron: {len(self.analisis)}"
            )

class NewsAnalysisAgentOptimized:
    """Agente optimizado para análisis de noticias.

    Mejoras de rendimiento:
    - Paralelización de análisis IA (múltiples batches simultáneos)
    - Batch insert a BD (una query por entidad)
    - Caching de análisis duplicados
    - Connection pooling reutilizado
    - Logging detallado de tiempos
    """

    ALLOWED_CATEGORIES = [
        "Sueldo mínimo", "Combustible", "Alimentos", "Vivienda", "Transporte",
        "Servicios básicos", "Impuestos", "Créditos", "Ahorro", "Inversiones",
        "Pensiones", "Mercado accionario", "Criptomonedas", "Política económica",
    ]

    URGENCY_LEVELS = ["bajo", "medio", "alto"]

    def __init__(self, max_parallel_analyses: int = 3):
        """Inicializa el agente con control de paralelización.

        Args:
            max_parallel_analyses: Número máximo de análisis paralelos (default: 3)
        """
        self.session_id = "news_analysis_session_optimized"
        self.agent = self._create_agent()
        self.analysis_semaphore = asyncio.Semaphore(max_parallel_analyses)
        self._analysis_cache = {}
        self._timing_stats = {}

    def _get_nvidia_api_key(self) -> str:
        api_keys = [
            os.getenv("NVIDIA_API_KEY"),
            os.getenv("NVIDIA_API_KEY_FALLBACK"),
            os.getenv("NVIDIA_API_KEY_FALLBACK2"),
            os.getenv("NVIDIA_API_KEY_FALLBACK3"),
            os.getenv("NVIDIA_API_KEY_FALLBACK4"),
        ]
        for api_key in api_keys:
            if api_key and api_key.strip():
                return api_key
        raise ValueError("No se encontraron claves de API de Nvidia. Configura NVIDIA_API_KEY en tu .env")

    def _create_agent(self) -> Agent:
        """Crea el agente una sola vez (reutilización)."""
        api_key = self._get_nvidia_api_key()
        model = Nvidia(id="qwen/qwen3-coder-480b-a35b-instruct", api_key=api_key)

        instructions = f"""
        Eres un analista financiero experto para Chile. Analizarás noticias y
        las cruzarás con el perfil financiero del usuario.

        REGLAS CRÍTICAS:
        1. Formato: Responde SÓLO con JSON (sin texto antes ni después).
        2. Categorías: Única y exclusivamente estas (nada de inventar):
           {', '.join(self.ALLOWED_CATEGORIES)}

           INSTRUCCIÓN DE MAPEO (MUY IMPORTANTE):
           Toma la noticia y "mapea" (asigna) a la categoría más cercana:
           - Noticias de bencina, petróleo, autos, transporte → "Combustible"
           - Noticias de luz, agua, gas, internet, cuentas básicas → "Servicios básicos"
           - Noticias de arriendo, dividendos, hipotecas, bienes raíces → "Vivienda"
           - Noticias de comida, supermercado, inflación de alimentos → "Alimentos"
           - Noticias de AFP, jubilación, pensión → "Pensiones"
           - Noticias de sueldo, salario, salario mínimo → "Sueldo mínimo"
           - Noticias de impuestos, reforma tributaria → "Impuestos"
           - Noticias de crédito, deuda, tarjetas → "Créditos"
           - Noticias de bolsa, acciones, cripto → "Mercado accionario" o "Criptomonedas"
           - Noticias de política económica general → "Política económica"
           - Si NO calza en ninguna (ej: deportes, farándula) → usa "Servicios básicos" por defecto.

           MÁXIMO 3 etiquetas por noticia. SIEMPRE pon al menos 1.

        3. Niveles: 'bajo', 'medio', o 'alto' (justifica en 1 línea).
        4. Datos numéricos: Sólo si aparecen en la búsqueda. Si no, omítelos.
        5. Contexto: Relaciona SIEMPRE con el perfil del usuario:
           - Su ingreso mensual y gastos
           - Su capacidad de ahorro actual
           - Cómo lo afecta a ÉL/ELLA específicamente

        6. Recomendación: Debe ser una acción concreta, directa, real.
           Ej: "Revisar presupuesto mensual", "Considerar transporte público",
               "No impacta finanzas personales", etc.

        No alucines. Sé pragmático y útil.
        """

        agent = Agent(
            name="NewsAnalysisAgent",
            tools=[TavilyTools()],
            model=model,
            instructions=instructions,
            description="Analiza noticias RSS con perfil financiero (OPTIMIZADO)",
            session_id=self.session_id,
            markdown=True,
        )
        return agent

    def _track_timing(self, operation: str, elapsed: float):
        """Registra tiempos para debug."""
        if operation not in self._timing_stats:
            self._timing_stats[operation] = {"count": 0, "total": 0, "max": 0}
        self._timing_stats[operation]["count"] += 1
        self._timing_stats[operation]["total"] += elapsed
        self._timing_stats[operation]["max"] = max(self._timing_stats[operation]["max"], elapsed)

    def _get_analysis_cache_key(self, source_url: str, user_id: str) -> str:
        """Genera key para cache de análisis."""
        combined = f"{source_url}:{user_id}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _categorize_news(self, news: dict) -> str:
        """Categoriza automáticamente una noticia por su contenido."""
        texto = (news.get("title", "") + " " + news.get("summary", "")).lower()

        mapeo = {
            "Combustible": ["bencina", "gasolina", "combustible", "petróleo", "diésel", "gas", "auto", "vehículo", "camión", "transporte"],
            "Vivienda": ["arriendo", "renta", "alquiler", "departamento", "casa", "vivienda", "hipoteca", "dividendo", "inmobiliar", "propiedad"],
            "Alimentos": ["alimento", "supermercado", "precio", "inflación", "carne", "pan", "comida", "mercado", "verdura", "frutas"],
            "Servicios básicos": ["luz", "agua", "internet", "electricidad", "calefacción", "gas domiciliario", "basura", "alcantarilla"],
            "Impuestos": ["impuesto", "tributario", "sii", "renta", "iva", "declaración", "reforma tributaria"],
            "Créditos": ["crédito", "deuda", "tarjeta", "banco", "préstamo", "financiamiento", "cobranza"],
            "Ahorro": ["ahorro", "inversión", "fondo", "depósito", "plazo fijo", "rendimiento"],
            "Sueldo mínimo": ["sueldo", "salario", "ingreso", "trabajo", "empleo", "sindicato", "huelga", "negociación"],
            "Transporte": ["transporte", "bus", "metro", "tren", "movilidad", "pasaje", "fono"],
            "Pensiones": ["pensión", "jubilación", "afp", "vejez", "jubilado", "retiro"],
            "Mercado accionario": ["bolsa", "acción", "índice", "mercado bursátil", "inversión"],
            "Criptomonedas": ["cripto", "bitcoin", "ethereum", "blockchain", "crypto"],
            "Política económica": ["política económica", "gobierno", "ministerio", "reforma", "proyecto de ley"],
        }

        for categoria, palabras in mapeo.items():
            if any(palabra in texto for palabra in palabras):
                return categoria
        return "Servicios básicos"

    def _build_user_context(self, user_profile: dict) -> str:
        """Construye contexto del perfil financiero."""
        monthly_income = float(user_profile.get("monthly_income", 0))
        monthly_expenses = float(user_profile.get("monthly_expenses", 0))
        monthly_balance = monthly_income - monthly_expenses
        savings_rate = (monthly_balance / monthly_income * 100) if monthly_income > 0 else 0
        can_save = monthly_balance > 0
        debt_level = "alto" if monthly_expenses > monthly_income * 0.7 else "medio" if monthly_expenses > monthly_income * 0.5 else "bajo"
        financial_stability = "estable" if can_save and debt_level == "bajo" else "moderado" if can_save else "inestable"

        income_type = "No especificado"
        if user_profile.get("income_type_rel") and user_profile["income_type_rel"].get("name"):
            income_type = user_profile["income_type_rel"]["name"]

        topics = user_profile.get("topics", [])

        return f"""
        PERFIL FINANCIERO DEL USUARIO:
        - Ingreso mensual: ${monthly_income:,.0f} CLP
        - Gastos mensuales: ${monthly_expenses:,.0f} CLP
        - Saldo mensual: ${monthly_balance:,.0f} CLP
        - Tasa de ahorro: {savings_rate:.1f}%
        - Tipo de contrato: {income_type}
        - Endeudamiento: {debt_level}
        - Estabilidad: {financial_stability}
        - Topics: {topics}
        """

    async def _analyze_batch_with_timeout(
        self,
        batch_news: list[dict],
        user_context: str,
        batch_idx: int
    ) -> Optional[list[dict]]:
        """Analiza un batch con semáforo para limitar paralelización."""
        async with self.analysis_semaphore:
            start = time.perf_counter()
            try:
                num_noticias = len(batch_news)

                prompt_sections = []
                for i, news in enumerate(batch_news, 1):
                    contenido = news.get("content_text", "") or news.get("summary", "Sin contenido detallado")
                    if len(contenido) > 800:
                        contenido = contenido[:800] + "..."

                    prompt_sections.append(f"""
                NOTICIA {i}:
                Título: {news.get('title', 'Sin Título')}
                Fuente: {news.get('source_url', 'Desconocida')}
                Contenido: {contenido}
                """)

                prompt_final = f"""
                {user_context}

                Analiza estas {num_noticias} noticias. Responde ÚNICAMENTE en JSON.

                FORMATO OBLIGATORIO:
                {{
                  "analisis": [
""" + ",\n".join([f"""                    {{
                      "titulo": "...",
                      "resumen": "...",
                      "analisis": "...",
                      "impacto_personal": "...",
                      "recomendacion": "...",
                      "nivel_urgencia": "bajo|medio|alto",
                      "etiquetas": ["Categoria1", "Categoria2"],
                      "fuente_url": "..."
                    }}""" for _ in range(num_noticias)]) + """
                  ]
                }}

                {chr(10).join(prompt_sections)}
                """

                response = self.agent.run(prompt_final)

                if response.content is None:
                    raise ValueError("Modelo no devolvió contenido")

                if isinstance(response.content, str):
                    raw_content = response.content.strip()
                    if raw_content.startswith("```json"):
                        raw_content = raw_content.replace("```json", "").replace("```", "").strip()
                    content_dict = json_module.loads(raw_content)
                else:
                    content_dict = response.content.model_dump()

                elapsed = time.perf_counter() - start
                self._track_timing(f"batch_analysis", elapsed)
                logger.info(f" Batch {batch_idx} analizado en {elapsed:.2f}s")

                return content_dict.get("analisis", [])

            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(f" Error en batch {batch_idx}: {str(e)}")
                return None

    async def analyze_and_save_news(
        self,
        news_items: list[dict],
        user_profile: dict,
        db_session
    ) -> list[dict]:
        """Analiza noticias CON PARALELIZACIÓN y batch insert a BD."""
        from app.modules.news.entities import News, NewsTag, NewsTagMap, PersonalizedAnalysisNews
        from sqlalchemy import insert

        if not news_items:
            return []

        start_total = time.perf_counter()
        user_context = self._build_user_context(user_profile)
        user_id = user_profile.get("user_id")
        saved_results = []

        logger.info(f" Iniciando análisis paralelo de {len(news_items)} noticias...")

        batch_tasks = []
        for batch_idx in range(0, len(news_items), 3):
            batch_news = news_items[batch_idx:batch_idx + 3]
            task = self._analyze_batch_with_timeout(batch_news, user_context, batch_idx // 3 + 1)
            batch_tasks.append((batch_idx, batch_news, task))

        logger.info(f" Esperando {len(batch_tasks)} análisis...")
        batch_results = []
        for batch_idx, batch_news, task in batch_tasks:
            result = await task
            if result:
                batch_results.append((batch_news, result))

        logger.info(" Preparando bulk inserts...")

        news_to_insert = []
        tags_to_insert = []
        tag_maps_to_insert = []
        analyses_to_insert = []
        existing_news_urls = set()

        start = time.perf_counter()
        existing = db_session.query(News.source_url).all()
        existing_news_urls = {row[0] for row in existing}
        elapsed = time.perf_counter() - start
        self._track_timing("pre_check_news", elapsed)

        news_db_map = {}

        for batch_news, analyses in batch_results:
            for news_item, analysis_dict in zip(batch_news, analyses):
                try:
                    analysis = NewsAnalysis(
                        titulo=analysis_dict.get("titulo", "Sin título"),
                        resumen=analysis_dict.get("resumen", ""),
                        analisis=analysis_dict.get("analisis", ""),
                        impacto_personal=analysis_dict.get("impacto_personal", ""),
                        recomendacion=analysis_dict.get("recomendacion", ""),
                        nivel_urgencia=analysis_dict.get("nivel_urgencia", "bajo"),
                        etiquetas=analysis_dict.get("etiquetas", ["Servicios básicos"]),
                        fuente_url=analysis_dict.get("fuente_url", "")
                    )

                    clean_tags = [c for c in analysis.etiquetas if c in self.ALLOWED_CATEGORIES]
                    if not clean_tags:
                        clean_tags = ["Servicios básicos"]
                    seen = set()
                    unique_tags = [t for t in clean_tags if not (t in seen or seen.add(t))]
                    analysis.etiquetas = unique_tags[:3]

                    if analysis.nivel_urgencia not in self.URGENCY_LEVELS:
                        analysis.nivel_urgencia = "bajo"

                    url_original = analysis.fuente_url or news_item.get("source_url") or ""
                    url_truncada = url_original[:250] if len(url_original) > 250 else url_original

                    if url_truncada not in existing_news_urls:
                        news_data = {
                            "title": analysis.titulo,
                            "summary": analysis.resumen,
                            "content_text": news_item.get("content_text", analysis.resumen),
                            "source_url": url_truncada,
                            "published_at": news_item.get("published_at") or datetime.now(),
                            "impact_level": analysis.nivel_urgencia,
                            "affects": analysis.impacto_personal[:100] if analysis.impacto_personal else None,
                            "target_audience": "Usuario personalizado"
                        }
                        news_to_insert.append(news_data)
                        news_db_map[url_truncada] = {"data": news_data, "tags": analysis.etiquetas}
                        existing_news_urls.add(url_truncada)
                    else:
                        news_db_map[url_truncada] = {"exists": True, "tags": analysis.etiquetas}

                    for etiqueta in analysis.etiquetas:
                        tags_to_insert.append({"name": etiqueta, "description": f"Noticias de {etiqueta}"})

                except Exception as e:
                    logger.warning(f"️  Error procesando análisis: {str(e)}")
                    continue

        logger.info(" Ejecutando bulk inserts...")

        if news_to_insert:
            start = time.perf_counter()
            result = db_session.execute(insert(News), news_to_insert)
            db_session.flush()
            elapsed = time.perf_counter() - start
            self._track_timing("bulk_insert_news", elapsed)
            logger.info(f"    {len(news_to_insert)} noticias insertadas en {elapsed:.2f}s")

        start = time.perf_counter()
        all_news = db_session.query(News.news_id, News.source_url).all()
        news_url_to_id = {url: nid for nid, url in all_news}
        
        # Also fetch existing tag_maps to avoid duplicates
        existing_tag_maps = db_session.query(NewsTagMap.news_id, NewsTagMap.tag_id).all()
        existing_pairs_in_db = {(nm[0], nm[1]) for nm in existing_tag_maps}
        
        elapsed = time.perf_counter() - start
        self._track_timing("fetch_news_ids", elapsed)

        if tags_to_insert:
            unique_tags = list({t["name"]: t for t in tags_to_insert}.values())

            start = time.perf_counter()
            existing_tags = db_session.query(NewsTag.name, NewsTag.tag_id).all()
            existing_tag_map = {name: tid for name, tid in existing_tags}

            tags_to_create = [t for t in unique_tags if t["name"] not in existing_tag_map]

            if tags_to_create:
                result = db_session.execute(insert(NewsTag), tags_to_create)
                db_session.flush()

            elapsed = time.perf_counter() - start
            self._track_timing("bulk_insert_tags", elapsed)
            logger.info(f"    Tags insertados/verificados en {elapsed:.2f}s")

        start = time.perf_counter()
        tag_maps_bulk = []
        seen_pairs = set()  # Track (news_id, tag_id) pairs

        for url_truncada, info in news_db_map.items():
            if url_truncada not in news_url_to_id:
                continue
            
            news_id = news_url_to_id[url_truncada]
            
            for tag_name in info.get("tags", []):
                tag_map = db_session.query(NewsTag.tag_id).filter(NewsTag.name == tag_name).first()
                if tag_map:
                    tag_id = tag_map[0]
                    pair = (news_id, tag_id)
                    
                    # Skip if pair already seen this batch OR already exists in DB
                    if pair not in seen_pairs and pair not in existing_pairs_in_db:
                        seen_pairs.add(pair)
                        tag_maps_bulk.append({
                            "news_id": news_id,
                            "tag_id": tag_id
                        })

        if tag_maps_bulk:
            db_session.execute(insert(NewsTagMap), tag_maps_bulk)
            db_session.flush()
            logger.info(f"    {len(tag_maps_bulk)} tag_maps insertados")

        elapsed = time.perf_counter() - start
        self._track_timing("bulk_insert_tag_maps", elapsed)

        start = time.perf_counter()
        analyses_bulk = []
        for batch_news, analyses in batch_results:
            for news_item, analysis_dict in zip(batch_news, analyses):
                url_truncada = (analysis_dict.get("fuente_url") or news_item.get("source_url") or "")[:250]

                if url_truncada in news_url_to_id:
                    news_id = news_url_to_id[url_truncada]
                    analysis_text = json_module.dumps({
                        "analisis": analysis_dict.get("analisis", ""),
                        "impacto_personal": analysis_dict.get("impacto_personal", ""),
                        "recomendacion": analysis_dict.get("recomendacion", ""),
                        "nivel_urgencia": analysis_dict.get("nivel_urgencia", "bajo"),
                        "etiquetas": analysis_dict.get("etiquetas", [])
                    })

                    analyses_bulk.append({
                        "news_id": news_id,
                        "user_id": user_id,
                        "analysis_text": analysis_text,
                        "generated_at": datetime.now()
                    })

        if analyses_bulk:
            db_session.execute(insert(PersonalizedAnalysisNews), analyses_bulk)
            db_session.flush()

        elapsed = time.perf_counter() - start
        self._track_timing("bulk_insert_analyses", elapsed)

        start = time.perf_counter()
        db_session.commit()
        elapsed = time.perf_counter() - start
        self._track_timing("final_commit", elapsed)

        for batch_news, analyses in batch_results:
            for analysis_dict in analyses:
                saved_results.append({
                    "news_id": "pending",
                    "titulo": analysis_dict.get("titulo", ""),
                    "resumen": analysis_dict.get("resumen", ""),
                    "analisis": analysis_dict.get("analisis", ""),
                    "impacto_personal": analysis_dict.get("impacto_personal", ""),
                    "recomendacion": analysis_dict.get("recomendacion", ""),
                    "nivel_urgencia": analysis_dict.get("nivel_urgencia", "bajo"),
                    "etiquetas": analysis_dict.get("etiquetas", []),
                    "fuente_url": analysis_dict.get("fuente_url", "")
                })

        elapsed_total = time.perf_counter() - start_total
        logger.info(f"\n{'='*80}")
        logger.info(f" ANÁLISIS COMPLETADO EN {elapsed_total:.2f} SEGUNDOS")
        logger.info(f"{'='*80}")
        self._print_timing_report()

        return saved_results

    def _print_timing_report(self):
        """Imprime reporte de tiempos para debugging."""
        logger.info("\n️  TIMING REPORT:")
        for operation, stats in sorted(self._timing_stats.items(), key=lambda x: x[1]["total"], reverse=True):
            avg = stats["total"] / stats["count"]
            logger.info(f"   {operation:30} | Total: {stats['total']:7.2f}s | Count: {stats['count']:3} | Max: {stats['max']:.2f}s | Avg: {avg:.2f}s")

    def _select_and_prioritize_news(
        self,
        all_news: list[dict],
        user_categories: list[str],
        target_count: int = 10
    ) -> list[dict]:
        """Selecciona y prioriza noticias."""
        categorized = []
        for news in all_news:
            cat = self._categorize_news(news)
            categorized.append((news, cat))

        prioritarias = []
        expansion = []

        for news, cat in categorized:
            if cat in user_categories or any(uc in cat or cat in uc for uc in user_categories):
                prioritarias.append(news)
            else:
                expansion.append(news)

        return (prioritarias + expansion)[:target_count]

    async def get_latest_news_from_endpoint(self, limit: int = 15) -> list[dict]:
        """Obtiene noticias del endpoint interno /v1/news/latest_news.

        Args:
            limit: Número máximo de noticias a retornar

        Returns:
            Lista de noticias con estructura {title, summary, source_url, published_at, etc}
        """
        import httpx
        import os

        endpoint_url = os.getenv("NEWS_ENDPOINT_URL", "http://localhost:8000/v1/news/latest_news")
        timeout_secs = int(os.getenv("NEWS_REQUEST_TIMEOUT", "30"))

        try:
            async with httpx.AsyncClient(timeout=timeout_secs) as client:
                response = await client.get(endpoint_url)
                response.raise_for_status()
                data = response.json()

                news_items = data if isinstance(data, list) else data.get("analyses", [])

                formatted = []
                for item in news_items:
                    formatted.append({
                        "title": item.get("title") or item.get("titulo", "Sin título"),
                        "summary": item.get("summary") or item.get("resumen", ""),
                        "content_text": item.get("content_text", ""),
                        "source_url": item.get("source_url") or item.get("fuente_url", ""),
                        "published_at": item.get("published_at"),
                        "link": item.get("source_url") or item.get("fuente_url", ""),
                    })

                logger.info(f" Obtenidas {len(formatted)} noticias del endpoint interno")
                return formatted[:limit]

        except Exception as e:
            logger.warning(f"️  Error obteniendo noticias de endpoint: {str(e)}")
            return []

    async def search_chilean_news(self, user_categories: list[str], keywords: str = "") -> list[dict]:
        """Busca noticias en dominios .cl vía agent.

        Args:
            user_categories: Categorías de interés del usuario
            keywords: Palabras clave opcionales para búsqueda

        Returns:
            Lista de noticias de dominios chilenos con estructura estándar
        """
        try:
            import os
            import re

            tavily_key = os.getenv("TAVILY_API_KEY")
            if not tavily_key:
                logger.warning("️  TAVILY_API_KEY no configurada, skipping Chilean search")
                return []

            search_terms = list(set(user_categories[:3]))
            if keywords:
                search_terms.insert(0, keywords)

            search_query = " OR ".join(search_terms) + " site:*.cl economics news"

            logger.info(f" Buscando noticias chilenas: {search_query}")

            response = self.agent.run(f"Search for: {search_query}. Return only the search results as a structured list.")

            if not response or not response.messages:
                logger.info("No results from Chilean search")
                return []

            formatted = []
            try:
                response_text = str(response.messages[-1].content if response.messages else "")
                urls = re.findall(r'https?://[^\s"<>\']+', response_text)

                for url in urls[:5]:
                    if ".cl" in url:
                        formatted.append({
                            "title": url.split("/")[-1][:50],
                            "summary": f"Noticia desde {url}",
                            "content_text": f"Fuente: {url}",
                            "source_url": url,
                            "published_at": datetime.now(),
                            "link": url,
                        })
            except Exception as parse_error:
                logger.warning(f"Could not parse search results: {parse_error}")

            logger.info(f" Encontradas {len(formatted)} noticias chilenas")
            return formatted

        except Exception as e:
            logger.error(f" Error en búsqueda chilena: {str(e)}")
            return []

    async def get_latest_rss_news(self, limit: int = 10) -> list[dict]:
        """Obtiene noticias RSS (reutiliza del original)."""
        from app.external_apis.rss.rss_client import fetch_feed
        from app.external_apis.rss.rss_sources import FEEDS
        from app.external_apis.rss.rss_mapper import map_entry
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [fetch_feed(client, url) for url in FEEDS]
            feeds = await asyncio.gather(*tasks, return_exceptions=True)

        news = []
        cutoff = datetime.now().timestamp() - (30 * 24 * 3600)

        for feed in feeds:
            if isinstance(feed, BaseException):
                continue

            feed_meta = getattr(feed, "feed", {})
            entries = getattr(feed, "entries", [])
            source = (
                feed_meta.get("title", "desconocida")
                if hasattr(feed_meta, "get")
                else "desconocida"
            )

            for entry in entries:
                mapped = map_entry(entry, source)
                pub_time = mapped.get("published") or 0

                if isinstance(pub_time, datetime):
                    pub_time = pub_time.timestamp()
                elif pub_time is None:
                    pub_time = 0

                try:
                    if pub_time == 0 or float(pub_time) > cutoff:
                        if not any(n.get("link") == mapped.get("link") for n in news):
                            news.append(mapped)
                except (ValueError, TypeError):
                    if not any(n.get("link") == mapped.get("link") for n in news):
                        news.append(mapped)

        news.sort(key=lambda x: x.get("published") or 0, reverse=True)
        return news[:limit]

    async def get_all_analyzed_news(self, user_id: str, db_session) -> list[dict]:
        """Obtiene todas las noticias analizadas del usuario."""
        from app.modules.news.entities import PersonalizedAnalysisNews
        from sqlalchemy.orm import joinedload

        results = db_session.query(PersonalizedAnalysisNews).filter(
            PersonalizedAnalysisNews.user_id == user_id
        ).options(
            joinedload(PersonalizedAnalysisNews.news)
        ).order_by(PersonalizedAnalysisNews.generated_at.desc()).all()

        output = []
        for pa in results:
            news_data = {
                "news_id": str(pa.news.news_id) if pa.news else None,
                "titulo": pa.news.title if pa.news else "Noticia eliminada",
                "summary": pa.news.summary if pa.news else "",
                "source_url": pa.news.source_url if pa.news else None,
                "published_at": pa.news.published_at.isoformat() if pa.news and pa.news.published_at else None,
            }

            try:
                analysis_data = json_module.loads(pa.analysis_text) if isinstance(pa.analysis_text, str) else pa.analysis_text
            except:
                analysis_data = {"analisis": "Error parseando análisis", "etiquetas": []}

            output.append({
                **news_data,
                "analisis": analysis_data.get("analisis", ""),
                "impacto_personal": analysis_data.get("impacto_personal", ""),
                "recomendacion": analysis_data.get("recomendacion", ""),
                "nivel_urgencia": analysis_data.get("nivel_urgencia", ""),
                "etiquetas": analysis_data.get("etiquetas", []),
                "analizado_el": pa.generated_at.isoformat() if pa.generated_at else None
            })

        return output

news_analysis_agent = NewsAnalysisAgentOptimized(max_parallel_analyses=3)
