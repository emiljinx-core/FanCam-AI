from typing import Optional, Sequence
import numpy as np


class DynamicZoomEngine:
    """
    Computes context-aware dynamic zoom scale:
    - Scales tighter (up to z_max) when the subject is distant/small.
    - Scales wider (down to z_min) when the subject is large/close.
    - Backs off zoom (widens view) when subject approaches frame boundaries.
    - Applies continuous exponential smoothing across timestamps to avoid focal pulsing.
    """

    def __init__(
        self,
        frame_width: float,
        frame_height: float,
        z_min: float = 1.0,
        z_max: float = 2.2,
        target_occupancy: float = 0.50,
        edge_margin: float = 0.12,
        time_constant_tau: float = 0.6,
    ):
        self.frame_width = float(frame_width)
        self.frame_height = float(frame_height)
        self.z_min = float(z_min)
        self.z_max = float(z_max)
        self.target_occupancy = float(target_occupancy)
        self.edge_margin = float(edge_margin)
        self.time_constant_tau = float(time_constant_tau)

        # Smoothed state
        self.current_zoom = 1.0

    def compute_zoom(
        self,
        box: Optional[Sequence[float]],
        dt: float,
    ) -> float:
        """
        Calculates smoothed zoom scale based on current box and time delta dt.
        """
        dt = float(np.clip(dt, 0.001, 0.5))

        if box is not None and len(box) == 4:
            x1, y1, x2, y2 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
            h_subj = max(1.0, y2 - y1)
            rho_subj = h_subj / self.frame_height

            # 1. Distance-based raw zoom scale
            # Smaller subject -> higher zoom
            z_dist = self.target_occupancy / max(rho_subj, 0.08)
            z_dist = float(np.clip(z_dist, self.z_min, self.z_max))

            # 2. Boundary proximity zoom back-off
            # Distance from subject box edges to frame boundaries
            d_left = x1 / self.frame_width
            d_right = (self.frame_width - x2) / self.frame_width
            d_top = y1 / self.frame_height
            d_bottom = (self.frame_height - y2) / self.frame_height

            d_edge = min(d_left, d_right, d_top, d_bottom)
            if d_edge < self.edge_margin:
                beta_edge = float(np.clip(d_edge / self.edge_margin, 0.0, 1.0))
                # Smoothly interpolate back towards z_min=1.0 as subject nears frame boundary
                z_target = 1.0 + (z_dist - 1.0) * beta_edge
            else:
                z_target = z_dist
        else:
            # If target missing, relax gently towards default wide zoom
            z_target = 1.0

        # 3. Continuous Exponential Smoothing
        # alpha = exp(-dt / tau)
        alpha = float(np.exp(-dt / self.time_constant_tau))
        self.current_zoom = float(alpha * self.current_zoom + (1.0 - alpha) * z_target)
        self.current_zoom = float(np.clip(self.current_zoom, self.z_min, self.z_max))

        return self.current_zoom
