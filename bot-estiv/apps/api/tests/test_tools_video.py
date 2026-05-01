"""Tests de tools/video.py — wrapper de FFmpeg con subprocess mockeado."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from bot_estiv.tools.video import (
    _run,
    add_text_overlay,
    fit_story,
    overlay_logo,
    story_pipeline,
)


# ---------------------------------------------------------------------------
# _run — wrapper de subprocess
# ---------------------------------------------------------------------------

def test_run_success_does_not_raise():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result) as mock_sub:
        _run(["ffmpeg", "-version"])
    mock_sub.assert_called_once()


def test_run_failure_raises_runtime_error():
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "Error: codec not found"
    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="ffmpeg falló"):
            _run(["ffmpeg", "-nonsense"])


def test_run_passes_capture_output_true():
    mock_result = MagicMock()
    mock_result.returncode = 0
    with patch("subprocess.run", return_value=mock_result) as mock_sub:
        _run(["ffmpeg", "-y"])
    _, kwargs = mock_sub.call_args
    assert kwargs.get("capture_output") is True


# ---------------------------------------------------------------------------
# fit_story — construye comando ffmpeg correcto
# ---------------------------------------------------------------------------

def test_fit_story_calls_ffmpeg_with_correct_args(tmp_path):
    src = tmp_path / "in.mp4"
    dst = tmp_path / "out.mp4"
    src.touch()

    mock_result = MagicMock(returncode=0, stderr="")
    with patch("subprocess.run", return_value=mock_result) as mock_sub:
        fit_story(src, dst)

    cmd = mock_sub.call_args[0][0]
    assert "ffmpeg" in cmd
    assert str(src) in cmd
    assert str(dst) in cmd
    assert "1080:1920" in " ".join(cmd)


# ---------------------------------------------------------------------------
# add_text_overlay — escapa caracteres especiales en texto
# ---------------------------------------------------------------------------

def test_add_text_overlay_escapes_apostrophe(tmp_path):
    src = tmp_path / "in.mp4"
    dst = tmp_path / "out.mp4"
    src.touch()

    mock_result = MagicMock(returncode=0, stderr="")
    with patch("subprocess.run", return_value=mock_result) as mock_sub:
        add_text_overlay(src, dst, text="Gardens Wood's pergola")

    cmd = mock_sub.call_args[0][0]
    cmd_str = " ".join(cmd)
    assert r"\'" in cmd_str


def test_add_text_overlay_escapes_colon(tmp_path):
    src = tmp_path / "in.mp4"
    dst = tmp_path / "out.mp4"
    src.touch()

    mock_result = MagicMock(returncode=0, stderr="")
    with patch("subprocess.run", return_value=mock_result) as mock_sub:
        add_text_overlay(src, dst, text="Texto: subtítulo")

    cmd = mock_sub.call_args[0][0]
    cmd_str = " ".join(cmd)
    assert r"\:" in cmd_str


def test_add_text_overlay_bottom_position(tmp_path):
    src = tmp_path / "in.mp4"
    dst = tmp_path / "out.mp4"
    src.touch()

    mock_result = MagicMock(returncode=0, stderr="")
    with patch("subprocess.run", return_value=mock_result) as mock_sub:
        add_text_overlay(src, dst, text="Hola", position="bottom")

    cmd_str = " ".join(mock_sub.call_args[0][0])
    assert "h-320" in cmd_str


def test_add_text_overlay_top_position(tmp_path):
    src = tmp_path / "in.mp4"
    dst = tmp_path / "out.mp4"
    src.touch()

    mock_result = MagicMock(returncode=0, stderr="")
    with patch("subprocess.run", return_value=mock_result) as mock_sub:
        add_text_overlay(src, dst, text="Hola", position="top")

    cmd_str = " ".join(mock_sub.call_args[0][0])
    assert "160" in cmd_str


# ---------------------------------------------------------------------------
# overlay_logo — incluye logo en el comando
# ---------------------------------------------------------------------------

def test_overlay_logo_includes_logo_path(tmp_path):
    src = tmp_path / "in.mp4"
    dst = tmp_path / "out.mp4"
    src.touch()

    mock_result = MagicMock(returncode=0, stderr="")
    with patch("subprocess.run", return_value=mock_result) as mock_sub:
        overlay_logo(src, dst)

    cmd = mock_sub.call_args[0][0]
    assert "-i" in cmd  # segunda entrada (logo)


# ---------------------------------------------------------------------------
# story_pipeline — pipeline completo con archivos temporales
# ---------------------------------------------------------------------------

def test_story_pipeline_calls_all_steps(tmp_path):
    """Verifica que el pipeline llame a las 3 etapas en orden."""
    fake_video_bytes = b"fake mp4 data"
    final_bytes = b"final video"

    call_order = []

    def mock_fit(src, dst):
        call_order.append("fit")
        dst.write_bytes(b"fitted")

    def mock_text(src, dst, text):
        call_order.append("text")
        dst.write_bytes(b"text_added")

    def mock_logo(src, dst):
        call_order.append("logo")
        dst.write_bytes(final_bytes)

    with (
        patch("bot_estiv.tools.video.fit_story", side_effect=mock_fit),
        patch("bot_estiv.tools.video.add_text_overlay", side_effect=mock_text),
        patch("bot_estiv.tools.video.overlay_logo", side_effect=mock_logo),
    ):
        result = story_pipeline(fake_video_bytes, "Artesanía en Quebracho", tmp_path)

    assert call_order == ["fit", "text", "logo"]
    assert result == final_bytes


def test_story_pipeline_creates_work_dir(tmp_path):
    work_dir = tmp_path / "pipeline_test"
    fake_bytes = b"video"

    with (
        patch("bot_estiv.tools.video.fit_story") as m1,
        patch("bot_estiv.tools.video.add_text_overlay") as m2,
        patch("bot_estiv.tools.video.overlay_logo") as m3,
    ):
        # Simular que cada paso escribe el archivo de salida
        def write_output(*args):
            args[1].write_bytes(b"output")

        m1.side_effect = write_output
        m2.side_effect = write_output
        m3.side_effect = lambda src, dst: dst.write_bytes(b"final")

        story_pipeline(fake_bytes, "headline", work_dir)

    assert work_dir.exists()
