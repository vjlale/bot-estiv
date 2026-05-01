"""Fixtures compartidos para todos los tests."""
import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Variables de entorno mínimas para que Settings no intente conectar a servicios reales
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://test:test@localhost/test")
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("APP_ENV", "test")


# ---- Fixtures de base de datos ----

@pytest.fixture
def mock_session():
    """AsyncSession completamente mockeada para tests unitarios."""
    session = AsyncMock()
    # execute().scalars().all() pattern
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    result.scalar_one_or_none.return_value = None
    result.scalar_one.return_value = MagicMock()
    session.execute.return_value = result
    return session


@pytest.fixture
def mock_session_factory(mock_session):
    """Context manager que devuelve mock_session."""
    factory = MagicMock()
    factory.__aenter__ = AsyncMock(return_value=mock_session)
    factory.__aexit__ = AsyncMock(return_value=False)
    return factory


# ---- Fixtures de LLM ----

@pytest.fixture
def mock_chain():
    """Cadena LangChain mockeada que devuelve un objeto configurable."""
    chain = MagicMock()
    chain.ainvoke = AsyncMock()
    return chain


@pytest.fixture
def mock_llm():
    """get_chat_model() mockeado para que no llame a la API de Gemini."""
    llm = MagicMock()
    llm.invoke = MagicMock()
    llm.ainvoke = AsyncMock()
    return llm


# ---- Cliente HTTP para tests de routers ----

@pytest.fixture
def app():
    """Instancia de la FastAPI app con dependencias sobreescritas."""
    # Importar aquí para que las env vars ya estén seteadas
    from bot_estiv.main import app as _app
    from bot_estiv.db import get_session

    async def override_get_session():
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        result.scalar_one_or_none.return_value = None
        session.execute.return_value = result
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        yield session

    _app.dependency_overrides[get_session] = override_get_session
    yield _app
    _app.dependency_overrides.clear()


@pytest.fixture
async def client(app):
    """httpx.AsyncClient apuntando a la app en modo test."""
    import httpx

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
