from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


DEV_ORIGINS = [
    "http://127.0.0.1:4173",
    "http://localhost:4173",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]


def _client() -> TestClient:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user:pass@localhost/db",
    )
    return TestClient(create_app(settings, session_factory=lambda: None))


def test_default_cors_allows_development_origins_and_frontend_preflight():
    client = _client()

    with client:
        for origin in DEV_ORIGINS:
            response = client.options(
                "/api/sessions",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            )

            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == origin
            allowed_methods = response.headers["access-control-allow-methods"]
            assert all(method in allowed_methods for method in ("GET", "POST", "PATCH"))
            assert "content-type" in response.headers["access-control-allow-headers"].lower()
            assert "access-control-allow-credentials" not in response.headers


def test_cors_still_rejects_unconfigured_origin():
    client = _client()

    with client:
        response = client.options(
            "/api/sessions",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.headers.get("access-control-allow-origin") is None
