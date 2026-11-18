from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
import cv2
import numpy as np

from app.core.rendering.audio_muxer import AudioMuxer


class VideoRenderer:
    """
    Renders reframed video highlight and side-by-side comparison video.
    Preserves exact FPS, total frame count, and timing.
    """

    TARGET_RESOLUTIONS = {
        "9:16": (1080, 1920),
        "1:1": (1080, 1080),
        "16:9": (1920, 1080),
    }

    @classmethod
    def render_highlight_video(
        cls,
        source_video_path: Path,
        crops_data: List[Dict[str, Any]],
        output_mp4_path: Path,
        aspect_ratio: str = "9:16",
        fps: float = 30.0,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Path:
        """
        Reads source video frames, crops the dynamic window, resizes to target delivery resolution,
        and uses AudioMuxer to mux original audio stream with sync preservation.
        """
        target_w, target_h = cls.TARGET_RESOLUTIONS.get(aspect_ratio, (1080, 1920))
        temp_video_path = output_mp4_path.parent / f"temp_render_{output_mp4_path.name}"
        temp_video_path.parent.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(source_video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open source video: {source_video_path}")

        # Choose mp4v codec for temporary OpenCV output
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(temp_video_path),
            fourcc,
            fps,
            (target_w, target_h),
        )

        total_frames = len(crops_data)
        frame_idx = 0

        try:
            while cap.isOpened() and frame_idx < total_frames:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                crop_info = crops_data[frame_idx]
                crop_int = crop_info.get("crop_int")
                if crop_int and len(crop_int) == 4:
                    x1, y1, x2, y2 = crop_int
                    # Slice crop
                    cropped_frame = frame[y1:y2, x1:x2]
                else:
                    cropped_frame = frame

                # Resize to target delivery resolution
                if cropped_frame.shape[1] != target_w or cropped_frame.shape[0] != target_h:
                    resized = cv2.resize(
                        cropped_frame,
                        (target_w, target_h),
                        interpolation=cv2.INTER_LANCZOS4,
                    )
                else:
                    resized = cropped_frame

                writer.write(resized)
                frame_idx += 1

                if progress_callback and total_frames > 0 and frame_idx % 10 == 0:
                    pct = min(1.0, frame_idx / total_frames)
                    progress_callback(pct)

        finally:
            cap.release()
            writer.release()

        # Mux with original audio preserving sync and FPS
        duration = total_frames / fps if fps > 0 else None
        AudioMuxer.mux_video_and_audio(
            rendered_video_path=temp_video_path,
            source_video_path=source_video_path,
            output_path=output_mp4_path,
            fps=fps,
            duration=duration,
        )

        # Clean up temporary OpenCV video
        if temp_video_path.exists():
            temp_video_path.unlink()

        return output_mp4_path

    @classmethod
    def render_comparison_video(
        cls,
        source_video_path: Path,
        crops_data: List[Dict[str, Any]],
        output_mp4_path: Path,
        aspect_ratio: str = "9:16",
        fps: float = 30.0,
    ) -> Path:
        """
        Renders side-by-side comparison video:
        Left: Source video with highlighted dynamic camera crop box and center point.
        Right: Reframed output highlight.
        """
        target_w, target_h = cls.TARGET_RESOLUTIONS.get(aspect_ratio, (1080, 1920))
        # Comparison layout: 1920 x 1080 split canvas
        comp_w, comp_h = 1920, 1080
        temp_video_path = output_mp4_path.parent / f"temp_comp_{output_mp4_path.name}"
        temp_video_path.parent.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(source_video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open source video: {source_video_path}")

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(temp_video_path),
            fourcc,
            fps,
            (comp_w, comp_h),
        )

        total_frames = len(crops_data)
        frame_idx = 0

        # Half width for each pane (960 x 1080)
        pane_w = comp_w // 2

        try:
            while cap.isOpened() and frame_idx < total_frames:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                crop_info = crops_data[frame_idx]
                crop_int = crop_info.get("crop_int", [0, 0, frame.shape[1], frame.shape[0]])
                x1, y1, x2, y2 = crop_int

                # Left Pane: Source video with overlaid crop rectangle
                left_display = frame.copy()
                cv2.rectangle(left_display, (x1, y1), (x2, y2), (52, 211, 153), 4)  # Emerald green box
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                cv2.circle(left_display, (cx, cy), 6, (0, 0, 255), -1)  # Red camera center

                # Scale left display to fit (pane_w, comp_h) preserving aspect ratio
                lh, lw = left_display.shape[:2]
                scale_left = min(pane_w / lw, comp_h / lh)
                scaled_lw, scaled_lh = int(lw * scale_left), int(lh * scale_left)
                resized_left = cv2.resize(left_display, (scaled_lw, scaled_lh))

                left_canvas = np.zeros((comp_h, pane_w, 3), dtype=np.uint8)
                off_x = (pane_w - scaled_lw) // 2
                off_y = (comp_h - scaled_lh) // 2
                left_canvas[off_y:off_y + scaled_lh, off_x:off_x + scaled_lw] = resized_left

                # Label Left
                cv2.putText(
                    left_canvas,
                    "SOURCE FOOTAGE & CAMERA TRACK",
                    (30, 45),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )

                # Right Pane: Cropped reframed target
                cropped = frame[y1:y2, x1:x2]
                rh, rw = cropped.shape[:2]
                scale_right = min(pane_w / rw, comp_h / rh)
                scaled_rw, scaled_rh = int(rw * scale_right), int(rh * scale_right)
                resized_right = cv2.resize(cropped, (scaled_rw, scaled_rh))

                right_canvas = np.zeros((comp_h, pane_w, 3), dtype=np.uint8)
                roff_x = (pane_w - scaled_rw) // 2
                roff_y = (comp_h - scaled_rh) // 2
                right_canvas[roff_y:roff_y + scaled_rh, roff_x:roff_x + scaled_rw] = resized_right

                # Label Right
                cv2.putText(
                    right_canvas,
                    f"FANCAM REFRAMED ({aspect_ratio})",
                    (30, 45),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (52, 211, 153),
                    2,
                )

                # Combine Left + Right
                combined = np.hstack([left_canvas, right_canvas])
                writer.write(combined)
                frame_idx += 1

        finally:
            cap.release()
            writer.release()

        # Mux comparison audio
        duration = total_frames / fps if fps > 0 else None
        AudioMuxer.mux_video_and_audio(
            rendered_video_path=temp_video_path,
            source_video_path=source_video_path,
            output_path=output_mp4_path,
            fps=fps,
            duration=duration,
        )

        if temp_video_path.exists():
            temp_video_path.unlink()

        return output_mp4_path
