from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging

def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    web_dir = Path(__file__).parent / "web"

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Local enterprise financial RAG assistant.",
    )
    register_exception_handlers(app)
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.get("/")
    async def root() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    app.include_router(router, prefix="/api/v1")
    return app

app = create_app()
