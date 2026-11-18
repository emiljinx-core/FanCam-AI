import sys
from pathlib import Path
import json
import pytest
import numpy as np

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.core.tasks import TaskManager
from app.core.pipeline import PipelineOrchestrator
from app.core.tracking import ByteTracker, DeepSortTracker

client = TestClient(app)


def test_tracker_initialization_selection():
    """Verify backend initializes tracker strictly corresponding to user selection."""
    bt = PipelineOrchestrator._initialize_tracker("bytetrack", fps=30.0)
    assert isinstance(bt, ByteTracker)

    ds = PipelineOrchestrator._initialize_tracker("deepsort", fps=30.0)
    assert isinstance(ds, DeepSortTracker)


def test_process_endpoint_tracking_algorithm_field(tmp_path):
    """
    Verify POST /api/process supports tracking_algorithm field, validates it,
    and preserves it into the created background task.
    """
    video_id = "test-video-algo"
    target_id = "p1"

    # Setup mock video directory & dummy file
    vid_dir = settings.UPLOADS_DIR / video_id
    vid_dir.mkdir(parents=True, exist_ok=True)
    video_file = vid_dir / "source.mp4"
    video_file.write_bytes(b"fake-mp4-data")

    # Setup target crop preview
    preview_targets = settings.PREVIEWS_DIR / video_id / "targets"
    preview_targets.mkdir(parents=True, exist_ok=True)
    (preview_targets / "frame_0_target_1.jpg").write_bytes(b"fake-image")

    # Setup target embedding
    targets_dir = vid_dir / "targets"
    targets_dir.mkdir(parents=True, exist_ok=True)
    np.save(str(targets_dir / "p1_embedding.npy"), np.ones(512, dtype=np.float32) / np.sqrt(512))

    # 1. Test passing tracking_algorithm="deepsort"
    resp_ds = client.post(
        "/api/process",
        json={
            "video_id": video_id,
            "target_id": target_id,
            "tracking_algorithm": "deepsort",
            "aspect_ratio": "9:16",
            "smoothing_level": 80,
        },
    )
    assert resp_ds.status_code == 202, resp_ds.text
    data_ds = resp_ds.json()
    task_ds = TaskManager.get_task(data_ds["task_id"])
    assert task_ds["tracker"] == "deepsort"

    # 2. Test passing tracking_algorithm="bytetrack"
    resp_bt = client.post(
        "/api/process",
        json={
            "video_id": video_id,
            "target_id": target_id,
            "tracking_algorithm": "bytetrack",
            "aspect_ratio": "9:16",
            "smoothing_level": 85,
        },
    )
    assert resp_bt.status_code == 202
    data_bt = resp_bt.json()
    task_bt = TaskManager.get_task(data_bt["task_id"])
    assert task_bt["tracker"] == "bytetrack"

    # 3. Test default fallback to bytetrack when omitted
    resp_default = client.post(
        "/api/process",
        json={
            "video_id": video_id,
            "target_id": target_id,
            "aspect_ratio": "9:16",
            "smoothing_level": 85,
        },
    )
    assert resp_default.status_code == 202
    data_default = resp_default.json()
    task_default = TaskManager.get_task(data_default["task_id"])
    assert task_default["tracker"] == "bytetrack"
