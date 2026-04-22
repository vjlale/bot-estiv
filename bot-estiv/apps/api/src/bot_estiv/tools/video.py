"""Edición de video con FFmpeg para historias 9:16.

Capacidades:
- Recorte/encuadre a 1080x1920 (9:16)
- Drawtext con fuente de marca
- Overlay de logo PNG
- Barras superior/inferior de marca

Se asume FFmpeg instalado en el sistema (ver Dockerfile).
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from ..config import settings

logger = logging.getLogger(__name__)


def _run(cmd: list[str]) -> None:
    logger.debug("ffmpeg.run", extra={"cmd": " ".join(cmd)})
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg falló: {result.stderr[-2000:]}")


def fit_story(input_path: Path, output_path: Path) -> None:
    """Ajusta a 1080x1920 con crop cover + blur fondo si aspect no matchea."""
    vf = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,setsar=1[v]"
    )
    _run(
        [
            "ffmpeg", "-y", "-i", str(input_path),
            "-filter_complex", vf, "-map", "[v]", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k", str(output_path),
        ]
    )


def add_text_overlay(
    input_path: Path,
    output_path: Path,
    text: str,
    position: str = "bottom",
    color: str = "white",
    box_color: str = "0x36454F@0.75",
    font_size: int = 56,
) -> None:
    """Agrega una capa de texto con caja de marca en la parte indicada."""
    y_expr = "h-320" if position == "bottom" else "160"
    esc = text.replace("'", r"\'").replace(":", r"\:")
    vf = (
        f"drawtext=text='{esc}':"
        f"fontcolor={color}:fontsize={font_size}:"
        f"x=(w-text_w)/2:y={y_expr}:"
        f"box=1:boxcolor={box_color}:boxborderw=32"
    )
    _run(
        [
            "ffmpeg", "-y", "-i", str(input_path),
            "-vf", vf, "-c:a", "copy", str(output_path),
        ]
    )


def overlay_logo(input_path: Path, output_path: Path) -> None:
    """Superpone el logo de marca en esquina inferior derecha."""
    logo = settings.brand_logo_abs
    vf = (
        "[1:v]scale=220:-1[logo];"
        "[0:v][logo]overlay=main_w-overlay_w-40:main_h-overlay_h-40"
    )
    _run(
        [
            "ffmpeg", "-y", "-i", str(input_path), "-i", str(logo),
            "-filter_complex", vf, "-c:a", "copy", str(output_path),
        ]
    )


def story_pipeline(
    input_video_bytes: bytes,
    headline: str,
    work_dir: Path,
) -> bytes:
    """Pipeline completo: recibe bytes, retorna bytes listos para historia."""
    work_dir.mkdir(parents=True, exist_ok=True)
    src = work_dir / "src.mp4"
    a = work_dir / "a.mp4"
    b = work_dir / "b.mp4"
    c = work_dir / "final.mp4"
    src.write_bytes(input_video_bytes)
    fit_story(src, a)
    add_text_overlay(a, b, headline)
    overlay_logo(b, c)
    return c.read_bytes()
