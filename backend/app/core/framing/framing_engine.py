from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple, Sequence
import numpy as np

from app.core.framing.camera_filter import CameraKalmanFilter, is_valid_detection_box
from app.core.framing.dynamic_zoom import DynamicZoomEngine


@dataclass
class FramingCrop:
    """Frame crop result containing both high-precision geometry and discrete integer render coordinates."""
    frame_index: int
    timestamp_sec: float
    # High-precision floating point coordinates: [left, top, right, bottom]
    crop_float: Tuple[float, float, float, float]
    camera_center: Tuple[float, float]
    velocity: Tuple[float, float]
    zoom_scale: float
    # Safe even integer slice coordinates: [x1, y1, x2, y2]
    crop_int: Tuple[int, int, int, int]
    is_subject_contained: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "timestamp_sec": round(self.timestamp_sec, 3),
            "crop_float": [round(c, 2) for c in self.crop_float],
            "camera_center": [round(c, 2) for c in self.camera_center],
            "velocity": [round(v, 2) for v in self.velocity],
            "zoom_scale": round(self.zoom_scale, 3),
            "crop_int": list(self.crop_int),
            "is_subject_contained": self.is_subject_contained,
        }


class CinematicFramingEngine:
    """
    Computes adaptive cinematic crop windows adhering to strict priority rules:
    Priority 1 (Hard Invariant): Exact target aspect ratio
    Priority 2 (Hard Invariant): Source boundary confinement [0, 0, W_frame, H_frame]
    Priority 3 (Soft Invariant): Subject containment whenever physically feasible
    """

    ASPECT_RATIOS = {
        "9:16": 9.0 / 16.0,
        "1:1": 1.0,
        "16:9": 16.0 / 9.0,
    }

    def __init__(
        self,
        frame_width: int,
        frame_height: int,
        aspect_ratio: str = "9:16",
        smoothing_level: int = 85,
        fps: float = 30.0,
    ):
        self.frame_width = int(frame_width)
        self.frame_height = int(frame_height)
        self.aspect_ratio_str = aspect_ratio
        self.target_ratio = self.ASPECT_RATIOS.get(aspect_ratio, 9.0 / 16.0)
        self.fps = max(1.0, float(fps))
        self.smoothing_level = smoothing_level

        self.kalman_filter = CameraKalmanFilter(
            frame_width=self.frame_width,
            frame_height=self.frame_height,
            smoothing_level=smoothing_level,
            fps=self.fps,
        )

        self.zoom_engine = DynamicZoomEngine(
            frame_width=self.frame_width,
            frame_height=self.frame_height,
            z_min=1.0,
            z_max=2.2,
            target_occupancy=0.50,
            edge_margin=0.12,
        )

        # Base maximum uncropped window fitting within source dimensions
        # having exact target aspect ratio
        r = self.target_ratio
        if (self.frame_width / self.frame_height) >= r:
            self.h_max = float(self.frame_height)
            self.w_max = float(self.h_max * r)
        else:
            self.w_max = float(self.frame_width)
            self.h_max = float(self.w_max / r)

    def process_frame(
        self,
        frame_index: int,
        timestamp_sec: float,
        detection_box: Optional[Sequence[float]] = None,
        confidence: Optional[float] = None,
        dt: Optional[float] = None,
    ) -> FramingCrop:
        """
        Processes a single frame and computes the exact reframing crop window.
        """
        if dt is None:
            dt = 1.0 / self.fps

        valid_box = is_valid_detection_box(
            detection_box, self.frame_width, self.frame_height
        )
        safe_box = detection_box if valid_box else None

        # 1. Update Camera Kalman Filter
        camera_center, velocity = self.kalman_filter.step(
            box=safe_box,
            timestamp=timestamp_sec,
            confidence=confidence,
        )
        cx, cy = camera_center

        # 2. Update Dynamic Zoom Engine
        zoom = self.zoom_engine.compute_zoom(box=safe_box, dt=dt)

        # 3. Compute Dimensions preserving Priority 1 (Exact Aspect Ratio)
        w_crop = self.w_max / zoom
        h_crop = self.h_max / zoom

        # 4. Priority 3: Soft Subject Containment Shift
        # Gently nudge camera center if subject's box extends outside crop window
        if safe_box is not None:
            bx1, by1, bx2, by2 = safe_box
            subj_w = bx2 - bx1
            subj_h = by2 - by1

            # Horizontal centering / containment
            if subj_w <= w_crop:
                # If subject fits, ensure it's enclosed
                if bx1 < (cx - w_crop / 2.0):
                    cx = bx1 + w_crop / 2.0
                elif bx2 > (cx + w_crop / 2.0):
                    cx = bx2 - w_crop / 2.0
            else:
                # If subject is wider than vertical crop, center on subject midpoint
                cx = (bx1 + bx2) / 2.0

            # Vertical centering / containment
            if subj_h <= h_crop:
                if by1 < (cy - h_crop / 2.0):
                    cy = by1 + h_crop / 2.0
                elif by2 > (cy + h_crop / 2.0):
                    cy = by2 - h_crop / 2.0
            else:
                cy = (by1 + by2) / 2.0

        # 5. Priority 2: Hard Source Boundary Clamping
        # left in [0, W_frame - w_crop], top in [0, H_frame - h_crop]
        max_left = max(0.0, self.frame_width - w_crop)
        max_top = max(0.0, self.frame_height - h_crop)

        left = float(np.clip(cx - w_crop / 2.0, 0.0, max_left))
        top = float(np.clip(cy - h_crop / 2.0, 0.0, max_top))
        right = left + w_crop
        bottom = top + h_crop

        crop_float = (left, top, right, bottom)

        # Check subject containment
        is_contained = False
        if safe_box is not None:
            bx1, by1, bx2, by2 = safe_box
            is_contained = (
                bx1 >= (left - 1.0)
                and by1 >= (top - 1.0)
                and bx2 <= (right + 1.0)
                and by2 <= (bottom + 1.0)
            )

        # 6. Discretize into Even Integer Coordinates for Video Codecs
        # Ensure slice indices are even integers and strictly valid
        h_int = int(round(h_crop / 2.0) * 2)
        h_int = max(2, min(self.frame_height, h_int))

        w_int = int(round((h_int * self.target_ratio) / 2.0) * 2)
        w_int = max(2, min(self.frame_width, w_int))

        left_int = int(round(left))
        top_int = int(round(top))

        # Clamp integer coordinates safely within array limits
        left_int = max(0, min(self.frame_width - w_int, left_int))
        top_int = max(0, min(self.frame_height - h_int, top_int))
        right_int = left_int + w_int
        bottom_int = top_int + h_int

        crop_int = (left_int, top_int, right_int, bottom_int)

        return FramingCrop(
            frame_index=frame_index,
            timestamp_sec=timestamp_sec,
            crop_float=crop_float,
            camera_center=(cx, cy),
            velocity=velocity,
            zoom_scale=zoom,
            crop_int=crop_int,
            is_subject_contained=is_contained,
        )

    def generate_trajectory_crops(
        self,
        trajectory: List[Dict[str, Any]],
    ) -> List[FramingCrop]:
        """
        Processes entire trajectory sequence and returns list of FramingCrops.
        """
        crops: List[FramingCrop] = []
        last_t = 0.0

        for idx, item in enumerate(trajectory):
            t_sec = float(item.get("timestamp_sec", idx / self.fps))
            dt = t_sec - last_t if idx > 0 else (1.0 / self.fps)
            last_t = t_sec

            box = item.get("box")
            conf = item.get("confidence")

            crop = self.process_frame(
                frame_index=int(item.get("frame_index", idx)),
                timestamp_sec=t_sec,
                detection_box=box,
                confidence=conf,
                dt=dt,
            )
            crops.append(crop)

        return crops
