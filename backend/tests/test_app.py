"""
App-wide guard tests: things that should stay true no matter which routes are
added later, most importantly that no route is accidentally left unprotected.

Run from backend/:  pytest tests/test_app.py
"""

from app.main import app

# The only routes that may be called without signing in.
PUBLIC_ROUTES = {
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("GET", "/health"),
}


HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def _operations():
    """Every (method, path, details) the API publishes.

    Read from the OpenAPI description rather than app.routes: with newer FastAPI
    versions app.routes only showed /health here, while the OpenAPI description
    (the same list /docs shows) has every route.
    """
    for path, methods in app.openapi()["paths"].items():
        for method, details in methods.items():
            if method.upper() in HTTP_METHODS:
                yield method.upper(), path, details


def test_every_route_requires_authentication_unless_explicitly_public():
    unprotected = []
    checked = 0
    for method, path, details in _operations():
        checked += 1
        if (method, path) in PUBLIC_ROUTES:
            continue
        # Routes that depend on get_current_user carry the bearer-token security scheme.
        if not details.get("security"):
            unprotected.append((method, path))
    assert checked >= 10  # guards against this test silently checking nothing
    assert unprotected == []


def test_the_expected_routes_exist():
    routes = {(method, path) for method, path, _ in _operations()}
    expected = {
        ("POST", "/auth/register"), ("POST", "/auth/login"), ("GET", "/auth/me"),
        ("POST", "/screenings"), ("GET", "/screenings"), ("DELETE", "/screenings"),
        ("GET", "/screenings/{screening_id}"), ("DELETE", "/screenings/{screening_id}"),
        ("POST", "/screenings/{screening_id}/labs"),
        ("GET", "/account/export"), ("DELETE", "/account"),
        ("GET", "/health"),
    }
    assert expected <= routes


def test_health_is_public_and_leaks_nothing_sensitive(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert set(response.json()) == {"status", "environment", "model_validated"}


def test_unknown_routes_and_wrong_methods(client):
    assert client.get("/nope").status_code == 404
    assert client.put("/screenings").status_code == 405
    assert client.patch("/account").status_code == 405


def test_cors_allows_the_configured_frontend_only(client):
    preflight = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    }
    allowed = client.options("/screenings", headers={"Origin": "http://localhost:3000", **preflight})
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"

    denied = client.options("/screenings", headers={"Origin": "https://evil.example", **preflight})
    assert "access-control-allow-origin" not in denied.headers


def test_models_are_loaded_at_startup(client):
    registry = client.app.state.registry
    assert len(registry.tier1.feature_names) == 12
    assert set(registry.lab_fields) == {"CA_125_Level", "CRP_Level"}
