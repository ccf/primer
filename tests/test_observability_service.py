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
