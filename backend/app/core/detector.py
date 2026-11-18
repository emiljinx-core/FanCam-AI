from pathlib import Path
from typing import List, Tuple, Dict, Any
import cv2
import numpy as np
import torch
from ultralytics import YOLO

from app.config import settings


class PersonDetector:
    _instance = None
    _model = None
    _device = "cpu"

    @classmethod
    def get_device(cls) -> str:
        """Explicitly determine device with CUDA verification and fallback to CPU."""
        if settings.FORCE_CPU:
            return "cpu"
        if torch.cuda.is_available():
            try:
                # Test allocation
                _ = torch.zeros(1).cuda()
                return "cuda:0"
            except Exception:
                return "cpu"
        return "cpu"

    @classmethod
    def load_model(cls) -> YOLO:
        """Lazy load singleton YOLO model."""
        if cls._model is None:
            cls._device = cls.get_device()
            model_path = settings.YOLO_MODEL_NAME
            cls._model = YOLO(model_path)
            # Move to device if needed
            if "cuda" in cls._device:
                cls._model.to(cls._device)
        return cls._model

    @classmethod
    def detect_people(
        cls,
        frame_bgr: np.ndarray,
        conf_threshold: float = 0.35,
    ) -> List[Dict[str, Any]]:
        """
        Run YOLO human detection (class 0: person).
        Returns list of detections with pixel coordinates and confidence:
        [
            {
                "x1": int, "y1": int, "x2": int, "y2": int,
                "confidence": float (0-100)
            }
        ]
        """
        model = cls.load_model()
        h, w = frame_bgr.shape[:2]

        # Ensure correct inference device
        device = cls._device

        results = model.predict(
            source=frame_bgr,
            classes=[0],  # class 0 = person
            conf=conf_threshold,
            device=device,
            verbose=False,
        )

        detections = []
        if not results or len(results) == 0:
            return detections

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return detections

        for i, box in enumerate(boxes):
            coords = box.xyxy[0].tolist()
            x1 = max(0, min(int(round(coords[0])), w - 1))
            y1 = max(0, min(int(round(coords[1])), h - 1))
            x2 = max(0, min(int(round(coords[2])), w))
            y2 = max(0, min(int(round(coords[3])), h))
            conf = float(box.conf[0].item()) * 100.0

            # Guard against invalid or 0-area boxes
            if x2 <= x1 or y2 <= y1:
                continue

            detections.append(
                {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "confidence": round(conf, 1),
                }
            )

        # Sort detections from left to right for stable frontend presentation
        detections.sort(key=lambda d: d["x1"])
        return detections

    @classmethod
    def crop_and_save_targets(
        cls,
        frame_bgr: np.ndarray,
        detections: List[Dict[str, Any]],
        output_dir: Path,
        prefix: str = "target",
    ) -> List[Dict[str, Any]]:
        """
        Crops each detected person, saves image to previews directory,
        and computes normalized boxes for frontend display.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        h, w = frame_bgr.shape[:2]

        results = []
        for idx, det in enumerate(detections, start=1):
            x1, y1, x2, y2 = det["x1"], det["y1"], det["x2"], det["y2"]
            crop = frame_bgr[y1:y2, x1:x2]

            # Save crop thumbnail
            crop_filename = f"{prefix}_{idx}.jpg"
            crop_path = output_dir / crop_filename
            cv2.imwrite(str(crop_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 90])

            # Normalized percentage coordinates for frontend (0 to 100)
            norm_top = round((y1 / h) * 100.0, 1)
            norm_left = round((x1 / w) * 100.0, 1)
            norm_width = round(((x2 - x1) / w) * 100.0, 1)
            norm_height = round(((y2 - y1) / h) * 100.0, 1)

            results.append(
                {
                    "id": f"p{idx}",
                    "name": f"Person #{idx:02d}",
                    "confidence": det["confidence"],
                    "box": {
                        "top": norm_top,
                        "left": norm_left,
                        "width": norm_width,
                        "height": norm_height,
                    },
                    "crop_filename": crop_filename,
                    "pixel_box": [x1, y1, x2, y2],
                    "role": "Lead Subject" if idx == 1 else "Subject",
                }
            )

        return results
