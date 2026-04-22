"""Tests de la parte pura de ingesta (chunk_manual)."""
from bot_estiv.rag.ingest import chunk_manual


def test_chunk_manual_splits_sections():
    sample = """\
1 Plataforma
texto intro

1.1 Esencia
Somos Gardens Wood.

1.2 Misión
Enriquecer vidas.

2 Identidad
Color y tipografía.
"""
    chunks = chunk_manual(sample)
    sections = [s for s, _ in chunks]
    assert "1" in sections
    assert "1.1" in sections
    assert "1.2" in sections
    assert "2" in sections
