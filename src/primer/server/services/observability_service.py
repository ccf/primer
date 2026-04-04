from __future__ import annotations

import logging
from contextlib import contextmanager
from time import perf_counter
from typing import TYPE_CHECKING, Any

from primer.common.config import settings

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

try:
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import (
        ConsoleMetricExporter,
        PeriodicExportingMetricReader,
    )
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover - optional local fallback
    OTEL_AVAILABLE = False


_observability_initialized = False
_log_record_factory_installed = False
_counters: dict[str, Any] = {}
_histograms: dict[str, Any] = {}


def observability_enabled() -> bool:
    return settings.otel_enabled and OTEL_AVAILABLE


def setup_observability(app: FastAPI) -> None:
    app.state.observability_enabled = observability_enabled()
    if not observability_enabled():
        return

    global _observability_initialized
    if not _observability_initialized:
        resource = Resource.create(
            {
                SERVICE_NAME: settings.otel_service_name,
                "deployment.environment": settings.otel_environment,
            }
        )

        tracer_provider = TracerProvider(resource=resource)
        if settings.otel_otlp_endpoint:
            tracer_provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_otlp_endpoint))
            )
        elif settings.otel_console_export:
            tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(tracer_provider)

        metric_readers = []
        if settings.otel_otlp_endpoint:
            metric_readers.append(
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=settings.otel_otlp_endpoint)
                )
            )
        elif settings.otel_console_export:
            metric_readers.append(PeriodicExportingMetricReader(ConsoleMetricExporter()))
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=metric_readers))

        _install_log_record_factory()
        _observability_initialized = True

    _instrument_requests(app)


def _install_log_record_factory() -> None:
    global _log_record_factory_installed
    if _log_record_factory_installed or not OTEL_AVAILABLE:
        return

    previous_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = previous_factory(*args, **kwargs)
        span = trace.get_current_span()
        span_context = span.get_span_context()
        if span_context and span_context.is_valid:
            record.otel_trace_id = format(span_context.trace_id, "032x")
            record.otel_span_id = format(span_context.span_id, "016x")
        else:
            record.otel_trace_id = ""
            record.otel_span_id = ""
        return record

    logging.setLogRecordFactory(record_factory)
    _log_record_factory_installed = True


def _instrument_requests(app: FastAPI) -> None:
    if getattr(app.state, "_otel_request_middleware_installed", False):
        return

    def _route_path(request) -> str:
        route = request.scope.get("route")
        return getattr(route, "path", request.url.path)

    @app.middleware("http")
    async def otel_request_middleware(request, call_next):
        with start_span(
            "http.request",
            {
                "http.method": request.method,
            },
        ) as span:
            started = perf_counter()
            try:
                response = await call_next(request)
            except Exception as exc:
                duration_ms = (perf_counter() - started) * 1000
                route_path = _route_path(request)
                attributes = {
                    "http.method": request.method,
                    "http.route": route_path,
                    "http.status_code": "500",
                }
                if span is not None:
                    span.set_attribute("error.type", exc.__class__.__name__)
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                record_counter("primer.http.requests", 1, attributes)
                record_histogram("primer.http.request.duration_ms", duration_ms, attributes)
                raise
            duration_ms = (perf_counter() - started) * 1000
            route_path = _route_path(request)
            attributes = {
                "http.method": request.method,
                "http.route": route_path,
                "http.status_code": str(response.status_code),
            }
            if span is not None:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            record_counter("primer.http.requests", 1, attributes)
            record_histogram("primer.http.request.duration_ms", duration_ms, attributes)
            return response

    app.state._otel_request_middleware_installed = True


def _get_tracer():
    if not observability_enabled():
        return None
    return trace.get_tracer(settings.otel_service_name)


def _get_meter():
    if not observability_enabled():
        return None
    return metrics.get_meter(settings.otel_service_name)


def _get_counter(name: str):
    meter = _get_meter()
    if meter is None:
        return None
    counter = _counters.get(name)
    if counter is None:
        counter = meter.create_counter(name)
        _counters[name] = counter
    return counter


def _get_histogram(name: str):
    meter = _get_meter()
    if meter is None:
        return None
    histogram = _histograms.get(name)
    if histogram is None:
        histogram = meter.create_histogram(name)
        _histograms[name] = histogram
    return histogram


@contextmanager
def start_span(name: str, attributes: dict[str, Any] | None = None):
    tracer = _get_tracer()
    if tracer is None:
        yield None
        return

    with tracer.start_as_current_span(name) as span:
        for key, value in (attributes or {}).items():
            if value is not None:
                span.set_attribute(key, value)
        yield span


def record_counter(name: str, value: int | float, attributes: dict[str, Any] | None = None) -> None:
    counter = _get_counter(name)
    if counter is None:
        return
    counter.add(value, attributes or {})


def record_histogram(
    name: str,
    value: int | float,
    attributes: dict[str, Any] | None = None,
) -> None:
    histogram = _get_histogram(name)
    if histogram is None:
        return
    histogram.record(value, attributes or {})
