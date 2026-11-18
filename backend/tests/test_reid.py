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
from app.core.reid import OSNetReIDExtractor

client = TestClient(app)

def test_osnet_reid():
    print("--- 1. Testing Direct OSNet Embedding Extraction ---")
    # Synthetic person crop (200x100 BGR)
    crop = np.zeros((200, 100, 3), dtype=np.uint8)
    crop[:50, :] = [180, 150, 120]  # head
    crop[50:140, :] = [50, 100, 220]  # shirt
    crop[140:, :] = [20, 20, 20]  # pants

    embedding = OSNetReIDExtractor.extract_embedding(crop)
    dim = embedding.shape[0]
    norm = np.linalg.norm(embedding)
    print(f"OSNet embedding dimension: {dim}")
    print(f"L2 Norm: {norm:.5f}")
    assert dim == 512, f"Expected 512-D, got {dim}"
    assert np.isclose(norm, 1.0, atol=1e-4), f"Embedding must be L2-normalized (got {norm})"
    print("✓ Direct OSNet extraction passed: exactly 512-D and L2-normalized!")

    print("\n--- 2. Testing Storage & Loading of Target Embedding ---")
    video_id = "test-reid-target"
    target_id = "p2"
    saved_path = OSNetReIDExtractor.save_target_embedding(
        video_id=video_id,
        target_id=target_id,
        embedding=embedding,
        storage_dir=settings.UPLOADS_DIR,
    )
    assert saved_path.exists(), f"Embedding file not found at {saved_path}"
    loaded = OSNetReIDExtractor.load_target_embedding(
        video_id=video_id,
        target_id=target_id,
        storage_dir=settings.UPLOADS_DIR,
    )
    assert loaded is not None
    assert np.allclose(embedding, loaded), "Loaded embedding must match saved embedding"
    print("✓ Embedding saved and loaded successfully!")

    print("\n--- 3. Testing POST /api/video/{video_id}/select-target Endpoint ---")
    # Setup test crop in preview directory
    targets_dir = settings.PREVIEWS_DIR / video_id / "targets"
    targets_dir.mkdir(parents=True, exist_ok=True)
    crop_path = targets_dir / "f0_target_2.jpg"
    cv2.imwrite(str(crop_path), crop)

    res = client.post(
        f"/api/video/{video_id}/select-target",
        json={"target_id": "p2", "crop_url": f"/static/previews/{video_id}/targets/f0_target_2.jpg"},
    )
    assert res.status_code == 200, f"Error {res.status_code}: {res.text}"
    body = res.json()
    print("Select Target Response:", body)
    assert body["video_id"] == video_id
    assert body["target_id"] == "p2"
    assert body["embedding_dimension"] == 512
    assert np.isclose(body["l2_norm"], 1.0, atol=1e-3)
    assert "p2_embedding.npy" in body["stored_path"]
    print("✓ Target selection endpoint correctly extracts and saves target signature!")

    # Cleanup
    shutil.rmtree(settings.UPLOADS_DIR / video_id, ignore_errors=True)
    shutil.rmtree(settings.PREVIEWS_DIR / video_id, ignore_errors=True)

if __name__ == "__main__":
    test_osnet_reid()
    print("\nALL RE-ID EMBEDDING TESTS PASSED!")
