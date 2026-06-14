"""
Conftest for real functional tests — file-based SQLite, real API keys.

These tests run the full POST->background worker->GET flow with real AI agents
calling NVIDIA/Tavily APIs. They take 5-15 minutes per test.
"""

import os
import time
import uuid
from datetime import date, datetime
from decimal import Decimal

from dotenv import load_dotenv

load_dotenv(override=True)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.agent.daily_tips_agent as dta_module
import app.modules.daily_tips.controller as dta_ctrl

# ---------------------------------------------------------------------------
# 1. Fix agent singletons — created with dummy keys by tests/conftest.py
# ---------------------------------------------------------------------------
from app.agent.daily_tips_agent import DailyTipsAgent
from app.shared.database import (
    Base,
    SessionLocal,
)
from app.shared.database import (
    engine as app_engine,
)
from main import app

_real_dta = DailyTipsAgent()
dta_module.daily_tips_agent = _real_dta
dta_ctrl.daily_tips_agent = _real_dta

import app.agent.financial_agent.financial_agent as fpa_module
import app.modules.financial_data.controller as fpa_ctrl
import app.modules.financial_data.service as fpa_svc
from app.agent.financial_agent.financial_agent import FinancialPlanningAgent

_real_fpa = FinancialPlanningAgent()
fpa_module.financial_planning_agent = _real_fpa
fpa_ctrl.financial_planning_agent = _real_fpa
fpa_svc.financial_planning_agent = _real_fpa

import app.agent.quizzes.quizz_agent as qa_module
import app.modules.education.service as edu_svc
from app.agent.quizzes.quizz_agent import QuizzAgent

_real_qa = QuizzAgent()
qa_module.quizz_agent = _real_qa

edu_svc.QuizzAgent = lambda: _real_qa

# ---------------------------------------------------------------------------
# 2. Database file path
# ---------------------------------------------------------------------------

DB_FILE = "test.db"

# ---------------------------------------------------------------------------
# 3. Reference data
# ---------------------------------------------------------------------------

REFERENCE_DATA = {
    "income_types": [
        {
            "name": "Sueldo fijo",
            "description": "Trabajador dependiente con sueldo fijo",
        },
        {
            "name": "Independiente",
            "description": "Trabajador independiente o freelance",
        },
        {
            "name": "Mixto",
            "description": "Combinación de ingresos dependientes e independientes",
        },
        {"name": "Otro", "description": "Otro tipo de ingreso"},
    ],
    "news_tags": [
        {"name": "Sueldo mínimo", "description": "Cambios en el salario mínimo"},
        {"name": "Combustible", "description": "Precios bencina/diesel"},
        {"name": "Alimentos", "description": "IPC y canasta básica"},
        {"name": "Vivienda", "description": "Arriendos, dividendos, UF"},
        {"name": "Transporte", "description": "Tarifas y movilidad"},
        {"name": "Servicios básicos", "description": "Luz, agua, internet"},
        {"name": "Impuestos", "description": "IVA, retenciones, SII"},
        {"name": "Créditos", "description": "Tasas y condiciones"},
        {"name": "Ahorro", "description": "APV, depósitos, fondos"},
        {"name": "Inversiones", "description": "Bolsa, fondos mutuos"},
    ],
    "transaction_types": [
        {"name": "Ingreso", "description": "Ingreso de dinero"},
        {"name": "Gasto", "description": "Gasto de dinero"},
    ],
    "transaction_frequencies": [
        {"name": "Única", "description": "Transacción única, no recurrente"},
        {"name": "Mensual", "description": "Se repite mensualmente"},
        {"name": "Semanal", "description": "Se repite semanalmente"},
    ],
    "transaction_categories": [
        {
            "name": "Alimentación",
            "description": "Gastos en comida y supermercado",
            "type": "Gasto",
        },
        {
            "name": "Transporte",
            "description": "Gastos en transporte público",
            "type": "Gasto",
        },
        {"name": "Salud", "description": "Gastos médicos", "type": "Gasto"},
        {"name": "Educación", "description": "Gastos en educación", "type": "Gasto"},
        {"name": "Entretenimiento", "description": "Gastos en ocio", "type": "Gasto"},
        {"name": "Vivienda", "description": "Arriendo, dividendo", "type": "Gasto"},
        {"name": "Servicios Básicos", "description": "Agua, luz, gas", "type": "Gasto"},
        {"name": "Otros Gastos", "description": "Otros gastos", "type": "Gasto"},
        {"name": "Sueldo", "description": "Sueldo mensual", "type": "Ingreso"},
        {
            "name": "Freelance",
            "description": "Ingresos independientes",
            "type": "Ingreso",
        },
        {
            "name": "Bonificación",
            "description": "Bonos y gratificaciones",
            "type": "Ingreso",
        },
        {
            "name": "Inversiones",
            "description": "Retornos de inversiones",
            "type": "Ingreso",
        },
        {"name": "Otros", "description": "Otros ingresos", "type": "Ingreso"},
    ],
    "notification_types": [
        {"name": "group_join_request", "description": "Solicitud para unirse a grupo"},
        {"name": "group_join_accepted", "description": "Solicitud aceptada"},
        {"name": "group_join_rejected", "description": "Solicitud rechazada"},
        {"name": "transaction_reminder", "description": "Recordatorio de transacción"},
        {"name": "system_info", "description": "Notificación informativa"},
        {"name": "educational_reminder", "description": "Recordatorio educativo"},
    ],
    "notification_statuses": [
        {"name": "pending", "description": "Pendiente"},
        {"name": "sent", "description": "Enviada"},
        {"name": "read", "description": "Leída"},
        {"name": "dismissed", "description": "Descartada"},
    ],
    "educational_topics": [
        {"name": "Ahorro", "description": "Estrategias de ahorro personal"},
        {"name": "Inversión", "description": "Conceptos de inversión"},
        {"name": "Presupuesto", "description": "Gestión de presupuesto"},
        {"name": "Deudas", "description": "Manejo de deudas"},
        {"name": "Impuestos", "description": "Educación tributaria"},
        {"name": "Seguros", "description": "Tipos de seguros"},
        {"name": "Jubilación", "description": "Planificación para la jubilación"},
        {"name": "Emprendimiento", "description": "Finanzas para emprendedores"},
    ],
}


def _seed_reference_data(db: Session):
    from app.modules.education.entities import EducationalTopic
    from app.modules.news.entities import NewsTag
    from app.modules.notifications.entities import NotificationStatus, NotificationType
    from app.modules.transactions.entities import (
        TransactionCategory,
        TransactionFrequency,
        TransactionType,
    )
    from app.modules.users.entities import IncomeType

    for data in REFERENCE_DATA["income_types"]:
        if not db.query(IncomeType).filter(IncomeType.name == data["name"]).first():
            db.add(IncomeType(name=data["name"], description=data["description"]))

    for data in REFERENCE_DATA["news_tags"]:
        if not db.query(NewsTag).filter(NewsTag.name == data["name"]).first():
            db.add(NewsTag(name=data["name"], description=data["description"]))

    tx_types = {}
    for data in REFERENCE_DATA["transaction_types"]:
        existing = (
            db.query(TransactionType)
            .filter(TransactionType.name == data["name"])
            .first()
        )
        if not existing:
            existing = TransactionType(
                name=data["name"], description=data["description"]
            )
            db.add(existing)
        tx_types[data["name"]] = existing

    for data in REFERENCE_DATA["transaction_frequencies"]:
        if (
            not db.query(TransactionFrequency)
            .filter(TransactionFrequency.name == data["name"])
            .first()
        ):
            db.add(
                TransactionFrequency(name=data["name"], description=data["description"])
            )

    for data in REFERENCE_DATA["transaction_categories"]:
        tx_type = tx_types[data["type"]]
        existing = (
            db.query(TransactionCategory)
            .filter(
                TransactionCategory.name == data["name"],
                TransactionCategory.transaction_type_id == tx_type.transaction_type_id,
            )
            .first()
        )
        if not existing:
            db.add(
                TransactionCategory(
                    name=data["name"],
                    description=data["description"],
                    transaction_type_id=tx_type.transaction_type_id,
                )
            )

    for data in REFERENCE_DATA["notification_types"]:
        if (
            not db.query(NotificationType)
            .filter(NotificationType.name == data["name"])
            .first()
        ):
            db.add(NotificationType(name=data["name"], description=data["description"]))

    for data in REFERENCE_DATA["notification_statuses"]:
        if (
            not db.query(NotificationStatus)
            .filter(NotificationStatus.name == data["name"])
            .first()
        ):
            db.add(
                NotificationStatus(name=data["name"], description=data["description"])
            )

    for data in REFERENCE_DATA["educational_topics"]:
        if (
            not db.query(EducationalTopic)
            .filter(EducationalTopic.name == data["name"])
            .first()
        ):
            db.add(EducationalTopic(name=data["name"], description=data["description"]))

    db.commit()


# ---------------------------------------------------------------------------
# 3. Session-scoped fixtures (DB, user, client) — created once per session
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create tables and seed reference data once per session."""
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    Base.metadata.create_all(bind=app_engine)
    db = SessionLocal()
    try:
        _seed_reference_data(db)
    finally:
        db.close()
    yield


@pytest.fixture(scope="session")
def test_user():
    from app.modules.news.entities import NewsTag, UserInterest
    from app.modules.users.entities import IncomeType, User
    from app.shared.security.password import hash_password

    db = SessionLocal()
    try:
        income_type = db.query(IncomeType).first()
        user = User(
            user_id=uuid.uuid4(),
            email="real_functional_test@example.com",
            password=hash_password("TestPass123!"),
            first_name="Funcional",
            last_name="TestUser",
            birth_date=date(1995, 5, 25),
            income_type_id=income_type.income_type_id,
            monthly_income=Decimal("1200000"),
            monthly_expenses=Decimal("600000"),
            created_at=datetime.utcnow(),
        )
        db.add(user)
        db.flush()

        interest_tags = (
            db.query(NewsTag)
            .filter(NewsTag.name.in_(["Ahorro", "Inversiones", "Créditos", "Vivienda"]))
            .all()
        )
        for tag in interest_tags:
            db.add(UserInterest(user_id=user.user_id, tag_id=tag.tag_id))

        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


@pytest.fixture(scope="session")
def auth_headers(test_user):
    from app.shared.security.auth_middleware import get_current_user

    app.dependency_overrides[get_current_user] = lambda: test_user
    return {"Authorization": "Bearer test-token"}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# 4. Helper
# ---------------------------------------------------------------------------


def poll_task(client, task_url, timeout_minutes=15, interval=10):
    """Poll task endpoint until completed or failed. Returns task data dict."""
    deadline = time.time() + timeout_minutes * 60
    last_status = "unknown"
    while time.time() < deadline:
        r = client.get(task_url)
        if r.status_code != 200:
            time.sleep(interval)
            continue
        data = r.json()
        last_status = data.get("status", "unknown")
        if last_status == "completed":
            return data
        if last_status in ("failed", "error"):
            pytest.fail(f"Task {last_status}: {data.get('error', 'unknown error')}")
        time.sleep(interval)
    pytest.fail(
        f"Task did not complete within {timeout_minutes} min "
        f"(last status: {last_status})"
    )
