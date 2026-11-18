from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal


class HealthResponse(BaseModel):
    status: str
    version: str
    message: str
    storage_ready: bool
    device: str
    cuda_available: bool


class UploadResponse(BaseModel):
    video_id: str
    filename: str
    size_bytes: int
    size_mb: float
    message: str


class VideoMetaResponse(BaseModel):
    video_id: str
    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float


class ExtractFrameRequest(BaseModel):
    timestamp_sec: Optional[float] = None
    frame_index: Optional[int] = None


class ExtractFrameResponse(BaseModel):
    video_id: str
    frame_index: int
    timestamp_sec: float
    frame_width: int
    frame_height: int
    preview_url: str


class NormalizedBox(BaseModel):
    top: float
    left: float
    width: float
    height: float


class DetectedPerson(BaseModel):
    id: str
    name: str
    confidence: float
    box: NormalizedBox
    crop_url: str
    role: str = "Subject"


class DetectFrameRequest(BaseModel):
    timestamp_sec: Optional[float] = None
    frame_index: Optional[int] = None
    conf_threshold: Optional[float] = 0.35


class DetectFrameResponse(BaseModel):
    video_id: str
    frame_index: int
    timestamp_sec: float
    frame_width: int
    frame_height: int
    frame_preview_url: str
    detected_people: List[DetectedPerson]
    total_detected: int
    device_used: str


class SelectTargetRequest(BaseModel):
    target_id: str
    crop_url: Optional[str] = None


class SelectTargetResponse(BaseModel):
    video_id: str
    target_id: str
    embedding_dimension: int
    l2_norm: float
    stored_path: str
    message: str


class ProcessVideoRequest(BaseModel):
    video_id: str
    target_id: str
    tracker: Optional[Literal["bytetrack", "deepsort"]] = None
    tracking_algorithm: Optional[Literal["bytetrack", "deepsort"]] = None
    aspect_ratio: Literal["9:16", "1:1", "16:9"] = "9:16"
    smoothing_level: int = Field(default=85, ge=0, le=100)

    def get_algorithm(self) -> str:
        algo = self.tracking_algorithm or self.tracker or "bytetrack"
        return algo


class ProcessVideoResponse(BaseModel):
    task_id: str
    video_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    video_id: str
    target_id: str
    tracker: str
    aspect_ratio: str
    smoothing_level: int
    status: Literal["queued", "processing", "completed", "failed"]
    progress: float
    current_step: str
    output_video_url: Optional[str] = None
    comparison_video_url: Optional[str] = None
    error: Optional[str] = None
    created_at: float
    updated_at: float
    completed_at: Optional[float] = None
