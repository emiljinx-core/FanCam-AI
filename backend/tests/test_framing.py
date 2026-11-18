import sys
from pathlib import Path
import numpy as np
import pytest

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.framing import (
    CameraKalmanFilter,
    DynamicZoomEngine,
    CinematicFramingEngine,
    FramingCrop,
    is_valid_detection_box,
)


def test_safeguard_1_bounding_box_validation():
    """
    Test Safeguard 1: Reject malformed, non-finite, inverted, and entirely out-of-frame detections.
    """
    fw, fh = 1920.0, 1080.0

    # 1. Valid box
    assert is_valid_detection_box([100, 100, 300, 500], fw, fh) is True

    # 2. None or wrong length
    assert is_valid_detection_box(None, fw, fh) is False
    assert is_valid_detection_box([100, 100], fw, fh) is False

    # 3. Non-finite coordinates (NaN, Inf)
    assert is_valid_detection_box([np.nan, 100, 300, 500], fw, fh) is False
    assert is_valid_detection_box([100, 100, np.inf, 500], fw, fh) is False

    # 4. Inverted coordinates (x2 <= x1 or y2 <= y1)
    assert is_valid_detection_box([300, 100, 100, 500], fw, fh) is False
    assert is_valid_detection_box([100, 500, 300, 200], fw, fh) is False

    # 5. Degenerate box (< min_size)
    assert is_valid_detection_box([100, 100, 100.5, 500], fw, fh) is False

    # 6. Entirely out-of-frame detections
    assert is_valid_detection_box([-200, -200, -10, -10], fw, fh) is False
    assert is_valid_detection_box([2000, 100, 2200, 400], fw, fh) is False
    assert is_valid_detection_box([100, 1100, 300, 1300], fw, fh) is False


def test_safeguard_2_reacquisition_smoothness_and_no_double_correction():
    """
    Test Safeguard 2: Ensure Kalman reacquisition and the 5-frame transition
    do not introduce sudden camera jumps or double-apply measurement corrections.
    """
    fw, fh = 1920.0, 1080.0
    filter = CameraKalmanFilter(frame_width=fw, frame_height=fh, smoothing_level=80, fps=30.0)

    # 1. Track target moving horizontally at 500, 500
    for i in range(10):
        t = i / 30.0
        filter.step([500.0, 400.0, 600.0, 600.0], timestamp=t, confidence=0.9)

    # 2. Target lost for 5 frames
    for i in range(10, 15):
        t = i / 30.0
        filter.step(None, timestamp=t)

    # 3. Target re-appears at shifted position (700, 500)
    # The camera should transition smoothly across frames without an instantaneous leap
    displacements = []
    # Start tracking displacement from the displayed camera center before reacquisition
    prev_center = (filter.state[0], filter.state[1])

    for i in range(15, 22):
        t = i / 30.0
        center, vel = filter.step([700.0, 400.0, 800.0, 600.0], timestamp=t, confidence=0.9)
        disp = np.linalg.norm(np.array(center) - np.array(prev_center))
        displacements.append(disp)
        prev_center = center

    # Maximum single-frame movement during reacquisition must be strictly bounded (< 65 pixels)
    assert max(displacements) < 65.0, f"Reacquisition jumped too abruptly: {max(displacements)} px"
    # Filter state must remain finite and bounded
    assert np.all(np.isfinite(filter.state))


def test_priority_hierarchy_and_aspect_ratio_invariance():
    """
    Verify:
    Priority 1 (Hard Invariant): Exact Aspect Ratio (within 1e-4)
    Priority 2 (Hard Invariant): Source Boundary Confinement [0, 0, W_frame, H_frame]
    Priority 3 (Soft Invariant): Subject Containment
    """
    fw, fh = 1920, 1080

    for ratio_name, target_r in [("9:16", 9.0 / 16.0), ("1:1", 1.0), ("16:9", 16.0 / 9.0)]:
        engine = CinematicFramingEngine(frame_width=fw, frame_height=fh, aspect_ratio=ratio_name, fps=30.0)

        # Test extreme coordinates and corner cases
        test_boxes = [
            [0, 0, 100, 200],                  # Top-left corner
            [fw - 150, fh - 300, fw, fh],      # Bottom-right corner
            [fw / 2 - 50, fh / 2 - 100, fw / 2 + 50, fh / 2 + 100],  # Center
            [-50, -50, 150, 200],              # Overlapping left/top edge
            [fw - 100, -20, fw + 50, 200],     # Overlapping right edge
            [100, 200, 1800, 1000],            # Massive oversized subject
        ]

        for idx, box in enumerate(test_boxes):
            crop = engine.process_frame(frame_index=idx, timestamp_sec=idx / 30.0, detection_box=box)
            l, t, r, b = crop.crop_float
            w = r - l
            h = b - t

            # Priority 1: Exact Aspect Ratio
            calc_ratio = w / h
            assert abs(calc_ratio - target_r) < 1e-4, f"Aspect ratio broken for {ratio_name}: {calc_ratio} vs {target_r}"

            # Priority 2: Source Boundary Confinement
            assert l >= 0.0, f"Left out of bounds: {l}"
            assert t >= 0.0, f"Top out of bounds: {t}"
            assert r <= fw, f"Right out of bounds: {r} > {fw}"
            assert b <= fh, f"Bottom out of bounds: {b} > {fh}"

            # Integer slice coordinate safety
            ix1, iy1, ix2, iy2 = crop.crop_int
            assert ix1 >= 0 and iy1 >= 0
            assert ix2 <= fw and iy2 <= fh
            assert (ix2 - ix1) % 2 == 0  # Even integer for video codecs
            assert (iy2 - iy1) % 2 == 0  # Even integer for video codecs


def test_dynamic_zoom_scaling():
    """
    Verify dynamic zoom scales up (tighter crop) for distant small subjects,
    and backs off to wide shot (z -> 1.0) as subject approaches boundaries.
    """
    fw, fh = 1920.0, 1080.0
    zoom_engine = DynamicZoomEngine(frame_width=fw, frame_height=fh, z_min=1.0, z_max=2.2)

    # 1. Distant/small subject centered: small height = 100px (100 / 1080 ~ 0.09)
    # Should scale tightly (zoom > 1.4)
    small_centered_box = [900.0, 500.0, 960.0, 600.0]
    for _ in range(15):
        z = zoom_engine.compute_zoom(small_centered_box, dt=1.0 / 30.0)
    assert z > 1.4, f"Expected tight zoom for small subject, got {z}"

    # 2. Subject approaches boundary (x near 0)
    # Zoom should back off towards 1.0 to give safety clearance
    near_edge_box = [10.0, 500.0, 70.0, 600.0]
    for _ in range(25):
        z_edge = zoom_engine.compute_zoom(near_edge_box, dt=1.0 / 30.0)
    assert z_edge < z, f"Zoom did not back off near boundary: {z_edge} vs {z}"


def test_bounded_coasting_and_recovery():
    """
    Verify that lost target triggers bounded velocity coasting and gracefully stops.
    """
    fw, fh = 1920.0, 1080.0
    filter = CameraKalmanFilter(frame_width=fw, frame_height=fh, smoothing_level=85, fps=30.0, coast_frames_limit=10)

    # Move rightward with velocity
    for i in range(10):
        t = i / 30.0
        filter.step([500.0 + i * 15.0, 500.0, 550.0 + i * 15.0, 600.0], timestamp=t)

    vx_active = filter.state[2]
    assert vx_active > 0.0

    # Target lost: coasting should decay velocity
    for i in range(10, 15):
        t = i / 30.0
        filter.step(None, timestamp=t)

    vx_coasting = filter.state[2]
    assert vx_coasting < vx_active, "Velocity did not decay during coasting"

    # Beyond coast limit: velocity halts
    for i in range(15, 30):
        t = i / 30.0
        filter.step(None, timestamp=t)

    assert abs(filter.state[2]) < 1.0, "Velocity did not halt after coast limit exceeded"
