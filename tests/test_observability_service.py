from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from primer.server.app import create_app
from primer.server.services import observability_service


def test_setup_observability_noops_when_packages_missing(monkeypatch):
    monkeypatch.setattr(observability_service.settings, "otel_enabled", True)
    monkeypatch.setattr(observability_service, "OTEL_AVAILABLE", False)

    app = create_app()

    assert app.state.observability_enabled is False


def test_observability_helpers_noop_without_otel(monkeypatch):
    monkeypatch.setattr(observability_service.settings, "otel_enabled", True)
    monkeypatch.setattr(observability_service, "OTEL_AVAILABLE", False)

    with observability_service.start_span("test-span") as span:
        assert span is None

    observability_service.record_counter("primer.test.counter", 1, {"scope": "test"})
    observability_service.record_histogram("primer.test.histogram", 12.5, {"scope": "test"})


def test_request_middleware_uses_route_template_for_metrics(monkeypatch):
    recorded: list[tuple[str, int | float, dict[str, str]]] = []

    @contextmanager
    def fake_span(_name, _attributes=None):
        class DummySpan:
            def set_attribute(self, *_args, **_kwargs):
                pass

        yield DummySpan()

    monkeypatch.setattr(observability_service, "start_span", fake_span)
    monkeypatch.setattr(
        observability_service,
        "record_counter",
        lambda name, value, attributes=None: recorded.append((name, value, attributes or {})),
    )
    monkeypatch.setattr(observability_service, "record_histogram", lambda *args, **kwargs: None)

    app = FastAPI()
    observability_service._instrument_requests(app)

    @app.get("/items/{item_id}")
    def get_item(item_id: str):
        return {"item_id": item_id}

    client = TestClient(app)

    response = client.get("/items/abc123")

    assert response.status_code == 200
    assert (
        "primer.http.requests",
        1,
        {
            "http.method": "GET",
            "http.route": "/items/{item_id}",
            "http.status_code": "200",
        },
    ) in recorded


def test_request_middleware_records_error_duration_with_route_template(monkeypatch):
    counters: list[tuple[str, int | float, dict[str, str]]] = []
    histograms: list[tuple[str, int | float, dict[str, str]]] = []

    @contextmanager
    def fake_span(_name, _attributes=None):
        class DummySpan:
            def set_attribute(self, *_args, **_kwargs):
                pass

        yield DummySpan()

    monkeypatch.setattr(observability_service, "start_span", fake_span)
    monkeypatch.setattr(
        observability_service,
        "record_counter",
        lambda name, value, attributes=None: counters.append((name, value, attributes or {})),
    )
    monkeypatch.setattr(
        observability_service,
        "record_histogram",
        lambda name, value, attributes=None: histograms.append((name, value, attributes or {})),
    )

    app = FastAPI()
    observability_service._instrument_requests(app)

    @app.get("/items/{item_id}")
    def get_item(item_id: str):
        _ = item_id
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/items/abc123")

    assert response.status_code == 500
    expected_attributes = {
        "http.method": "GET",
        "http.route": "/items/{item_id}",
        "http.status_code": "500",
    }
    assert ("primer.http.requests", 1, expected_attributes) in counters
    assert any(
        name == "primer.http.request.duration_ms"
        and attributes == expected_attributes
        and value >= 0
        for name, value, attributes in histograms
    )
