import json
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

from app.config import settings


class TaskManager:
    """Thread-safe in-memory and disk-persisted Task Manager."""

    _lock = threading.Lock()
    _tasks: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _get_task_file(cls, task_id: str, video_id: str) -> Path:
        task_dir = settings.OUTPUTS_DIR / video_id / "tasks"
        task_dir.mkdir(parents=True, exist_ok=True)
        return task_dir / f"{task_id}.json"

    @classmethod
    def create_task(
        cls,
        video_id: str,
        target_id: str,
        tracker: str,
        aspect_ratio: str,
        smoothing_level: int,
    ) -> str:
        task_id = str(uuid.uuid4())
        now = time.time()

        task_data = {
            "task_id": task_id,
            "video_id": video_id,
            "target_id": target_id,
            "tracker": tracker,
            "aspect_ratio": aspect_ratio,
            "smoothing_level": smoothing_level,
            "status": "queued",
            "progress": 0.0,
            "current_step": "Task queued in worker runner.",
            "output_video_url": None,
            "comparison_video_url": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
        }

        with cls._lock:
            cls._tasks[task_id] = task_data

        # Persist initial state
        cls._save_to_disk(task_id, task_data)
        return task_id

    @classmethod
    def _save_to_disk(cls, task_id: str, data: Dict[str, Any]) -> None:
        try:
            task_file = cls._get_task_file(task_id, data["video_id"])
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    @classmethod
    def get_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        with cls._lock:
            if task_id in cls._tasks:
                return dict(cls._tasks[task_id])

        # Attempt recovery from disk if in-memory cache missed
        for task_file in settings.OUTPUTS_DIR.glob(f"*/tasks/{task_id}.json"):
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                with cls._lock:
                    cls._tasks[task_id] = data
                return data
            except Exception:
                pass

        return None

    @classmethod
    def update_progress(cls, task_id: str, progress: float, step: str) -> None:
        with cls._lock:
            if task_id in cls._tasks:
                task = cls._tasks[task_id]
                task["status"] = "processing"
                task["progress"] = round(min(99.0, max(0.0, progress)), 1)
                task["current_step"] = step
                task["updated_at"] = time.time()
                data_copy = dict(task)
            else:
                return
        cls._save_to_disk(task_id, data_copy)

    @classmethod
    def mark_completed(
        cls,
        task_id: str,
        output_video_url: str,
        comparison_video_url: Optional[str] = None,
    ) -> None:
        now = time.time()
        with cls._lock:
            if task_id in cls._tasks:
                task = cls._tasks[task_id]
                task["status"] = "completed"
                task["progress"] = 100.0
                task["current_step"] = "FanCam processing completed successfully."
                task["output_video_url"] = output_video_url
                task["comparison_video_url"] = comparison_video_url
                task["updated_at"] = now
                task["completed_at"] = now
                data_copy = dict(task)
            else:
                return
        cls._save_to_disk(task_id, data_copy)

    @classmethod
    def mark_failed(cls, task_id: str, error_message: str) -> None:
        now = time.time()
        with cls._lock:
            if task_id in cls._tasks:
                task = cls._tasks[task_id]
                task["status"] = "failed"
                task["current_step"] = "Processing failed."
                task["error"] = error_message
                task["updated_at"] = now
                data_copy = dict(task)
            else:
                return
        cls._save_to_disk(task_id, data_copy)
