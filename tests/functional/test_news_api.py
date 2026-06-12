"""
Real functional tests: news module.

Endpoints rápidos (RSS real, sin LLM) + flujo completo de análisis:
POST /v1/news/analyze-full -> worker en background (RSS + NVIDIA API) ->
poll task hasta completar -> GET /v1/news/analyzed

Para que el flujo sea viable con los modelos gratis de NVIDIA NIM, el test
acota el trabajo del worker vía env vars (leídas en cada request):
- MIN_NEWS_FOR_SEARCH=0       -> desactiva la búsqueda Tavily de respaldo
- NEWS_ANALYSIS_TARGET_COUNT=3 -> analiza solo 3 noticias = 1 batch = 1 llamada LLM
"""

import os

import pytest

from tests.functional_real.conftest import poll_task

TIMEOUT_MINUTES = 20

ANALYSIS_FIELDS = (
    "titulo",
    "resumen",
    "analisis",
    "impacto_personal",
    "recomendacion",
    "nivel_urgencia",
    "etiquetas",
)


class TestNewsRealFlow:
    def test_topics_catalog(self, client):
        r = client.get("/v1/news/topics")
        assert r.status_code == 200
        topics = r.json()
        assert len(topics) >= 1
        for topic in topics:
            assert "id" in topic
            assert topic["name"]

    def test_latest_news_rss(self, client):
        """RSS feeds reales, sin LLM — debe responder en segundos."""
        r = client.get("/v1/news/latest_news")
        assert r.status_code == 200
        news = r.json()
        assert isinstance(news, list)
        if not news:
            pytest.skip("Los RSS feeds no devolvieron noticias (¿red caída?)")
        for item in news[:5]:
            assert item["link"]
            assert item["title"]
            assert "source" in item

    def test_analyze_full_flow(self, client, auth_headers):
        # Acotar trabajo: sin búsqueda Tavily y solo 1 batch de análisis
        os.environ["MIN_NEWS_FOR_SEARCH"] = "0"
        os.environ["NEWS_ANALYSIS_TARGET_COUNT"] = "3"

        r = client.post("/v1/news/analyze-full", headers=auth_headers)
        assert r.status_code == 202
        body = r.json()
        assert body["status"] == "pending"
        task_id = body["task_id"]

        task_data = poll_task(
            client,
            f"/v1/news/analyze/status/{task_id}",
            timeout_minutes=TIMEOUT_MINUTES,
        )

        assert task_data["status"] == "completed"
        result = task_data["result"]
        assert result["success"] is True

        if result.get("message") == "No hay noticias para analizar":
            pytest.skip("Los RSS feeds no entregaron noticias para analizar")

        # Si hubo noticias pero analyzed_count == 0, todos los batches
        # fallaron contra la API de NVIDIA -> es un fallo
        assert result["analyzed_count"] >= 1
        for analysis in result["analyses"]:
            for field in ANALYSIS_FIELDS:
                assert field in analysis, f"Falta el campo '{field}' en el análisis"
            assert analysis["nivel_urgencia"] in ("bajo", "medio", "alto")
            assert 1 <= len(analysis["etiquetas"]) <= 3

        summary = result["user_profile_summary"]
        assert summary["monthly_income"] == 1200000.0
        assert summary["monthly_expenses"] == 600000.0

        # Los análisis quedaron persistidos y disponibles para el usuario
        r = client.get("/v1/news/analyzed", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["total_count"] >= 1
