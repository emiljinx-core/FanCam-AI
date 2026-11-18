import os
import sys
from io import BytesIO
from pathlib import Path

# Insert backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

# Helper: Create dummy valid MP4 header (ftyp box)
def make_dummy_mp4_bytes(size: int) -> bytes:
    # 4 bytes size (0x00, 0x00, 0x00, 0x20), 4 bytes 'ftyp', 4 bytes 'isom', padding
    header = b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41"
    if size < len(header):
        return header[:size]
    return header + b"\x00" * (size - len(header))

def test_1_valid_upload():
    print("Running Test 1: Valid upload under 100 MiB...")
    data = make_dummy_mp4_bytes(5 * 1024 * 1024)  # 5 MiB
    response = client.post(
        "/api/upload",
        files={"file": ("my_cool_dance.mp4", BytesIO(data), "video/mp4")},
    )
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    body = response.json()
    video_id = body["video_id"]
    assert body["filename"] == "my_cool_dance.mp4"
    assert body["size_bytes"] == 5 * 1024 * 1024
    
    # Check that disk path does NOT use original filename
    stored_file = settings.UPLOADS_DIR / video_id / "source.mp4"
    assert stored_file.exists(), f"Stored file should be at {stored_file}"
    assert not (settings.UPLOADS_DIR / video_id / "my_cool_dance.mp4").exists(), "Original filename must not be used on disk!"
    print("✓ Test 1 Passed: Valid upload stored securely.")

def test_2_exactly_100_mib():
    print("Running Test 2: Exactly 100 MiB upload accepted...")
    exact_100_mib = 100 * 1024 * 1024
    # To test without consuming 100MB RAM, generate BytesIO
    data = make_dummy_mp4_bytes(exact_100_mib)
    response = client.post(
        "/api/upload",
        files={"file": ("limit.mp4", BytesIO(data), "video/mp4")},
    )
    assert response.status_code == 201, f"Expected 201 for 100 MiB, got {response.status_code}: {response.text}"
    video_id = response.json()["video_id"]
    stored_file = settings.UPLOADS_DIR / video_id / "source.mp4"
    assert stored_file.exists()
    # Clean up large test file
    import shutil
    shutil.rmtree(settings.UPLOADS_DIR / video_id, ignore_errors=True)
    print("✓ Test 2 Passed: Exactly 100 MiB accepted.")

def test_3_oversized_file():
    print("Running Test 3: Oversized upload (> 100 MiB) rejected...")
    oversized = (100 * 1024 * 1024) + 1024  # 100 MiB + 1 KB
    data = make_dummy_mp4_bytes(oversized)
    
    # Record directories before upload
    dirs_before = set(os.listdir(settings.UPLOADS_DIR)) if settings.UPLOADS_DIR.exists() else set()
    
    response = client.post(
        "/api/upload",
        files={"file": ("too_large.mp4", BytesIO(data), "video/mp4")},
    )
    assert response.status_code == 413, f"Expected 413, got {response.status_code}: {response.text}"
    assert "Please upload a file with less than 100 MB." in response.json()["detail"]
    
    # Check no leftover partial files/directories
    dirs_after = set(os.listdir(settings.UPLOADS_DIR)) if settings.UPLOADS_DIR.exists() else set()
    assert dirs_before == dirs_after, f"Leftover directories found: {dirs_after - dirs_before}"
    print("✓ Test 3 Passed: Rejected with exact message and no leftover files.")

def test_4_empty_file():
    print("Running Test 4: Empty file rejected...")
    dirs_before = set(os.listdir(settings.UPLOADS_DIR)) if settings.UPLOADS_DIR.exists() else set()
    response = client.post(
        "/api/upload",
        files={"file": ("empty.mp4", BytesIO(b""), "video/mp4")},
    )
    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
    dirs_after = set(os.listdir(settings.UPLOADS_DIR)) if settings.UPLOADS_DIR.exists() else set()
    assert dirs_before == dirs_after, "No leftover directories allowed on empty file failure."
    print("✓ Test 4 Passed: Empty file rejected and cleaned up.")

def test_5_unsupported_ext_spoofed_mime():
    print("Running Test 5: Unsupported extension with spoofed MIME rejected...")
    dirs_before = set(os.listdir(settings.UPLOADS_DIR)) if settings.UPLOADS_DIR.exists() else set()
    response = client.post(
        "/api/upload",
        files={"file": ("malicious.exe", BytesIO(b"fakecontent"), "video/mp4")},
    )
    assert response.status_code == 415, f"Expected 415, got {response.status_code}: {response.text}"
    assert "Unsupported container" in response.json()["detail"]
    dirs_after = set(os.listdir(settings.UPLOADS_DIR)) if settings.UPLOADS_DIR.exists() else set()
    assert dirs_before == dirs_after, "No leftover directory on invalid extension."
    print("✓ Test 5 Passed: Spoofed MIME rejected.")

def test_6_allowed_ext_invalid_content():
    print("Running Test 6: Allowed extension with invalid content rejected...")
    dirs_before = set(os.listdir(settings.UPLOADS_DIR)) if settings.UPLOADS_DIR.exists() else set()
    # File named .mp4 but containing random text / non-video header
    response = client.post(
        "/api/upload",
        files={"file": ("fake_video.mp4", BytesIO(b"NOT A REAL VIDEO CONTENT HEADER"), "video/mp4")},
    )
    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
    assert "Unsupported container" in response.json()["detail"]
    dirs_after = set(os.listdir(settings.UPLOADS_DIR)) if settings.UPLOADS_DIR.exists() else set()
    assert dirs_before == dirs_after, "No leftover directory on invalid content."
    print("✓ Test 6 Passed: Invalid container content rejected and cleaned up.")

def test_7_no_static_exposure():
    print("Running Test 7: Verify uploads directory is NOT exposed via static routes...")
    # Attempting to fetch anything from /static/uploads should 404
    response = client.get("/static/uploads/some_video.mp4")
    assert response.status_code == 404, f"Expected 404 for private upload access, got {response.status_code}"
    print("✓ Test 7 Passed: Private uploads are not accessible via static route.")

if __name__ == "__main__":
    test_1_valid_upload()
    test_2_exactly_100_mib()
    test_3_oversized_file()
    test_4_empty_file()
    test_5_unsupported_ext_spoofed_mime()
    test_6_allowed_ext_invalid_content()
    test_7_no_static_exposure()
    print("\nALL 7 TESTS PASSED SUCCESSFULLY!")
