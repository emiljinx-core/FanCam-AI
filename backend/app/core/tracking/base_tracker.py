from abc import ABC, abstractmethod
from dataclasses import dataclass, field, InitVar
from enum import Enum
from typing import List, Optional, Tuple, Sequence
import numpy as np


class TrackState(Enum):
    """Lifecycle states of a tracked object."""
    TENTATIVE = 1
    CONFIRMED = 2
    LOST = 3
    DELETED = 4


@dataclass
class Detection:
    """
    Standardized input detection across all trackers.
    Consistently maintains [x1, y1, x2, y2] pixel coordinates.
    Accepts either `box` or `tlbr` as keyword argument.
    """
    box: Optional[Sequence[float]] = None  # [x1, y1, x2, y2]
    confidence: float = 1.0
    class_id: int = 0
    feature: Optional[np.ndarray] = None  # Re-ID visual appearance embedding (e.g. 512-D)
    tlbr: InitVar[Optional[Sequence[float]]] = None

    def __post_init__(self, tlbr: Optional[Sequence[float]] = None):
        if self.box is None:
            if tlbr is not None:
                self.box = list(tlbr)
            else:
                raise ValueError("Detection requires either 'box' or 'tlbr' coordinates [x1, y1, x2, y2]")
        if len(self.box) != 4:
            raise ValueError(f"Detection box must have 4 coordinates [x1, y1, x2, y2], got {len(self.box)}")
        x1, y1, x2, y2 = self.box
        if x2 < x1 or y2 < y1:
            raise ValueError(f"Invalid bounding box coordinates: [{x1}, {y1}, {x2}, {y2}]")

    @property
    def x1(self) -> float:
        return float(self.box[0])

    @property
    def y1(self) -> float:
        return float(self.box[1])

    @property
    def x2(self) -> float:
        return float(self.box[2])

    @property
    def y2(self) -> float:
        return float(self.box[3])

    @property
    def tlbr(self) -> np.ndarray:
        return np.array([self.x1, self.y1, self.x2, self.y2], dtype=np.float32)

    @property
    def tlwh(self) -> np.ndarray:
        return np.array([self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1], dtype=np.float32)

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass
class Track:
    """
    Standard track entity representing an object tracked across time.
    Consistent [x1, y1, x2, y2] coordinate structure.
    """
    track_id: int
    box: Sequence[float]  # [x1, y1, x2, y2]
    confidence: float
    state: TrackState = TrackState.CONFIRMED
    class_id: int = 0
    age: int = 0
    hits: int = 1
    time_since_update: int = 0
    feature: Optional[np.ndarray] = None
    features: List[np.ndarray] = field(default_factory=list)

    @property
    def x1(self) -> float:
        return float(self.box[0])

    @property
    def y1(self) -> float:
        return float(self.box[1])

    @property
    def x2(self) -> float:
        return float(self.box[2])

    @property
    def y2(self) -> float:
        return float(self.box[3])

    @property
    def tlbr(self) -> np.ndarray:
        return np.array([self.x1, self.y1, self.x2, self.y2], dtype=np.float32)

    @property
    def tlwh(self) -> np.ndarray:
        return np.array([self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1], dtype=np.float32)

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def area(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)


class BaseTracker(ABC):
    """
    Abstract Base Class for all tracking algorithms (ByteTrack, DeepSORT, etc.).
    Takes incoming Detections in [x1, y1, x2, y2] coordinates and returns active Tracks.
    """

    @abstractmethod
    def update(
        self,
        detections: List[Detection],
        frame_bgr: Optional[np.ndarray] = None,
    ) -> List[Track]:
        """
        Update tracker with new frame detections.
        Args:
            detections: List of Detection objects with [x1, y1, x2, y2] boxes.
            frame_bgr: Optional image frame for appearance feature extraction (DeepSORT).
        Returns:
            List of active confirmed Track objects.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset internal tracker state."""
        pass
