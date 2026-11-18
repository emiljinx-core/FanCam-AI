from dataclasses import dataclass
from typing import Tuple, Optional, Sequence
import numpy as np


def is_valid_detection_box(
    box: Optional[Sequence[float]],
    frame_width: float,
    frame_height: float,
    min_size: float = 2.0,
) -> bool:
    """
    Safeguard 1: Validates bounding boxes before Kalman measurement updates.
    Rejects:
    - None or wrong sequence length
    - Non-finite coordinates (NaN, Inf)
    - Inverted coordinates (x2 <= x1, y2 <= y1)
    - Degenerate boxes with width or height < min_size
    - Entirely out-of-frame detections (no overlap with [0, frame_width] x [0, frame_height])
    """
    if box is None or len(box) != 4:
        return False

    try:
        x1, y1, x2, y2 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
    except (TypeError, ValueError):
        return False

    # Check finite
    if not (np.isfinite(x1) and np.isfinite(y1) and np.isfinite(x2) and np.isfinite(y2)):
        return False

    # Check inverted or degenerate
    if (x2 - x1) < min_size or (y2 - y1) < min_size:
        return False

    # Check entirely out of frame
    if x2 <= 0.0 or x1 >= frame_width or y2 <= 0.0 or y1 >= frame_height:
        return False

    return True


class CameraKalmanFilter:
    """
    2D Kinematic Kalman Filter for camera pan and velocity estimation:
    - State: [c_x, c_y, v_x, v_y]^T
    - Measurement: [c_x, c_y]^T
    - Dynamic timestamp delta_t support
    - Controlled process noise q based on smoothing_level
    - Bounded target-loss coasting with velocity decay
    - Safeguard 2: Gated smooth reacquisition without double-applying corrections
    """

    def __init__(
        self,
        frame_width: float,
        frame_height: float,
        smoothing_level: int = 85,
        fps: float = 30.0,
        coast_frames_limit: Optional[int] = None,
    ):
        self.frame_width = float(frame_width)
        self.frame_height = float(frame_height)
        self.fps = max(1.0, float(fps))
        self.smoothing_level = max(0, min(100, smoothing_level))

        # Dynamic process noise scaling based on smoothing level
        # High smoothing -> low process noise q -> smooth inertia
        # Low smoothing -> higher process noise q -> responsive pan
        norm_s = float(self.smoothing_level) / 100.0
        self.q_var = 150.0 * ((1.0 - norm_s) ** 2) + 1.0

        # Measurement noise base
        self.r_base = 15.0

        # State: [cx, cy, vx, vy]
        self.state: Optional[np.ndarray] = None
        self.cov: Optional[np.ndarray] = None
        self.last_timestamp: Optional[float] = None

        # Coasting and loss management
        self.consecutive_lost_frames = 0
        self.coast_frames_limit = (
            coast_frames_limit if coast_frames_limit is not None else int(round(1.5 * self.fps))
        )
        self.velocity_decay = 0.94

        # Safeguard 2: Reacquisition smoothing state
        # Blend reacquisition over 5 frames to prevent sudden jump,
        # but apply the Kalman update once per cycle cleanly.
        self.reacquisition_countdown = 0
        self.reacquisition_total_steps = 5
        self.reacquisition_offset: np.ndarray = np.zeros(2, dtype=np.float32)

    def _init_state(self, cx: float, cy: float, timestamp: float) -> None:
        self.state = np.array([cx, cy, 0.0, 0.0], dtype=np.float32)
        self.cov = np.diag([20.0, 20.0, 100.0, 100.0]).astype(np.float32)
        self.last_timestamp = timestamp
        self.consecutive_lost_frames = 0
        self.reacquisition_countdown = 0
        self.reacquisition_offset = np.zeros(2, dtype=np.float32)

    def step(
        self,
        box: Optional[Sequence[float]],
        timestamp: float,
        confidence: Optional[float] = None,
    ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Executes one prediction-update cycle.
        Returns:
            camera_center: (cx, cy)
            velocity: (vx, vy)
        """
        # Compute delta_t
        if self.last_timestamp is None:
            dt = 1.0 / self.fps
        else:
            dt = timestamp - self.last_timestamp
            if dt <= 0.0 or not np.isfinite(dt):
                dt = 1.0 / self.fps
        dt = float(np.clip(dt, 0.001, 0.2))
        self.last_timestamp = timestamp

        valid_box = is_valid_detection_box(box, self.frame_width, self.frame_height)

        # 1. First initialization
        if self.state is None:
            if valid_box and box is not None:
                cx = float((box[0] + box[2]) / 2.0)
                cy = float((box[1] + box[3]) / 2.0)
                self._init_state(cx, cy, timestamp)
            else:
                # Default to frame center if first frame has no target
                cx = self.frame_width / 2.0
                cy = self.frame_height / 2.0
                self._init_state(cx, cy, timestamp)

            return (float(self.state[0]), float(self.state[1])), (0.0, 0.0)

        # 2. State Transition Matrix F and Process Noise Q
        F = np.array(
            [
                [1.0, 0.0, dt, 0.0],
                [0.0, 1.0, 0.0, dt],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=np.float32,
        )

        dt2 = dt * dt
        dt3 = dt2 * dt
        q = self.q_var
        Q = q * np.array(
            [
                [dt3 / 3.0, 0.0, dt2 / 2.0, 0.0],
                [0.0, dt3 / 3.0, 0.0, dt2 / 2.0],
                [dt2 / 2.0, 0.0, dt, 0.0],
                [0.0, dt2 / 2.0, 0.0, dt],
            ],
            dtype=np.float32,
        )

        # 3. Predict step
        state_pred = F @ self.state
        cov_pred = F @ self.cov @ F.T + Q

        # Handle Target Presence vs Absence
        if valid_box and box is not None:
            meas_cx = float((box[0] + box[2]) / 2.0)
            meas_cy = float((box[1] + box[3]) / 2.0)

            # Reacquisition transition trigger: if target was previously lost
            if self.consecutive_lost_frames > 2:
                # Capture difference from current camera prediction to target measurement
                raw_diff = np.array(
                    [meas_cx - state_pred[0], meas_cy - state_pred[1]],
                    dtype=np.float32,
                )
                self.reacquisition_countdown = self.reacquisition_total_steps
                self.reacquisition_offset = raw_diff

            self.consecutive_lost_frames = 0

            # Measurement z
            z = np.array([meas_cx, meas_cy], dtype=np.float32)

            # Measurement Matrix H
            H = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=np.float32)

            # Measurement Covariance R scaled by confidence
            conf = float(confidence) if (confidence is not None and np.isfinite(confidence)) else 0.5
            conf = max(0.2, min(1.0, conf))
            r_scale = (self.r_base / conf) ** 2
            R = np.diag([r_scale, r_scale]).astype(np.float32)

            # Kalman Update
            y = z - (H @ state_pred)  # Residual
            S = H @ cov_pred @ H.T + R  # Residual covariance
            K = cov_pred @ H.T @ np.linalg.inv(S)  # Kalman gain

            self.state = state_pred + (K @ y)
            I = np.eye(4, dtype=np.float32)
            self.cov = (I - K @ H) @ cov_pred

        else:
            # Target is missing / lost / out-of-frame: Bounded Coasting
            self.consecutive_lost_frames += 1

            if self.consecutive_lost_frames <= self.coast_frames_limit:
                # Coast using decaying velocity
                state_pred[2] *= self.velocity_decay
                state_pred[3] *= self.velocity_decay
                self.state = state_pred
                self.cov = cov_pred
            else:
                # Exceeded coast limit: halt velocity and gently drift to frame center
                frame_center = np.array(
                    [self.frame_width / 2.0, self.frame_height / 2.0], dtype=np.float32
                )
                drift_speed = 0.03
                self.state[0] += drift_speed * (frame_center[0] - self.state[0])
                self.state[1] += drift_speed * (frame_center[1] - self.state[1])
                self.state[2] = 0.0
                self.state[3] = 0.0
                self.cov = cov_pred

        # Safeguard 2: Apply smooth 5-frame reacquisition dampener to the camera output
        # (Offsets output camera position to smoothly transition without snapping,
        # but does not double-apply Kalman updates to internal filter state).
        display_cx = float(self.state[0])
        display_cy = float(self.state[1])

        if self.reacquisition_countdown > 0:
            fraction = float(self.reacquisition_countdown) / float(self.reacquisition_total_steps)
            # Offset = meas_cx - state_pred. Since self.state jumped towards meas_cx,
            # subtracting (self.state - state_pred) * fraction holds the camera smoothly near state_pred.
            correction_jump = self.state[:2] - state_pred[:2]
            display_cx -= float(correction_jump[0] * fraction)
            display_cy -= float(correction_jump[1] * fraction)
            self.reacquisition_countdown -= 1
            if self.reacquisition_countdown == 0:
                self.reacquisition_offset = np.zeros(2, dtype=np.float32)

        # Enforce bounds on camera center
        display_cx = float(np.clip(display_cx, 0.0, self.frame_width))
        display_cy = float(np.clip(display_cy, 0.0, self.frame_height))

        velocity = (float(self.state[2]), float(self.state[3]))
        return (display_cx, display_cy), velocity
