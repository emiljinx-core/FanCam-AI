import sys
import shutil
from pathlib import Path
import numpy as np
import cv2

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def create_synthetic_mp4(filepath: Path, width=320, height=240, fps=10, duration_sec=2):
    """Generate a clean synthetic MP4 using OpenCV VideoWriter."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(filepath), fourcc, fps, (width, height))
    total_frames = int(fps * duration_sec)

    for i in range(total_frames):
        # Create distinct frame colors
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        color_val = int((i / total_frames) * 255)
        frame[:, :] = (color_val, 120, 255 - color_val)
        # Put frame number text
        cv2.putText(frame, f"Frame {i}", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        out.write(frame)

    out.release()

def test_metadata_and_frame_extraction():
    video_id = "test-video-meta"
    video_dir = settings.UPLOADS_DIR / video_id
    video_file = video_dir / "source.mp4"

    try:
        # Create 20 frames, 10 fps (2.0s duration), 320x240
        create_synthetic_mp4(video_file, width=320, height=240, fps=10, duration_sec=2)
        assert video_file.exists(), "Synthetic video should exist"

        print("Testing GET /api/video/{video_id}/meta...")
        res_meta = client.get(f"/api/video/{video_id}/meta")
        assert res_meta.status_code == 200, f"Error {res_meta.status_code}: {res_meta.text}"
        meta = res_meta.json()
        print("Meta received:", meta)
        assert meta["video_id"] == video_id
        assert meta["width"] == 320
        assert meta["height"] == 240
        assert meta["fps"] == 10.0
        assert meta["frame_count"] == 20
        assert meta["duration_seconds"] == 2.0
        print("✓ Metadata test passed!")

        print("\nTesting POST /api/video/{video_id}/extract-frame (Default Frame 0)...")
        res_frame0 = client.post(f"/api/video/{video_id}/extract-frame", json={})
        assert res_frame0.status_code == 200, f"Error {res_frame0.status_code}: {res_frame0.text}"
        frame0_data = res_frame0.json()
        print("Frame 0 data:", frame0_data)
        assert frame0_data["frame_index"] == 0
        assert frame0_data["timestamp_sec"] == 0.0
        assert frame0_data["preview_url"] == f"/static/previews/{video_id}/frame_0.jpg"

        # Check preview image exists on disk and static route serves it
        preview_file = settings.PREVIEWS_DIR / video_id / "frame_0.jpg"
        assert preview_file.exists(), f"Frame file should exist at {preview_file}"
        res_static = client.get(frame0_data["preview_url"])
        assert res_static.status_code == 200, f"Static route failed: {res_static.status_code}"
        assert res_static.headers["content-type"].startswith("image/jpeg")
        print("✓ Default Frame 0 extraction & static preview passed!")

        print("\nTesting POST /api/video/{video_id}/extract-frame (Scrubbing to 1.5s)...")
        res_frame_scrub = client.post(
            f"/api/video/{video_id}/extract-frame",
            json={"timestamp_sec": 1.5},
        )
        assert res_frame_scrub.status_code == 200, f"Error {res_frame_scrub.status_code}: {res_frame_scrub.text}"
        scrub_data = res_frame_scrub.json()
        print("Scrub data (1.5s):", scrub_data)
        assert scrub_data["frame_index"] == 15
        assert scrub_data["timestamp_sec"] == 1.5
        assert scrub_data["preview_url"] == f"/static/previews/{video_id}/frame_15.jpg"
        print("✓ Timeline scrubbing extraction passed!")

        print("\nTesting non-existent video_id (404)...")
        res_404 = client.get("/api/video/unknown-id/meta")
        assert res_404.status_code == 404
        res_404_frame = client.post("/api/video/unknown-id/extract-frame", json={})
        assert res_404_frame.status_code == 404
        print("✓ 404 error handling passed!")

    finally:
        # Cleanup test directories
        shutil.rmtree(video_dir, ignore_errors=True)
        shutil.rmtree(settings.PREVIEWS_DIR / video_id, ignore_errors=True)

if __name__ == "__main__":
    test_metadata_and_frame_extraction()
    print("\nALL PHASE 3A TESTS PASSED SUCCESSFULLY!")
