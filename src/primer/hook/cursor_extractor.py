"""Extract structured metadata from Primer-owned Cursor session bundles."""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from primer.hook.extractor import SessionMetadata

if TYPE_CHECKING:
    from primer.mcp.reader import LocalSession

logger = logging.getLogger(__name__)


class CursorExtractor:
    """Extractor for imported Cursor session bundles."""

    agent_type = "cursor"

    def get_data_dir(self) -> Path:
        return Path.home() / ".primer" / "cursor"

    def get_sessions_dir(self) -> Path:
        return self.get_data_dir() / "sessions"

    def get_native_workspace_storage_dir(self) -> Path:
        return (
            Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "workspaceStorage"
        )

    def get_session_path(self, session_id: str) -> Path:
        return self.get_sessions_dir() / f"{self.validate_session_id(session_id)}.json"

    def validate_session_id(self, session_id: str) -> str:
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("missing required session_id")

        normalized = session_id.strip()
        if normalized in {".", ".."} or "/" in normalized or "\\" in normalized:
            raise ValueError("unsafe session_id")

        candidate = (self.get_sessions_dir() / f"{normalized}.json").resolve()
        sessions_dir = self.get_sessions_dir().resolve()
        try:
            candidate.relative_to(sessions_dir)
        except ValueError as exc:
            raise ValueError("unsafe session_id") from exc

        return normalized

    def discover_sessions(self) -> list[LocalSession]:
        results: list[LocalSession] = []
        seen_ids: set[str] = set()
        results.extend(self._discover_imported_sessions(seen_ids))
        results.extend(self._discover_native_sessions(seen_ids))
        return results

    def _discover_imported_sessions(self, seen_ids: set[str]) -> list:
        sessions_dir = self.get_sessions_dir()
        if not sessions_dir.exists():
            return []
        return self._discover_bundle_paths(
            sessions_dir.glob("*.json"),
            seen_ids,
            "imported Cursor bundle",
        )

    def _discover_native_sessions(self, seen_ids: set[str]) -> list:
        # Cursor workspaceStorage currently exposes workspace metadata we can use
        # for future project-path inference, but not a reliable native session
        # transcript contract. Until that exists, imported bundles remain the only
        # supported discovery path.
        _ = seen_ids
        return []

    def _discover_bundle_paths(
        self,
        bundle_paths,
        seen_ids: set[str],
        source_label: str,
        inferred_project_path: str | None = None,
    ) -> list:
        from primer.mcp.reader import LocalSession

        results: list[LocalSession] = []
        for bundle_path in bundle_paths:
            try:
                meta = self.extract(str(bundle_path))
                session_id = self.validate_session_id(meta.session_id)
            except ValueError:
                logger.warning("Skipping invalid %s: %s", source_label, bundle_path)
                continue
            except Exception:
                logger.exception("Error reading %s: %s", source_label, bundle_path)
                continue

            if session_id in seen_ids:
                continue
            seen_ids.add(session_id)
            project_path = meta.project_path or inferred_project_path
            results.append(
                LocalSession(
                    session_id=session_id,
                    transcript_path=str(bundle_path),
                    facets_path=None,
                    has_facets=False,
                    project_path=project_path or None,
                    agent_type=self.agent_type,
                )
            )
        return results

    def extract(self, transcript_path: str) -> SessionMetadata:
        meta = SessionMetadata(agent_type=self.agent_type)
        path = Path(transcript_path)
        if not path.exists():
            return meta

        try:
            with open(path) as f:
                bundle = json.load(f)
        except (json.JSONDecodeError, OSError):
            return meta

        if not isinstance(bundle, dict):
            return meta

        meta.session_id = bundle.get("session_id", "")
        meta.project_path = bundle.get("project_path", "") or ""
        meta.project_name = bundle.get("project_name", "") or ""
        if not meta.project_name and meta.project_path:
            meta.project_name = Path(meta.project_path).name
        meta.agent_version = bundle.get("agent_version", "") or ""
        meta.permission_mode = bundle.get("permission_mode", "") or ""
        meta.primary_model = bundle.get("primary_model", "") or ""
        meta.summary = bundle.get("summary", "") or ""
        meta.first_prompt = bundle.get("first_prompt", "") or ""
        meta.started_at = _parse_timestamp(bundle.get("started_at"))
        meta.ended_at = _parse_timestamp(bundle.get("ended_at"))
        if meta.started_at and meta.ended_at:
            duration_seconds = (meta.ended_at - meta.started_at).total_seconds()
            meta.duration_seconds = duration_seconds if duration_seconds >= 0 else None

        messages = bundle.get("messages", [])
        if isinstance(messages, list):
            meta.messages = _normalize_messages(messages)

        meta.message_count = len(meta.messages)
        meta.user_message_count = sum(
            1 for message in meta.messages if message.get("role") == "human"
        )
        meta.assistant_message_count = sum(
            1 for message in meta.messages if message.get("role") == "assistant"
        )
        if not meta.first_prompt:
            meta.first_prompt = _extract_first_prompt(meta.messages)

        tool_counter: Counter[str] = Counter()
        tool_usages = bundle.get("tool_usages", [])
        if isinstance(tool_usages, list):
            for usage in tool_usages:
                if not isinstance(usage, dict):
                    continue
                tool_name = usage.get("tool_name")
                if not tool_name:
                    continue
                call_count = _safe_non_negative_int(usage.get("call_count", 0))
                if call_count <= 0:
                    continue
                tool_counter[tool_name] += call_count
                meta.tool_call_count += call_count
        meta.tool_counts = dict(tool_counter)

        model_tokens: dict[str, dict[str, int]] = {}
        model_usages = bundle.get("model_usages", [])
        if isinstance(model_usages, list):
            for usage in model_usages:
                if not isinstance(usage, dict):
                    continue
                model_name = usage.get("model_name")
                if not model_name:
                    continue
                bucket = model_tokens.setdefault(
                    model_name,
                    {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0},
                )
                input_tokens = _safe_non_negative_int(usage.get("input_tokens", 0))
                output_tokens = _safe_non_negative_int(usage.get("output_tokens", 0))
                cache_read_tokens = _safe_non_negative_int(usage.get("cache_read_tokens", 0))
                cache_creation_tokens = _safe_non_negative_int(
                    usage.get("cache_creation_tokens", 0)
                )

                bucket["input"] += input_tokens
                bucket["output"] += output_tokens
                bucket["cache_read"] += cache_read_tokens
                bucket["cache_creation"] += cache_creation_tokens

                meta.input_tokens += input_tokens
                meta.output_tokens += output_tokens
                meta.cache_read_tokens += cache_read_tokens
                meta.cache_creation_tokens += cache_creation_tokens

        meta.model_tokens = model_tokens
        if not meta.primary_model and model_tokens:
            meta.primary_model = max(
                model_tokens,
                key=lambda model: (
                    model_tokens[model].get("input", 0) + model_tokens[model].get("output", 0)
                ),
            )

        return meta


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_first_prompt(messages: list[dict]) -> str:
    for message in messages:
        if message.get("role") != "human":
            continue
        content = message.get("content_text")
        if isinstance(content, str) and content:
            return content[:500]
    return ""


def _normalize_messages(messages: list[object]) -> list[dict]:
    normalized: list[dict] = []
    next_ordinal = 0

    for message in messages:
        if not isinstance(message, dict):
            continue

        normalized_message: dict = {
            "ordinal": next_ordinal,
            "role": _normalize_role(message.get("role")),
        }

        content_text = message.get("content_text")
        if isinstance(content_text, str):
            normalized_message["content_text"] = content_text

        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list):
            normalized_message["tool_calls"] = tool_calls

        tool_results = message.get("tool_results")
        if isinstance(tool_results, list):
            normalized_message["tool_results"] = tool_results

        token_count = message.get("token_count")
        if token_count is not None:
            normalized_message["token_count"] = _safe_non_negative_int(token_count)

        model = message.get("model")
        if isinstance(model, str):
            normalized_message["model"] = model

        normalized.append(normalized_message)
        next_ordinal += 1

    return normalized


def _normalize_role(role: object) -> str:
    if not isinstance(role, str):
        return "assistant"

    normalized = role.strip().lower()
    if normalized == "user":
        return "human"
    if normalized == "model":
        return "assistant"
    if normalized in {"human", "assistant", "tool_result"}:
        return normalized
    return normalized or "assistant"


def _safe_int(value: object) -> int:
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_non_negative_int(value: object) -> int:
    return max(0, _safe_int(value))
