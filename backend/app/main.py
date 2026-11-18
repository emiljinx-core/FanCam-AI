from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routes import router as api_router, health_check
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure storage directories exist at startup
    settings.init_directories()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file mounts:
# Expose ONLY public outputs and previews for frontend presentation.
# Source uploads remain unmounted and private on the backend filesystem.
settings.init_directories()

app.mount(
    "/static/outputs",
    StaticFiles(directory=str(settings.OUTPUTS_DIR)),
    name="outputs",
)
app.mount(
    "/static/previews",
    StaticFiles(directory=str(settings.PREVIEWS_DIR)),
    name="previews",
)

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }

@app.get("/health", include_in_schema=False)
async def root_health_check():
    return await health_check()