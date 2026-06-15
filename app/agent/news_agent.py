"""
News analysis agent.
"""

import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from openai import APIStatusError, AsyncOpenAI
from pydantic import BaseModel, Field

load_dotenv()

logger = logging.getLogger(__name__)


class NewsAnalysis(BaseModel):
    """Modelo para el análisis de una noticia individual."""

    titulo: str = Field(..., description="Título de la noticia")
    resumen: str = Field(..., description="Resumen detallado de la noticia (neutro)")
    analisis: str = Field(
        ...,
        description="Análisis financiero explicándole al usuario por qué esto le importa (en segunda persona, ej: 'Esta noticia te afecta porque...')",
    )
    impacto_personal: str = Field(
        ...,
        description="Impacto personalizado hablándole directamente al usuario (ej: 'Como tu ingreso es X, esto significa que...')",
    )
    recomendacion: str = Field(
        ...,
        description="Recomendación de acción concreta hablándole al usuario (ej: 'Te recomiendo que...')",
    )
    nivel_urgencia: str = Field(
        ..., description="Nivel de urgencia: 'bajo', 'medio' o 'alto'"
    )
    etiquetas: list[str] = Field(
        ..., description="Lista de categorías/etiquetas relevantes (MÁXIMO 3)"
    )
    fuente_url: Optional[str] = Field(None, description="URL de la fuente original")


class NewsAnalysisAgent:
    """Agente de análisis de noticias.

        Obtiene noticias REALES desde RSS feeds chilenos verificados,
        luego las analiza contra el perfil financiero del usuario.

    Usa Nvidia llama-3.3-nemotron-super-49b-v1 con 5 API keys
    de respaldo por si alguna tiene rate limit.

    Diferencias con la versión anterior:
    - NO usa Agno (llamada directa a API Nvidia con openai)
        - NO usa Tavily durante el análisis (solo como búsqueda opcional)
        - El modelo solo analiza el contenido que recibe, no inventa nada
        - Las URLs provienen exclusivamente de los RSS feeds reales
        - Fallback automático entre 3 API keys Gemini
    """

    ALLOWED_CATEGORIES = [
        "Sueldo mínimo",
        "Combustible",
        "Alimentos",
        "Vivienda",
        "Transporte",
        "Servicios básicos",
        "Impuestos",
        "Créditos",
        "Ahorro",
        "Inversiones",
        "Pensiones",
        "Mercado accionario",
        "Criptomonedas",
        "Política económica",
    ]
    URGENCY_LEVELS = ["bajo", "medio", "alto"]

    CATEGORY_KEYWORDS = {
        "Combustible": [
            "bencina",
            "gasolina",
            "combustible",
            "petróleo",
            "diésel",
            "gas",
            "auto",
            "vehículo",
            "camión",
            "transporte público",
            "taxi",
            "uber",
        ],
        "Vivienda": [
            "arriendo",
            "renta",
            "alquiler",
            "departamento",
            "casa",
            "vivienda",
            "hipoteca",
            "dividendo",
            "inmobiliar",
            "propiedad",
            "corredora",
        ],
        "Alimentos": [
            "alimento",
            "supermercado",
            "precio",
            "inflación",
            "carne",
            "pan",
            "comida",
            "verdura",
            "fruta",
            "canasta",
            "aceite",
            "leche",
        ],
        "Servicios básicos": [
            "luz",
            "agua",
            "internet",
            "electricidad",
            "calefacción",
            "gas domiciliario",
            "basura",
            "alcantarillado",
            "cuenta",
            "suministro",
        ],
        "Impuestos": [
            "impuesto",
            "tributario",
            "sii",
            "renta",
            "iva",
            "declaración",
            "reforma tributaria",
            "exención",
        ],
        "Créditos": [
            "crédito",
            "deuda",
            "tarjeta",
            "banco",
            "préstamo",
            "financiamiento",
            "cobranza",
            "tasa",
            "cmf",
            "morosidad",
        ],
        "Ahorro": [
            "ahorro",
            "inversión",
            "fondo",
            "depósito",
            "plazo fijo",
            "rendimiento",
            "interés",
            "cuenta",
        ],
        "Sueldo mínimo": [
            "sueldo",
            "salario",
            "ingreso",
            "trabajo",
            "empleo",
            "sindicato",
            "huelga",
            "negociación",
            "salario mínimo",
            "remuneración",
        ],
        "Transporte": [
            "transporte",
            "bus",
            "metro",
            "tren",
            "movilidad",
            "pasaje",
            "tarifa",
            "subsidio transporte",
        ],
        "Pensiones": [
            "pensión",
            "jubilación",
            "afp",
            "vejez",
            "jubilado",
            "retiro",
            "previsión",
            "ahorro previsional",
        ],
        "Mercado accionario": [
            "bolsa",
            "acción",
            "índice",
            "mercado bursátil",
            "ip",
            "valor",
        ],
        "Criptomonedas": [
            "cripto",
            "bitcoin",
            "ethereum",
            "blockchain",
            "crypto",
            "activo digital",
        ],
        "Política económica": [
            "política económica",
            "gobierno",
            "ministerio",
            "reforma",
            "proyecto de ley",
            "banco central",
            "hacienda",
            "economía",
        ],
    }

    NVIDIA_MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1"
    NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

    def __init__(self, max_parallel_analyses: int = 3):
        self.max_parallel = max_parallel_analyses
        self._clients: list[AsyncOpenAI] = []

    def _get_nvidia_api_keys(self) -> list[str]:
        keys = [
            os.getenv("NVIDIA_API_KEY"),
            os.getenv("NVIDIA_API_KEY_FALLBACK"),
            os.getenv("NVIDIA_API_KEY_FALLBACK2"),
            os.getenv("NVIDIA_API_KEY_FALLBACK3"),
            os.getenv("NVIDIA_API_KEY_FALLBACK4"),
        ]
        valid = [k.strip() for k in keys if k and k.strip()]
        if not valid:
            raise ValueError(
                "No se encontraron API keys de Nvidia. Configura NVIDIA_API_KEY en tu .env"
            )
        return valid

    @property
    def clients(self) -> list[AsyncOpenAI]:
        if not self._clients:
            self._clients = [
                AsyncOpenAI(base_url=self.NVIDIA_BASE_URL, api_key=k)
                for k in self._get_nvidia_api_keys()
            ]
        return self._clients

    def _categorize_news(self, news: dict) -> str:
        """Categoriza una noticia por su contenido (mapeo por keywords)."""
        texto = (news.get("title", "") + " " + news.get("summary", "")).lower()
        for categoria, palabras in self.CATEGORY_KEYWORDS.items():
            if any(p in texto for p in palabras):
                return categoria
        return "Servicios básicos"

    def _build_user_context(self, user_profile: dict) -> str:
        """Construye el contexto financiero del usuario para el prompt."""
        mi = float(user_profile.get("monthly_income", 0))
        me = float(user_profile.get("monthly_expenses", 0))
        mb = mi - me
        sr = (mb / mi * 100) if mi > 0 else 0
        dl = "alto" if me > mi * 0.7 else "medio" if me > mi * 0.5 else "bajo"
        fs = (
            "estable"
            if mb > 0 and dl == "bajo"
            else "moderado"
            if mb > 0
            else "inestable"
        )
        it = user_profile.get("income_type_rel", {}).get("name", "No especificado")
        topics = user_profile.get("topics", [])
        return (
            f"PERFIL FINANCIERO DEL USUARIO:\n"
            f"- Ingreso mensual: ${mi:,.0f} CLP\n"
            f"- Gastos mensuales: ${me:,.0f} CLP\n"
            f"- Saldo mensual: ${mb:,.0f} CLP\n"
            f"- Tasa de ahorro: {sr:.1f}%\n"
            f"- Tipo de contrato: {it}\n"
            f"- Endeudamiento: {dl}\n"
            f"- Estabilidad: {fs}\n"
            f"- Intereses: {topics}"
        )

    def _select_and_prioritize_news(
        self, all_news: list[dict], user_categories: list[str], target_count: int = 10
    ) -> list[dict]:
        """Selecciona y prioriza noticias según categorías del usuario."""
        categorized = [(n, self._categorize_news(n)) for n in all_news]
        prio = [n for n, c in categorized if c in user_categories]
        rest = [n for n, c in categorized if c not in user_categories]
        return (prio + rest)[:target_count]

    async def _resolve_google_news_url(self, url: str) -> str:
        """Resuelve URLs de Google News a la URL real del artículo."""
        if "news.google.com" not in url:
            return url
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
                r = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
                return str(r.url)
        except Exception:
            return url

    async def get_latest_rss_news(self, limit: int = 10) -> list[dict]:
        """Obtiene noticias directamente de los RSS feeds chilenos."""
        import httpx

        from app.external_apis.rss.rss_client import fetch_feed
        from app.external_apis.rss.rss_mapper import map_entry
        from app.external_apis.rss.rss_sources import FEEDS

        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [fetch_feed(client, url) for url in FEEDS]
            feeds = await asyncio.gather(*tasks, return_exceptions=True)

        news = []
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
                pub = mapped.get("published")
                pub_ts = pub.timestamp() if isinstance(pub, datetime) else 0
                cutoff = datetime.now().timestamp() - 30 * 86400
                if pub_ts == 0 or pub_ts > cutoff:
                    if not any(n.get("link") == mapped.get("link") for n in news):
                        news.append(mapped)

        news.sort(key=lambda x: x.get("published") or 0, reverse=True)

        result = []
        for n in news[:limit]:
            url = n.get("link", "")
            resolved = await self._resolve_google_news_url(url)
            summary = n.get("summary", "")
            result.append(
                {
                    "title": n.get("title", ""),
                    "summary": summary,
                    "content_text": summary,
                    "source_url": resolved,
                    "published_at": n.get("published"),
                    "link": resolved,
                }
            )
        return result

    async def get_latest_news_from_endpoint(self, limit: int = 15) -> list[dict]:
        """Obtiene noticias desde el endpoint interno /v1/news/latest_news."""
        import httpx

        endpoint = os.getenv(
            "NEWS_ENDPOINT_URL", "http://localhost:8000/v1/news/latest_news"
        )
        timeout_secs = int(os.getenv("NEWS_REQUEST_TIMEOUT", "30"))
        try:
            async with httpx.AsyncClient(timeout=timeout_secs) as c:
                resp = await c.get(endpoint)
                resp.raise_for_status()
                data = resp.json()
            items = data if isinstance(data, list) else data.get("analyses", [])
            formatted = []
            for item in items:
                url = (
                    item.get("source_url")
                    or item.get("fuente_url")
                    or item.get("link", "")
                )
                resolved = await self._resolve_google_news_url(url)
                summary = item.get("summary") or item.get("resumen", "")
                formatted.append(
                    {
                        "title": item.get("title") or item.get("titulo", "Sin título"),
                        "summary": summary,
                        "content_text": item.get("content_text", "") or summary,
                        "source_url": resolved,
                        "published_at": item.get("published_at"),
                        "link": resolved,
                    }
                )
            return formatted[:limit]
        except Exception as e:
            logger.warning(f"Error obteniendo noticias de endpoint: {e}")
            return []

    async def search_chilean_news(
        self, user_categories: list[str], keywords: str = ""
    ) -> list[dict]:
        """Busca noticias chilenas usando Tavily (solo como respaldo)."""
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            logger.warning("TAVILY_API_KEY no configurada, saltando búsqueda chilena")
            return []
        try:
            from tavily import TavilyClient

            terms = list(set(user_categories[:3]))
            if keywords:
                terms.insert(0, keywords)
            query = " OR ".join(terms) + " economia finanzas Chile"
            logger.info(f"Buscando noticias chilenas via Tavily: {query}")
            tc = TavilyClient(api_key=tavily_key)
            resp = tc.search(
                query=query,
                search_depth="advanced",
                max_results=5,
                include_raw_content=False,
            )
            results = []
            for r in resp.get("results", []):
                url = r.get("url", "")
                if url:
                    results.append(
                        {
                            "title": r.get("title", "").strip()
                            or url.split("/")[-1][:50],
                            "summary": (r.get("content", "") or "")[:300],
                            "content_text": r.get("content", "") or "",
                            "source_url": url,
                            "published_at": datetime.now(),
                            "link": url,
                        }
                    )
            logger.info(f"Tavily devolvió {len(results)} noticias chilenas")
            return results
        except Exception as e:
            logger.error(f"Error en búsqueda Tavily: {e}")
            return []

    def _parse_json(self, raw: str) -> Optional[dict]:
        """Extrae y parsea el JSON de la respuesta del modelo."""
        if not raw:
            return None
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        fb = cleaned.find("{")
        lb = cleaned.rfind("}")
        if fb != -1 and lb != -1:
            candidate = cleaned[fb : lb + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
            try:
                fixed = re.sub(r",\s*}", "}", candidate)
                fixed = re.sub(r",\s*]", "]", fixed)
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

        # JSON truncado por max_tokens: extraer objetos completos del array
        array_match = re.search(r'"analisis"\s*:\s*\[', cleaned)
        if array_match:
            items = []
            i = array_match.end()
            while i < len(cleaned):
                if cleaned[i] == "{":
                    depth = 0
                    in_string = False
                    escape = False
                    j = i
                    while j < len(cleaned):
                        c = cleaned[j]
                        if escape:
                            escape = False
                        elif c == "\\" and in_string:
                            escape = True
                        elif c == '"':
                            in_string = not in_string
                        elif not in_string:
                            if c == "{":
                                depth += 1
                            elif c == "}":
                                depth -= 1
                                if depth == 0:
                                    try:
                                        items.append(json.loads(cleaned[i : j + 1]))
                                    except json.JSONDecodeError:
                                        pass
                                    break
                        j += 1
                    i = j + 1
                else:
                    i += 1
            if items:
                logger.warning(f"JSON truncado: se recuperaron {len(items)} objeto(s) parciales")
                return {"analisis": items}

        return None

    async def _analyze_batch(
        self, batch: list[dict], user_context: str, batch_idx: int
    ) -> Optional[list[dict]]:
        """Analiza un lote de noticias llamando directamente a la API de Nvidia.

        CRÍTICO: El modelo recibe el contenido REAL de las noticias RSS
        y SOLO puede analizar ese contenido. No se le pide buscar nada.
        """
        sections = []
        for i, n in enumerate(batch, 1):
            content = n.get("content_text", "") or n.get(
                "summary", "Sin contenido disponible"
            )
            if len(content) > 1500:
                content = content[:1500] + "..."
            url = n.get("source_url") or n.get("link", "URL no disponible")
            sections.append(
                f"NOTICIA {i}:\n"
                f"Título: {n.get('title', 'Sin título')}\n"
                f"URL real: {url}\n"
                f"Contenido:\n{content}\n"
                f"---"
            )

        news_json_example = ",\n".join(
            [
                json.dumps(
                    {
                        "titulo": "ejemplo título",
                        "resumen": "resumen basado en el contenido entregado",
                        "analisis": "Esta noticia te afecta porque... (explicación en segunda persona)",
                        "impacto_personal": "Considerando tu situación financiera, esto significa que tú...",
                        "recomendacion": "Te recomiendo que hagas... (acción concreta)",
                        "nivel_urgencia": "bajo",
                        "etiquetas": ["Categoría1"],
                        "fuente_url": "https://ejemplo.com/noticia",
                    },
                    ensure_ascii=False,
                )
                for _ in range(len(batch))
            ]
        )

        prompt = (
            f"{user_context}\n\n"
            f"INSTRUCCIÓN: Eres un asesor financiero personal. Analiza CADA una de las {
                len(batch)
            } noticias "
            f"y HÁBLALE DIRECTAMENTE AL USUARIO explicándole por qué le afecta.\n\n"
            f"REGLAS ABSOLUTAS:\n"
            f"1. USA ÚNICAMENTE la información del contenido de cada noticia.\n"
            f"2. NO inventes datos numéricos, citas, ni información que no esté en el contenido.\n"
            f"3. NO uses tu conocimiento previo ni busques en internet. Solo el contenido de abajo.\n"
            f"4. fuente_url debe ser EXACTAMENTE la URL listada en 'URL real'. NO LA INVENTES.\n"
            f"5. Si no hay suficiente información, sé honesto ('No hay suficiente información').\n"
            f"6. Las etiquetas deben ser de esta lista: {
                ', '.join(self.ALLOWED_CATEGORIES)
            }\n"
            f"7. Máximo 3 etiquetas por noticia, mínimo 1.\n"
            f"8. nivel_urgencia debe ser 'bajo', 'medio' o 'alto'.\n"
            f"9. TONO: Háblale al usuario de TÚ. Usa 'te', 'tu', 'tienes', 'puedes'. "
            f"Como si fueras su asesor financiero personal.\n"
            f"   - En 'analisis': explícale por qué esta noticia le importa A ÉL/ELLA. "
            f"Ej: 'Esta noticia sobre el alza de combustible te afecta directamente porque...'\n"
            f"   - En 'impacto_personal': dile específicamente cómo impacta su situación. "
            f"Ej: 'Considerando que gastas $X al mes en transporte, este aumento significa...'\n"
            f"   - En 'recomendacion': dale una acción concreta que PUEDE HACER. "
            f"Ej: 'Te recomiendo que revises tu presupuesto de transporte y consideres...'\n\n"
            f"NOTICIAS A ANALIZAR:\n\n"
            f"{''.join(sections)}\n\n"
            f"Responde EXACTAMENTE con este formato JSON (sin texto adicional, sin markdown):\n"
            f"{{\n"
            f'  "analisis": [\n'
            f"{news_json_example}\n"
            f"  ]\n"
            f"}}"
        )

        last_error = None
        for client_idx, client in enumerate(self.clients):
            try:
                response = await client.chat.completions.create(
                    model=self.NVIDIA_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=8192,
                )
                raw = response.choices[0].message.content
                if not raw:
                    raise ValueError("Modelo devolvió respuesta vacía")

                parsed = self._parse_json(raw)
                if not parsed:
                    raise ValueError(
                        f"No se pudo extraer JSON de la respuesta: {raw[:200]}..."
                    )
                if "analisis" not in parsed:
                    raise ValueError(
                        f"Respuesta JSON no contiene campo 'analisis': {parsed}"
                    )

                analyses = parsed["analisis"]
                if len(analyses) != len(batch):
                    logger.warning(
                        f"Batch {batch_idx}: se esperaban {len(batch)} análisis, "
                        f"se recibieron {len(analyses)}"
                    )

                logger.info(
                    f"Batch {batch_idx} analizado con key {client_idx} ({
                        len(analyses)
                    } noticias)"
                )
                return analyses

            except APIStatusError as e:
                last_error = e
                if e.status_code in (429, 503):
                    logger.warning(
                        f"Key {client_idx} rate limit, probando siguiente..."
                    )
                    continue
                logger.error(
                    f"Error API con key {client_idx} (status {e.status_code}): {e}"
                )
                continue
            except Exception as e:
                last_error = e
                logger.error(f"Error con key {client_idx}: {e}")
                continue

        logger.error(
            f"Batch {batch_idx} falló tras {len(self.clients)} intentos: {last_error}"
        )
        return None

    async def analyze_and_save_news(
        self, news_items: list[dict], user_profile: dict, db_session
    ) -> list[dict]:
        """Analiza noticias con Nvidia API y guarda resultados en DB."""
        from sqlalchemy import insert

        from app.modules.news.entities import (
            News,
            NewsTag,
            NewsTagMap,
            PersonalizedAnalysisNews,
        )

        if not news_items:
            return []

        user_context = self._build_user_context(user_profile)
        user_id = user_profile.get("user_id")
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        logger.info(f"Analizando {len(news_items)} noticias con Nvidia API...")

        sem = asyncio.Semaphore(self.max_parallel)

        async def _batch_with_sem(batch, idx):
            async with sem:
                return await self._analyze_batch(batch, user_context, idx)

        tasks = []
        for i in range(0, len(news_items), 3):
            batch = news_items[i : i + 3]
            tasks.append(_batch_with_sem(batch, i // 3 + 1))

        batch_results = await asyncio.gather(*tasks)
        batched_news = [news_items[i : i + 3] for i in range(0, len(news_items), 3)]

        # ── DB persistence ──
        existing_urls = {r[0] for r in db_session.query(News.source_url).all()}
        news_to_insert = []
        tags_to_insert = []
        news_db_map = {}

        for batch_news, analyses in zip(batched_news, batch_results):
            if not analyses:
                continue
            for item, ad in zip(batch_news, analyses):
                try:
                    url = (
                        item.get("source_url")
                        or item.get("link")
                        or ad.get("fuente_url", "")
                        or ""
                    )[:250]
                    tags = [
                        t
                        for t in ad.get("etiquetas", ["Servicios básicos"])
                        if t in self.ALLOWED_CATEGORIES
                    ]
                    if not tags:
                        tags = ["Servicios básicos"]
                    tags = list(dict.fromkeys(tags))[:3]
                    urgency = ad.get("nivel_urgencia", "bajo")
                    if urgency not in self.URGENCY_LEVELS:
                        urgency = "bajo"

                    if url not in existing_urls:
                        content = item.get("content_text", "") or ad.get("resumen", "")
                        news_to_insert.append(
                            {
                                "title": ad.get(
                                    "titulo", item.get("title", "Sin título")
                                ),
                                "summary": ad.get("resumen", ""),
                                "content_text": content,
                                "source_url": url,
                                "published_at": item.get("published_at")
                                or datetime.now(),
                                "impact_level": urgency,
                                "affects": ad.get("impacto_personal", "")[:100]
                                if ad.get("impacto_personal")
                                else None,
                                "target_audience": "Usuario personalizado",
                            }
                        )
                        news_db_map[url] = {"tags": tags}
                        existing_urls.add(url)
                    else:
                        news_db_map[url] = {"tags": tags, "exists": True}

                    for t in tags:
                        tags_to_insert.append(
                            {"name": t, "description": f"Noticias de {t}"}
                        )

                except Exception as e:
                    logger.warning(f"Error procesando análisis: {e}")
                    continue

        # Bulk insert news
        if news_to_insert:
            logger.info(f"Insertando {len(news_to_insert)} noticias nuevas")
            db_session.execute(insert(News), news_to_insert)
            db_session.flush()

        # Map URLs to IDs
        url_to_id = {
            url: nid
            for nid, url in db_session.query(News.news_id, News.source_url).all()
        }

        # Tags
        if tags_to_insert:
            unique_tags = {t["name"]: t for t in tags_to_insert}.values()
            existing_tags = {
                r[0]: r[1] for r in db_session.query(NewsTag.name, NewsTag.tag_id).all()
            }
            new_tags = [t for t in unique_tags if t["name"] not in existing_tags]
            if new_tags:
                db_session.execute(insert(NewsTag), list(new_tags))
                db_session.flush()
                existing_tags.update(
                    {
                        r[0]: r[1]
                        for r in db_session.query(NewsTag.name, NewsTag.tag_id).all()
                    }
                )

            existing_pairs = {
                (r[0], r[1])
                for r in db_session.query(NewsTagMap.news_id, NewsTagMap.tag_id).all()
            }
            tag_map_bulk = []
            seen_pairs = set()
            for url, info in news_db_map.items():
                nid = url_to_id.get(url)
                if not nid:
                    continue
                for tname in info.get("tags", []):
                    tid = existing_tags.get(tname)
                    if (
                        tid
                        and (nid, tid) not in seen_pairs
                        and (nid, tid) not in existing_pairs
                    ):
                        seen_pairs.add((nid, tid))
                        tag_map_bulk.append({"news_id": nid, "tag_id": tid})
            if tag_map_bulk:
                logger.info(f"Insertando {len(tag_map_bulk)} tag_maps")
                db_session.execute(insert(NewsTagMap), tag_map_bulk)
                db_session.flush()

        # Personalized analyses
        analyses_bulk = []
        for batch_news, analyses in zip(batched_news, batch_results):
            if not analyses:
                continue
            for item, ad in zip(batch_news, analyses):
                try:
                    url = (
                        item.get("source_url")
                        or item.get("link")
                        or ad.get("fuente_url", "")
                        or ""
                    )[:250]
                    nid = url_to_id.get(url)
                    if not nid:
                        continue
                    analyses_bulk.append(
                        {
                            "news_id": nid,
                            "user_id": user_id,
                            "analysis_text": json.dumps(
                                {
                                    "analisis": ad.get("analisis", ""),
                                    "impacto_personal": ad.get("impacto_personal", ""),
                                    "recomendacion": ad.get("recomendacion", ""),
                                    "nivel_urgencia": ad.get("nivel_urgencia", "bajo"),
                                    "etiquetas": ad.get("etiquetas", []),
                                },
                                ensure_ascii=False,
                            ),
                            "generated_at": datetime.now(),
                        }
                    )
                except Exception:
                    continue

        if analyses_bulk:
            logger.info(f"Insertando {len(analyses_bulk)} análisis personalizados")
            db_session.execute(insert(PersonalizedAnalysisNews), analyses_bulk)
            db_session.flush()

        db_session.commit()

        # Build response
        saved_results = []
        for batch_news, analyses in zip(batched_news, batch_results):
            if not analyses:
                continue
            for item, ad in zip(batch_news, analyses):
                try:
                    url = (
                        item.get("source_url")
                        or item.get("link")
                        or ad.get("fuente_url", "")
                        or ""
                    )[:250]
                    saved_results.append(
                        {
                            "news_id": str(url_to_id.get(url, "")),
                            "titulo": ad.get("titulo", ""),
                            "resumen": ad.get("resumen", ""),
                            "analisis": ad.get("analisis", ""),
                            "impacto_personal": ad.get("impacto_personal", ""),
                            "recomendacion": ad.get("recomendacion", ""),
                            "nivel_urgencia": ad.get("nivel_urgencia", "bajo"),
                            "etiquetas": ad.get("etiquetas", []),
                            "fuente_url": url,
                        }
                    )
                except Exception:
                    continue

        logger.info(f"Análisis completado: {len(saved_results)} noticias procesadas")
        return saved_results

    async def get_all_analyzed_news(self, user_id: str, db_session) -> list[dict]:
        """Obtiene todas las noticias analizadas de un usuario."""
        from sqlalchemy.orm import joinedload

        from app.modules.news.entities import PersonalizedAnalysisNews

        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        results = (
            db_session.query(PersonalizedAnalysisNews)
            .filter(PersonalizedAnalysisNews.user_id == user_id)
            .options(joinedload(PersonalizedAnalysisNews.news))
            .order_by(PersonalizedAnalysisNews.generated_at.desc())
            .all()
        )

        output = []
        for pa in results:
            nd = {
                "news_id": str(pa.news.news_id) if pa.news else None,
                "titulo": pa.news.title if pa.news else "Noticia eliminada",
                "summary": pa.news.summary if pa.news else "",
                "source_url": pa.news.source_url if pa.news else None,
                "published_at": pa.news.published_at.isoformat()
                if pa.news and pa.news.published_at
                else None,
            }
            try:
                ad = (
                    json.loads(pa.analysis_text)
                    if isinstance(pa.analysis_text, str)
                    else (pa.analysis_text or {})
                )
            except Exception:
                ad = {"analisis": "Error parseando análisis", "etiquetas": []}
            output.append(
                {
                    **nd,
                    "analisis": ad.get("analisis", ""),
                    "impacto_personal": ad.get("impacto_personal", ""),
                    "recomendacion": ad.get("recomendacion", ""),
                    "nivel_urgencia": ad.get("nivel_urgencia", ""),
                    "etiquetas": ad.get("etiquetas", []),
                    "analizado_el": pa.generated_at.isoformat()
                    if pa.generated_at
                    else None,
                }
            )
        return output


news_analysis_agent = NewsAnalysisAgent(max_parallel_analyses=3)
