import sys
import subprocess
from pathlib import Path
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.config import settings
from app.core.rendering.audio_muxer import AudioMuxer
from app.core.rendering.video_renderer import VideoRenderer
from app.core.tasks import TaskManager
from app.core.pipeline import PipelineOrchestrator
from app.core.reid import OSNetReIDExtractor

client = TestClient(app)


def create_synthetic_test_video(path: Path, num_frames: int = 30, fps: float = 30.0, with_audio: bool = False):
    """Generates a synthetic MP4 test video, optionally with a sine-wave audio track."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_raw = path.with_name(f"raw_{path.name}")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(temp_raw), fourcc, fps, (640, 360))

    for i in range(num_frames):
        # Draw moving rectangle
        frame = np.zeros((360, 640, 3), dtype=np.uint8)
        x = int(50 + i * 10)
        cv2.rectangle(frame, (x, 100), (x + 80, 260), (0, 255, 0), -1)
        writer.write(frame)
    writer.release()

    ffmpeg_exe = AudioMuxer.get_ffmpeg_exe()

    if with_audio:
        # Generate sine wave audio track in container
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i",
            str(temp_raw),
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=1000:duration={num_frames/fps}",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if temp_raw.exists():
            temp_raw.unlink()
    else:
        if path.exists():
            path.unlink()
        temp_raw.rename(path)


def test_audio_stream_detection(tmp_path):
    """Verify audio stream detection correctly distinguishes silent vs audio videos."""
    silent_vid = tmp_path / "silent.mp4"
    audio_vid = tmp_path / "with_audio.mp4"

    create_synthetic_test_video(silent_vid, num_frames=15, with_audio=False)
    create_synthetic_test_video(audio_vid, num_frames=15, with_audio=True)

    assert AudioMuxer.has_audio_stream(silent_vid) is False
    assert AudioMuxer.has_audio_stream(audio_vid) is True


def test_video_renderer_and_audio_muxing(tmp_path):
    """
    Verify VideoRenderer renders expected delivery resolutions,
    preserves exact frame count, and muxes audio.
    """
    source_vid = tmp_path / "source_test.mp4"
    create_synthetic_test_video(source_vid, num_frames=20, fps=25.0, with_audio=True)

    crops_data = [
        {"crop_int": [50 + i * 5, 20, 250 + i * 5, 340]}
        for i in range(20)
    ]

    out_highlight = tmp_path / "fancam_p1_9_16.mp4"
    out_comparison = tmp_path / "comparison_p1.mp4"

    # 1. Render Highlight
    VideoRenderer.render_highlight_video(
        source_video_path=source_vid,
        crops_data=crops_data,
        output_mp4_path=out_highlight,
        aspect_ratio="9:16",
        fps=25.0,
    )

    assert out_highlight.exists()
    assert out_highlight.stat().st_size > 0

    # Inspect rendered highlight properties
    cap = cv2.VideoCapture(str(out_highlight))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    cap.release()

    assert (w, h) == (1080, 1920), f"Expected 1080x1920 for 9:16, got {w}x{h}"
    assert count == 20, f"Frame count mismatch: {count} vs 20"
    assert abs(fps - 25.0) < 1.0, f"FPS mismatch: {fps} vs 25.0"
    assert AudioMuxer.has_audio_stream(out_highlight) is True

    # 2. Render Comparison
    VideoRenderer.render_comparison_video(
        source_video_path=source_vid,
        crops_data=crops_data,
        output_mp4_path=out_comparison,
        aspect_ratio="9:16",
        fps=25.0,
    )

    assert out_comparison.exists()
    assert out_comparison.stat().st_size > 0

    cap_comp = cv2.VideoCapture(str(out_comparison))
    cw = int(cap_comp.get(cv2.CAP_PROP_FRAME_WIDTH))
    ch = int(cap_comp.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap_comp.release()
    assert (cw, ch) == (1920, 1080), f"Expected 1920x1080 comparison canvas, got {cw}x{ch}"


def test_download_endpoint():
    """Verify GET /api/download/{video_id} returns 200 with video file, and 404 for unknown video."""
    video_id = "test-download-vid"
    out_dir = settings.OUTPUTS_DIR / video_id
    out_dir.mkdir(parents=True, exist_ok=True)
    fake_video = out_dir / "fancam_p1_9_16.mp4"
    fake_video.write_bytes(b"fake-mp4-video-content-stream")

    # 1. Valid download
    res = client.get(f"/api/download/{video_id}")
    assert res.status_code == 200
    assert "video/mp4" in res.headers["content-type"]
    assert f"fancam_{video_id}.mp4" in res.headers["content-disposition"]
    assert res.content == b"fake-mp4-video-content-stream"

    # 2. Non-existent download
    res_404 = client.get("/api/download/non-existent-video-xyz")
    assert res_404.status_code == 404
