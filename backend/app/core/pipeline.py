import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import cv2
import numpy as np

from app.config import settings
from app.core.tasks import TaskManager
from app.core.video import VideoProcessor
from app.core.detector import PersonDetector
from app.core.reid import OSNetReIDExtractor
from app.core.tracking import (
    ByteTracker,
    DeepSortTracker,
    Detection,
    TargetMatcher,
    TargetState,
)
from app.core.framing import (
    CinematicFramingEngine,
    FramingCrop,
)
from app.core.rendering import VideoRenderer


class PipelineOrchestrator:
    """Orchestrates end-to-end background FanCam video processing."""

    @classmethod
    def _initialize_tracker(cls, tracker_name: str, fps: float = 30.0):
        """Instantiate tracker strictly based on user selection."""
        tracker_clean = (tracker_name or "bytetrack").lower().strip()
        if tracker_clean == "deepsort":
            return DeepSortTracker(
                max_age=int(round(fps * 2.0)),
                n_init=2,
                max_cosine_distance=0.4,
                nn_budget=100,
            )
        else:
            return ByteTracker(
                high_thresh=0.5,
                low_thresh=0.1,
                match_thresh_high=0.8,
                match_thresh_low=0.5,
                track_buffer=int(round(fps * 2.0)),
            )

    @classmethod
    def track_video(
        cls,
        video_id: str,
        target_id: str,
        tracker_name: str,
        task_id: Optional[str] = None,
        max_frames: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Synchronous processing loop for video tracking & target re-identification:
        VideoProcessor -> PersonDetector -> Feature Extraction -> Tracker -> TargetMatcher.
        Saves trajectory to storage/outputs/{video_id}/trajectory.json.
        """
        source_path = VideoProcessor.get_source_path(settings.UPLOADS_DIR, video_id)
        if not source_path or not source_path.exists():
            raise FileNotFoundError(f"Source video for '{video_id}' not found.")

        # Load reference target embedding (512-D unit vector)
        target_embedding = OSNetReIDExtractor.load_target_embedding(
            video_id=video_id,
            target_id=target_id,
            storage_dir=settings.UPLOADS_DIR,
        )
        if target_embedding is None:
            raise RuntimeError(
                f"Signature embedding for target '{target_id}' could not be loaded."
            )

        metadata = VideoProcessor.get_metadata(source_path)
        fps = metadata.fps if metadata.fps > 0 else 30.0
        total_frames = metadata.frame_count if metadata.frame_count > 0 else 1
        if max_frames and max_frames > 0:
            total_frames = min(total_frames, max_frames)

        # Initialize tracker and target matcher
        tracker = cls._initialize_tracker(tracker_name, fps=fps)
        matcher = TargetMatcher(
            reference_signature=target_embedding,
            similarity_threshold=0.50,
            ambiguity_margin=0.08,
            max_lost_frames=int(round(fps * 1.5)),
            gallery_update_threshold=0.75,
            gallery_budget=20,
        )

        cap = cv2.VideoCapture(str(source_path))
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video source: {source_path}")

        trajectory: List[Dict[str, Any]] = []
        frame_idx = 0
        last_progress_update = time.time()

        try:
            while cap.isOpened():
                ret, frame_bgr = cap.read()
                if not ret or frame_bgr is None:
                    break

                if max_frames and frame_idx >= max_frames:
                    break

                timestamp_sec = frame_idx / fps

                # 1. Human detection (class 0)
                raw_dets = PersonDetector.detect_people(frame_bgr, conf_threshold=0.35)
                h, w = frame_bgr.shape[:2]

                detections: List[Detection] = []
                for det in raw_dets:
                    x1, y1, x2, y2 = det["x1"], det["y1"], det["x2"], det["y2"]
                    conf = det["confidence"] / 100.0  # Normalized [0.0, 1.0]

                    # Extract appearance embedding for the detection crop
                    crop = frame_bgr[y1:y2, x1:x2]
                    feature = None
                    if crop.size > 0 and (x2 - x1) >= 8 and (y2 - y1) >= 16:
                        try:
                            feature = OSNetReIDExtractor.extract_embedding(crop)
                        except Exception:
                            feature = None

                    detections.append(
                        Detection(
                            box=[float(x1), float(y1), float(x2), float(y2)],
                            confidence=conf,
                            class_id=0,
                            feature=feature,
                        )
                    )

                # 2. Update multi-object tracker
                active_tracks = tracker.update(detections)

                # 3. Associate and lock onto target subject
                match_result = matcher.match_target(
                    frame_index=frame_idx,
                    active_tracks=active_tracks,
                    frame_bgr=frame_bgr,
                )

                record = {
                    "frame_index": match_result.frame_index,
                    "timestamp_sec": round(timestamp_sec, 3),
                    "state": match_result.state.value,
                    "box": [round(coord, 2) for coord in match_result.box]
                    if match_result.box
                    else None,
                    "confidence": round(match_result.confidence, 4)
                    if match_result.confidence is not None
                    else None,
                    "similarity": round(match_result.similarity, 4)
                    if match_result.similarity is not None
                    else None,
                    "active_track_id": match_result.active_track_id,
                    "is_ambiguous": match_result.is_ambiguous,
                    "message": match_result.message,
                }
                trajectory.append(record)

                frame_idx += 1

                # Update progress periodically (from 10% to 50% during tracking)
                if task_id and (time.time() - last_progress_update > 0.5 or frame_idx == total_frames):
                    progress_pct = 10.0 + 40.0 * min(1.0, frame_idx / total_frames)
                    TaskManager.update_progress(
                        task_id=task_id,
                        progress=round(progress_pct, 1),
                        step=f"Tracking target with {tracker_name.upper()} (Frame {frame_idx}/{total_frames})...",
                    )
                    last_progress_update = time.time()

        finally:
            cap.release()

        # Save trajectory JSON artifact
        output_dir = settings.OUTPUTS_DIR / video_id
        output_dir.mkdir(parents=True, exist_ok=True)
        trajectory_file = output_dir / "trajectory.json"
        with open(trajectory_file, "w") as f:
            json.dump(
                {
                    "video_id": video_id,
                    "target_id": target_id,
                    "tracker": tracker_name,
                    "fps": round(fps, 2),
                    "total_frames": len(trajectory),
                    "trajectory": trajectory,
                },
                f,
                indent=2,
            )

        return trajectory

    @classmethod
    async def run_pipeline(cls, task_id: str) -> None:
        """
        Asynchronous worker pipeline executing tracking, framing, and rendering.
        Plugs cleanly into Steps 5, 6, and 7.
        """
        task = TaskManager.get_task(task_id)
        if not task:
            return

        video_id = task["video_id"]
        target_id = task["target_id"]
        tracker = task["tracker"]
        aspect_ratio = task["aspect_ratio"]
        smoothing_level = task["smoothing_level"]

        try:
            # Stage 1: Load target embedding signature & initialize
            TaskManager.update_progress(
                task_id=task_id,
                progress=10.0,
                step=f"Initializing {tracker.upper()} tracker and loading OSNet signature for {target_id}...",
            )
            embedding = OSNetReIDExtractor.load_target_embedding(
                video_id=video_id,
                target_id=target_id,
                storage_dir=settings.UPLOADS_DIR,
            )
            if embedding is None:
                raise RuntimeError(
                    f"Signature embedding for target '{target_id}' could not be loaded."
                )

            # Stage 2: Multi-object tracking & Re-ID association (Step 5 execution)
            # Run tracking in a separate thread so asyncio event loop stays responsive
            await asyncio.to_thread(
                cls.track_video,
                video_id=video_id,
                target_id=target_id,
                tracker_name=tracker,
                task_id=task_id,
            )

            # Stage 3: Adaptive cinematic framing & Kalman filter (Step 6 execution)
            TaskManager.update_progress(
                task_id=task_id,
                progress=55.0,
                step=f"Computing dynamic {aspect_ratio} bounding crop with smoothing level {smoothing_level}...",
            )

            # Load generated trajectory
            traj_path = settings.OUTPUTS_DIR / video_id / "trajectory.json"
            if not traj_path.exists():
                raise FileNotFoundError(f"Trajectory data for '{video_id}' not found.")

            with open(traj_path, "r") as f:
                traj_data = json.load(f)
            trajectory_records = traj_data.get("trajectory", [])

            # Get video source dimensions
            source_path = VideoProcessor.get_source_path(settings.UPLOADS_DIR, video_id)
            meta = VideoProcessor.get_metadata(source_path)

            framing_engine = CinematicFramingEngine(
                frame_width=meta.width,
                frame_height=meta.height,
                aspect_ratio=aspect_ratio,
                smoothing_level=smoothing_level,
                fps=meta.fps,
            )

            crops = framing_engine.generate_trajectory_crops(trajectory_records)

            # Save crops.json artifact
            crops_file = settings.OUTPUTS_DIR / video_id / "crops.json"
            with open(crops_file, "w") as f:
                json.dump(
                    {
                        "video_id": video_id,
                        "target_id": target_id,
                        "aspect_ratio": aspect_ratio,
                        "smoothing_level": smoothing_level,
                        "frame_width": meta.width,
                        "frame_height": meta.height,
                        "total_frames": len(crops),
                        "crops": [c.to_dict() for c in crops],
                    },
                    f,
                    indent=2,
                )

            TaskManager.update_progress(
                task_id=task_id,
                progress=75.0,
                step="Adaptive cinematic framing complete. Preparing video rendering...",
            )

            # Stage 4: Video rendering & audio muxing (Step 7 execution)
            TaskManager.update_progress(
                task_id=task_id,
                progress=80.0,
                step="Rendering dynamically reframed video frames...",
            )

            crops_dicts = [c.to_dict() for c in crops]
            output_filename = f"fancam_{target_id}_{aspect_ratio.replace(':', '_')}.mp4"
            final_output_path = settings.OUTPUTS_DIR / video_id / output_filename

            comparison_filename = f"comparison_{target_id}.mp4"
            final_comparison_path = settings.OUTPUTS_DIR / video_id / comparison_filename

            def on_render_progress(fraction: float):
                pct = 80.0 + 15.0 * fraction
                TaskManager.update_progress(
                    task_id=task_id,
                    progress=round(pct, 1),
                    step=f"Rendering FanCam highlight ({int(fraction * 100)}%)...",
                )

            # Render highlight with audio muxing
            await asyncio.to_thread(
                VideoRenderer.render_highlight_video,
                source_video_path=source_path,
                crops_data=crops_dicts,
                output_mp4_path=final_output_path,
                aspect_ratio=aspect_ratio,
                fps=meta.fps,
                progress_callback=on_render_progress,
            )

            # Render comparison side-by-side video
            TaskManager.update_progress(
                task_id=task_id,
                progress=95.0,
                step="Rendering comparison video...",
            )
            await asyncio.to_thread(
                VideoRenderer.render_comparison_video,
                source_video_path=source_path,
                crops_data=crops_dicts,
                output_mp4_path=final_comparison_path,
                aspect_ratio=aspect_ratio,
                fps=meta.fps,
            )

            output_url = f"/static/outputs/{video_id}/{output_filename}"
            comparison_url = f"/static/outputs/{video_id}/{comparison_filename}"

            TaskManager.mark_completed(
                task_id=task_id,
                output_video_url=output_url,
                comparison_video_url=comparison_url,
            )

        except Exception as e:
            TaskManager.mark_failed(task_id=task_id, error_message=str(e))
