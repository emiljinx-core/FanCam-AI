from typing import List, Tuple
import numpy as np
from scipy.optimize import linear_sum_assignment


def compute_iou_matrix(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
    """
    Computes pairwise IoU between two sets of boxes in [x1, y1, x2, y2] format.
    boxes_a: (N, 4)
    boxes_b: (M, 4)
    Returns: (N, M) matrix of IoU values in [0, 1].
    """
    if len(boxes_a) == 0 or len(boxes_b) == 0:
        return np.zeros((len(boxes_a), len(boxes_b)), dtype=np.float32)

    boxes_a = np.ascontiguousarray(boxes_a, dtype=np.float32)
    boxes_b = np.ascontiguousarray(boxes_b, dtype=np.float32)

    # Intersection coordinates
    tl = np.maximum(boxes_a[:, None, :2], boxes_b[None, :, :2])  # (N, M, 2)
    br = np.minimum(boxes_a[:, None, 2:], boxes_b[None, :, 2:])  # (N, M, 2)

    wh = np.maximum(0.0, br - tl)  # (N, M, 2)
    inter_area = wh[:, :, 0] * wh[:, :, 1]  # (N, M)

    area_a = np.maximum(0.0, boxes_a[:, 2] - boxes_a[:, 0]) * np.maximum(0.0, boxes_a[:, 3] - boxes_a[:, 1])
    area_b = np.maximum(0.0, boxes_b[:, 2] - boxes_b[:, 0]) * np.maximum(0.0, boxes_b[:, 3] - boxes_b[:, 1])

    union_area = area_a[:, None] + area_b[None, :] - inter_area
    union_area = np.maximum(1e-6, union_area)

    return inter_area / union_area


def linear_assignment(
    cost_matrix: np.ndarray,
    threshold: float,
) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """
    Solve linear assignment problem with strict duplicate prevention:
    - Guaranteed bijective matching (one detection <-> at most one track).
    - Unmatched tracks and unmatched detections are isolated.
    """
    if cost_matrix.size == 0:
        return [], list(range(cost_matrix.shape[0])), list(range(cost_matrix.shape[1]))

    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    matched_indices = []
    unmatched_a = set(range(cost_matrix.shape[0]))
    unmatched_b = set(range(cost_matrix.shape[1]))

    for r, c in zip(row_ind, col_ind):
        if cost_matrix[r, c] <= threshold:
            matched_indices.append((r, c))
            unmatched_a.discard(r)
            unmatched_b.discard(c)

    return matched_indices, sorted(list(unmatched_a)), sorted(list(unmatched_b))


class KalmanBoxFilter:
    """
    8-state Kalman Filter for bounding box tracking:
    State vector: [x_center, y_center, aspect_ratio (w/h), height, vx, vy, va, vh]
    """

    def __init__(self):
        ndim, dt = 4, 1.0

        # State transition matrix (constant velocity model)
        self._motion_mat = np.eye(2 * ndim, 2 * ndim)
        for i in range(ndim):
            self._motion_mat[i, ndim + i] = dt

        # Measurement matrix (observes x, y, a, h)
        self._update_mat = np.eye(ndim, 2 * ndim)

        # Noise weights
        self._std_weight_position = 1.0 / 20
        self._std_weight_velocity = 1.0 / 160

    def initiate(self, measurement: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """measurement is [x_center, y_center, aspect_ratio, height]"""
        mean_pos = measurement
        mean_vel = np.zeros_like(mean_pos)
        mean = np.r_[mean_pos, mean_vel]

        std = [
            2 * self._std_weight_position * measurement[3],
            2 * self._std_weight_position * measurement[3],
            1e-2,
            2 * self._std_weight_position * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            1e-5,
            10 * self._std_weight_velocity * measurement[3],
        ]
        covariance = np.diag(np.square(std))
        return mean, covariance

    def predict(self, mean: np.ndarray, covariance: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        std_pos = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-2,
            self._std_weight_position * mean[3],
        ]
        std_vel = [
            self._std_weight_velocity * mean[3],
            self._std_weight_velocity * mean[3],
            1e-5,
            self._std_weight_velocity * mean[3],
        ]
        motion_cov = np.diag(np.square(np.r_[std_pos, std_vel]))

        mean = np.dot(self._motion_mat, mean)
        covariance = np.linalg.multi_dot((self._motion_mat, covariance, self._motion_mat.T)) + motion_cov
        return mean, covariance

    def update(
        self,
        mean: np.ndarray,
        covariance: np.ndarray,
        measurement: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        std = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-1,
            self._std_weight_position * mean[3],
        ]
        innovation_cov = np.diag(np.square(std))

        # Projected measurement covariance: S = H * P * H^T + R
        projected_mean = np.dot(self._update_mat, mean)
        projected_cov = np.linalg.multi_dot((self._update_mat, covariance, self._update_mat.T)) + innovation_cov

        # Kalman gain: K = P * H^T * S^-1  (shape: 8x4)
        # S is 4x4, (H * P) is 4x8 -> Solve S * K^T = H * P
        hp = np.dot(self._update_mat, covariance)  # shape: (4, 8)
        kalman_gain = np.linalg.solve(projected_cov, hp).T  # shape: (8, 4)

        innovation = measurement - projected_mean
        new_mean = mean + np.dot(innovation, kalman_gain.T)
        new_covariance = covariance - np.linalg.multi_dot((kalman_gain, projected_cov, kalman_gain.T))
        return new_mean, new_covariance


def scipy_cho_factor(a):
    import scipy.linalg
    return scipy.linalg.cho_factor(a, lower=True, check_finite=False)


def scipy_cho_solve(chol, b):
    import scipy.linalg
    return scipy.linalg.cho_solve(chol, b, check_finite=False)
