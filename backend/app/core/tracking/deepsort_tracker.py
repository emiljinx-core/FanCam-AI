from typing import List, Tuple, Optional
import numpy as np
from scipy.spatial.distance import cdist
from scipy.optimize import linear_sum_assignment

from app.core.tracking.base_tracker import BaseTracker, Track, Detection, TrackState
from app.core.tracking.kalman_filter import KalmanBoxFilter, compute_iou_matrix, linear_assignment
from app.core.reid import OSNetReIDExtractor


# Chi-square 0.95 quantile for 4 degrees of freedom (x, y, a, h)
CHI2_INV_95 = 9.4877


class NearestNeighborDistanceMetric:
    """
    A nearest neighbor distance metric that operates on appearance feature galleries.
    For each target, returns the nearest cosine distance among all gallery vectors.
    """

    def __init__(self, metric: str = "cosine", matching_threshold: float = 0.4, budget: int = 100):
        self.metric = metric
        self.matching_threshold = matching_threshold
        self.budget = budget
        self.samples = {}  # track_id -> List[np.ndarray]

    def partial_fit(self, features: np.ndarray, targets: List[int]):
        for feature, target in zip(features, targets):
            if feature is None:
                continue
            self.samples.setdefault(target, []).append(feature)
            if len(self.samples[target]) > self.budget:
                self.samples[target].pop(0)

    def distance(self, features: np.ndarray, targets: List[int]) -> np.ndarray:
        """
        Compute cost matrix between features of detections and track targets:
        cost[i, j] = min_{f in gallery[targets[i]]} (1 - <f, features[j]>)
        """
        cost_matrix = np.zeros((len(targets), len(features)), dtype=np.float32)
        for i, target in enumerate(targets):
            gallery = self.samples.get(target, [])
            if len(gallery) == 0:
                cost_matrix[i, :] = 1.0
                continue
            gallery_arr = np.array(gallery, dtype=np.float32)
            # Cosine distance: 1 - cosine_similarity
            dists = cdist(gallery_arr, features, metric="cosine")
            cost_matrix[i, :] = np.min(dists, axis=0)
        return cost_matrix


class DeepSortTrack:
    """Internal track for DeepSORT fusing Kalman motion with appearance gallery."""
    _count = 0

    def __init__(self, detection: Detection, n_init: int, max_age: int):
        DeepSortTrack._count += 1
        self.track_id = DeepSortTrack._count
        self.state = TrackState.CONFIRMED if n_init <= 1 else TrackState.TENTATIVE
        self.hits = 1
        self.age = 1
        self.time_since_update = 0
        self._n_init = n_init
        self._max_age = max_age

        self.confidence = detection.confidence
        self.class_id = detection.class_id
        self.feature = detection.feature
        self.features: List[np.ndarray] = [detection.feature] if detection.feature is not None else []

        self.kalman_filter = KalmanBoxFilter()
        measurement = self._box_to_z(detection.box)
        self.mean, self.covariance = self.kalman_filter.initiate(measurement)
        self.hits = 1
        self.age = 1
        self.time_since_update = 0
        self._n_init = n_init
        self._max_age = max_age

        self.confidence = detection.confidence
        self.class_id = detection.class_id
        self.feature = detection.feature
        self.features: List[np.ndarray] = [detection.feature] if detection.feature is not None else []

        self.kalman_filter = KalmanBoxFilter()
        measurement = self._box_to_z(detection.box)
        self.mean, self.covariance = self.kalman_filter.initiate(measurement)

    @staticmethod
    def _box_to_z(box: List[float]) -> np.ndarray:
        x1, y1, x2, y2 = box
        w = max(1e-4, x2 - x1)
        h = max(1e-4, y2 - y1)
        cx = x1 + w / 2.0
        cy = y1 + h / 2.0
        return np.array([cx, cy, w / h, h], dtype=np.float32)

    @staticmethod
    def _z_to_box(mean: np.ndarray) -> List[float]:
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

        if detection.feature is not None:
            self.feature = detection.feature
            self.features.append(detection.feature)

        if self.state in (TrackState.TENTATIVE, TrackState.LOST) and self.hits >= self._n_init:
            self.state = TrackState.CONFIRMED

    def mark_missed(self):
        if self.state == TrackState.TENTATIVE:
            self.state = TrackState.DELETED
        elif self.time_since_update > self._max_age:
            self.state = TrackState.DELETED
        else:
            self.state = TrackState.LOST

    def is_confirmed(self) -> bool:
        return self.state in (TrackState.CONFIRMED, TrackState.LOST)

    def is_deleted(self) -> bool:
        return self.state == TrackState.DELETED

    def gating_distance(self, measurements: np.ndarray) -> np.ndarray:
        """
        Compute squared Mahalanobis distance between Kalman prediction and measurements.
        measurements: (M, 4) in [x, y, a, h] format.
        """
        d = measurements - self.mean[:4]
        # Projected measurement covariance S
        H = np.eye(4, 8)
        std = [
            (1.0 / 20) * self.mean[3],
            (1.0 / 20) * self.mean[3],
            1e-1,
            (1.0 / 20) * self.mean[3],
        ]
        R = np.diag(np.square(std))
        S = np.linalg.multi_dot((H, self.covariance, H.T)) + R
        try:
            cholesky_factor = np.linalg.cholesky(S)
            z = np.linalg.solve(cholesky_factor, d.T)
            sq_mahalanobis = np.sum(np.square(z), axis=0)
            return sq_mahalanobis
        except np.linalg.LinAlgError:
            return np.full((len(measurements),), np.inf, dtype=np.float32)

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
            features=list(self.features),
        )


class DeepSortTracker(BaseTracker):
    """
    DeepSORT Tracker:
    1. Kalman motion prediction.
    2. OSNet MSMT17 appearance embeddings (512-D).
    3. Cosine-distance appearance matching.
    4. Mahalanobis-distance gating.
    5. Hungarian assignment.
    6. Matching cascade and strict track lifecycle management.
    """

    def __init__(
        self,
        max_cosine_distance: float = 0.4,  # corresponds to similarity >= 0.60
        nn_budget: int = 100,
        n_init: int = 3,
        max_age: int = 30,
    ):
        self.max_cosine_distance = max_cosine_distance
        self.n_init = n_init
        self.max_age = max_age
        self.metric = NearestNeighborDistanceMetric(
            metric="cosine",
            matching_threshold=max_cosine_distance,
            budget=nn_budget,
        )
        self.tracks: List[DeepSortTrack] = []

    def reset(self) -> None:
        self.tracks.clear()
        self.metric.samples.clear()
        DeepSortTrack._count = 0

    def _extract_missing_features(
        self,
        detections: List[Detection],
        frame_bgr: Optional[np.ndarray],
    ):
        """Extract genuine OSNet embeddings for detections that do not already have one."""
        if frame_bgr is None:
            return
        h_frame, w_frame = frame_bgr.shape[:2]
        for det in detections:
            if det.feature is None:
                x1 = max(0, min(int(round(det.x1)), w_frame - 1))
                y1 = max(0, min(int(round(det.y1)), h_frame - 1))
                x2 = max(0, min(int(round(det.x2)), w_frame))
                y2 = max(0, min(int(round(det.y2)), h_frame))
                if x2 > x1 and y2 > y1:
                    crop = frame_bgr[y1:y2, x1:x2]
                    det.feature = OSNetReIDExtractor.extract_embedding(crop)

    def _gate_cost_matrix(
        self,
        cost_matrix: np.ndarray,
        tracks: List[DeepSortTrack],
        detections: List[Detection],
        gating_threshold: float = CHI2_INV_95,
    ) -> np.ndarray:
        """Apply Mahalanobis distance gating to prevent unfeasible associations."""
        if cost_matrix.size == 0:
            return cost_matrix

        measurements = np.array([
            DeepSortTrack._box_to_z(d.box) for d in detections
        ], dtype=np.float32)

        for i, track in enumerate(tracks):
            gating_dist = track.gating_distance(measurements)
            cost_matrix[i, gating_dist > gating_threshold] = 1e5
        return cost_matrix

    def _matching_cascade(
        self,
        tracks: List[DeepSortTrack],
        detections: List[Detection],
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """
        DeepSORT Matching Cascade:
        Prioritizes recently updated tracks by iterating over age levels.
        """
        unmatched_detections = list(range(len(detections)))
        matches = []
        track_indices = list(range(len(tracks)))

        for level in range(self.max_age):
            if len(unmatched_detections) == 0:
                break

            # Find tracks with time_since_update == level + 1
            level_track_indices = [
                k for k in track_indices if tracks[k].time_since_update == level + 1
            ]
            if len(level_track_indices) == 0:
                continue

            sub_tracks = [tracks[k] for k in level_track_indices]
            sub_dets = [detections[m] for m in unmatched_detections]

            features = np.array([d.feature for d in sub_dets if d.feature is not None], dtype=np.float32)
            if len(features) == len(sub_dets) and len(features) > 0:
                targets = [t.track_id for t in sub_tracks]
                cost_matrix = self.metric.distance(features, targets)
                cost_matrix = self._gate_cost_matrix(cost_matrix, sub_tracks, sub_dets)

                sub_matches, sub_unmatched_a, sub_unmatched_b = linear_assignment(
                    cost_matrix, threshold=self.max_cosine_distance
                )

                for r, c in sub_matches:
                    matches.append((level_track_indices[r], unmatched_detections[c]))

                unmatched_detections = [unmatched_detections[c] for c in sub_unmatched_b]

        unmatched_tracks = [
            k for k in track_indices if k not in [m[0] for m in matches]
        ]
        return matches, unmatched_tracks, unmatched_detections

    def update(
        self,
        detections: List[Detection],
        frame_bgr: Optional[np.ndarray] = None,
    ) -> List[Track]:
        # 1. Feature extraction if missing
        self._extract_missing_features(detections, frame_bgr)

        # 2. Kalman prediction for existing tracks
        for track in self.tracks:
            track.predict()

        # 3. Split tracks into confirmed and unconfirmed (tentative)
        confirmed_indices = [i for i, t in enumerate(self.tracks) if t.is_confirmed()]
        unconfirmed_indices = [i for i, t in enumerate(self.tracks) if not t.is_confirmed()]

        confirmed_tracks = [self.tracks[i] for i in confirmed_indices]
        unconfirmed_tracks = [self.tracks[i] for i in unconfirmed_indices]

        # 4. Association Stage 1: Matching Cascade on Confirmed Tracks (Appearance + Mahalanobis Gating)
        matches_a, unmatched_tracks_a, unmatched_dets = self._matching_cascade(
            confirmed_tracks, detections
        )

        # 5. Association Stage 2: IoU matching for remaining confirmed tracks with time_since_update == 1 and tentative tracks
        iou_track_candidates = (
            [confirmed_tracks[i] for i in unmatched_tracks_a if confirmed_tracks[i].time_since_update == 1]
            + unconfirmed_tracks
        )
        unmatched_tracks_a = [
            confirmed_tracks[i] for i in unmatched_tracks_a if confirmed_tracks[i].time_since_update > 1
        ]

        if len(iou_track_candidates) > 0 and len(unmatched_dets) > 0:
            track_boxes = np.array([t.box for t in iou_track_candidates], dtype=np.float32)
            det_boxes = np.array([detections[i].box for i in unmatched_dets], dtype=np.float32)
            iou_cost = 1.0 - compute_iou_matrix(track_boxes, det_boxes)

            matches_b, unmatched_tracks_b, unmatched_dets_b = linear_assignment(
                iou_cost, threshold=0.7
            )
        else:
            matches_b = []
            unmatched_tracks_b = list(range(len(iou_track_candidates)))
            unmatched_dets_b = list(range(len(unmatched_dets)))

        # 6. Apply updates for matches from Stage 1
        for t_idx, d_idx in matches_a:
            confirmed_tracks[t_idx].update(detections[d_idx])

        # Apply updates for matches from Stage 2
        for t_idx, d_idx in matches_b:
            iou_track_candidates[t_idx].update(detections[unmatched_dets[d_idx]])

        # 7. Mark unmatched tracks as missed
        for t in unmatched_tracks_a:
            t.mark_missed()
        for idx in unmatched_tracks_b:
            iou_track_candidates[idx].mark_missed()

        # 8. Initialize new tracks from unmatched detections
        for idx in unmatched_dets_b:
            det = detections[unmatched_dets[idx]]
            new_track = DeepSortTrack(det, n_init=self.n_init, max_age=self.max_age)
            self.tracks.append(new_track)
            if new_track.is_confirmed() and new_track.feature is not None:
                self.metric.partial_fit(np.array([new_track.feature], dtype=np.float32), [new_track.track_id])

        # 9. Update appearance feature metric for confirmed tracks
        features_to_fit = []
        targets_to_fit = []
        for track in self.tracks:
            if track.is_confirmed() and track.feature is not None and track.time_since_update == 0:
                features_to_fit.append(track.feature)
                targets_to_fit.append(track.track_id)

        if len(features_to_fit) > 0:
            self.metric.partial_fit(np.array(features_to_fit, dtype=np.float32), targets_to_fit)

        # 10. Clean up deleted tracks
        self.tracks = [t for t in self.tracks if not t.is_deleted()]

        # Return only confirmed active tracks
        return [t.to_public_track() for t in self.tracks if t.is_confirmed() and t.time_since_update == 0]
