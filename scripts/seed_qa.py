"""
ChauchaApp QA Seed Script (Python).

Generates test data for the QA environment using SQLAlchemy ORM.
Focuses on user data needed for authentication testing.

Usage:
    python -m scripts.seed_qa

Default test password: TestPass123!
"""

import os
import sys
import uuid
from datetime import date
from decimal import Decimal

import bcrypt
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import all entities to register them with SQLAlchemy
import app.modules  # noqa: F401
from app.shared.database import Base
from app.modules.users.entities import IncomeType, User
from app.modules.transactions.entities import (
    TransactionType,
    TransactionFrequency,
    TransactionCategory,
    Transaction,
)
from app.modules.groups.entities import FamilyGroup, GroupMember
from app.modules.notifications.entities import NotificationType, NotificationStatus
from app.modules.education.entities import EducationalTopic


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/chauchaapp_db_qa",
)
TEST_PASSWORD = "TestPass123!"


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def seed_lookup_tables(session):
    """Seed all lookup tables with initial values."""

    # Income Types
    income_types = [
        IncomeType(name="Sueldo fijo", description="Trabajador dependiente con sueldo fijo"),
        IncomeType(name="Independiente", description="Trabajador independiente o freelance"),
        IncomeType(name="Mixto", description="Combinación de ingresos dependientes e independientes"),
        IncomeType(name="Otro", description="Otro tipo de ingreso"),
    ]
    for it in income_types:
        existing = session.query(IncomeType).filter_by(name=it.name).first()
        if not existing:
            session.add(it)

    # Transaction Types
    transaction_types_data = [
        ("Ingreso", "Ingreso de dinero"),
        ("Gasto", "Gasto de dinero"),
    ]
    for name, desc in transaction_types_data:
        if not session.query(TransactionType).filter_by(name=name).first():
            session.add(TransactionType(name=name, description=desc))

    session.flush()  # Flush to get IDs for FK references

    # Transaction Frequencies
    frequencies_data = [
        ("Única", "Transacción única, no recurrente"),
        ("Mensual", "Se repite mensualmente"),
        ("Semanal", "Se repite semanalmente"),
    ]
    for name, desc in frequencies_data:
        if not session.query(TransactionFrequency).filter_by(name=name).first():
            session.add(TransactionFrequency(name=name, description=desc))

    # Transaction Categories
    expense_type = session.query(TransactionType).filter_by(name="Gasto").first()
    income_type = session.query(TransactionType).filter_by(name="Ingreso").first()

    expense_categories = [
        ("Alimentación", "Gastos en comida y supermercado"),
        ("Transporte", "Gastos en transporte público, combustible, etc."),
        ("Salud", "Gastos médicos, farmacia, seguros de salud"),
        ("Educación", "Gastos en educación, cursos, materiales"),
        ("Entretenimiento", "Gastos en ocio, entretenimiento, suscripciones"),
        ("Vivienda", "Arriendo, dividendo, mantención del hogar"),
        ("Servicios Básicos", "Agua, luz, gas, internet, teléfono"),
        ("Otros Gastos", "Otros gastos no categorizados"),
    ]
    for name, desc in expense_categories:
        if not session.query(TransactionCategory).filter_by(name=name).first():
            session.add(TransactionCategory(
                name=name, description=desc,
                transaction_type_id=expense_type.transaction_type_id if expense_type else None,
            ))

    income_categories = [
        ("Sueldo", "Sueldo mensual de trabajo dependiente"),
        ("Freelance", "Ingresos por trabajos independientes"),
        ("Inversiones", "Retornos de inversiones"),
        ("Otros Ingresos", "Otros ingresos no categorizados"),
    ]
    for name, desc in income_categories:
        if not session.query(TransactionCategory).filter_by(name=name).first():
            session.add(TransactionCategory(
                name=name, description=desc,
                transaction_type_id=income_type.transaction_type_id if income_type else None,
            ))

    # Notification Types
    notification_types = [
        ("group_join_request", "Solicitud de un usuario para unirse a tu grupo familiar"),
        ("group_join_accepted", "Tu solicitud para unirse a un grupo fue aceptada"),
        ("group_join_rejected", "Tu solicitud para unirse a un grupo fue rechazada"),
        ("transaction_reminder", "Recordatorio de una transacción programada"),
        ("system_info", "Notificación informativa del sistema"),
        ("educational_reminder", "Recordatorio de progreso en módulo educativo"),
    ]
    for name, desc in notification_types:
        if not session.query(NotificationType).filter_by(name=name).first():
            session.add(NotificationType(name=name, description=desc))

    # Notification Statuses
    notification_statuses = [
        ("pending", "Notificación pendiente de envío"),
        ("sent", "Notificación enviada al usuario"),
        ("read", "Notificación leída por el usuario"),
        ("dismissed", "Notificación descartada por el usuario"),
    ]
    for name, desc in notification_statuses:
        if not session.query(NotificationStatus).filter_by(name=name).first():
            session.add(NotificationStatus(name=name, description=desc))

    # Educational Topics
    topics = [
        ("ahorro", "Estrategias y técnicas de ahorro personal"),
        ("inversion", "Conceptos de inversión y mercados financieros"),
        ("presupuesto", "Planificación y gestión de presupuesto personal"),
        ("deudas", "Manejo y estrategias para salir de deudas"),
        ("impuestos", "Educación tributaria y declaración de impuestos"),
        ("seguros", "Tipos de seguros y protección financiera"),
        ("jubilacion", "Planificación para la jubilación y AFP"),
        ("emprendimiento", "Finanzas para emprendedores"),
    ]
    for name, desc in topics:
        if not session.query(EducationalTopic).filter_by(name=name).first():
            session.add(EducationalTopic(name=name, description=desc))

    session.flush()
    print("  ✓ Lookup tables seeded")


def seed_users(session):
    """Seed test users for authentication testing."""

    hashed_pw = hash_password(TEST_PASSWORD)

    # Get income type references
    salaried = session.query(IncomeType).filter_by(name="Sueldo fijo").first()
    independent = session.query(IncomeType).filter_by(name="Independiente").first()
    mixed = session.query(IncomeType).filter_by(name="Mixto").first()
    other = session.query(IncomeType).filter_by(name="Otro").first()

    test_users = [
        # Auth test users
        User(
            first_name="Test", last_name="Login",
            email="test_login@chauchaapp.cl", password=hashed_pw,
            birth_date=date(1990, 5, 15),
            income_type_id=salaried.income_type_id if salaried else None,
            monthly_income=Decimal("850000.00"), monthly_expenses=Decimal("620000.00"),
        ),
        User(
            first_name="Test", last_name="Register",
            email="test_register@chauchaapp.cl", password=hashed_pw,
            birth_date=date(1995, 8, 22),
            income_type_id=independent.income_type_id if independent else None,
            monthly_income=Decimal("1200000.00"), monthly_expenses=Decimal("780000.00"),
        ),
        User(
            first_name="Test", last_name="Family",
            email="test_family@chauchaapp.cl", password=hashed_pw,
            birth_date=date(1990, 5, 15),
            income_type_id=salaried.income_type_id if salaried else None,
            monthly_income=Decimal("850000.00"), monthly_expenses=Decimal("620000.00"),
        ),
        # Diverse users
        User(
            first_name="María", last_name="González",
            email="maria.gonzalez@test.cl", password=hashed_pw,
            birth_date=date(1988, 3, 10),
            income_type_id=salaried.income_type_id if salaried else None,
            monthly_income=Decimal("1500000.00"), monthly_expenses=Decimal("980000.00"),
        ),
        User(
            first_name="Carlos", last_name="Muñoz",
            email="carlos.munoz@test.cl", password=hashed_pw,
            birth_date=date(1992, 11, 28),
            income_type_id=independent.income_type_id if independent else None,
            monthly_income=Decimal("2000000.00"), monthly_expenses=Decimal("1350000.00"),
        ),
        User(
            first_name="Valentina", last_name="Rojas",
            email="valentina.rojas@test.cl", password=hashed_pw,
            birth_date=date(1985, 7, 3),
            income_type_id=mixed.income_type_id if mixed else None,
            monthly_income=Decimal("1800000.00"), monthly_expenses=Decimal("1100000.00"),
        ),
        User(
            first_name="Andrés", last_name="Silva",
            email="andres.silva@test.cl", password=hashed_pw,
            birth_date=date(1998, 1, 20),
            income_type_id=salaried.income_type_id if salaried else None,
            monthly_income=Decimal("650000.00"), monthly_expenses=Decimal("520000.00"),
        ),
        User(
            first_name="Camila", last_name="Torres",
            email="camila.torres@test.cl", password=hashed_pw,
            birth_date=date(1993, 9, 14),
            income_type_id=other.income_type_id if other else None,
            monthly_income=Decimal("900000.00"), monthly_expenses=Decimal("670000.00"),
        ),
        User(
            first_name="Diego", last_name="Fernández",
            email="diego.fernandez@test.cl", password=hashed_pw,
            birth_date=date(1987, 12, 5),
            income_type_id=salaried.income_type_id if salaried else None,
            monthly_income=Decimal("2500000.00"), monthly_expenses=Decimal("1800000.00"),
        ),
        User(
            first_name="Javiera", last_name="López",
            email="javiera.lopez@test.cl", password=hashed_pw,
            birth_date=date(1996, 4, 18),
            income_type_id=independent.income_type_id if independent else None,
            monthly_income=Decimal("1100000.00"), monthly_expenses=Decimal("850000.00"),
        ),
        User(
            first_name="Felipe", last_name="Martínez",
            email="felipe.martinez@test.cl", password=hashed_pw,
            birth_date=date(1991, 6, 30),
            income_type_id=mixed.income_type_id if mixed else None,
            monthly_income=Decimal("3000000.00"), monthly_expenses=Decimal("2100000.00"),
        ),
    ]

    for user in test_users:
        existing = session.query(User).filter_by(email=user.email).first()
        if not existing:
            session.add(user)

    session.flush()
    print("  ✓ Test users seeded (11 users)")


def seed_family_group(session):
    """Seed family group for shared cartola testing."""
    admin = session.query(User).filter_by(email="test_login@chauchaapp.cl").first()
    member = session.query(User).filter_by(email="test_family@chauchaapp.cl").first()
    member2 = session.query(User).filter_by(email="maria.gonzalez@test.cl").first()
    member3 = session.query(User).filter_by(email="carlos.munoz@test.cl").first()
    if not admin or not member:
        return None

    group = (
        session.query(FamilyGroup)
        .filter_by(name="Grupo Familiar Test", admin_id=admin.user_id)
        .first()
    )
    if not group:
        group = FamilyGroup(name="Grupo Familiar Test", admin_id=admin.user_id)
        session.add(group)
        session.flush()

    for user in (admin, member, member2, member3):
        if not user:
            continue
        existing = (
            session.query(GroupMember)
            .filter_by(user_id=user.user_id, family_group_id=group.family_group_id)
            .first()
        )
        if not existing:
            session.add(
                GroupMember(user_id=user.user_id, family_group_id=group.family_group_id)
            )

    session.flush()
    print("  ✓ Family group seeded")
    return group


def seed_transactions(session, family_group):
    """Seed sample transactions for all test users."""

    # Get type/frequency references
    expense_type = session.query(TransactionType).filter_by(name="Gasto").first()
    income_type = session.query(TransactionType).filter_by(name="Ingreso").first()
    one_time = session.query(TransactionFrequency).filter_by(name="Única").first()
    monthly = session.query(TransactionFrequency).filter_by(name="Mensual").first()
    weekly = session.query(TransactionFrequency).filter_by(name="Semanal").first()

    # Get all transaction categories
    alimentacion = session.query(TransactionCategory).filter_by(name="Alimentación").first()
    transporte = session.query(TransactionCategory).filter_by(name="Transporte").first()
    salud = session.query(TransactionCategory).filter_by(name="Salud").first()
    educacion = session.query(TransactionCategory).filter_by(name="Educación").first()
    entretenimiento = session.query(TransactionCategory).filter_by(name="Entretenimiento").first()
    vivienda = session.query(TransactionCategory).filter_by(name="Vivienda").first()
    servicios_basicos = session.query(TransactionCategory).filter_by(name="Servicios Básicos").first()
    otros_gastos = session.query(TransactionCategory).filter_by(name="Otros Gastos").first()
    sueldo = session.query(TransactionCategory).filter_by(name="Sueldo").first()
    freelance = session.query(TransactionCategory).filter_by(name="Freelance").first()
    inversiones = session.query(TransactionCategory).filter_by(name="Inversiones").first()
    otros_ingresos = session.query(TransactionCategory).filter_by(name="Otros Ingresos").first()

    all_transactions = []
    family_group_id = family_group.family_group_id if family_group else None

    def _add_tx(
        email, tx_type, category, frequency, amount, description, tx_date, family_group_id=None
    ):
        """Helper to build a Transaction and append to the list."""
        user = session.query(User).filter_by(email=email).first()
        if not user:
            return
        all_transactions.append(Transaction(
            user_id=user.user_id,
            family_group_id=family_group_id,
            amount=Decimal(str(amount)),
            transaction_type_id=tx_type.transaction_type_id,
            transaction_category_id=category.transaction_category_id,
            transaction_frequency_id=frequency.transaction_frequency_id,
            description=description,
            transaction_date=tx_date,
        ))

    # =========================================
    # test_login@chauchaapp.cl: 27 transactions
    # =========================================

    test_login_transactions = [
        (income_type, sueldo, monthly, 850000, "Sueldo mensual", date(2026, 1, 1)),
        (expense_type, vivienda, monthly, 350000, "Arriendo", date(2026, 1, 5)),
        (expense_type, servicios_basicos, monthly, 42000, "Luz y Agua", date(2026, 1, 10)),
        (expense_type, otros_gastos, monthly, 10000, "Seguro celular", date(2026, 1, 15)),
        (expense_type, entretenimiento, monthly, 8500, "Netflix", date(2026, 1, 20)),
        (expense_type, salud, monthly, 30000, "Seguro salud", date(2026, 1, 25)),
        (expense_type, alimentacion, weekly, 15000, "Supermercado semanal", date(2026, 5, 1)),
        (expense_type, transporte, weekly, 5000, "Carga Bip semanal", date(2026, 5, 3)),
        (expense_type, alimentacion, one_time, 45000, "Súper Líder", date(2026, 4, 5)),
        (expense_type, transporte, one_time, 15000, "Carga Bip", date(2026, 4, 6)),
        (expense_type, salud, one_time, 32000, "Farmacia Cruz Verde", date(2026, 4, 20)),
        (expense_type, educacion, one_time, 150000, "Curso Online", date(2026, 4, 22)),
        (expense_type, entretenimiento, one_time, 25000, "Cine y cena", date(2026, 4, 25)),
        (expense_type, otros_gastos, one_time, 60000, "Compra imprevista", date(2026, 4, 28)),
        (expense_type, vivienda, one_time, 45000, "Mantención hogar", date(2026, 3, 15)),
        (expense_type, transporte, one_time, 60000, "Tag autopista", date(2026, 3, 20)),
        (expense_type, salud, one_time, 85000, "Dentista", date(2026, 2, 15)),
        (expense_type, alimentacion, one_time, 55000, "Supermercado Mayo", date(2026, 5, 3)),
        (expense_type, transporte, one_time, 15000, "Carga Bip Mayo", date(2026, 5, 7)),
        (expense_type, salud, one_time, 150000, "Consulta Médica", date(2026, 4, 8)),
        (expense_type, educacion, one_time, 200000, "Curso Desarrollo Web", date(2026, 4, 12)),
        (expense_type, entretenimiento, one_time, 95000, "Cena Aniversario", date(2026, 4, 18)),
        (expense_type, alimentacion, one_time, 70000, "Supermercado Extra Abril", date(2026, 4, 25)),
        (expense_type, alimentacion, one_time, 120000, "Cumpleaños", date(2026, 5, 15)),
        (expense_type, transporte, one_time, 35000, "Mantención auto", date(2026, 5, 20)),
        (income_type, freelance, one_time, 200000, "Proyecto freelance", date(2026, 4, 15)),
        (income_type, inversiones, one_time, 50000, "Dividendos", date(2026, 3, 1)),
    ]

    for tx_type, category, frequency, amount, description, tx_date in test_login_transactions:
        _add_tx(
            "test_login@chauchaapp.cl",
            tx_type,
            category,
            frequency,
            amount,
            description,
            tx_date,
            family_group_id=family_group_id,
        )

    for tx_type, category, frequency, amount, description, tx_date in test_login_transactions:
        family_tx_date = date(2026, 1, 2) if description == "Sueldo mensual" else tx_date
        _add_tx(
            "test_family@chauchaapp.cl",
            tx_type,
            category,
            frequency,
            amount,
            description,
            family_tx_date,
            family_group_id=family_group_id,
        )

    # =========================================
    # Other QA users
    # =========================================

    # maria.gonzalez@test.cl - salaried, 1,500,000
    _add_tx("maria.gonzalez@test.cl", income_type, sueldo, monthly, 1500000, "Sueldo mensual", date(2026, 1, 1))
    _add_tx("maria.gonzalez@test.cl", expense_type, alimentacion, one_time, 85000, "Supermercado mensual", date(2026, 4, 3))
    _add_tx("maria.gonzalez@test.cl", expense_type, salud, one_time, 45000, "Farmacia", date(2026, 4, 15))
    _add_tx("maria.gonzalez@test.cl", expense_type, entretenimiento, one_time, 35000, "Salida familiar", date(2026, 5, 10))

    # carlos.munoz@test.cl - independent, 2,000,000
    _add_tx("carlos.munoz@test.cl", income_type, sueldo, monthly, 2000000, "Ingreso mensual", date(2026, 1, 1))
    _add_tx("carlos.munoz@test.cl", expense_type, transporte, one_time, 120000, "Mantención vehículo", date(2026, 4, 8))
    _add_tx("carlos.munoz@test.cl", expense_type, educacion, one_time, 80000, "Curso marketing", date(2026, 5, 5))
    _add_tx("carlos.munoz@test.cl", expense_type, vivienda, one_time, 250000, "Reparación hogar", date(2026, 3, 20))

    # valentina.rojas@test.cl - mixed, 1,800,000
    _add_tx("valentina.rojas@test.cl", income_type, sueldo, monthly, 1800000, "Ingreso mensual", date(2026, 1, 1))
    _add_tx("valentina.rojas@test.cl", expense_type, salud, one_time, 65000, "Consulta médica", date(2026, 4, 12))
    _add_tx("valentina.rojas@test.cl", expense_type, entretenimiento, one_time, 55000, "Concierto", date(2026, 5, 8))
    _add_tx("valentina.rojas@test.cl", expense_type, alimentacion, one_time, 95000, "Supermercado Quincena", date(2026, 4, 20))

    # andres.silva@test.cl - salaried, 650,000
    _add_tx("andres.silva@test.cl", income_type, sueldo, monthly, 650000, "Sueldo mensual", date(2026, 1, 1))
    _add_tx("andres.silva@test.cl", expense_type, transporte, one_time, 25000, "Carga Bip", date(2026, 4, 10))
    _add_tx("andres.silva@test.cl", expense_type, alimentacion, one_time, 35000, "Supermercado", date(2026, 5, 15))

    # camila.torres@test.cl - other, 900,000
    _add_tx("camila.torres@test.cl", income_type, sueldo, monthly, 900000, "Ingreso mensual", date(2026, 1, 1))
    _add_tx("camila.torres@test.cl", expense_type, entretenimiento, one_time, 40000, "Streaming anual", date(2026, 4, 5))
    _add_tx("camila.torres@test.cl", expense_type, alimentacion, one_time, 50000, "Supermercado", date(2026, 5, 2))
    _add_tx("camila.torres@test.cl", expense_type, otros_gastos, one_time, 25000, "Suscripción revista", date(2026, 3, 10))

    # diego.fernandez@test.cl - salaried, 2,500,000
    _add_tx("diego.fernandez@test.cl", income_type, sueldo, monthly, 2500000, "Sueldo mensual", date(2026, 1, 1))
    _add_tx("diego.fernandez@test.cl", expense_type, educacion, one_time, 350000, "Diplomado", date(2026, 4, 3))
    _add_tx("diego.fernandez@test.cl", expense_type, salud, one_time, 95000, "Consulta especialista", date(2026, 5, 10))
    _add_tx("diego.fernandez@test.cl", expense_type, vivienda, one_time, 180000, "Mantención hogar", date(2026, 3, 15))
    _add_tx("diego.fernandez@test.cl", expense_type, transporte, one_time, 75000, "Tag autopista", date(2026, 4, 22))

    # javiera.lopez@test.cl - independent, 1,100,000
    _add_tx("javiera.lopez@test.cl", income_type, sueldo, monthly, 1100000, "Ingreso mensual", date(2026, 1, 1))
    _add_tx("javiera.lopez@test.cl", expense_type, alimentacion, one_time, 65000, "Supermercado", date(2026, 4, 7))
    _add_tx("javiera.lopez@test.cl", expense_type, entretenimiento, one_time, 30000, "Salida cultural", date(2026, 5, 12))

    # felipe.martinez@test.cl - mixed, 3,000,000
    _add_tx("felipe.martinez@test.cl", income_type, sueldo, monthly, 3000000, "Ingreso mensual", date(2026, 1, 1))
    _add_tx("felipe.martinez@test.cl", expense_type, educacion, one_time, 500000, "MBA cuota", date(2026, 4, 1))
    _add_tx("felipe.martinez@test.cl", expense_type, vivienda, one_time, 400000, "Dividendo extra", date(2026, 5, 5))
    _add_tx("felipe.martinez@test.cl", expense_type, salud, one_time, 120000, "Seguro salud extra", date(2026, 3, 10))
    _add_tx("felipe.martinez@test.cl", expense_type, alimentacion, one_time, 150000, "Supermercado familiar", date(2026, 4, 20))

    # Deduplicate and insert
    for tx in all_transactions:
        existing = session.query(Transaction).filter_by(
            user_id=tx.user_id,
            description=tx.description,
            transaction_date=tx.transaction_date
        ).first()
        if not existing:
            session.add(tx)

    session.flush()
    print(f"  ✓ Sample transactions seeded ({len(all_transactions)} transactions)")


def main():
    """Run the QA seed process."""
    print(f"\n{'='*60}")
    print("ChauchaApp QA Seed Script")
    print(f"{'='*60}")
    print(f"Database: {DATABASE_URL}")
    print(f"Test password: {TEST_PASSWORD}")
    print(f"{'='*60}\n")

    engine = create_engine(DATABASE_URL, echo=False)

    # Create tables if they don't exist (for local development)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print("Seeding lookup tables...")
        seed_lookup_tables(session)

        print("Seeding test users...")
        seed_users(session)

        print("Seeding family group...")
        family_group = seed_family_group(session)

        print("Seeding sample transactions...")
        seed_transactions(session, family_group)

        session.commit()
        print(f"\n{'='*60}")
        print("✅ QA seed completed successfully!")
        print(f"{'='*60}")
        print("\nTest credentials:")
        print(f"  Email: test_login@chauchaapp.cl")
        print(f"  Password: {TEST_PASSWORD}")
        print(f"{'='*60}\n")

    except Exception as e:
        session.rollback()
        print(f"\n❌ Seed failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
