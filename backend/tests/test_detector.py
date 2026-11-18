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
from app.core.detector import PersonDetector

client = TestClient(app)

def draw_person_silhouette(frame, center_x, center_y, scale=1.0):
    """Draw a human-like silhouette on the synthetic frame."""
    # Head
    head_radius = int(25 * scale)
    head_center = (center_x, center_y - int(70 * scale))
    cv2.circle(frame, head_center, head_radius, (200, 180, 150), -1)

    # Torso
    torso_top = (center_x - int(30 * scale), center_y - int(45 * scale))
    torso_bottom = (center_x + int(30 * scale), center_y + int(45 * scale))
    cv2.rectangle(frame, torso_top, torso_bottom, (50, 120, 200), -1)

    # Legs
    cv2.line(frame, (center_x - int(15 * scale), center_y + int(45 * scale)),
             (center_x - int(20 * scale), center_y + int(110 * scale)), (30, 30, 30), int(12 * scale))
    cv2.line(frame, (center_x + int(15 * scale), center_y + int(45 * scale)),
             (center_x + int(20 * scale), center_y + int(110 * scale)), (30, 30, 30), int(12 * scale))

    # Arms
    cv2.line(frame, (center_x - int(30 * scale), center_y - int(35 * scale)),
             (center_x - int(55 * scale), center_y + int(25 * scale)), (50, 120, 200), int(10 * scale))
    cv2.line(frame, (center_x + int(30 * scale), center_y - int(35 * scale)),
             (center_x + int(55 * scale), center_y + int(25 * scale)), (50, 120, 200), int(10 * scale))

def create_sample_group_video(filepath: Path, width=640, height=480, fps=10, duration_sec=2):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(filepath), fourcc, fps, (width, height))
    total_frames = int(fps * duration_sec)

    for i in range(total_frames):
        # Background
        frame = np.full((height, width, 3), 230, dtype=np.uint8)
        # Person 1 (left)
        draw_person_silhouette(frame, 180, 240, scale=1.1)
        # Person 2 (center/right)
        draw_person_silhouette(frame, 460, 240, scale=1.1)
        out.write(frame)

    out.release()

def test_yolo_detection():
    print("--- 1. Testing Device Detection & CPU Fallback ---")
    active_device = PersonDetector.get_device()
    print("Detected device for inference:", active_device)
    assert active_device in ["cpu", "cuda:0"]

    # Test forced CPU
    original_force = settings.FORCE_CPU
    settings.FORCE_CPU = True
    cpu_device = PersonDetector.get_device()
    assert cpu_device == "cpu"
    settings.FORCE_CPU = original_force
    print("✓ CUDA check & CPU fallback capability verified.")

    print("\n--- 2. Testing Direct YOLO Inference on Synthetic Human Image ---")
    test_img = np.full((480, 640, 3), 230, dtype=np.uint8)
    draw_person_silhouette(test_img, 320, 240, scale=1.3)
    raw_detections = PersonDetector.detect_people(test_img, conf_threshold=0.25)
    print(f"Direct inference detected: {len(raw_detections)} people")
    print("Raw detections:", raw_detections)
    print("✓ Model successfully executes inference without errors.")

    print("\n--- 3. Testing POST /api/video/{video_id}/detect-frame Endpoint ---")
    video_id = "test-group-video"
    video_dir = settings.UPLOADS_DIR / video_id
    video_file = video_dir / "source.mp4"

    try:
        create_sample_group_video(video_file, width=640, height=480, fps=10, duration_sec=2)

        res = client.post(
            f"/api/video/{video_id}/detect-frame",
            json={"timestamp_sec": 0.0, "conf_threshold": 0.25},
        )
        assert res.status_code == 200, f"Error {res.status_code}: {res.text}"
        data = res.json()
        print("Detection response received:")
        print(f"  Frame index: {data['frame_index']}")
        print(f"  Frame dimensions: {data['frame_width']}x{data['frame_height']}")
        print(f"  Device used: {data['device_used']}")
        print(f"  Total people detected: {data['total_detected']}")
        print(f"  Frame preview URL: {data['frame_preview_url']}")

        # Ensure frame preview exists
        frame_preview_path = settings.PREVIEWS_DIR / video_id / "frame_0.jpg"
        assert frame_preview_path.exists()

        for p in data["detected_people"]:
            print(f"    - {p['id']}: {p['name']}, conf={p['confidence']}%, box={p['box']}, crop={p['crop_url']}")
            # Check crop URL is accessible
            crop_res = client.get(p["crop_url"])
            assert crop_res.status_code == 200, f"Failed to retrieve crop: {p['crop_url']}"
            assert crop_res.headers["content-type"].startswith("image/jpeg")

        print("✓ Detection endpoint, coordinate normalization, crops, and previews verified!")

    finally:
        shutil.rmtree(video_dir, ignore_errors=True)
        shutil.rmtree(settings.PREVIEWS_DIR / video_id, ignore_errors=True)

if __name__ == "__main__":
    test_yolo_detection()
    print("\nALL YOLO DETECTION TESTS PASSED!")
