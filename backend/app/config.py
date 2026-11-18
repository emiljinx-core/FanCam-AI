import shutil
import sys
from pathlib import Path

from pydantic_settings import BaseSettings


def _default_ffmpeg_path() -> str:
    """Resolve FFmpeg from PATH or the active Python/Conda environment."""
    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path

    env = Path(sys.base_prefix)
    candidates = [
        env / "Library" / "bin" / "ffmpeg.exe",  # Windows (Conda)
        env / "bin" / "ffmpeg",  # Linux/macOS
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return "ffmpeg"  # Let subprocess resolve via PATH


class Settings(BaseSettings):
    PROJECT_NAME: str = "FanCam Backend API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"

    # Base directory resolves strictly relative to backend root
    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    # Storage paths
    STORAGE_DIR: Path = BASE_DIR / "storage"
    UPLOADS_DIR: Path = STORAGE_DIR / "uploads"
    OUTPUTS_DIR: Path = STORAGE_DIR / "outputs"
    PREVIEWS_DIR: Path = STORAGE_DIR / "previews"
    MODELS_DIR: Path = BASE_DIR / "weights"

    # Constraint configs
    MAX_UPLOAD_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB strict limit
    ALLOWED_EXTENSIONS: set = {".mp4", ".mov"}

    # Detection Configs
    YOLO_MODEL_NAME: str = "yolov8n.pt"
    DETECTION_CONF_THRESHOLD: float = 0.35
    FORCE_CPU: bool = False  # Allows overriding CUDA if needed

    # FFmpeg executable path
    FFMPEG_PATH: str = _default_ffmpeg_path()

    # Contact form email delivery (Resend)
    RESEND_API_KEY: str = ""
    CONTACT_EMAIL_TO: str = ""
    CONTACT_EMAIL_FROM: str = "onboarding@resend.dev"

    # CORS origins
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    def init_directories(self) -> None:
        """Create storage directories if they do not already exist."""
        for directory in [
            self.STORAGE_DIR,
            self.UPLOADS_DIR,
            self.OUTPUTS_DIR,
            self.PREVIEWS_DIR,
            self.MODELS_DIR,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
