import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BAYTA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("BAYTA_SCHEDULER_ENABLED", "0")

    from app.core.config import get_settings
    from app.db.session import reset_engine

    get_settings.cache_clear()
    reset_engine()

    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c

    get_settings.cache_clear()
    reset_engine()


@pytest.fixture
def db(client):
    """A session bound to the same temp database as `client`."""
    from app.db.session import session_factory

    s = session_factory()()
    try:
        yield s
    finally:
        s.close()
