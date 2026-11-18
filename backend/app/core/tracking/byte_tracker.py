from typing import List, Optional, Tuple
import numpy as np

from app.core.tracking.base_tracker import BaseTracker, Track, Detection, TrackState
from app.core.tracking.kalman_filter import KalmanBoxFilter, compute_iou_matrix, linear_assignment


class STrack:
    """Internal track state representation for ByteTrack with Kalman filtering."""
    _count = 0

    def __init__(self, detection: Detection):
        STrack._count += 1
        self.track_id = STrack._count
        self.state = TrackState.TENTATIVE
        self.is_activated = False

        self.confidence = detection.confidence
        self.class_id = detection.class_id
        self.feature = detection.feature

        self.kalman_filter = KalmanBoxFilter()
        measurement = self._box_to_z(detection.box)
        self.mean, self.covariance = self.kalman_filter.initiate(measurement)

        self.age = 0
        self.hits = 1
        self.time_since_update = 0

    @staticmethod
    def _box_to_z(box: List[float]) -> np.ndarray:
        """Converts [x1, y1, x2, y2] to [center_x, center_y, aspect_ratio (w/h), height]."""
        x1, y1, x2, y2 = box
        w = max(1e-4, x2 - x1)
        h = max(1e-4, y2 - y1)
        cx = x1 + w / 2.0
        cy = y1 + h / 2.0
        return np.array([cx, cy, w / h, h], dtype=np.float32)

    @staticmethod
    def _z_to_box(mean: np.ndarray) -> List[float]:
        """Converts [center_x, center_y, aspect_ratio, height] back to [x1, y1, x2, y2]."""
        cx, cy, a, h = mean[:4]
        w = a * h
        x1 = cx - w / 2.0
        y1 = cy - h / 2.0
        x2 = cx + w / 2.0
        y2 = cy + h / 2.0
        return [float(x1), float(y1), float(x2), float(y2)]

    @property
    def box(self) -> List[float]:
        return self._z_to_box(self.mean)

    def predict(self):
        self.mean, self.covariance = self.kalman_filter.predict(self.mean, self.covariance)
        self.age += 1
        self.time_since_update += 1

    def update(self, detection: Detection):
        measurement = self._box_to_z(detection.box)
        self.mean, self.covariance = self.kalman_filter.update(self.mean, self.covariance, measurement)
        self.confidence = detection.confidence
        self.hits += 1
        self.time_since_update = 0
        self.state = TrackState.CONFIRMED
        self.is_activated = True
        if detection.feature is not None:
            self.feature = detection.feature

    def mark_lost(self):
        self.state = TrackState.LOST

    def mark_deleted(self):
        self.state = TrackState.DELETED

    def to_public_track(self) -> Track:
        return Track(
            track_id=self.track_id,
            box=self.box,
            confidence=self.confidence,
            state=self.state,
            class_id=self.class_id,
            age=self.age,
            hits=self.hits,
            time_since_update=self.time_since_update,
            feature=self.feature,
        )


class ByteTracker(BaseTracker):
    """
    ByteTrack implementation:
    - 2-stage association (high-confidence followed by low-confidence recovery).
    - Bijective assignment preventing duplicate track/detection matches.
    - Handles temporary missing detections and track recovery.
    - Enforces track buffer buffer expiration.
    """

    def __init__(
        self,
        high_thresh: float = 0.5,
        low_thresh: float = 0.1,
        match_thresh_high: float = 0.8,
        match_thresh_low: float = 0.5,
        track_buffer: int = 30,
    ):
        self.high_thresh = high_thresh
        self.low_thresh = low_thresh
        self.match_thresh_high = match_thresh_high
        self.match_thresh_low = match_thresh_low
        self.track_buffer = track_buffer

        self.tracked_stracks: List[STrack] = []
        self.lost_stracks: List[STrack] = []
        self.frame_id = 0

    def reset(self) -> None:
        self.tracked_stracks.clear()
        self.lost_stracks.clear()
        self.frame_id = 0
        STrack._count = 0

    def update(
        self,
        detections: List[Detection],
        frame_bgr: Optional[np.ndarray] = None,
    ) -> List[Track]:
        self.frame_id += 1

        # 1. Split detections into high-score (D_high) and low-score (D_low)
        d_high: List[Detection] = []
        d_low: List[Detection] = []

        for det in detections:
            if det.confidence >= self.high_thresh:
                d_high.append(det)
            elif det.confidence >= self.low_thresh:
                d_low.append(det)

        # 2. Predict positions for all tracked and lost tracks
        for strack in self.tracked_stracks:
            strack.predict()
        for strack in self.lost_stracks:
            strack.predict()

        # Candidates pool for primary matching: tracked + lost
        candidates = self.tracked_stracks + self.lost_stracks

        # 3. First Association: Match candidates with high-confidence detections
        if len(candidates) > 0 and len(d_high) > 0:
            track_boxes = np.array([t.box for t in candidates], dtype=np.float32)
            det_boxes = np.array([d.box for d in d_high], dtype=np.float32)
            cost_matrix = 1.0 - compute_iou_matrix(track_boxes, det_boxes)

            matches_1, unmatched_tracks_1, unmatched_dets_1 = linear_assignment(
                cost_matrix, threshold=1.0 - (1.0 - self.match_thresh_high)
            )
        else:
            matches_1 = []
            unmatched_tracks_1 = list(range(len(candidates)))
            unmatched_dets_1 = list(range(len(d_high)))

        activated_tracks: List[STrack] = []
        refind_tracks: List[STrack] = []

        for t_idx, d_idx in matches_1:
            track = candidates[t_idx]
            det = d_high[d_idx]
            if track.state == TrackState.CONFIRMED:
                track.update(det)
                activated_tracks.append(track)
            else:
                track.update(det)
                refind_tracks.append(track)

        # 4. Second Association: Match remaining unmatched confirmed tracks with low-confidence detections
        rem_confirmed_tracks = [
            candidates[i]
            for i in unmatched_tracks_1
            if candidates[i].state == TrackState.CONFIRMED
        ]

        if len(rem_confirmed_tracks) > 0 and len(d_low) > 0:
            rem_boxes = np.array([t.box for t in rem_confirmed_tracks], dtype=np.float32)
            det_low_boxes = np.array([d.box for d in d_low], dtype=np.float32)
            cost_matrix_low = 1.0 - compute_iou_matrix(rem_boxes, det_low_boxes)

            matches_2, unmatched_tracks_2, _ = linear_assignment(
                cost_matrix_low, threshold=1.0 - (1.0 - self.match_thresh_low)
            )
        else:
            matches_2 = []
            unmatched_tracks_2 = list(range(len(rem_confirmed_tracks)))

        for t_idx, d_idx in matches_2:
            track = rem_confirmed_tracks[t_idx]
            det = d_low[d_idx]
            track.update(det)
            activated_tracks.append(track)

        # 5. Deal with lost tracks (unmatched confirmed tracks)
        lost_from_confirmed = [rem_confirmed_tracks[i] for i in unmatched_tracks_2]
        for track in lost_from_confirmed:
            track.mark_lost()

        # 6. Initialize new tracks from unmatched high-confidence detections
        new_tracks: List[STrack] = []
        for d_idx in unmatched_dets_1:
            det = d_high[d_idx]
            # Initialize as confirmed if above threshold
            new_track = STrack(det)
            new_track.state = TrackState.CONFIRMED
            new_tracks.append(new_track)

        # 7. Update tracker state pools & enforce buffer expiration
        # Active pool
        self.tracked_stracks = [
            t for t in (activated_tracks + refind_tracks + new_tracks)
            if t.state == TrackState.CONFIRMED
        ]

        # Lost pool (update with newly lost tracks and keep existing within buffer)
        current_lost = [
            t for t in self.lost_stracks
            if t not in refind_tracks and t not in activated_tracks
        ] + lost_from_confirmed

        self.lost_stracks = []
        for track in current_lost:
            if track.time_since_update <= self.track_buffer:
                self.lost_stracks.append(track)
            else:
                track.mark_deleted()

        # Return confirmed active tracks
        return [t.to_public_track() for t in self.tracked_stracks]
