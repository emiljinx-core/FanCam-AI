import sys
from pathlib import Path
import numpy as np
import pytest

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.tracking import TargetMatcher, TargetState, Track, TrackState

def make_unit_vector(dim: int, seed: int) -> np.ndarray:
    np.random.seed(seed)
    v = np.random.randn(dim).astype(np.float32)
    return v / np.linalg.norm(v)

def create_similar_vector(base: np.ndarray, similarity: float) -> np.ndarray:
    """Creates a unit vector having approximately the specified cosine similarity with base."""
    dim = len(base)
    orthogonal = np.random.randn(dim).astype(np.float32)
    orthogonal -= np.dot(base, orthogonal) * base
    orthogonal /= np.linalg.norm(orthogonal)
    sim = max(-1.0, min(1.0, similarity))
    combined = sim * base + np.sqrt(max(0.0, 1.0 - sim ** 2)) * orthogonal
    return combined / np.linalg.norm(combined)

def make_track(track_id: int, box, feature, conf=0.9):
    return Track(
        track_id=track_id,
        box=box,
        confidence=conf,
        state=TrackState.CONFIRMED,
        feature=feature,
    )

def test_enforce_actual_reference_immutability():
    """
    Requirement 1: Enforce actual reference immutability.
    Verifies that self._immutable_reference is strictly read-only and
    cannot be modified in-place by external operations.
    """
    ref_sig = make_unit_vector(512, seed=123)
    matcher = TargetMatcher(reference_signature=ref_sig)

    # 1. The array flag writeable must be False
    assert matcher.immutable_reference.flags.writeable is False

    # 2. Attempting in-place modification must raise ValueError
    with pytest.raises(ValueError):
        matcher.immutable_reference[0] = 999.0

    with pytest.raises(ValueError):
        matcher._immutable_reference += 1.0

def test_prevent_cumulative_gallery_identity_drift():
    """
    Requirement 2: Prevent cumulative gallery identity drift.
    Simulate a chain drift attack:
      v0: Original Reference (1.0 with ref)
      v1: Close to v0 (sim=0.76 with ref) -> Admitted to gallery
      v2: Close to v1 (sim=0.76 with v1), but drifts further away from v0 (sim=0.68 with ref)!
    In naive systems, v2 would be admitted because max(sim_gallery)=0.76.
    In our system, v2 MUST BE REJECTED from the gallery because its similarity
    directly against the original immutable reference (0.68) is below gallery_update_threshold (0.75)!
    """
    ref_sig = make_unit_vector(512, seed=456)
    matcher = TargetMatcher(
        reference_signature=ref_sig,
        similarity_threshold=0.60,
        gallery_update_threshold=0.75,
    )

    assert matcher.gallery_size == 1  # Contains only initial reference copy

    # Step 1: Feature v1 is close to original reference (sim=0.78 >= 0.75)
    v1 = create_similar_vector(ref_sig, similarity=0.78)
    res1 = matcher.match_target(frame_index=0, active_tracks=[make_track(1, [10, 10, 50, 50], v1)])
    assert res1.state == TargetState.TRACKED
    assert matcher.gallery_size == 2  # Admitted safely

    # Step 2: Feature v2 has high similarity with v1 (0.80), but its similarity to ref_sig is only 0.68 (< 0.75)!
    # Construct v2 such that dot(v2, ref_sig) = 0.68, dot(v2, v1) >= 0.75
    v2 = create_similar_vector(ref_sig, similarity=0.68)
    res2 = matcher.match_target(frame_index=1, active_tracks=[make_track(1, [15, 15, 55, 55], v2)])

    # It can be temporarily tracked under active lock because effective_sim >= 0.55
    assert res2.state == TargetState.TRACKED

    # CRITICAL INVARIANT: It must NOT be added to the gallery because ref_similarity < 0.75!
    assert matcher.gallery_size == 2, (
        f"Gallery should NOT admit drifted vector v2! Size was {matcher.gallery_size}"
    )

def test_ambiguous_candidate_rejection_margin():
    """Verify ambiguous candidate rejection when margin < ambiguity_margin."""
    ref_sig = make_unit_vector(512, seed=42)
    matcher = TargetMatcher(
        reference_signature=ref_sig,
        similarity_threshold=0.60,
        ambiguity_margin=0.08,
    )

    feat_best = create_similar_vector(ref_sig, similarity=0.72)
    feat_second = create_similar_vector(ref_sig, similarity=0.69)

    t1 = make_track(1, [100.0, 100.0, 150.0, 250.0], feat_best)
    t2 = make_track(2, [200.0, 100.0, 250.0, 250.0], feat_second)

    res = matcher.match_target(frame_index=0, active_tracks=[t1, t2])
    assert res.state == TargetState.REACQUIRING
    assert res.is_ambiguous is True
    assert res.box is None
    assert matcher.active_track_id is None

def test_explicit_tracking_states_lifecycle():
    """Verify TRACKED -> REACQUIRING -> LOST -> TRACKED lifecycle."""
    ref_sig = make_unit_vector(512, seed=99)
    matcher = TargetMatcher(
        reference_signature=ref_sig,
        similarity_threshold=0.60,
        max_lost_frames=3,
    )

    feat_target = create_similar_vector(ref_sig, similarity=0.90)
    track_target = make_track(1, [100.0, 100.0, 150.0, 250.0], feat_target)

    # 1. Target detected and locked
    res1 = matcher.match_target(0, [track_target])
    assert res1.state == TargetState.TRACKED

    # 2. Target missing for 2 frames (< max_lost=3) -> REACQUIRING
    assert matcher.match_target(1, []).state == TargetState.REACQUIRING
    assert matcher.match_target(2, []).state == TargetState.REACQUIRING

    # 3. Target missing for frame 4 (> max_lost=3) -> LOST
    assert matcher.match_target(3, []).state == TargetState.REACQUIRING
    assert matcher.match_target(4, []).state == TargetState.LOST

    # 4. Target reappears (reacquired) -> TRACKED
    track_reacquired = make_track(5, [110.0, 105.0, 160.0, 255.0], feat_target)
    res_rec = matcher.match_target(5, [track_reacquired])
    assert res_rec.state == TargetState.TRACKED
    assert res_rec.active_track_id == 5
