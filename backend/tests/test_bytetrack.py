import sys
from pathlib import Path
import numpy as np
import cv2
import pytest

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.tracking import ByteTracker, Detection, Track, TrackState
from app.core.detector import PersonDetector
from app.config import settings

@pytest.fixture
def real_frames():
    """Load local test scene and generate realistic consecutive frames."""
    test_scene_path = settings.MODELS_DIR / "test_scene.jpg"
    assert test_scene_path.exists(), f"Local test scene missing at {test_scene_path}"
    f1 = cv2.imread(str(test_scene_path))
    assert f1 is not None, "Failed to decode test scene image"

    f2 = np.roll(f1, 6, axis=1)
    return f1, f2

def get_frame_detections(frame: np.ndarray, conf_thresh: float = 0.25):
    """Run detector to get standard Detection objects for tracker."""
    raw_dets = PersonDetector.detect_people(frame, conf_threshold=conf_thresh)
    return [
        Detection(
            box=[d["x1"], d["y1"], d["x2"], d["y2"]],
            confidence=d["confidence"] / 100.0,
            class_id=0,
        )
        for d in raw_dets
    ]

def test_bytetracker_initialization_and_interface():
    tracker = ByteTracker(high_thresh=0.5, low_thresh=0.1)
    assert hasattr(tracker, "update")
    assert hasattr(tracker, "reset")
    tracker.reset()

def test_bytetracker_empty_frame():
    tracker = ByteTracker(high_thresh=0.5, low_thresh=0.1)
    tracker.reset()
    tracks = tracker.update([])
    assert isinstance(tracks, list)
    assert len(tracks) == 0

def test_bytetracker_sequential_tracking_and_id_persistence(real_frames):
    f1, f2 = real_frames
    tracker = ByteTracker(high_thresh=0.4, low_thresh=0.1)
    tracker.reset()

    # Frame 1
    dets_1 = get_frame_detections(f1)
    tracks_1 = tracker.update(dets_1)
    assert isinstance(tracks_1, list)
    assert len(tracks_1) >= 3, f"Expected >= 3 tracks in frame 1, got {len(tracks_1)}"

    track_ids_1 = {t.track_id for t in tracks_1}

    # Verify track box properties
    for t in tracks_1:
        assert isinstance(t.track_id, int)
        assert t.track_id > 0
        assert t.state == TrackState.CONFIRMED
        assert len(t.tlbr) == 4
        assert t.area > 0

    # Frame 2
    dets_2 = get_frame_detections(f2)
    tracks_2 = tracker.update(dets_2)
    assert isinstance(tracks_2, list)
    assert len(tracks_2) >= 3, f"Expected >= 3 tracks in frame 2, got {len(tracks_2)}"

    track_ids_2 = {t.track_id for t in tracks_2}

    # Verify ID persistence across movement
    overlap = track_ids_1.intersection(track_ids_2)
    assert len(overlap) >= 3, f"Track IDs must persist across frames! IDs F1: {track_ids_1}, IDs F2: {track_ids_2}"

def test_bytetracker_reset_clears_state(real_frames):
    f1, _ = real_frames
    tracker = ByteTracker(high_thresh=0.4, low_thresh=0.1)
    tracker.reset()
    dets_1 = get_frame_detections(f1)
    _ = tracker.update(dets_1)
    tracker.reset()
    # Post-reset frame 1 should reinitialize cleanly
    tracks_fresh = tracker.update(dets_1)
    assert len(tracks_fresh) >= 3
