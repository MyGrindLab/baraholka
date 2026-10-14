import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from src.core.settings import Settings, settings
from src.main import app

ITEMS = "/api/items"


def texts(resp) -> list[str]:
    return sorted(i["text"] for i in resp.json()["items"])


def cors_options(application: FastAPI) -> dict:
    for mw in application.user_middleware:
        if mw.cls is CORSMiddleware:
            return dict(mw.kwargs)
    raise AssertionError("CORSMiddleware not installed")


# ---- AC2: unknown channel -> 404 -------------------------------------------


@pytest.mark.parametrize("name", ["nope", "users", "channels", "system.indexes"])
@pytest.mark.parametrize(
    "path",
    ["/api/items?channel={n}", "/api/{n}/1", "/api/{n}/1/replies"],
)
def test_unknown_channel_returns_404(client, path, name):
    resp = client.get(path.format(n=name))
    assert resp.status_code == 404
    assert resp.json()["detail"] == f"Channel '{name}' not found"


def test_items_registered_channel_returns_200(client):
    resp = client.get(ITEMS, params={"channel": "chan_a"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 3  # reply excluded


def test_item_by_id_registered_channel_returns_200(client):
    resp = client.get("/api/chan_a/1")
    assert resp.status_code == 200
    assert resp.json()["message_id"] == 1


def test_replies_registered_channel_returns_200(client):
    resp = client.get("/api/chan_a/1/replies")
    assert resp.status_code == 200
    assert [r["message_id"] for r in resp.json()] == [4]


# ---- AC3: literal search ---------------------------------------------------


def test_search_dot_is_literal(client):
    resp = client.get(ITEMS, params={"channel": "chan_a", "search": "a.b"})
    assert resp.status_code == 200
    assert texts(resp) == ["a.b phone"]


def test_search_unbalanced_paren_returns_200(client):
    resp = client.get(ITEMS, params={"channel": "chan_a", "search": "("})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_search_dot_star_matches_only_literal(client):
    resp = client.get(ITEMS, params={"channel": "chan_a", "search": ".*"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_search_stays_case_insensitive(client):
    resp = client.get(ITEMS, params={"channel": "chan_a", "search": "A.B"})
    assert resp.status_code == 200
    assert texts(resp) == ["a.b phone"]


# ---- Length limits ---------------------------------------------------------


def test_search_200_chars_ok(client):
    resp = client.get(ITEMS, params={"channel": "chan_a", "search": "x" * 200})
    assert resp.status_code == 200


def test_search_201_chars_rejected(client):
    resp = client.get(ITEMS, params={"channel": "chan_a", "search": "x" * 201})
    assert resp.status_code == 422


@pytest.mark.parametrize("field", ["subcategory", "category", "channel"])
def test_100_chars_not_rejected_by_validation(client, field):
    resp = client.get(ITEMS, params={"channel": "chan_a", field: "x" * 100})
    # A 100-char channel is valid input but unknown -> 404, never 422.
    assert resp.status_code in (200, 404)


@pytest.mark.parametrize("field", ["subcategory", "category", "channel"])
def test_101_chars_rejected(client, field):
    resp = client.get(ITEMS, params={"channel": "chan_a", field: "x" * 101})
    assert resp.status_code == 422


# ---- Subcategory exact match ----------------------------------------------


def test_subcategory_exact_match_hits_array_element(client):
    resp = client.get(
        ITEMS,
        params={"channel": "chan_a", "category": "furniture", "subcategory": "tables"},
    )
    assert resp.status_code == 200
    assert texts(resp) == ["sofa"]


def test_subcategory_partial_substring_does_not_match(client):
    resp = client.get(
        ITEMS,
        params={"channel": "chan_a", "category": "furniture", "subcategory": "table"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ---- channel=all -----------------------------------------------------------


def test_channel_all_empty_channels_returns_empty_page(db):
    resp = TestClient(app).get(ITEMS, params={"channel": "all"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["total_pages"] == 0


def test_channel_all_is_not_treated_as_unknown_channel(client):
    # mongomock does not implement $unionWith, which the real "all" path uses
    # when channels exist, so the aggregation itself is not verified here.
    # Only assert "all" is never rejected as an unknown channel (404).
    try:
        resp = client.get(ITEMS, params={"channel": "all"})
    except Exception as exc:
        assert "unionWith" in str(exc) or "NotImplemented" in type(exc).__name__
    else:
        assert resp.status_code != 404


# ---- AC1: CORS -------------------------------------------------------------


def test_allow_origins_list_parsing():
    s = Settings(debug=False, allow_origins=" https://a.org , ,https://b.org ")
    assert s.allow_origins_list == ["https://a.org", "https://b.org"]


def test_main_app_cors_credentials_disabled():
    assert cors_options(app)["allow_credentials"] is False


def test_main_app_cors_origins_follow_settings():
    expected = ["*"] if settings.debug else settings.allow_origins_list
    assert cors_options(app)["allow_origins"] == expected


def test_production_default_is_not_wildcard():
    s = Settings(debug=False)
    assert "*" not in s.allow_origins_list


def _build_app(s: Settings) -> FastAPI:
    # Same expression as src/main.py.
    application = FastAPI()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if s.debug else s.allow_origins_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/ping")
    def ping() -> dict:
        return {}

    return application


def _preflight(application: FastAPI, origin: str):
    return TestClient(application).options(
        "/ping",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )


def test_prod_preflight_echoes_allowed_origin():
    s = Settings(debug=False, allow_origins="https://a.org,https://b.org")
    resp = _preflight(_build_app(s), "https://b.org")
    assert resp.headers.get("access-control-allow-origin") == "https://b.org"


def test_prod_preflight_denies_foreign_origin():
    s = Settings(debug=False, allow_origins="https://a.org,https://b.org")
    resp = _preflight(_build_app(s), "https://evil.example")
    assert "access-control-allow-origin" not in resp.headers
    assert resp.status_code == 400


def test_debug_preflight_allows_any_origin():
    s = Settings(debug=True, allow_origins="https://a.org")
    resp = _preflight(_build_app(s), "https://evil.example")
    assert resp.headers.get("access-control-allow-origin") == "*"
