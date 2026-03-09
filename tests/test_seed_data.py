from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


def _load_seed_data_module():
    seed_path = Path(__file__).resolve().parents[1] / "scripts" / "seed_data.py"
    spec = spec_from_file_location("seed_data", seed_path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seed_data = _load_seed_data_module()


def test_parse_selected_agent_types_accepts_known_values(monkeypatch):
    monkeypatch.setenv("PRIMER_SEED_AGENT_TYPES", "codex_cli, gemini_cli")

    assert seed_data._parse_selected_agent_types() == {"codex_cli", "gemini_cli"}


def test_parse_selected_agent_types_rejects_unknown_values(monkeypatch):
    monkeypatch.setenv("PRIMER_SEED_AGENT_TYPES", "codex_cli,unknown")

    with pytest.raises(ValueError, match="Unknown agent types"):
        seed_data._parse_selected_agent_types()


def test_build_seed_auth_headers_prefers_admin_key(monkeypatch):
    monkeypatch.setenv("PRIMER_ADMIN_API_KEY", "admin-key")
    monkeypatch.setenv("PRIMER_API_KEY", "api-key")

    assert seed_data._build_seed_auth_headers() == {"x-admin-key": "admin-key"}


def test_build_seed_auth_headers_falls_back_to_api_key(monkeypatch):
    monkeypatch.delenv("PRIMER_ADMIN_API_KEY", raising=False)
    monkeypatch.setenv("PRIMER_API_KEY", "api-key")

    assert seed_data._build_seed_auth_headers() == {"x-api-key": "api-key"}


def test_should_force_facets_respects_env(monkeypatch):
    monkeypatch.setenv("PRIMER_SEED_FORCE_FACETS", "true")

    assert seed_data._should_force_facets() is True


def test_build_facets_returns_payload_with_optional_satisfaction():
    seed_data.random.seed(42)

    facets = seed_data._build_facets(
        session_type="feature",
        outcome="partial",
        project_name="api-service",
        summary=None,
        friction_counts={"tool_failure": 2},
        friction_detail="Command exited with status 1",
        include_user_satisfaction=False,
    )

    assert facets["underlying_goal"] == "Working on feature task for api-service"
    assert facets["outcome"] == "partial"
    assert facets["session_type"] == "feature"
    assert facets["brief_summary"] == "Session for api-service"
    assert facets["friction_counts"] == {"tool_failure": 2}
    assert facets["friction_detail"] == "Command exited with status 1"
    assert facets["primary_success"] in seed_data.PRIMARY_SUCCESS_VALUES
    assert facets["goal_categories"]
    assert facets["user_satisfaction_counts"] is None
    assert 0.0 <= facets["confidence_score"] <= 1.0


def test_build_facets_can_include_user_satisfaction():
    seed_data.random.seed(42)

    facets = seed_data._build_facets(
        session_type="feature",
        outcome="partial",
        project_name="api-service",
        summary=None,
        friction_counts=None,
        friction_detail=None,
        include_user_satisfaction=True,
    )

    assert facets["user_satisfaction_counts"]


def test_scale_session_count_preserves_expected_subset_volume():
    scaled = seed_data._scale_session_count_for_selected_agents(
        session_count=10,
        full_agent_mix={"claude_code": 70, "codex_cli": 20, "gemini_cli": 10},
        filtered_agent_mix={"codex_cli": 20},
    )

    assert scaled == 2


def test_codex_seed_config_uses_current_models_and_permissions():
    codex_config = seed_data.AGENT_TYPE_CONFIG["codex_cli"]

    assert codex_config["versions"] == ["0.111.0", "0.110.1", "0.110.0"]
    assert codex_config["permission_modes"] == ["on-request", "on-failure", "never"]

    for persona_weights in codex_config["model_weights"].values():
        assert set(persona_weights) <= {"gpt-5.4", "gpt-5.3-codex", "gpt-5-mini", "gpt-4.1"}
