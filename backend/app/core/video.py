from pathlib import Path
from typing import Optional, Tuple
import cv2
import numpy as np


class VideoMetadata:
    def __init__(
        self,
        width: int,
        height: int,
        fps: float,
        frame_count: int,
        duration_seconds: float,
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.frame_count = frame_count
        self.duration_seconds = duration_seconds

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "fps": round(self.fps, 2),
            "frame_count": self.frame_count,
            "duration_seconds": round(self.duration_seconds, 2),
        }


class VideoProcessor:
    """Handles video file reading, property extraction, and seeking."""

    @staticmethod
    def get_source_path(uploads_dir: Path, video_id: str) -> Optional[Path]:
        """Find the video file within the video's upload directory."""
        video_dir = uploads_dir / video_id
        if not video_dir.exists() or not video_dir.is_dir():
            return None

        # Look for source.mp4, source.mov or any matching file
        for ext in [".mp4", ".mov"]:
            candidate = video_dir / f"source{ext}"
            if candidate.exists() and candidate.is_file():
                return candidate

        # Fallback to any file in directory
        for f in video_dir.iterdir():
            if f.is_file() and f.suffix.lower() in [".mp4", ".mov"]:
                return f

        return None

    @classmethod
    def get_metadata(cls, video_path: Path) -> VideoMetadata:
        """Inspect video and extract technical properties."""
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found at {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        try:
            if not cap.isOpened():
                raise ValueError("Could not open video file with OpenCV.")

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if fps <= 0:
                fps = 30.0  # Safe default if container metadata omits valid fps

            duration_seconds = frame_count / fps if frame_count > 0 else 0.0

            return VideoMetadata(
                width=width,
                height=height,
                fps=fps,
                frame_count=frame_count,
                duration_seconds=duration_seconds,
            )
        finally:
            cap.release()

    @classmethod
    def extract_frame(
        cls,
        video_path: Path,
        timestamp_sec: Optional[float] = None,
        frame_index: Optional[int] = None,
    ) -> Tuple[np.ndarray, int, float]:
        """
        Extract a single frame at the given timestamp or frame index.
        Returns: (frame_bgr, target_frame_index, actual_timestamp_sec)
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found at {video_path}")

        cap = cv2.VideoCapture(str(video_path))
        try:
            if not cap.isOpened():
                raise ValueError("Could not open video file.")

            fps = float(cap.get(cv2.CAP_PROP_FPS))
            if fps <= 0:
                fps = 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # Determine frame index
            if frame_index is not None:
                target_frame = max(0, min(frame_index, max(0, total_frames - 1)))
            elif timestamp_sec is not None:
                target_frame = int(round(timestamp_sec * fps))
                target_frame = max(0, min(target_frame, max(0, total_frames - 1)))
            else:
                target_frame = 0

            # Seek
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            success, frame = cap.read()

            if not success or frame is None:
                # If direct seek fails, rewind to 0 and attempt read
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                success, frame = cap.read()
                target_frame = 0

            if not success or frame is None:
                raise RuntimeError("Failed to decode frame from video.")

            actual_timestamp = target_frame / fps
            return frame, target_frame, round(actual_timestamp, 3)
        finally:
            cap.release()

    @classmethod
    def save_frame_preview(
        cls,
        frame: np.ndarray,
        output_dir: Path,
        filename: str = "frame_0.jpg",
    ) -> Path:
        """Save a frame image to the previews directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / filename
        cv2.imwrite(str(file_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return file_path
