import sys
import shutil
import time
from pathlib import Path
import numpy as np
import cv2

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.core.tasks import TaskManager
from app.core.reid import OSNetReIDExtractor

client = TestClient(app)

def create_synthetic_mp4(filepath: Path):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(filepath), fourcc, 10, (320, 240))
    for _ in range(10):
        out.write(np.zeros((240, 320, 3), dtype=np.uint8))
    out.release()

def test_step4_pipeline():
    video_id = "test-video-step4"
    video_dir = settings.UPLOADS_DIR / video_id
    video_file = video_dir / "source.mp4"

    try:
        # 1. Setup video and target crop
        create_synthetic_mp4(video_file)
        targets_dir = settings.PREVIEWS_DIR / video_id / "targets"
        targets_dir.mkdir(parents=True, exist_ok=True)
        crop_path = targets_dir / "f0_target_2.jpg"
        cv2.imwrite(str(crop_path), np.zeros((100, 50, 3), dtype=np.uint8))

        print("--- 1. Testing Strict Validations on POST /api/process ---")

        # A. Missing embedding check
        res_no_emb = client.post(
            "/api/process",
            json={"video_id": video_id, "target_id": "p2"},
        )
        assert res_no_emb.status_code == 400, f"Expected 400, got {res_no_emb.status_code}"
        assert "embedding" in res_no_emb.json()["detail"].lower()
        print("✓ Missing embedding rejected with 400.")

        # Create valid embedding for target p2
        fake_emb = np.ones((512,), dtype=np.float32)
        fake_emb /= np.linalg.norm(fake_emb)
        OSNetReIDExtractor.save_target_embedding(video_id, "p2", fake_emb, settings.UPLOADS_DIR)

        # B. Non-existent target ID check
        res_bad_target = client.post(
            "/api/process",
            json={"video_id": video_id, "target_id": "p99"},
        )
        assert res_bad_target.status_code == 404, f"Expected 404, got {res_bad_target.status_code}"
        assert "does not belong to video" in res_bad_target.json()["detail"]
        print("✓ Invalid target rejected with 404 (no silent defaulting).")

        # C. Invalid tracker check
        res_bad_tracker = client.post(
            "/api/process",
            json={"video_id": video_id, "target_id": "p2", "tracker": "random_tracker"},
        )
        assert res_bad_tracker.status_code == 422, "Expected 422 for invalid tracker"
        print("✓ Invalid tracker rejected with 422.")

        # D. Invalid aspect ratio check
        res_bad_ratio = client.post(
            "/api/process",
            json={"video_id": video_id, "target_id": "p2", "aspect_ratio": "4:3"},
        )
        assert res_bad_ratio.status_code == 422, "Expected 422 for unsupported aspect ratio"
        print("✓ Unsupported aspect ratio rejected with 422.")

        # E. Invalid smoothing level check (< 0 or > 100)
        res_bad_smoothing = client.post(
            "/api/process",
            json={"video_id": video_id, "target_id": "p2", "smoothing_level": 150},
        )
        assert res_bad_smoothing.status_code == 422, "Expected 422 for smoothing > 100"
        print("✓ Out of bounds smoothing rejected with 422.")

        # F. Non-existent video ID
        res_bad_vid = client.post(
            "/api/process",
            json={"video_id": "unknown-uuid", "target_id": "p2"},
        )
        assert res_bad_vid.status_code == 404
        print("✓ Non-existent video rejected with 404.")

        print("\n--- 2. Testing Valid Task Submission & Status Polling via GET /api/status/{task_id} ---")
        res_valid = client.post(
            "/api/process",
            json={
                "video_id": video_id,
                "target_id": "p2",
                "tracker": "bytetrack",
                "aspect_ratio": "9:16",
                "smoothing_level": 85,
            },
        )
        assert res_valid.status_code == 202, f"Expected 202, got {res_valid.status_code}: {res_valid.text}"
        res_body = res_valid.json()
        task_id = res_body["task_id"]
        assert res_body["status"] == "queued"
        print(f"Task queued successfully! Task ID: {task_id}")

        # Poll status
        print("Polling GET /api/status/{task_id}...")
        completed = False
        for _ in range(20):
            res_poll = client.get(f"/api/status/{task_id}")
            assert res_poll.status_code == 200, f"Error {res_poll.status_code}: {res_poll.text}"
            poll_data = res_poll.json()
            print(f"  [{poll_data['status'].upper()}] Progress: {poll_data['progress']}% | Step: {poll_data['current_step']}")

            if poll_data["status"] == "completed":
                completed = True
                assert poll_data["progress"] == 100.0
                assert poll_data["output_video_url"] is not None
                print("✓ Output video URL:", poll_data["output_video_url"])
                print("✓ Comparison video URL:", poll_data["comparison_video_url"])
                break
            elif poll_data["status"] == "failed":
                raise RuntimeError(f"Task failed: {poll_data['error']}")

            time.sleep(0.4)

        assert completed, "Task did not complete within expected time."
        print("✓ Status polling transitions verified!")

        print("\n--- 3. Testing 404 on Unknown task_id ---")
        res_unknown_task = client.get("/api/status/non-existent-task-id")
        assert res_unknown_task.status_code == 404
        print("✓ Unknown task ID returns 404.")

    finally:
        shutil.rmtree(video_dir, ignore_errors=True)
        shutil.rmtree(settings.PREVIEWS_DIR / video_id, ignore_errors=True)
        shutil.rmtree(settings.OUTPUTS_DIR / video_id, ignore_errors=True)

if __name__ == "__main__":
    test_step4_pipeline()
    print("\nALL STEP 4 TESTS PASSED SUCCESSFULLY!")
