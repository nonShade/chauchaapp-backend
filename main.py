"""
ChauchaApp Backend API.

FastAPI application with authentication endpoints,
CORS middleware, and global exception handlers.
"""

from app.shared.exceptions import AppException
from app.modules.users.controller import router as users_router
from app.modules.groups.controller import router as groups_router
from app.modules.daily_tips.controller import router as daily_tips_router
from app.modules.transactions.controller import router as transactions_router
from app.modules.news.controller import router as news_router
from app.modules.financial_data.controller import router as financial_planning_router
from app.modules.auth.controller import router as auth_router
from app.modules.groups.controller import router as groups_router
from app.modules.notifications.controller import router as notifications_router
from app.modules.education.controller import router as education_router
from app.modules.financial_data.controller import router as financial_planning_router
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()


app = FastAPI(
    title="ChauchaApp API",
    description="API Backend for ChauchaApp — financial literacy platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
cors_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:8081,http://localhost:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(transactions_router)
app.include_router(news_router)
app.include_router(financial_planning_router)
app.include_router(daily_tips_router)
app.include_router(groups_router)
app.include_router(users_router)
app.include_router(groups_router)
app.include_router(notifications_router)
app.include_router(education_router)
app.include_router(financial_planning_router)


# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Map AppException subclasses to appropriate HTTP status codes."""
    status_map = {
        "VALIDATION_ERROR": 400,
        "NOT_FOUND": 404,
        "CONFLICT": 409,
        "UNAUTHORIZED": 401,
        "FORBIDDEN": 403,
        "INTERNAL_ERROR": 500,
    }
    status_code = status_map.get(exc.code, 500)
    return JSONResponse(
        status_code=status_code,
        content={"error": exc.message},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unhandled exceptions."""
    return JSONResponse(
        status_code=500,
        content={"error": "Ocurrió un error interno. Intente más tarde."},
    )


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
