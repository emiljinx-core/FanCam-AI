from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Sequence
import numpy as np
import cv2

from app.core.tracking.base_tracker import Track
from app.core.reid import OSNetReIDExtractor


class TargetState(Enum):
    """Explicit tracking states for the target person."""
    TRACKED = "tracked"          # Target is actively tracked with high confidence
    REACQUIRING = "reacquiring"  # Candidate matches are under evaluation or ambiguous
    LOST = "lost"                # Target is not visible in the frame (occluded or exited)


@dataclass
class TargetMatchResult:
    """Per-frame result returned by the TargetMatcher."""
    frame_index: int
    state: TargetState
    box: Optional[Sequence[float]]  # [x1, y1, x2, y2] if tracked/reacquired, else None
    confidence: float
    similarity: float
    active_track_id: Optional[int]
    is_ambiguous: bool = False
    message: str = ""


class TargetMatcher:
    """
    Appearance-based target identity matcher and occlusion/late-entry defense engine:
    1. Ambiguous candidate rejection: Enforces a similarity margin (margin = best_sim - second_sim).
    2. Gallery contamination prevention: Original reference signature is strictly immutable.
       Gallery only updates with unambiguous, high-similarity matches.
    3. Explicit tracking states: Distinguishes TRACKED, REACQUIRING, and LOST.
    """

    def __init__(
        self,
        reference_signature: np.ndarray,
        similarity_threshold: float = 0.60,
        ambiguity_margin: float = 0.08,
        gallery_update_threshold: float = 0.75,
        max_lost_frames: int = 15,
        gallery_budget: int = 50,
    ):
        if reference_signature is None or reference_signature.ndim != 1:
            raise ValueError("Reference signature must be a 1D feature vector.")

        # 1. Immutable reference signature (enforced read-only at numpy array level)
        norm = np.linalg.norm(reference_signature)
        if norm > 0:
            ref = (reference_signature / norm).astype(np.float32)
        else:
            ref = reference_signature.astype(np.float32)

        # Make the internal array strictly read-only
        ref.flags.writeable = False
        self._immutable_reference: np.ndarray = ref

        # 2. Appearance gallery of confirmed positive samples (for viewpoint/lighting adaptation)
        self.gallery_budget = gallery_budget
        self._gallery: List[np.ndarray] = [self._immutable_reference.copy()]

        # Thresholds
        self.similarity_threshold = similarity_threshold
        self.ambiguity_margin = ambiguity_margin
        self.gallery_update_threshold = gallery_update_threshold
        self.max_lost_frames = max_lost_frames

        # Tracking state
        self.active_track_id: Optional[int] = None
        self.consecutive_misses: int = 0
        self.last_known_box: Optional[Sequence[float]] = None

    @property
    def immutable_reference(self) -> np.ndarray:
        return self._immutable_reference

    @property
    def gallery_size(self) -> int:
        return len(self._gallery)

    def reset(self) -> None:
        """Reset matcher session while preserving the immutable signature."""
        self._gallery = [self._immutable_reference.copy()]
        self.active_track_id = None
        self.consecutive_misses = 0
        self.last_known_box = None

    def _compute_similarities(self, feature: np.ndarray) -> Tuple[float, float, float]:
        """
        Computes similarities independently:
        Returns:
            (ref_sim, gallery_sim, effective_sim)
        where:
            - ref_sim: Cosine similarity strictly against the immutable reference signature.
            - gallery_sim: Maximum cosine similarity against confirmed gallery samples.
            - effective_sim: Combined match score max(ref_sim, gallery_sim).
        """
        if feature is None or feature.size == 0:
            return 0.0, 0.0, 0.0

        norm = np.linalg.norm(feature)
        if norm <= 0:
            return 0.0, 0.0, 0.0
        feat_norm = (feature / norm).astype(np.float32)

        # 1. Similarity strictly against the immutable reference
        ref_sim = float(np.dot(self._immutable_reference, feat_norm))

        # 2. Similarity against gallery samples (if any)
        if len(self._gallery) > 0:
            gallery_arr = np.array(self._gallery, dtype=np.float32)
            gallery_sim = float(np.max(np.dot(gallery_arr, feat_norm)))
        else:
            gallery_sim = ref_sim

        effective_sim = max(ref_sim, gallery_sim)
        return ref_sim, gallery_sim, effective_sim

    def _extract_crop_feature(self, track: Track, frame_bgr: Optional[np.ndarray]) -> Optional[np.ndarray]:
        """Extract or retrieve feature vector for a track."""
        if track.feature is not None:
            return track.feature

        if frame_bgr is None:
            return None

        h_f, w_f = frame_bgr.shape[:2]
        x1 = max(0, min(int(round(track.x1)), w_f - 1))
        y1 = max(0, min(int(round(track.y1)), h_f - 1))
        x2 = max(0, min(int(round(track.x2)), w_f))
        y2 = max(0, min(int(round(track.y2)), h_f))

        if x2 <= x1 or y2 <= y1:
            return None

        crop = frame_bgr[y1:y2, x1:x2]
        try:
            feat = OSNetReIDExtractor.extract_embedding(crop)
            track.feature = feat
            return feat
        except Exception:
            return None

    def _update_gallery_safely(self, feature: np.ndarray, ref_similarity: float, is_ambiguous: bool) -> bool:
        """
        Gallery contamination & cumulative identity drift prevention:
        A candidate vector is only admitted into the gallery if:
        1. The match is completely unambiguous (is_ambiguous is False).
        2. Its similarity strictly against the ORIGINAL IMMUTABLE REFERENCE meets gallery_update_threshold.
           (Admitting a vector based solely on similarity to drifted gallery members is forbidden).
        """
        if is_ambiguous:
            return False

        # Must meet the threshold directly against the original reference signature!
        if ref_similarity < self.gallery_update_threshold:
            return False

        norm = np.linalg.norm(feature)
        if norm <= 0:
            return False
        feat_norm = (feature / norm).astype(np.float32)

        self._gallery.append(feat_norm)
        if len(self._gallery) > self.gallery_budget:
            # Pop oldest dynamic sample
            self._gallery.pop(0)
        return True

    def match_target(
        self,
        frame_index: int,
        active_tracks: List[Track],
        frame_bgr: Optional[np.ndarray] = None,
    ) -> TargetMatchResult:
        """
        Evaluate all active tracks and return unambiguous target match result.
        """
        if not active_tracks:
            self.consecutive_misses += 1
            state = TargetState.LOST if self.consecutive_misses > self.max_lost_frames else TargetState.REACQUIRING
            return TargetMatchResult(
                frame_index=frame_index,
                state=state,
                box=None,
                confidence=0.0,
                similarity=0.0,
                active_track_id=self.active_track_id,
                is_ambiguous=False,
                message="No active tracks present in frame.",
            )

        # 1. Compute similarities for all candidate tracks
        # Stores: (track, ref_sim, gallery_sim, effective_sim, feat)
        candidate_evaluations: List[Tuple[Track, float, float, float, np.ndarray]] = []
        for track in active_tracks:
            feat = self._extract_crop_feature(track, frame_bgr)
            if feat is not None:
                ref_sim, gal_sim, eff_sim = self._compute_similarities(feat)
                candidate_evaluations.append((track, ref_sim, gal_sim, eff_sim, feat))

        if not candidate_evaluations:
            self.consecutive_misses += 1
            state = TargetState.LOST if self.consecutive_misses > self.max_lost_frames else TargetState.REACQUIRING
            return TargetMatchResult(
                frame_index=frame_index,
                state=state,
                box=None,
                confidence=0.0,
                similarity=0.0,
                active_track_id=self.active_track_id,
                message="No candidate features extractable.",
            )

        # Sort candidates by effective similarity in descending order
        candidate_evaluations.sort(key=lambda x: x[3], reverse=True)
        best_track, best_ref_sim, best_gal_sim, best_eff_sim, best_feat = candidate_evaluations[0]

        # 2. Check for Ambiguous Candidates
        is_ambiguous = False
        if len(candidate_evaluations) > 1:
            _, _, _, second_eff_sim, _ = candidate_evaluations[1]
            margin = best_eff_sim - second_eff_sim
            if (
                best_eff_sim >= self.similarity_threshold
                and second_eff_sim >= (self.similarity_threshold - 0.10)
                and margin < self.ambiguity_margin
            ):
                is_ambiguous = True

        # 3. Decision Logic: Lock Verification vs Re-acquisition
        # Case A: We currently have a locked active track
        if self.active_track_id is not None:
            active_eval = next((item for item in candidate_evaluations if item[0].track_id == self.active_track_id), None)

            # If the currently locked track is present and maintains good similarity
            if active_eval is not None:
                track, ref_sim, gal_sim, eff_sim, feat = active_eval
                if eff_sim >= (self.similarity_threshold - 0.05):
                    # Lock is maintained
                    self.consecutive_misses = 0
                    self.last_known_box = track.box
                    # Update gallery ONLY if ref_sim directly satisfies gallery_update_threshold
                    self._update_gallery_safely(feat, ref_similarity=ref_sim, is_ambiguous=is_ambiguous)

                    return TargetMatchResult(
                        frame_index=frame_index,
                        state=TargetState.TRACKED,
                        box=track.box,
                        confidence=track.confidence,
                        similarity=round(eff_sim, 4),
                        active_track_id=self.active_track_id,
                        is_ambiguous=is_ambiguous,
                        message="Active lock verified.",
                    )

        # Case B: Re-acquisition or Late-Entry Mode (active track not locked or lost)
        # If best candidate is ambiguous, do not force an arbitrary association!
        if is_ambiguous:
            self.consecutive_misses += 1
            return TargetMatchResult(
                frame_index=frame_index,
                state=TargetState.REACQUIRING,
                box=None,
                confidence=best_track.confidence,
                similarity=round(best_eff_sim, 4),
                active_track_id=self.active_track_id,
                is_ambiguous=True,
                message=f"Ambiguous candidates detected (margin={best_eff_sim - second_eff_sim:.3f} < {self.ambiguity_margin}). Association deferred.",
            )

        # Unambiguous match above threshold
        if best_eff_sim >= self.similarity_threshold:
            self.active_track_id = best_track.track_id
            self.consecutive_misses = 0
            self.last_known_box = best_track.box
            # Update gallery safely requiring original-reference verification
            self._update_gallery_safely(best_feat, ref_similarity=best_ref_sim, is_ambiguous=False)

            return TargetMatchResult(
                frame_index=frame_index,
                state=TargetState.TRACKED,
                box=best_track.box,
                confidence=best_track.confidence,
                similarity=round(best_eff_sim, 4),
                active_track_id=self.active_track_id,
                is_ambiguous=False,
                message="Target successfully reacquired / locked.",
            )

        # No candidate passed the threshold
        self.consecutive_misses += 1
        state = TargetState.LOST if self.consecutive_misses > self.max_lost_frames else TargetState.REACQUIRING
        return TargetMatchResult(
            frame_index=frame_index,
            state=state,
            box=None,
            confidence=0.0,
            similarity=round(best_eff_sim, 4),
            active_track_id=self.active_track_id,
            is_ambiguous=False,
            message="No track matches target appearance threshold.",
        )
