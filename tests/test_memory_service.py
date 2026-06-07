"""Tests for the memory store service layer (Plan 2a: scopes + sketches)."""

from primer.common.config import settings
from primer.server.services.memory_service import memory_capture_active


def test_memory_disabled_by_default():
    assert settings.memory_enabled is False
    assert memory_capture_active() is False


def test_memory_requires_redaction(monkeypatch):
    monkeypatch.setattr(settings, "memory_enabled", True)
    monkeypatch.setattr(settings, "redaction_enabled", False)
    assert memory_capture_active() is False


def test_memory_active_when_enabled_with_redaction(monkeypatch):
    monkeypatch.setattr(settings, "memory_enabled", True)
    monkeypatch.setattr(settings, "redaction_enabled", True)
    assert memory_capture_active() is True
