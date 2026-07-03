# ChauchaApp — Backend

API REST para ChauchaApp, una aplicación de educación financiera personal orientada a usuarios chilenos. Permite registrar ingresos y gastos, analizar noticias económicas según el perfil financiero del usuario, recibir tips diarios y acceder a módulos de aprendizaje generados por IA.

Construido con **FastAPI + PostgreSQL + agentes de IA** (Agno, NVIDIA LLaMA 3.3, Tavily).

---

## Qué hace la aplicación

- **Finanzas personales** — Registro de transacciones (ingresos y gastos) con tipos de transacción e ingresos configurables
- **Noticias analizadas por IA** — Obtiene noticias desde RSS chilenos y las analiza contra el perfil financiero de cada usuario, indicando impacto personal y recomendaciones concretas
- **Tips financieros diarios** — Un agente de IA genera batches semanales de tips adaptados a categorías financieras relevantes
- **Módulos de aprendizaje** — Contenido educativo generado dinámicamente por IA, con seguimiento de progreso por sección y quizzes de evaluación
- **Grupos familiares** — Sistema de invitaciones para compartir la gestión financiera con otros miembros de la familia
- **Planificación financiera** — Recomendaciones basadas en los ingresos y gastos declarados por el usuario
- **Notificaciones** — Sistema de notificaciones internas por eventos (invitaciones, logros, cambios de estado)

---

## Stack tecnológico

| Capa                   | Tecnología                       |
| ---------------------- | -------------------------------- |
| Framework web          | FastAPI + Uvicorn                |
| Lenguaje               | Python 3.12                      |
| Base de datos          | PostgreSQL 16                    |
| ORM                    | SQLAlchemy 2.0                   |
| Migraciones            | Alembic                          |
| Validación de datos    | Pydantic v2                      |
| Autenticación          | JWT (PyJWT) + bcrypt             |
| Agentes de IA          | Agno + NVIDIA LLaMA 3.3 Nemotron |
| Búsqueda web           | Tavily + DuckDuckGo Search       |
| Feeds de noticias      | feedparser (RSS)                 |
| Contenedores           | Docker + Docker Compose          |
| CI/CD                  | GitHub Actions → VPS             |
| Gestor de dependencias | uv                               |

---

## Arquitectura

El proyecto sigue una arquitectura modular por feature. Cada módulo es autónomo y contiene su propia capa HTTP, lógica de negocio, acceso a datos y schemas de validación.

```
main.py                        ← Entrypoint: app, routers, CORS, handlers de excepciones
app/
├── modules/                   ← Feature modules
│   └── <feature>/
│       ├── controller.py      ← Capa HTTP (rutas FastAPI, sin lógica de negocio)
│       ├── service.py         ← Lógica de negocio
│       ├── repository.py      ← Queries a la base de datos
│       ├── dto.py             ← Schemas Pydantic (request/response)
│       ├── entities.py        ← Modelos SQLAlchemy (ORM)
│       └── exceptions.py      ← Errores específicos del módulo (opcional)
├── agent/                     ← Agentes de IA
│   ├── news_agent.py
│   ├── daily_tips_agent.py
│   ├── financial_agent/
│   └── quizzes/
├── shared/                    ← Utilidades transversales
│   ├── database.py            ← Engine, SessionLocal, Base declarativa
│   ├── exceptions.py          ← Jerarquía AppException → códigos HTTP
│   ├── background.py          ← Task manager para operaciones de larga duración
│   ├── base_entity.py         ← AuditMixin (created_at, updated_at, created_by, updated_by)
│   └── security/              ← JWT, bcrypt, middleware de autenticación
└── external_apis/             ← Integraciones con APIs externas
```

### Manejo de excepciones

Todos los módulos lanzan subclases de `AppException(code, message)`. El handler global en `main.py` traduce el campo `code` al status HTTP correspondiente:

| Código             | HTTP |
| ------------------ | ---- |
| `VALIDATION_ERROR` | 400  |
| `UNAUTHORIZED`     | 401  |
| `FORBIDDEN`        | 403  |
| `NOT_FOUND`        | 404  |
| `CONFLICT`         | 409  |
| Cualquier otro     | 500  |

---

## Módulos de la API

| Módulo         | Prefijo de ruta          | Descripción                                |
| -------------- | ------------------------ | ------------------------------------------ |
| auth           | `/v1/auth`               | Registro, login, logout, refresh de token  |
| users          | `/v1/users`              | Perfil de usuario y preferencias de temas  |
| transactions   | `/v1/transactions`       | CRUD de transacciones, tipos e ingresos    |
| news           | `/v1/news`               | Noticias financieras analizadas por IA     |
| daily_tips     | `/tips`                  | Tips financieros diarios y semanales       |
| education      | `/v1/education`          | Módulos de aprendizaje, progreso y quizzes |
| financial_data | `/v1/financial-planning` | Planificación y resumen financiero         |
| groups         | `/v1/family-group`       | Grupos familiares e invitaciones           |
| notifications  | `/v1/notifications`      | Notificaciones internas del sistema        |

La documentación interactiva completa (Swagger UI) está disponible en `/docs` una vez levantado el servidor.

---

## Inicio rápido

### Requisitos

- Python 3.12+
- PostgreSQL 16
- [`uv`](https://github.com/astral-sh/uv) (gestor de dependencias)
- Docker y Docker Compose (recomendado para desarrollo)

### Con Docker (recomendado)

```bash
# 1. Copiar y configurar variables de entorno
cp .env.example .env
# Editar .env y completar NVIDIA_API_KEY, TAVILY_API_KEY y las claves JWT

# 2. Levantar base de datos + aplicación
docker compose --profile development up
```

La API queda disponible en `http://localhost:8000`.
La documentación Swagger en `http://localhost:8000/docs`.

### Sin Docker

```bash
# Instalar dependencias
uv pip install -r requirements.txt

# Levantar servidor con recarga automática
uvicorn main:app --reload
```

> Requiere una instancia de PostgreSQL corriendo y la variable `DATABASE_URL` configurada en `.env`.

---

## Variables de entorno

Crear un archivo `.env` en la raíz del proyecto basándose en `.env.example`:

```env
# Base de datos
DATABASE_URL=postgresql://postgres:password@localhost:5432/chauchaapp_db

# Seguridad
JWT_SECRET=tu_secreto_aqui
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30
SECRET_KEY=otro_secreto_aqui

# APIs externas (requeridas para que los agentes de IA funcionen)
NVIDIA_API_KEY=tu_clave_nvidia
TAVILY_API_KEY=tu_clave_tavily

# Servidor
DEBUG=true
PORT=8000
HOST=0.0.0.0
CORS_ORIGINS=http://localhost:8081,http://localhost:3000
```

---

## Testing

El proyecto separa los tests en tres niveles para no mezclar velocidades:

```bash
# Suite rápida: unitarios e integración (sin APIs externas, sin PostgreSQL real)
pytest tests/unit tests/integration

# Con reporte de cobertura
pytest --cov=app tests/unit tests/integration

# Tests funcionales reales (llaman APIs de NVIDIA y Tavily, pueden tardar varios minutos)
pytest tests/functional_real/
```

> **No ejecutar `pytest tests/` directamente.** Los tests en `tests/functional_real/` requieren API keys válidas y pueden tardar entre 5 y 15 minutos por test.

Los tests rápidos usan SQLite en memoria como base de datos y un `MagicMock` como sesión de SQLAlchemy, por lo que no requieren ninguna base de datos corriendo.

---

## Agentes de IA y background tasks

Las operaciones de IA pueden tardar desde varios segundos hasta minutos, dependiendo del modelo y la complejidad del prompt. Para no dejar las peticiones HTTP colgadas, se implementó un sistema de tareas en background:

1. El cliente hace `POST` al endpoint correspondiente → recibe un `task_id` inmediatamente
2. El agente corre en un hilo separado
3. El cliente consulta periódicamente `GET /tasks/{task_id}` hasta que el estado sea `completed` o `failed`

**Agentes disponibles:**

- **`news_agent`** — Obtiene noticias desde fuentes RSS chilenas verificadas y las analiza con NVIDIA LLaMA 3.3 Nemotron, generando resumen, análisis de impacto personal y recomendación concreta para cada usuario
- **`daily_tips_agent`** — Genera un lote de 7 tips financieros semanales usando Agno + Tavily para búsqueda de contexto actualizado
- **`financial_agent`** — Genera un análisis de planificación financiera personalizado según el perfil del usuario
- **`quizz_agent`** — Genera preguntas de evaluación para los módulos de educación financiera

---

## Despliegue

El despliegue es continuo: cada push a la rama `develop` activa el workflow en `.github/workflows/deploy.yml`, que conecta al VPS por SSH y reconstruye los contenedores en modo producción.

Docker Compose maneja tres perfiles independientes:

| Perfil        | Puerto | Base de datos        |
| ------------- | ------ | -------------------- |
| `development` | 8000   | `chauchaapp_db`      |
| `qa`          | 8001   | `chauchaapp_db_qa`   |
| `production`  | 8002   | `chauchaapp_db_prod` |

```bash
# Levantar en modo desarrollo
docker compose --profile development up

# Levantar en modo QA
docker compose --profile qa up

# Levantar en modo producción
docker compose --profile production up
```

Para instrucciones de configuración inicial del servidor (SSH keys, permisos, Docker, GitHub Secrets), ver [`VPS-SETUP-GUIDE.md`](./VPS-SETUP-GUIDE.md).

---

## Estructura de carpetas completa

```
chauchaapp-backend/
├── app/
│   ├── agent/
│   │   ├── daily_tips_agent.py
│   │   ├── financial_agent/
│   │   ├── news_agent.py
│   │   └── quizzes/
│   ├── external_apis/
│   ├── modules/
│   │   ├── auth/
│   │   ├── daily_tips/
│   │   ├── education/
│   │   ├── financial_data/
│   │   ├── groups/
│   │   ├── news/
│   │   ├── notifications/
│   │   ├── quizzes/
│   │   ├── transactions/
│   │   └── users/
│   └── shared/
│       ├── background.py
│       ├── background_dto.py
│       ├── base_entity.py
│       ├── database.py
│       ├── exceptions.py
│       └── security/
├── scripts/
│   ├── schema.sql
│   ├── seed_defaults.py
│   └── seed_qa.py
├── tests/
│   ├── functional_real/
│   ├── integration/
│   └── unit/
├── alembic/
├── docker-compose.yml
├── Dockerfile
├── main.py
├── requirements.txt
└── .env.example
```
