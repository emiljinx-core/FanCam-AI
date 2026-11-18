import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple
from app.config import settings


class AudioMuxer:
    """
    Subprocess FFmpeg caller:
    - Audio stream detection
    - Stream copy (-c:a copy) when container/codec is compatible
    - Fallback to AAC (-c:a aac -b:a 192k) when copy is incompatible
    - Preserves source FPS, expected frame count, duration, and audio synchronization
    - Web optimization (-movflags +faststart)
    - Graceful video-only fallback for silent source clips
    """

    @classmethod
    def get_ffmpeg_exe(cls) -> str:
        """Locates the FFmpeg executable."""
        candidates = [
            getattr(settings, "FFMPEG_PATH", None),
            shutil.which("ffmpeg"),
        ]
        for c in candidates:
            if c and Path(c).exists():
                return str(c)
        return "ffmpeg"

    @classmethod
    def has_audio_stream(cls, source_video_path: Path) -> bool:
        """Checks whether the source video contains at least one audio stream."""
        ffmpeg_exe = cls.get_ffmpeg_exe()
        try:
            # Run lightweight ffmpeg probe
            cmd = [
                ffmpeg_exe,
                "-hide_banner",
                "-i",
                str(source_video_path),
            ]
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            # ffmpeg reports stream info on stderr
            output = res.stderr or ""
            return "Audio:" in output
        except Exception:
            return False

    @classmethod
    def mux_video_and_audio(
        cls,
        rendered_video_path: Path,
        source_video_path: Path,
        output_path: Path,
        fps: float = 30.0,
        duration: Optional[float] = None,
    ) -> Path:
        """
        Muxes the rendered video and source audio into output_path:
        1. Tries stream copy (-c:a copy).
        2. If stream copy fails or is incompatible, falls back to AAC (-c:a aac -b:a 192k).
        3. If no audio stream exists, converts video directly to web-compatible H.264.
        """
        ffmpeg_exe = cls.get_ffmpeg_exe()
        has_audio = cls.has_audio_stream(source_video_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_out = output_path.with_name(f"temp_mux_{output_path.name}")

        dur_args = ["-t", f"{duration:.3f}"] if duration is not None and duration > 0 else []

        if has_audio:
            # Attempt 1: Stream copy (-c:a copy)
            copy_cmd = [
                ffmpeg_exe,
                "-y",
                "-i",
                str(rendered_video_path),
                "-i",
                str(source_video_path),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0?",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "19",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "copy",
            ] + dur_args + [
                "-movflags",
                "+faststart",
                str(temp_out),
            ]

            res_copy = subprocess.run(
                copy_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if res_copy.returncode == 0 and temp_out.exists() and temp_out.stat().st_size > 0:
                if output_path.exists():
                    output_path.unlink()
                temp_out.rename(output_path)
                return output_path

            # Attempt 2: AAC fallback (-c:a aac -b:a 192k)
            aac_cmd = [
                ffmpeg_exe,
                "-y",
                "-i",
                str(rendered_video_path),
                "-i",
                str(source_video_path),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0?",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "19",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
            ] + dur_args + [
                "-movflags",
                "+faststart",
                str(temp_out),
            ]

            res_aac = subprocess.run(
                aac_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if res_aac.returncode == 0 and temp_out.exists() and temp_out.stat().st_size > 0:
                if output_path.exists():
                    output_path.unlink()
                temp_out.rename(output_path)
                return output_path

        # Fallback / Silent video path: encode video to web-ready MP4 (libx264, faststart)
        video_only_cmd = [
            ffmpeg_exe,
            "-y",
            "-i",
            str(rendered_video_path),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "19",
            "-pix_fmt",
            "yuv420p",
        ] + dur_args + [
            "-movflags",
            "+faststart",
            str(temp_out),
        ]
        res_vo = subprocess.run(
            video_only_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if res_vo.returncode == 0 and temp_out.exists() and temp_out.stat().st_size > 0:
            if output_path.exists():
                output_path.unlink()
            temp_out.rename(output_path)
            return output_path

        # If ffmpeg encounters an issue, fall back to moving rendered video directly
        if rendered_video_path != output_path:
            shutil.copyfile(rendered_video_path, output_path)
        return output_path
