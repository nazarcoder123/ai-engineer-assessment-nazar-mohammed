"""Main FastAPI application exposing the POST /ask endpoint and interactive UI."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.models.request import AskRequest
from app.models.response import AskResponse
from app.services.chatbot_service import ChatbotService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for initialization and cleanup."""
    settings = get_settings()
    logger.info("Starting AI Engineer Chatbot Assessment application...")
    logger.info(f"Dataset path: {settings.absolute_dataset_path}")
    logger.info(f"Resolved LLM Provider: {settings.resolved_llm_provider}")
    logger.info(f"Superhero API configured: {settings.has_superhero_token}")
    logger.info(f"LLM API configured: {settings.has_llm_key}")
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title="AI Engineer Chatbot Assessment",
    description=(
        "Production-oriented FastAPI chatbot that routes questions to a Curated Text Dataset, "
        "the Superhero API, or both, synthesizing answers with a real hosted LLM and explicit source citations."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency Injection for ChatbotService
def get_service(settings: Settings = Depends(get_settings)) -> ChatbotService:
    return ChatbotService(settings=settings)


# Custom Validation Error Handler (Returns clear, structured 422 JSON)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err.get("loc", []))
        errors.append({"field": field, "message": err.get("msg")})
    return JSONResponse(
        status_code=422,
        content={"error": "Validation Error", "details": errors},
    )


# Generic Exception Handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal Server Error", "message": "An unexpected error occurred while processing the request."},
    )


# ------------------------------------------------------------------------------
# Core Assessment Endpoint: POST /ask
# ------------------------------------------------------------------------------
@app.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask a question",
    description="Accepts a natural-language question, routes it to the relevant source (Dataset, Superhero API, or Both), and returns the answer with explicit source attribution.",
    status_code=status.HTTP_200_OK,
)
async def ask_endpoint(
    request: AskRequest,
    service: ChatbotService = Depends(get_service),
) -> AskResponse:
    """Core endpoint required by the technical assessment."""
    try:
        response = await service.answer_question(request)
        return response
    except Exception as e:
        logger.error(f"Error handling /ask request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process question: {str(e)}",
        )


# Health Check
@app.get("/health", summary="Health check endpoint", tags=["Monitoring"])
async def health_check(settings: Settings = Depends(get_settings)):
    return {
        "status": "healthy",
        "superhero_api_configured": settings.has_superhero_token,
        "llm_configured": settings.has_llm_key,
        "active_provider": settings.resolved_llm_provider,
    }


# Static Files and Interactive Web UI
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "AI Engineer Chatbot API is running. Visit /docs for Swagger UI."}
