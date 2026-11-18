import sys
from pathlib import Path
import numpy as np
import pytest

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.tracking import DeepSortTracker, Detection, Track, TrackState

def generate_orthogonal_features(dim: int = 512):
    """Generate two orthogonal unit vectors representing two distinct people."""
    f1 = np.zeros(dim, dtype=np.float32)
    f2 = np.zeros(dim, dtype=np.float32)
    f1[: dim // 2] = 1.0 / np.sqrt(dim // 2)
    f2[dim // 2 :] = 1.0 / np.sqrt(dim // 2)
    return f1, f2

def test_deepsort_initialization_and_interface():
    """Verify DeepSortTracker implements BaseTracker contract."""
    tracker = DeepSortTracker()
    assert hasattr(tracker, "update")
    assert hasattr(tracker, "reset")
    tracker.reset()
    tracks = tracker.update([])
    assert isinstance(tracks, list)
    assert len(tracks) == 0

def test_deepsort_tentative_to_confirmed_lifecycle():
    """Verify tracks transition from TENTATIVE to CONFIRMED after n_init consecutive hits."""
    tracker = DeepSortTracker(n_init=3)
    tracker.reset()

    det = Detection(box=[100.0, 100.0, 150.0, 250.0], confidence=0.9)

    # Frame 1: Tentative (not returned in public active tracks)
    tracks_1 = tracker.update([det])
    assert len(tracks_1) == 0
    assert len(tracker.tracks) == 1
    assert tracker.tracks[0].state == TrackState.TENTATIVE

    # Frame 2: Still tentative
    tracks_2 = tracker.update([det])
    assert len(tracks_2) == 0
    assert tracker.tracks[0].hits == 2

    # Frame 3: Reaches n_init=3 -> Confirmed
    tracks_3 = tracker.update([det])
    assert len(tracks_3) == 1
    assert tracks_3[0].state == TrackState.CONFIRMED
    assert tracker.tracks[0].is_confirmed()

def test_appearance_based_identity_association_under_spatial_cross():
    """
    Core DeepSORT capability:
    Two subjects cross paths with high spatial overlap.
    Their visual appearance embeddings ensure tracks NEVER swap identities.
    """
    feat_a, feat_b = generate_orthogonal_features(512)
    tracker = DeepSortTracker(n_init=1, max_cosine_distance=0.4)
    tracker.reset()

    # Frame 1: Subject A at x=180, Subject B at x=220
    det_a1 = Detection(box=[180.0, 100.0, 230.0, 250.0], confidence=0.9, feature=feat_a)
    det_b1 = Detection(box=[220.0, 100.0, 270.0, 250.0], confidence=0.9, feature=feat_b)
    tracks_1 = tracker.update([det_a1, det_b1])
    assert len(tracks_1) == 2

    id_a = next(t.track_id for t in tracks_1 if t.x1 < 200)
    id_b = next(t.track_id for t in tracks_1 if t.x1 > 200)
    assert id_a != id_b

    # Frame 2: Both subjects cross at overlapping coordinates (A at 202, B at 198)
    # Pure motion/IoU would be ambiguous, but appearance features distinguish them cleanly
    det_a2 = Detection(box=[202.0, 100.0, 252.0, 250.0], confidence=0.9, feature=feat_a)
    det_b2 = Detection(box=[198.0, 100.0, 248.0, 250.0], confidence=0.9, feature=feat_b)
    tracks_2 = tracker.update([det_a2, det_b2])
    assert len(tracks_2) == 2

    # Check that feat_a matched id_a and feat_b matched id_b
    track_dict_2 = {t.track_id: t for t in tracks_2}
    assert id_a in track_dict_2
    assert id_b in track_dict_2

    # Frame 3: Subjects separate (A moves right to 230, B moves left to 170)
    det_a3 = Detection(box=[230.0, 100.0, 280.0, 250.0], confidence=0.9, feature=feat_a)
    det_b3 = Detection(box=[170.0, 100.0, 220.0, 250.0], confidence=0.9, feature=feat_b)
    tracks_3 = tracker.update([det_a3, det_b3])
    assert len(tracks_3) == 2

    final_track_a = next(t for t in tracks_3 if t.track_id == id_a)
    final_track_b = next(t for t in tracks_3 if t.track_id == id_b)

    # Subject A should now be on the right (x=230) and Subject B on the left (x=170)
    assert final_track_a.x1 > 220.0, "Subject A identity must remain with feature A"
    assert final_track_b.x1 < 180.0, "Subject B identity must remain with feature B"

def test_deepsort_occlusion_and_reacquisition_via_appearance():
    """
    Verify DeepSORT occlusion handling:
    Subject is occluded (no detection for 5 frames).
    When they reappear, the appearance matching cascade reconnects them to their existing track.
    """
    feat_target, _ = generate_orthogonal_features(512)
    tracker = DeepSortTracker(n_init=1, max_age=15, max_cosine_distance=0.4)
    tracker.reset()

    # Frame 1: Target visible
    tracks_1 = tracker.update([Detection(box=[100.0, 100.0, 150.0, 250.0], confidence=0.9, feature=feat_target)])
    assert len(tracks_1) == 1
    target_id = tracks_1[0].track_id

    # Frames 2 to 6: Target completely occluded (missing for 5 frames)
    for _ in range(5):
        tracks_empty = tracker.update([])
        assert len(tracks_empty) == 0

    # Verify track transitioned to LOST (not deleted yet because max_age=15)
    lost_track = next((t for t in tracker.tracks if t.track_id == target_id), None)
    assert lost_track is not None
    assert lost_track.state == TrackState.LOST
    assert lost_track.time_since_update == 5

    # Frame 7: Target reappears with their appearance feature
    reappear_det = Detection(box=[105.0, 102.0, 155.0, 252.0], confidence=0.9, feature=feat_target)
    tracks_recovered = tracker.update([reappear_det])

    assert len(tracks_recovered) == 1
    assert tracks_recovered[0].track_id == target_id, "Track must be reacquired with identical ID after occlusion"
    assert tracks_recovered[0].state == TrackState.CONFIRMED

def test_mahalanobis_gating_blocks_distant_appearance_imposter():
    """
    Verify Mahalanobis distance gating:
    Even if an imposter somehow had a similar appearance vector,
    if they are physically in an impossible spatial location (far outside Kalman gate),
    the association is blocked.
    """
    feat_target, _ = generate_orthogonal_features(512)
    tracker = DeepSortTracker(n_init=1, max_age=5)
    tracker.reset()

    # Track at top-left [10, 10, 50, 50]
    _ = tracker.update([Detection(box=[10.0, 10.0, 50.0, 50.0], confidence=0.9, feature=feat_target)])

    # Far away detection at bottom-right [1000, 1000, 1050, 1050] with same feature
    imposter_det = Detection(box=[1000.0, 1000.0, 1050.0, 1050.0], confidence=0.9, feature=feat_target)
    tracks_2 = tracker.update([imposter_det])

    # The existing track must NOT jump across the screen
    # Instead, a new track is created
    assert len(tracks_2) == 1
    assert tracks_2[0].track_id != 1, "Distant detection must not be assigned to original track due to Mahalanobis gate"
