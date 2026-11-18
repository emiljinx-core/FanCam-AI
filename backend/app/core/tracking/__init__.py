from app.core.tracking.base_tracker import (
    BaseTracker,
    Track,
    Detection,
    TrackState,
)
from app.core.tracking.byte_tracker import ByteTracker
from app.core.tracking.deepsort_tracker import DeepSortTracker
from app.core.tracking.target_matcher import (
    TargetMatcher,
    TargetState,
    TargetMatchResult,
)

# Alias for backward compatibility
TrackedBox = Detection

__all__ = [
    "BaseTracker",
    "Track",
    "Detection",
    "TrackedBox",
    "TrackState",
    "ByteTracker",
    "DeepSortTracker",
    "TargetMatcher",
    "TargetState",
    "TargetMatchResult",
]
