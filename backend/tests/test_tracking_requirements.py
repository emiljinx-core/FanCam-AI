import sys
from pathlib import Path
import numpy as np
import pytest

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.tracking import ByteTracker, Detection, Track, TrackState

def test_detection_coordinate_invariants():
    """Verify Detection class consistently enforces [x1, y1, x2, y2]."""
    det = Detection(box=[50.0, 60.0, 150.0, 200.0], confidence=0.95, class_id=0)
    assert det.x1 == 50.0
    assert det.y1 == 60.0
    assert det.x2 == 150.0
    assert det.y2 == 200.0
    assert det.width == 100.0
    assert det.height == 140.0
    assert det.area == 14000.0
    assert det.center == (100.0, 130.0)

    # Invalid box coordinates should raise ValueError
    with pytest.raises(ValueError):
        Detection(box=[150.0, 60.0, 50.0, 200.0], confidence=0.8) # x2 < x1

def test_track_state_enum():
    """Verify TrackState enum values."""
    assert TrackState.TENTATIVE.value == 1
    assert TrackState.CONFIRMED.value == 2
    assert TrackState.LOST.value == 3
    assert TrackState.DELETED.value == 4

def test_low_confidence_detection_association():
    """
    ByteTrack core feature:
    A confirmed track must associate with a low-confidence detection (e.g. 0.25)
    in the second association stage, preventing premature loss.
    """
    tracker = ByteTracker(high_thresh=0.5, low_thresh=0.1, match_thresh_low=0.7)
    tracker.reset()

    # Frame 1: Person detected with high confidence (0.9)
    det_f1 = [Detection(box=[100.0, 100.0, 150.0, 250.0], confidence=0.9)]
    tracks_f1 = tracker.update(det_f1)
    assert len(tracks_f1) == 1
    track_id = tracks_f1[0].track_id

    # Frame 2: Person partially occluded / blurry -> confidence drops to 0.25 (below high_thresh=0.5)
    det_f2 = [Detection(box=[104.0, 102.0, 154.0, 252.0], confidence=0.25)]
    tracks_f2 = tracker.update(det_f2)

    assert len(tracks_f2) == 1, "Track must be maintained via 2nd-stage low-confidence association"
    assert tracks_f2[0].track_id == track_id, "Track ID must remain identical"
    assert tracks_f2[0].confidence == 0.25

def test_temporary_missing_detections_and_track_recovery():
    """
    Verify track recovery:
    When a detection vanishes for a few frames (e.g. full occlusion),
    the track transitions to LOST, and when the detection reappears, it is recovered.
    """
    tracker = ByteTracker(high_thresh=0.5, low_thresh=0.1, track_buffer=10)
    tracker.reset()

    # Frame 1: Detected
    tracks_1 = tracker.update([Detection(box=[100.0, 100.0, 150.0, 250.0], confidence=0.85)])
    assert len(tracks_1) == 1
    orig_id = tracks_1[0].track_id

    # Frames 2, 3: Missing detection (person behind pillar)
    tracks_2 = tracker.update([])
    assert len(tracks_2) == 0, "No active confirmed tracks during total occlusion"
    assert len(tracker.lost_stracks) == 1
    assert tracker.lost_stracks[0].state == TrackState.LOST

    tracks_3 = tracker.update([])
    assert len(tracks_3) == 0
    assert tracker.lost_stracks[0].time_since_update == 2

    # Frame 4: Reappears slightly shifted
    tracks_4 = tracker.update([Detection(box=[108.0, 105.0, 158.0, 255.0], confidence=0.88)])
    assert len(tracks_4) == 1, "Track should be recovered from LOST pool"
    assert tracks_4[0].track_id == orig_id, f"Recovered track should maintain ID {orig_id}, got {tracks_4[0].track_id}"
    assert tracks_4[0].state == TrackState.CONFIRMED

def test_track_expiration_after_configured_buffer():
    """
    Verify track expiration:
    When missing for > track_buffer frames, the track is permanently deleted.
    """
    buffer_len = 3
    tracker = ByteTracker(high_thresh=0.5, low_thresh=0.1, track_buffer=buffer_len)
    tracker.reset()

    # Frame 1: Detected
    _ = tracker.update([Detection(box=[100.0, 100.0, 150.0, 250.0], confidence=0.9)])

    # Update with empty frames exceeding buffer
    for i in range(buffer_len + 2):
        _ = tracker.update([])

    # Both active and lost pools must be empty (track expired & deleted)
    assert len(tracker.tracked_stracks) == 0
    assert len(tracker.lost_stracks) == 0

    # If a detection appears now at the same location, it should be treated as a brand new track
    tracks_new = tracker.update([Detection(box=[100.0, 100.0, 150.0, 250.0], confidence=0.9)])
    assert len(tracks_new) == 1
    assert tracks_new[0].track_id != 1, "Expired track ID must not be reused"

def test_duplicate_assignment_prevention():
    """
    Bijective matching check:
    One detection must NEVER be assigned to multiple tracks.
    One track must NEVER match multiple detections.
    """
    tracker = ByteTracker(high_thresh=0.5, low_thresh=0.1)
    tracker.reset()

    # Frame 1: Two distinct tracks initialized
    dets_f1 = [
        Detection(box=[50.0, 50.0, 100.0, 150.0], confidence=0.9),   # Subject A
        Detection(box=[60.0, 50.0, 110.0, 150.0], confidence=0.9),   # Subject B (close to A)
    ]
    tracks_f1 = tracker.update(dets_f1)
    assert len(tracks_f1) == 2
    id_a, id_b = tracks_f1[0].track_id, tracks_f1[1].track_id
    assert id_a != id_b

    # Frame 2: Only ONE detection is present, overlapping both tracks
    single_det = [Detection(box=[55.0, 50.0, 105.0, 150.0], confidence=0.9)]
    tracks_f2 = tracker.update(single_det)

    # Exactly 1 track must be updated; the other must NOT receive duplicate assignment
    assert len(tracks_f2) == 1, "Only one track can be assigned to the single detection"
    assigned_id = tracks_f2[0].track_id
    assert assigned_id in (id_a, id_b)

    # The other track must be in lost pool
    assert len(tracker.lost_stracks) == 1
    unassigned_id = tracker.lost_stracks[0].track_id
    assert unassigned_id != assigned_id
