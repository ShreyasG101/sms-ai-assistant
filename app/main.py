"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.database import init_db
from app.routes import health, sms

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan - initialize on startup."""
    logger.info("Starting SMS AI Assistant...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down SMS AI Assistant...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="SMS AI Assistant",
        description="Self-hosted AI assistant accessible via SMS",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Register routes
    app.include_router(health.router)
    app.include_router(sms.router)

    logger.info(f"App configured with AI provider: {settings.ai_provider}")
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
