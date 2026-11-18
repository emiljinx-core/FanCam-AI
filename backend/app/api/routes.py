import os
import shutil
import uuid
from pathlib import Path
import cv2
import numpy as np
import torch
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.config import settings
from app.core.video import VideoProcessor
from app.core.detector import PersonDetector
from app.core.reid import OSNetReIDExtractor
from app.core.tasks import TaskManager
from app.core.pipeline import PipelineOrchestrator
from app.core.mailer import EmailDeliveryError, send_contact_email
from app.models.schemas import (
    HealthResponse,
    UploadResponse,
    VideoMetaResponse,
    ExtractFrameRequest,
    ExtractFrameResponse,
    DetectFrameRequest,
    DetectFrameResponse,
    DetectedPerson,
    NormalizedBox,
    SelectTargetRequest,
    SelectTargetResponse,
    ProcessVideoRequest,
    ProcessVideoResponse,
    TaskStatusResponse,
    ContactRequest,
    ContactResponse,
)

router = APIRouter()

VALID_BOX_TYPES = {b"ftyp", b"moov", b"mdat", b"free", b"wide"}
ALLOWED_MIME_TYPES = {"video/mp4", "video/quicktime", "application/octet-stream"}


def is_valid_mp4_or_mov(header_chunk: bytes) -> bool:
    if len(header_chunk) < 8:
        return False
    box_type = header_chunk[4:8]
    return box_type in VALID_BOX_TYPES


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    storage_ok = (
        settings.STORAGE_DIR.exists()
        and settings.UPLOADS_DIR.exists()
        and settings.OUTPUTS_DIR.exists()
        and settings.PREVIEWS_DIR.exists()
    )
    cuda_ok = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_ok else "CPU"

    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        message="FanCam backend is up and running.",
        storage_ready=storage_ok,
        device=device_name,
        cuda_available=cuda_ok,
    )


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Ingestion"],
)
async def upload_video(file: UploadFile = File(...)) -> UploadResponse:
    original_filename = file.filename or "uploaded_video.mp4"
    file_ext = Path(original_filename).suffix.lower()

    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported container. Please provide a valid .mp4 or .mov file.",
        )

    content_type = (file.content_type or "").lower()
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported container. Please provide a valid .mp4 or .mov file.",
        )

    video_id = str(uuid.uuid4())
    video_dir = settings.UPLOADS_DIR / video_id
    video_dir.mkdir(parents=True, exist_ok=True)
    destination_path = video_dir / f"source{file_ext}"

    total_bytes = 0
    chunk_size = 1024 * 1024
    header_checked = False

    try:
        with open(destination_path, "wb") as out_file:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break

                if not header_checked:
                    if not is_valid_mp4_or_mov(chunk):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Unsupported container. Please provide a valid .mp4 or .mov file.",
                        )
                    header_checked = True

                total_bytes += len(chunk)

                if total_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Please upload a file with less than 100 MB.",
                    )

                out_file.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file uploaded. Please provide a valid video.",
            )

    except Exception:
        if destination_path.exists():
            try:
                os.remove(destination_path)
            except OSError:
                pass
        if video_dir.exists():
            try:
                shutil.rmtree(video_dir, ignore_errors=True)
            except OSError:
                pass
        raise
    finally:
        await file.close()

    size_mb = round(total_bytes / (1024 * 1024), 2)

    return UploadResponse(
        video_id=video_id,
        filename=original_filename,
        size_bytes=total_bytes,
        size_mb=size_mb,
        message="Video verified and stored successfully.",
    )


@router.get(
    "/video/{video_id}/meta",
    response_model=VideoMetaResponse,
    tags=["Video Processing"],
)
async def get_video_metadata(video_id: str) -> VideoMetaResponse:
    video_path = VideoProcessor.get_source_path(settings.UPLOADS_DIR, video_id)
    if not video_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video '{video_id}' not found.",
        )

    try:
        meta = VideoProcessor.get_metadata(video_path)
        return VideoMetaResponse(
            video_id=video_id,
            width=meta.width,
            height=meta.height,
            fps=round(meta.fps, 2),
            frame_count=meta.frame_count,
            duration_seconds=round(meta.duration_seconds, 2),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to inspect video: {str(e)}",
        )


@router.post(
    "/video/{video_id}/extract-frame",
    response_model=ExtractFrameResponse,
    tags=["Video Processing"],
)
async def extract_frame(
    video_id: str,
    req: ExtractFrameRequest = ExtractFrameRequest(),
) -> ExtractFrameResponse:
    video_path = VideoProcessor.get_source_path(settings.UPLOADS_DIR, video_id)
    if not video_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video '{video_id}' not found.",
        )

    try:
        frame, frame_idx, actual_timestamp = VideoProcessor.extract_frame(
            video_path=video_path,
            timestamp_sec=req.timestamp_sec,
            frame_index=req.frame_index,
        )

        h, w = frame.shape[:2]
        preview_dir = settings.PREVIEWS_DIR / video_id
        preview_filename = f"frame_{frame_idx}.jpg"
        VideoProcessor.save_frame_preview(frame, preview_dir, preview_filename)

        preview_url = f"/static/previews/{video_id}/{preview_filename}"

        return ExtractFrameResponse(
            video_id=video_id,
            frame_index=frame_idx,
            timestamp_sec=actual_timestamp,
            frame_width=w,
            frame_height=h,
            preview_url=preview_url,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract frame: {str(e)}",
        )


@router.post(
    "/video/{video_id}/detect-frame",
    response_model=DetectFrameResponse,
    tags=["Detection"],
)
async def detect_frame_people(
    video_id: str,
    req: DetectFrameRequest = DetectFrameRequest(),
) -> DetectFrameResponse:
    video_path = VideoProcessor.get_source_path(settings.UPLOADS_DIR, video_id)
    if not video_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video '{video_id}' not found.",
        )

    try:
        frame, frame_idx, actual_timestamp = VideoProcessor.extract_frame(
            video_path=video_path,
            timestamp_sec=req.timestamp_sec,
            frame_index=req.frame_index,
        )
        h, w = frame.shape[:2]

        preview_dir = settings.PREVIEWS_DIR / video_id
        frame_filename = f"frame_{frame_idx}.jpg"
        VideoProcessor.save_frame_preview(frame, preview_dir, frame_filename)
        frame_preview_url = f"/static/previews/{video_id}/{frame_filename}"

        conf = req.conf_threshold or settings.DETECTION_CONF_THRESHOLD
        raw_detections = PersonDetector.detect_people(frame, conf_threshold=conf)

        targets_dir = preview_dir / "targets"
        target_results = PersonDetector.crop_and_save_targets(
            frame_bgr=frame,
            detections=raw_detections,
            output_dir=targets_dir,
            prefix=f"f{frame_idx}_target",
        )

        detected_people: list[DetectedPerson] = []
        for target in target_results:
            crop_url = f"/static/previews/{video_id}/targets/{target['crop_filename']}"
            detected_people.append(
                DetectedPerson(
                    id=target["id"],
                    name=target["name"],
                    confidence=target["confidence"],
                    box=NormalizedBox(**target["box"]),
                    crop_url=crop_url,
                    role=target["role"],
                )
            )

        return DetectFrameResponse(
            video_id=video_id,
            frame_index=frame_idx,
            timestamp_sec=actual_timestamp,
            frame_width=w,
            frame_height=h,
            frame_preview_url=frame_preview_url,
            detected_people=detected_people,
            total_detected=len(detected_people),
            device_used=PersonDetector.get_device(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect humans in frame: {str(e)}",
        )


@router.post(
    "/video/{video_id}/select-target",
    response_model=SelectTargetResponse,
    tags=["Re-ID"],
)
async def select_target(
    video_id: str,
    req: SelectTargetRequest,
) -> SelectTargetResponse:
    targets_dir = settings.PREVIEWS_DIR / video_id / "targets"
    if not targets_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No detected targets found for video '{video_id}'. Run detection first.",
        )

    target_crop_path = None
    if req.crop_url:
        crop_name = Path(req.crop_url).name
        candidate = targets_dir / crop_name
        if candidate.exists():
            target_crop_path = candidate

    if not target_crop_path:
        t_num = req.target_id.replace("p", "").strip()
        candidates = list(targets_dir.glob(f"*target_{t_num}.jpg"))
        if candidates:
            target_crop_path = candidates[0]

    if not target_crop_path or not target_crop_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target '{req.target_id}' does not exist for video '{video_id}'.",
        )

    crop_bgr = cv2.imread(str(target_crop_path))
    if crop_bgr is None or crop_bgr.size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decode target crop image.",
        )

    try:
        embedding = OSNetReIDExtractor.extract_embedding(crop_bgr)
        dim = int(embedding.shape[0])
        l2_norm = float(np.linalg.norm(embedding))

        stored_path = OSNetReIDExtractor.save_target_embedding(
            video_id=video_id,
            target_id=req.target_id,
            embedding=embedding,
            storage_dir=settings.UPLOADS_DIR,
        )

        return SelectTargetResponse(
            video_id=video_id,
            target_id=req.target_id,
            embedding_dimension=dim,
            l2_norm=round(l2_norm, 4),
            stored_path=str(stored_path.name),
            message=f"OSNet appearance signature initialized for {req.target_id} ({dim}-D).",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract Re-ID embedding: {str(e)}",
        )


@router.post(
    "/process",
    response_model=ProcessVideoResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Processing Pipeline"],
)
async def process_video(
    req: ProcessVideoRequest,
    background_tasks: BackgroundTasks,
) -> ProcessVideoResponse:
    """
    Triggers asynchronous video reframing and tracking.
    Validates:
      1. Uploaded video exists.
      2. Target ID crop exists for this video.
      3. Selected target's Re-ID embedding exists.
      4. Tracker is bytetrack or deepsort.
      5. Aspect ratio is 9:16, 1:1, or 16:9.
      6. Smoothing level is within 0-100.
    No silent defaulting allowed.
    """
    # 1. Video file existence
    video_path = VideoProcessor.get_source_path(settings.UPLOADS_DIR, req.video_id)
    if not video_path or not video_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source video '{req.video_id}' not found.",
        )

    # 2. Target crop existence (validates target belongs to this video)
    targets_dir = settings.PREVIEWS_DIR / req.video_id / "targets"
    t_num = req.target_id.replace("p", "").strip()
    matching_crops = list(targets_dir.glob(f"*target_{t_num}.jpg")) if targets_dir.exists() else []
    if not matching_crops:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target ID '{req.target_id}' does not belong to video '{req.video_id}'.",
        )

    # 3. Target Re-ID embedding existence
    embedding = OSNetReIDExtractor.load_target_embedding(
        video_id=req.video_id,
        target_id=req.target_id,
        storage_dir=settings.UPLOADS_DIR,
    )
    if embedding is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Re-ID embedding for target '{req.target_id}' not found. Please select target via /api/video/{req.video_id}/select-target first.",
        )

    # 4, 5, 6. Tracker, Aspect Ratio, and Smoothing validation are strictly enforced by ProcessVideoRequest Pydantic schema
    selected_tracker = req.get_algorithm()

    # Create task in state manager
    task_id = TaskManager.create_task(
        video_id=req.video_id,
        target_id=req.target_id,
        tracker=selected_tracker,
        aspect_ratio=req.aspect_ratio,
        smoothing_level=req.smoothing_level,
    )

    # Dispatch to background task runner
    background_tasks.add_task(PipelineOrchestrator.run_pipeline, task_id)

    return ProcessVideoResponse(
        task_id=task_id,
        video_id=req.video_id,
        status="queued",
        message="FanCam video processing task queued successfully.",
    )


@router.get(
    "/status/{task_id}",
    response_model=TaskStatusResponse,
    tags=["Processing Pipeline"],
)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Poll task execution progress by task_id."""
    task = TaskManager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )

    return TaskStatusResponse(**task)


@router.get(
    "/download/{video_id}",
    tags=["Processing Pipeline"],
)
async def download_video(video_id: str):
    """
    Downloads the completed reframed FanCam MP4 video file.
    """
    output_dir = settings.OUTPUTS_DIR / video_id
    if not output_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Outputs for video '{video_id}' not found.",
        )

    # Search for fancam_*.mp4 files
    candidates = list(output_dir.glob("fancam_*.mp4"))
    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rendered FanCam video for '{video_id}' not found. Please ensure processing completed.",
        )

    # Return the newest rendered highlight
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    target_file = candidates[0]

    return FileResponse(
        path=str(target_file),
        media_type="video/mp4",
        filename=f"fancam_{video_id}.mp4",
    )


@router.post("/contact", response_model=ContactResponse, tags=["Contact"])
def submit_contact(payload: ContactRequest) -> ContactResponse:
    """Validate a contact submission and deliver it to the configured inbox."""
    if payload.website.strip():
        # Honeypot filled by a bot: acknowledge without sending anything.
        return ContactResponse(message="Thanks for reaching out.")

    try:
        email_id = send_contact_email(
            name=payload.name,
            email=payload.email,
            subject=payload.subject,
            message=payload.message,
        )
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return ContactResponse(
        message="Your message has been sent successfully.",
        email_id=email_id,
    )
