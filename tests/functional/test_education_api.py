"""
Real functional test: education module — generación + ciclo de vida completo.

POST /v1/education/modules/generate -> worker en background (Tavily + NVIDIA,
hasta 3 intentos de generación) -> poll task -> catálogo -> detalle ->
progreso por secciones -> quiz aprobado -> módulo completado.

Se genera UN solo módulo (mínimo trabajo posible) porque cada generación
implica una búsqueda con Tavily + 1-3 llamadas al modelo de NVIDIA NIM,
que en el tier gratis puede tardar varios minutos.
"""

from tests.functional_real.conftest import poll_task

TIMEOUT_MINUTES = 30

MODULE_FIELDS = (
    "id",
    "slug",
    "title",
    "description",
    "level",
    "estimatedTimeMinutes",
    "topicsCount",
    "category",
    "tags",
    "createdAt",
    "learningObjectives",
    "content",
    "topics",
    "quiz",
)


class TestEducationRealFlow:
    def test_generate_module_and_complete_lifecycle(self, client, test_user):
        # ── 1. Generar un módulo con el agente real ────────────────────
        payload = {"items": [{"topic": "Ahorro personal", "level": "Principiante"}]}
        r = client.post("/v1/education/modules/generate", json=payload)
        assert r.status_code == 202
        task_id = r.json()["task_id"]

        task_data = poll_task(
            client,
            f"/v1/education/modules/tasks/{task_id}",
            timeout_minutes=TIMEOUT_MINUTES,
        )

        assert task_data["status"] == "completed"
        items = task_data["result"]["items"]
        assert len(items) == 1

        module = items[0]["module"]
        for field in MODULE_FIELDS:
            assert field in module, f"Falta el campo '{field}' en el módulo"
        assert module["level"] == "Principiante"

        quiz = module["quiz"]
        assert quiz["questionsCount"] == len(quiz["questions"]) >= 1
        assert 0 < quiz["passingScore"] <= 100
        for question in quiz["questions"]:
            assert question["question"]
            assert question["options"] and len(question["options"]) >= 2
            assert question["correctAnswer"] is not None
            assert 0 <= question["correctAnswer"] < len(question["options"])

        sections = module["content"]["sections"]
        assert len(sections) >= 1

        module_id = module["id"]
        slug = module["slug"]

        # ── 2. El módulo aparece en el catálogo ────────────────────────
        r = client.get("/v1/education/modules")
        assert r.status_code == 200
        listing = r.json()
        assert listing["totalCount"] >= 1
        assert module_id in [m["id"] for m in listing["modules"]]

        # ── 3. Detalle por slug (sin usuario -> progreso vacío) ────────
        r = client.get(f"/v1/education/modules/{slug}")
        assert r.status_code == 200
        detail = r.json()
        assert detail["module"]["id"] == module_id
        assert detail["progress"]["status"] == "not_started"

        # ── 4. Iniciar progreso del usuario ────────────────────────────
        user_id = str(test_user.user_id)
        r = client.post(
            f"/v1/education/modules/{module_id}/progress/start",
            params={"user_id": user_id},
        )
        assert r.status_code == 200
        progress = r.json()
        assert progress["status"] == "in_progress"
        assert progress["startedAt"] is not None

        # ── 5. Completar todas las secciones de contenido ──────────────
        for section in sections:
            r = client.patch(
                f"/v1/education/modules/{module_id}/progress/sections",
                params={"user_id": user_id},
                json={"sectionId": section["id"]},
            )
            assert r.status_code == 200
        progress = r.json()
        assert set(progress["completedSections"]) == {s["id"] for s in sections}

        # ── 6. Quiz aprobado -> módulo completado ──────────────────────
        attempt = {
            "score": 100,
            "correctAnswers": quiz["questionsCount"],
            "totalQuestions": quiz["questionsCount"],
        }
        r = client.post(
            f"/v1/education/modules/{module_id}/quiz/attempts",
            params={"user_id": user_id},
            json=attempt,
        )
        assert r.status_code == 200
        outcome = r.json()
        assert outcome["passed"] is True
        assert outcome["progress"]["status"] == "completed"
        assert outcome["progress"]["progressPercentage"] == 100
        assert outcome["progress"]["completedAt"] is not None
