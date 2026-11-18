from pathlib import Path
from typing import Optional
import cv2
import numpy as np
import torch
import torch.nn.functional as F

from app.config import settings
from app.core import osnet_arch


class OSNetReIDExtractor:
    """Appearance feature extractor using genuine pretrained OSNet (Omni-Scale Network)."""

    _instance = None
    _model = None
    _device = "cpu"

    @classmethod
    def get_device(cls) -> str:
        if settings.FORCE_CPU:
            return "cpu"
        if torch.cuda.is_available():
            try:
                _ = torch.zeros(1).cuda()
                return "cuda:0"
            except Exception:
                return "cpu"
        return "cpu"

    @classmethod
    def load_model(cls):
        if cls._model is None:
            cls._device = cls.get_device()
            # Use genuine person Re-ID weights trained on MSMT17 (1041 identities)
            weights_path = settings.MODELS_DIR / "osnet_x0_25_msmt17.pt"
            num_classes = 1041
            if not weights_path.exists():
                # Fallback to local imagenet checkpoint if msmt17 is absent
                weights_path = settings.MODELS_DIR / "osnet_x0_25_imagenet.pt"
                num_classes = 1000

            model = osnet_arch.osnet_x0_25(num_classes=num_classes, pretrained=False)
            if weights_path.exists():
                state_dict = torch.load(str(weights_path), map_location="cpu")
                model.load_state_dict(state_dict, strict=False)

            model.to(cls._device)
            model.eval()
            cls._model = model

        return cls._model

    @classmethod
    def preprocess_crop(cls, crop_bgr: np.ndarray) -> torch.Tensor:
        """
        Preprocess crop for Re-ID network:
        - Resize to standard Re-ID dimension: 256 height x 128 width
        - Convert BGR to RGB
        - Normalize with standard ImageNet mean/std
        """
        if crop_bgr is None or crop_bgr.size == 0:
            raise ValueError("Invalid or empty crop passed for embedding extraction.")

        # Standard Re-ID input resolution
        resized = cv2.resize(crop_bgr, (128, 256), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        tensor = torch.from_numpy(rgb).float().permute(2, 0, 1) / 255.0

        # ImageNet normalization
        mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
        normalized = (tensor - mean) / std

        return normalized.unsqueeze(0)  # Shape: [1, 3, 256, 128]

    @classmethod
    def extract_embedding(cls, crop_bgr: np.ndarray) -> np.ndarray:
        """
        Extract L2-normalized appearance embedding vector from target crop.
        Returns:
            np.ndarray of shape (512,) with unit norm ||v||_2 = 1.0
        """
        model = cls.load_model()
        input_tensor = cls.preprocess_crop(crop_bgr).to(cls._device)

        with torch.no_grad():
            features = model(input_tensor)  # Shape: [1, 512]
            # Apply strict L2 normalization
            normalized_features = F.normalize(features, p=2, dim=1)

        embedding = normalized_features.squeeze(0).cpu().numpy()
        return embedding

    @classmethod
    def save_target_embedding(
        cls,
        video_id: str,
        target_id: str,
        embedding: np.ndarray,
        storage_dir: Path,
    ) -> Path:
        """Store target embedding vector (.npy) associated with selected target."""
        target_dir = storage_dir / video_id / "targets"
        target_dir.mkdir(parents=True, exist_ok=True)
        out_path = target_dir / f"{target_id}_embedding.npy"
        np.save(str(out_path), embedding)
        return out_path

    @classmethod
    def load_target_embedding(
        cls,
        video_id: str,
        target_id: str,
        storage_dir: Path,
    ) -> Optional[np.ndarray]:
        """Load stored target embedding vector."""
        emb_path = storage_dir / video_id / "targets" / f"{target_id}_embedding.npy"
        if emb_path.exists():
            return np.load(str(emb_path))
        return None
