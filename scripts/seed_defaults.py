"""
Seed default data into the database on first startup.

Idempotent: skips if data already exists.
Runs automatically via FastAPI lifespan hook.
"""

import json
import logging
import uuid
from datetime import datetime

from app.shared.database import SessionLocal
from app.modules.daily_tips.entities import DailyTip
from app.modules.financial_data.entities import FinancialPlanningTip
from app.modules.education.entities import EducationalModule
from app.modules.news.entities import News, NewsTag, NewsTagMap

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────
# Default Daily Tips (7 tips, one per day)
# ────────────────────────────────────────────────────────────────

DEFAULT_TIPS = [
    {
        "title": "Fondo de Emergencia: Tu Primera Meta",
        "text": "Antes de invertir o gastar en lujos, asegúrate de tener un fondo de emergencia que cubra al menos 3 meses de tus gastos básicos. En Chile, el costo de vida mensual promedio es de $450.000 CLP. Ahorra esta meta antes de cualquier otro objetivo financiero.",
        "category": "Ahorro",
        "day_of_week": 0,
    },
    {
        "title": "Controla el 'Gasto Hormiga'",
        "text": "Esos pequeños gastos diarios como el café, el pan o la micro suman más de lo que crees. Si gastas $2.000 CLP diarios en 'antojos', eso son $60.000 al mes. Lleva un registro semanal y verás dónde se va tu plata.",
        "category": "Alimentos",
        "day_of_week": 1,
    },
    {
        "title": "UF y tu Bolsillo",
        "text": "La UF (Unidad de Fomento) sube con la inflación. Si tienes un crédito hipotecario o dividendo en UF, tu cuota puede aumentar cada año. Revisa siempre si tu sueldo sube al mismo ritmo que la UF para no perder poder adquisitivo.",
        "category": "Vivienda",
        "day_of_week": 2,
    },
    {
        "title": "Beneficios Tributarios por Ahorro",
        "text": "Si eres menor de 35 años y ahorras en una Cuenta de Ahorro para la Vivienda (DS-1), el Estado te da un subsidio directo. Además, los aportes al APV (Ahorro Previsional Voluntario) tienen beneficio tributario de hasta el 15% de lo ahorrado.",
        "category": "Impuestos",
        "day_of_week": 3,
    },
    {
        "title": "Compara antes de Endeudarte",
        "text": "Antes de pedir un crédito de consumo, compara la Carga Anual Equivalente (CAE) entre bancos. Una diferencia de 5 puntos porcentuales en un crédito de $5.000.000 a 3 años puede significar más de $500.000 CLP de diferencia en intereses.",
        "category": "Créditos",
        "day_of_week": 4,
    },
    {
        "title": "Inversión desde $1.000",
        "text": "Hoy en día puedes invertir en fondos mutuos desde montos muy bajos. Aplicaciones como Fintual o Tyba permiten empezar con $1.000 CLP. Invertir consistentemente es más importante que el monto inicial.",
        "category": "Inversiones",
        "day_of_week": 5,
    },
    {
        "title": "Presupuesto 50/30/20",
        "text": "Una regla simple: destina el 50% de tus ingresos a necesidades (arriendo, comida, cuentas), 30% a gustos (salidas, ropa, ocio) y 20% a ahorro e inversión. Ajústala según tu realidad, pero el 20% de ahorro no es negociable.",
        "category": "Ahorro",
        "day_of_week": 6,
    },
]

# ────────────────────────────────────────────────────────────────
# Default Financial Planning Tips (6 tips)
# ────────────────────────────────────────────────────────────────

DEFAULT_PLANNING_TIPS = [
    {
        "title": "Fondo de Emergencia",
        "description": "Construye un colchón financiero que cubra 3 a 6 meses de tus gastos fijos. Esto te protege ante imprevistos como perder el trabajo o una emergencia médica.",
        "icon": "shield",
        "category": "emergencia",
        "keyPoints": [
            "Guarda 3-6 meses de gastos básicos",
            "Mantenlo en una cuenta separada y de fácil acceso",
            "No lo uses para gastos planificados, solo emergencias reales",
        ],
        "actionItems": [
            "Calcula tus gastos mensuales totales",
            "Abre una cuenta de ahorro separada",
            "Automatiza un depósito mensual del 10% de tu sueldo",
        ],
        "resources": [],
    },
    {
        "title": "Metas Financieras SMART",
        "description": "Define metas específicas, medibles, alcanzables, relevantes y con plazo definido para darle dirección a tu dinero.",
        "icon": "target",
        "category": "metas",
        "keyPoints": [
            "Las metas sin plazo son solo deseos",
            "Divide tus metas en corto, mediano y largo plazo",
            "Revisa tu avance cada mes",
        ],
        "actionItems": [
            "Escribe 3 metas financieras para este año",
            "Asigna un monto y fecha a cada una",
            "Crea una cuenta de ahorro por cada meta",
        ],
        "resources": [],
    },
    {
        "title": "Estrategia para Pagar Deudas",
        "description": "Usa el método 'bola de nieve' o ' avalancha' para salir de deudas más rápido y pagar menos intereses.",
        "icon": "trending-up",
        "category": "deudas",
        "keyPoints": [
            "Paga primero las deudas con mayor interés (avalancha)",
            "O paga las más pequeñas primero para motivarte (bola de nieve)",
            "Nunca hagas el mínimo en tus tarjetas de crédito",
        ],
        "actionItems": [
            "Lista todas tus deudas con montos e intereses",
            "Elige un método (avalancha o bola de nieve)",
            "Destina un 20% extra de tu presupuesto a pagar deudas",
        ],
        "resources": [],
    },
    {
        "title": "Ahorro Previsional Voluntario (APV)",
        "description": "El APV te permite ahorrar para tu jubilación con beneficios tributarios. El Estado aporta hasta un 15% adicional de lo que ahorres.",
        "icon": "calendar",
        "category": "retiro",
        "keyPoints": [
            "Beneficio tributario de hasta 15% del Estado",
            "Puedes retirar el dinero antes de jubilar con algunas restricciones",
            "Elige entre APV A o APV B según tu perfil",
        ],
        "actionItems": [
            "Consulta en tu AFP el monto máximo de APV",
            "Compara las alternativas APV A y APV B",
            "Empieza con un monto pequeño y ve aumentando",
        ],
        "resources": [],
    },
    {
        "title": "Hábitos de Ahorro Automático",
        "description": "La mejor forma de ahorrar es automatizarlo. Si no ves el dinero, no lo gastas.",
        "icon": "piggybank",
        "category": "habitos",
        "keyPoints": [
            "Automatiza un traspaso el día después de tu sueldo",
            "Empieza con un 5% y aumenta gradualmente",
            "Revisa y ajusta cada 3 meses",
        ],
        "actionItems": [
            "Configura una transferencia automática el día 1 de cada mes",
            "Empieza con el 5% de tu ingreso",
            "Aumenta un 1% cada mes hasta llegar al 20%",
        ],
        "resources": [],
    },
    {
        "title": "Presupuesto 50/30/20",
        "description": "Distribuye tus ingresos en tres categorías para tener claridad financiera sin complicarte.",
        "icon": "wallet",
        "category": "presupuesto",
        "keyPoints": [
            "50% para necesidades (arriendo, cuentas, comida)",
            "30% para deseos (ocio, viajes, gustos)",
            "20% para ahorro e inversión",
        ],
        "actionItems": [
            "Calcula tus porcentajes actuales",
            "Ajusta tus gastos para acercarte a la regla",
            "Usa una app de presupuesto mensual",
        ],
        "resources": [],
    },
]

# ────────────────────────────────────────────────────────────────
# Default Educational Modules (2 modules)
# ────────────────────────────────────────────────────────────────

DEFAULT_MODULES = [
    {
        "id": "mod-ahorro-inteligente",
        "slug": "ahorro-inteligente",
        "title": "Ahorro Inteligente",
        "description": "Aprende a ahorrar de forma efectiva con métodos probados y crea el hábito del ahorro.",
        "level": "Principiante",
        "estimatedTimeMinutes": 15,
        "category": "Finanzas Personales",
        "tags": ["ahorro", "principiante", "metas"],
        "topicsCount": 2,
        "createdAt": "2026-01-01T00:00:00Z",
        "learningObjectives": [
            "Entender la importancia del ahorro sistemático",
            "Aplicar la regla 50/30/20",
            "Crear un fondo de emergencia",
        ],
        "content": {
            "introduction": "El ahorro es la base de toda salud financiera. Sin importar cuánto ganes, todos podemos ahorrar si tenemos la estrategia correcta.",
            "sections": [
                {
                    "id": "sec-1",
                    "title": "¿Por qué ahorrar?",
                    "content": "Ahorrar no es guardar 'lo que sobra', sino apartar primero un porcentaje de tus ingresos. La mayoría de las personas ahorran al revés: gastan primero y ahorran lo que queda. El truco es pagarte a ti primero. Si ganas $500.000 CLP mensuales y ahorras el 10%, en un año tendrás $600.000 CLP sin apenas sentirlo.",
                },
                {
                    "id": "sec-2",
                    "title": "La Regla 50/30/20",
                    "content": "Distribuye tu sueldo así: 50% para necesidades básicas (arriendo, cuentas, comida, transporte), 30% para gustos (salidas, ropa, ocio) y 20% para ahorro e inversión. Esta regla es flexible: si tus necesidades son el 60%, ajusta los gustos al 20% y mantén el 20% de ahorro.",
                },
                {
                    "id": "sec-3",
                    "title": "Fondo de Emergencia",
                    "content": "Tu primera meta debe ser ahorrar 3 meses de gastos básicos. En Chile, el gasto promedio mensual es de $450.000 CLP, así que tu meta serían $1.350.000 CLP. Guarda este dinero en una cuenta separada y no la toques salvo que sea una emergencia real.",
                },
            ],
            "practicalTips": [
                "Abre una cuenta de ahorro automático que se active el día de tu sueldo",
                "Usa la técnica de 'ahorrar las monedas': guarda todas las monedas de $500 y $100",
                "Revisa tus suscripciones: Spotify, Netflix, etc. ¿Usas todas?",
            ],
        },
        "topics": [{"id": "t-1", "name": "Ahorro"}, {"id": "t-2", "name": "Presupuesto"}],
        "quiz": {
            "id": "q-ahorro",
            "title": "Evaluación: Ahorro Inteligente",
            "questionsCount": 3,
            "passingScore": 60,
            "questions": [
                {
                    "id": "qa-1",
                    "type": "multiple_choice",
                    "question": "Según la regla 50/30/20, ¿qué porcentaje de tus ingresos deberías destinar al ahorro?",
                    "options": ["10%", "20%", "30%", "50%"],
                    "explanation": "El 20% de tus ingresos debe ir al ahorro e inversión según la regla 50/30/20.",
                    "correctAnswer": 1,
                },
                {
                    "id": "qa-2",
                    "type": "true_false",
                    "question": "El fondo de emergencia debe cubrir al menos 1 mes de gastos.",
                    "options": ["Verdadero", "Falso"],
                    "explanation": "Debe cubrir al menos 3 meses, idealmente 6 meses de gastos básicos.",
                    "correctAnswer": 1,
                },
                {
                    "id": "qa-3",
                    "type": "multiple_choice",
                    "question": "¿Cuál es la mejor estrategia para empezar a ahorrar?",
                    "options": ["Gastar primero y ahorrar lo que sobra", "Ahorrar primero al recibir tu sueldo", "Esperar a tener un mejor sueldo", "Invertir antes de ahorrar"],
                    "explanation": "La clave es 'pagarte a ti mismo primero': ahorrar en cuanto recibes tu sueldo.",
                    "correctAnswer": 1,
                },
            ],
        },
    },
    {
        "id": "mod-creditos-responsables",
        "slug": "creditos-responsables",
        "title": "Créditos Responsables",
        "description": "Entiende cómo funcionan los créditos en Chile y aprende a usarlos sin caer en sobreendeudamiento.",
        "level": "Intermedio",
        "estimatedTimeMinutes": 20,
        "category": "Créditos",
        "tags": ["creditos", "deudas", "intermedio", "cae"],
        "topicsCount": 2,
        "createdAt": "2026-01-01T00:00:00Z",
        "learningObjectives": [
            "Diferenciar entre crédito responsable y sobreendeudamiento",
            "Calcular el costo total de un crédito",
            "Leer y entender una tabla de amortización",
        ],
        "content": {
            "introduction": "Los créditos no son malos si se usan con inteligencia. Una deuda bien tomada puede ser una herramienta para alcanzar metas; una deuda mal tomada puede convertirse en una pesadilla financiera.",
            "sections": [
                {
                    "id": "sec-1",
                    "title": "CAE vs. Interés Nominal",
                    "content": "La Carga Anual Equivalente (CAE) incluye todos los costos del crédito: intereses, comisiones y seguros. El interés nominal solo muestra una parte. Siempre compara la CAE entre distintas instituciones. En Chile, la CAE de un crédito de consumo puede variar entre 15% y 40% dependiendo del banco y tu historial.",
                },
                {
                    "id": "sec-2",
                    "title": "Tabla de Amortización",
                    "content": "En un crédito en UF con cuota fija, al principio pagas más intereses que capital. Recién después de la mitad del plazo empiezas a pagar más capital que intereses. Esto significa que si pagas tu crédito antes, ahorras una cantidad significativa de intereses futuros.",
                },
                {
                    "id": "sec-3",
                    "title": "La Regla del 30%",
                    "content": "Tus cuotas mensuales totales (incluyendo dividendo, tarjetas, créditos) no deberían superar el 30% de tus ingresos mensuales. Si ganas $700.000 CLP, el máximo recomendado de cuotas es $210.000 CLP mensuales. Superar este límite te pone en riesgo de sobreendeudamiento.",
                },
            ],
            "practicalTips": [
                "Usa el simulador de CMF (Comisión para el Mercado Financiero) para comparar créditos",
                "Paga más del mínimo en tus tarjetas de crédito para reducir intereses",
                "Si tienes varias deudas, consolídalas en un solo crédito con menor tasa",
            ],
        },
        "topics": [{"id": "t-3", "name": "Créditos"}, {"id": "t-4", "name": "Deudas"}],
        "quiz": {
            "id": "q-creditos",
            "title": "Evaluación: Créditos Responsables",
            "questionsCount": 3,
            "passingScore": 60,
            "questions": [
                {
                    "id": "qc-1",
                    "type": "multiple_choice",
                    "question": "¿Qué significa CAE?",
                    "options": ["Costo Anual Efectivo", "Carga Anual Equivalente", "Cuota Anual Especial", "Capital Ajustado por Interés"],
                    "explanation": "La CAE (Carga Anual Equivalente) incluye todos los costos del crédito.",
                    "correctAnswer": 1,
                },
                {
                    "id": "qc-2",
                    "type": "true_false",
                    "question": "Solo debes considerar la tasa de interés al comparar créditos.",
                    "options": ["Verdadero", "Falso"],
                    "explanation": "Debes considerar la CAE que incluye intereses, comisiones, seguros y otros costos.",
                    "correctAnswer": 1,
                },
                {
                    "id": "qc-3",
                    "type": "multiple_choice",
                    "question": "¿Qué porcentaje máximo de tus ingresos deberían ser tus cuotas mensuales?",
                    "options": ["50%", "40%", "30%", "20%"],
                    "explanation": "La regla del 30%: tus cuotas no deben superar el 30% de tus ingresos mensuales.",
                    "correctAnswer": 2,
                },
            ],
        },
    },
]

# ────────────────────────────────────────────────────────────────
# Default News (5 pre-written financial news)
# ────────────────────────────────────────────────────────────────

DEFAULT_NEWS = [
    {
        "title": "IPC de Abril: Inflación en Chile baja al 3.5% anual",
        "summary": "El Índice de Precios al Consumidor (IPC) registró una variación mensual del 0.2% en abril, ubicando la inflación anual en 3.5%, la más baja en los últimos 24 meses.",
        "content_text": "El Instituto Nacional de Estadísticas (INE) informó que el IPC de abril mostró una variación mensual del 0.2%, por debajo de las expectativas del mercado. Esto se explica principalmente por la baja en los precios de combustibles y alimentos. Los analistas proyectan que el Banco Central podría recortar la tasa de interés en los próximos meses, lo que beneficiaría a quienes tienen créditos en UF.",
        "source_url": "https://www.ine.cl/",
        "published_at": datetime(2026, 5, 8, 10, 0),
        "impact_level": "alto",
        "affects": "todos",
        "target_audience": "general",
        "tags": ["IPC", "Inflación", "Chile"],
    },
    {
        "title": "Banco Central mantiene tasa de interés en 5%",
        "summary": "El Banco Central de Chile decidió mantener la Tasa de Política Monetaria (TPM) en 5%, señalando que la inflación sigue dentro del rango meta pero las perspectivas económicas globales son inciertas.",
        "content_text": "En su reunión mensual, el Consejo del Banco Central decidió por unanimidad mantener la tasa de interés en 5%. La decisión se basa en que la inflación interanual se encuentra dentro del rango meta del 3-4%, aunque las presiones inflacionarias externas y la incertidumbre global recomendaron prudencia. Esta tasa afecta directamente a los créditos de consumo e hipotecarios.",
        "source_url": "https://www.bcentral.cl/",
        "published_at": datetime(2026, 5, 15, 14, 30),
        "impact_level": "medio",
        "affects": "deudores",
        "target_audience": "personas con créditos",
        "tags": ["Banco Central", "TPM", "Tasa de interés"],
    },
    {
        "title": "Precio del dólar sube a $950 tras anuncio de aranceles en EE.UU.",
        "summary": "El dólar estadounidense alcanzó los $950 CLP, su nivel más alto en el año, luego de que la administración Trump anunciara nuevos aranceles a productos chinos.",
        "content_text": "El tipo de cambio subió $25 pesos en una sola jornada, alcanzando los $950 CLP por dólar. Esto afecta directamente el precio de los combustibles, los productos importados (electrónicos, ropa, autos) y los viajes al extranjero. Para quienes reciben remesas desde el extranjero, el tipo de cambio alto es beneficioso. Se recomienda a quienes tengan deudas en dólares cubrirse ante nuevas alzas.",
        "source_url": "https://www.sii.cl/",
        "published_at": datetime(2026, 5, 20, 9, 15),
        "impact_level": "alto",
        "affects": "importadores y viajeros",
        "target_audience": "general",
        "tags": ["Dólar", "Tipo de cambio", "Importaciones"],
    },
    {
        "title": "Nuevo subsidio DS-1: Postulaciones abiertas para vivienda",
        "summary": "El Ministerio de Vivienda abrió las postulaciones al subsidio DS-1 para familias que quieran comprar su primera vivienda, con montos de hasta 1.100 UF.",
        "content_text": "El Fondo Solidario de Elección de Vivienda (DS-1) está disponible para familias con ahorro previo de mínimo 30 UF (aproximadamente $1.000.000 CLP). El subsidio puede financiar viviendas de hasta 1.100 UF (unos $37 millones CLP). Los interesados deben postular en línea a través del sitio del MINVU. El plazo de postulación vence el 30 de junio.",
        "source_url": "https://www.minvu.cl/",
        "published_at": datetime(2026, 5, 22, 11, 0),
        "impact_level": "alto",
        "affects": "familias que buscan vivienda",
        "target_audience": "jóvenes y familias",
        "tags": ["Vivienda", "Subsidio", "DS-1"],
    },
    {
        "title": "Isapres: Nueva tabla de factores de riesgo para 2026",
        "summary": "La Superintendencia de Salud aprobó las nuevas tablas de factores de riesgo para las Isapres, que regirán a partir de julio de 2026.",
        "content_text": "Las nuevas tablas de factores de riesgo consideran principalmente la edad y el sexo de los beneficiarios. Según la Superintendencia de Salud, el 70% de los cotizantes mantendrá o verá reducido su plan, mientras que el 30% podría experimentar alzas. Se recomienda revisar el detalle en la página de la Superintendencia y, de ser necesario, cambiarse de Isapre durante el período de adecuación.",
        "source_url": "https://www.supersalud.cl/",
        "published_at": datetime(2026, 5, 25, 16, 0),
        "impact_level": "alto",
        "affects": "cotizantes de Isapres",
        "target_audience": "trabajadores con Isapre",
        "tags": ["Isapres", "Salud", "Factor de riesgo"],
    },
]


def seed_daily_tips(db) -> int:
    """Seed default daily tips if none exist."""
    existing = db.query(DailyTip).filter(DailyTip.is_active == True).count()
    if existing > 0:
        return 0

    now = datetime.utcnow()
    for data in DEFAULT_TIPS:
        tip = DailyTip(
            daily_tip_id=uuid.uuid4(),
            title=data["title"],
            text=data["text"],
            category=data["category"],
            day_of_week=data["day_of_week"],
            generated_at=now,
            is_active=True,
        )
        db.add(tip)
    db.flush()
    logger.info("Seeded %d daily tips", len(DEFAULT_TIPS))
    return len(DEFAULT_TIPS)


def seed_financial_planning(db) -> int:
    """Seed default financial planning tips if none exist."""
    existing = db.query(FinancialPlanningTip).filter(
        FinancialPlanningTip.is_active == True
    ).count()
    if existing > 0:
        return 0

    now = datetime.utcnow()
    for data in DEFAULT_PLANNING_TIPS:
        tip = FinancialPlanningTip(
            planning_tip_id=uuid.uuid4(),
            title=data["title"],
            description=data["description"],
            icon=data["icon"],
            category=data["category"],
            key_points=data["keyPoints"],
            action_items=data["actionItems"],
            resources=data["resources"],
            generated_at=now,
            is_active=True,
        )
        db.add(tip)
    db.flush()
    logger.info("Seeded %d financial planning tips", len(DEFAULT_PLANNING_TIPS))
    return len(DEFAULT_PLANNING_TIPS)


def seed_educational_modules(db) -> int:
    """Seed default educational modules if none exist."""
    existing = db.query(EducationalModule).count()
    if existing > 0:
        return 0

    for mod_data in DEFAULT_MODULES:
        module = EducationalModule(
            educational_module_id=uuid.uuid4(),
            title=mod_data["title"],
            description=mod_data["description"],
            content=json.dumps(mod_data, ensure_ascii=False),
            duration=mod_data["estimatedTimeMinutes"],
            difficulty=mod_data["level"],
        )
        db.add(module)
    db.flush()
    logger.info("Seeded %d educational modules", len(DEFAULT_MODULES))
    return len(DEFAULT_MODULES)


def seed_news_tags(db) -> dict[str, uuid.UUID]:
    """Ensure common news tags exist, return {name: id} map."""
    from sqlalchemy.exc import IntegrityError

    tag_names = [
        "IPC", "Inflación", "Chile", "Banco Central", "TPM",
        "Tasa de interés", "Dólar", "Tipo de cambio", "Importaciones",
        "Vivienda", "Subsidio", "DS-1", "Isapres", "Salud", "Factor de riesgo",
    ]

    tag_map = {}
    for name in tag_names:
        existing = db.query(NewsTag).filter(NewsTag.name == name).first()
        if existing:
            tag_map[name] = existing.tag_id
        else:
            tag_id = uuid.uuid4()
            db.add(NewsTag(tag_id=tag_id, name=name, description=f"Noticias sobre {name.lower()}"))
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                real = db.query(NewsTag).filter(NewsTag.name == name).one()
                tag_map[name] = real.tag_id
                continue
            tag_map[name] = tag_id

    return tag_map


def seed_news(db) -> int:
    """Seed default news articles if none exist."""
    existing = db.query(News).count()
    if existing > 0:
        return 0

    tag_map = seed_news_tags(db)

    for news_data in DEFAULT_NEWS:
        tags = news_data.pop("tags", [])
        news_id = uuid.uuid4()
        news = News(
            news_id=news_id,
            title=news_data["title"],
            summary=news_data["summary"],
            content_text=news_data["content_text"],
            source_url=news_data["source_url"],
            image_url=None,
            published_at=news_data["published_at"],
            impact_level=news_data["impact_level"],
            affects=news_data["affects"],
            target_audience=news_data["target_audience"],
        )
        db.add(news)

        for tag_name in tags:
            tag_id = tag_map.get(tag_name)
            if tag_id:
                db.add(NewsTagMap(news_id=news_id, tag_id=tag_id))

    db.flush()
    logger.info("Seeded %d news articles", len(DEFAULT_NEWS))
    return len(DEFAULT_NEWS)


def seed_all_defaults() -> dict[str, int]:
    """Run all seeders independently. Returns dict of {entity: count_seeded}."""
    counts = {}
    for seeder_name, seeder_fn in [
        ("daily_tips", seed_daily_tips),
        ("financial_planning", seed_financial_planning),
        ("educational_modules", seed_educational_modules),
        ("news", seed_news),
    ]:
        db = SessionLocal()
        try:
            count = seeder_fn(db)
            db.commit()
            counts[seeder_name] = count
        except Exception:
            db.rollback()
            logger.exception("Failed to seed %s", seeder_name)
        finally:
            db.close()

    seeded = {k: v for k, v in counts.items() if v > 0}
    if seeded:
        logger.info("Default data seeded: %s", seeded)
    else:
        logger.info("Default data already exists, skipping")
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_all_defaults()
