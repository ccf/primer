"""Extract structured metadata from imported and native Cursor sessions."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlparse

from primer.hook.extractor import SessionMetadata

if TYPE_CHECKING:
    from primer.mcp.reader import LocalSession

logger = logging.getLogger(__name__)
_GIT_REPO_PATTERN = re.compile(r"^Git repo:\s+(.+)$", re.MULTILINE)


@dataclass
class NativeCursorComposerState:
    started_at: datetime | None = None
    ended_at: datetime | None = None
    git_branch: str | None = None
    primary_model: str | None = None
    summary: str | None = None
    tool_counts: dict[str, int] = field(default_factory=dict)


class CursorExtractor:
    """Extractor for imported Cursor bundles and native Cursor transcripts."""

    agent_type = "cursor"

    def get_data_dir(self) -> Path:
        return Path.home() / ".primer" / "cursor"

    def get_sessions_dir(self) -> Path:
        return self.get_data_dir() / "sessions"

    def get_native_workspace_storage_dir(self) -> Path:
        return (
            Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "workspaceStorage"
        )

    def get_native_projects_dir(self) -> Path:
        return Path.home() / ".cursor" / "projects"

    def get_native_global_state_db_path(self) -> Path:
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Cursor"
            / "User"
            / "globalStorage"
            / "state.vscdb"
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
            chain(sessions_dir.glob("*.json"), sessions_dir.glob("*.jsonl")),
            seen_ids,
            "imported Cursor bundle",
        )

    def _discover_native_sessions(self, seen_ids: set[str]) -> list:
        projects_dir = self.get_native_projects_dir()
        if not projects_dir.exists():
            return []

        results = []

        for project_dir in sorted(projects_dir.iterdir()):
            transcripts_dir = project_dir / "agent-transcripts"
            if not transcripts_dir.is_dir():
                continue

            for session_dir in sorted(transcripts_dir.iterdir()):
                if not session_dir.is_dir():
                    continue
                transcript_path = session_dir / f"{session_dir.name}.jsonl"
                if not transcript_path.exists():
                    continue
                results.extend(
                    self._discover_bundle_paths(
                        [transcript_path],
                        seen_ids,
                        "native Cursor transcript",
                    )
                )

        return results

    def _discover_bundle_paths(
        self,
        bundle_paths,
        seen_ids: set[str],
        source_label: str,
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

            if meta.message_count <= 0:
                logger.warning("Skipping %s with no messages: %s", source_label, bundle_path)
                continue

            if session_id in seen_ids:
                continue
            seen_ids.add(session_id)
            results.append(
                LocalSession(
                    session_id=session_id,
                    transcript_path=str(bundle_path),
                    facets_path=None,
                    has_facets=False,
                    project_path=meta.project_path or None,
                    agent_type=self.agent_type,
                )
            )
        return results

    def extract(self, transcript_path: str) -> SessionMetadata:
        path = Path(transcript_path)
        if path.suffix == ".jsonl":
            return self._extract_native_transcript(path)

        meta = SessionMetadata(agent_type=self.agent_type)
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

    def _extract_native_transcript(self, transcript_path: Path) -> SessionMetadata:
        meta = SessionMetadata(agent_type=self.agent_type)
        if not transcript_path.exists():
            return meta

        meta.session_id = transcript_path.stem
        meta.messages = _load_native_messages(transcript_path)
        meta.message_count = len(meta.messages)
        meta.user_message_count = sum(
            1 for message in meta.messages if message.get("role") == "human"
        )
        meta.assistant_message_count = sum(
            1 for message in meta.messages if message.get("role") == "assistant"
        )
        meta.first_prompt = _extract_first_prompt(meta.messages)
        meta.summary = _extract_last_assistant_summary(meta.messages)

        project_path = self._resolve_native_project_path(transcript_path, meta.messages)
        meta.project_path = project_path or ""
        if meta.project_path:
            meta.project_name = Path(meta.project_path).name
        else:
            meta.project_name = _native_project_slug(transcript_path)

        composer_state = None
        if _is_native_cursor_transcript_path(transcript_path):
            composer_state = self._load_native_composer_state(meta.session_id)
            if composer_state is not None:
                meta.git_branch = composer_state.git_branch or meta.git_branch
                meta.primary_model = composer_state.primary_model or meta.primary_model
                meta.summary = meta.summary or composer_state.summary or ""
                if composer_state.tool_counts:
                    meta.tool_counts = composer_state.tool_counts
                    meta.tool_call_count = sum(composer_state.tool_counts.values())

        if transcript_path.parent == self.get_sessions_dir():
            started_at, ended_at = _native_session_time_bounds(
                transcript_path.parent,
                single_file=transcript_path,
            )
        else:
            started_at, ended_at = _native_session_time_bounds(transcript_path.parent)

        if composer_state is not None:
            started_at = composer_state.started_at or started_at
            ended_at = composer_state.ended_at or ended_at

        meta.started_at = started_at
        meta.ended_at = ended_at
        if meta.started_at and meta.ended_at:
            duration_seconds = (meta.ended_at - meta.started_at).total_seconds()
            meta.duration_seconds = duration_seconds if duration_seconds >= 0 else None

        return meta

    def _resolve_native_project_path(
        self,
        transcript_path: Path,
        messages: list[dict],
    ) -> str | None:
        explicit_project_path = _extract_git_repo_path(messages)
        if explicit_project_path:
            return explicit_project_path

        return self._load_workspace_project_paths().get(_native_project_slug(transcript_path))

    def _load_workspace_project_paths(self) -> dict[str, str]:
        cached = getattr(self, "_workspace_project_paths", None)
        if cached is not None:
            return cached

        workspace_paths: dict[str, str] = {}
        workspace_storage_dir = self.get_native_workspace_storage_dir()
        if workspace_storage_dir.exists():
            for workspace_dir in workspace_storage_dir.iterdir():
                workspace_json_path = workspace_dir / "workspace.json"
                if not workspace_json_path.exists():
                    continue
                folder_path = _load_workspace_folder_path(workspace_json_path)
                if not folder_path:
                    continue
                workspace_paths.setdefault(_project_slug_from_path(folder_path), folder_path)

        self._workspace_project_paths = workspace_paths
        return workspace_paths

    def _load_native_composer_state(self, session_id: str) -> NativeCursorComposerState | None:
        db_path = self.get_native_global_state_db_path()
        if not db_path.exists():
            return None

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        except sqlite3.Error:
            logger.debug("Unable to open Cursor global state database: %s", db_path, exc_info=True)
            return None

        try:
            row = conn.execute(
                "select value from cursorDiskKV where key = ?",
                (f"composerData:{session_id}",),
            ).fetchone()
            if row is None or not row[0]:
                return None

            composer = json.loads(row[0])
            if not isinstance(composer, dict):
                return None

            header_ids = {
                header.get("bubbleId")
                for header in composer.get("fullConversationHeadersOnly", [])
                if isinstance(header, dict) and isinstance(header.get("bubbleId"), str)
            }
            tool_counter: Counter[str] = Counter()
            model_counter: Counter[str] = Counter()

            if header_ids:
                bubble_prefix = f"bubbleId:{session_id}:"
                for key, value in conn.execute(
                    "select key, value from cursorDiskKV where key like ?",
                    (f"{bubble_prefix}%",),
                ):
                    bubble_id = key.removeprefix(bubble_prefix)
                    if bubble_id not in header_ids:
                        continue
                    bubble = _load_json_object(value)
                    if bubble is None:
                        continue
                    tool_data = bubble.get("toolFormerData")
                    if not isinstance(tool_data, dict):
                        continue

                    status = tool_data.get("status")
                    if isinstance(status, str) and status not in {"completed", "error"}:
                        continue

                    tool_name = tool_data.get("name")
                    if isinstance(tool_name, str) and tool_name:
                        tool_counter[tool_name] += 1

                    model_counter.update(_extract_toolformer_models(tool_data))

            active_branch = composer.get("activeBranch")
            git_branch = ""
            if isinstance(active_branch, dict):
                branch_name = active_branch.get("branchName")
                if isinstance(branch_name, str):
                    git_branch = branch_name
            if not git_branch:
                committed_to_branch = composer.get("committedToBranch")
                if isinstance(committed_to_branch, str):
                    git_branch = committed_to_branch

            summary = ""
            for field_name in ("name", "subtitle"):
                field_value = composer.get(field_name)
                if isinstance(field_value, str) and field_value:
                    summary = field_value[:500]
                    break

            primary_model = model_counter.most_common(1)[0][0] if model_counter else None

            return NativeCursorComposerState(
                started_at=_parse_cursor_unix_ms(composer.get("createdAt")),
                ended_at=_parse_cursor_unix_ms(composer.get("lastUpdatedAt")),
                git_branch=git_branch or None,
                primary_model=primary_model,
                summary=summary or None,
                tool_counts=dict(tool_counter),
            )
        except (json.JSONDecodeError, sqlite3.Error):
            logger.debug(
                "Unable to load Cursor composer state for session %s",
                session_id,
                exc_info=True,
            )
            return None
        finally:
            conn.close()


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


def _extract_last_assistant_summary(messages: list[dict]) -> str:
    for message in reversed(messages):
        if message.get("role") != "assistant":
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


def _load_native_messages(transcript_path: Path) -> list[dict]:
    normalized: list[dict] = []
    next_ordinal = 0

    try:
        lines = transcript_path.read_text().splitlines()
    except OSError:
        return normalized

    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue

        role = _normalize_role(payload.get("role"))
        message = payload.get("message")
        if not isinstance(message, dict):
            continue

        content_text = _extract_native_content_text(message.get("content"))
        if not content_text:
            continue

        normalized.append(
            {
                "ordinal": next_ordinal,
                "role": role,
                "content_text": content_text,
            }
        )
        next_ordinal += 1

    return normalized


def _extract_native_content_text(content: object) -> str:
    if not isinstance(content, list):
        return ""

    text_parts: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        if part.get("type") != "text":
            continue
        text = part.get("text")
        if isinstance(text, str) and text:
            text_parts.append(text)

    return "\n\n".join(text_parts)


def _extract_git_repo_path(messages: list[dict]) -> str | None:
    for message in messages:
        content = message.get("content_text")
        if not isinstance(content, str):
            continue
        match = _GIT_REPO_PATTERN.search(content)
        if match:
            return match.group(1).strip()
    return None


def _is_native_cursor_transcript_path(transcript_path: Path) -> bool:
    return bool(_native_project_slug(transcript_path))


def _native_project_slug(transcript_path: Path) -> str:
    try:
        if transcript_path.parents[1].name != "agent-transcripts":
            return ""
        return transcript_path.parents[2].name
    except IndexError:
        return ""


def _native_session_time_bounds(
    session_dir: Path,
    *,
    single_file: Path | None = None,
) -> tuple[datetime | None, datetime | None]:
    if single_file is not None:
        jsonl_paths = [single_file] if single_file.is_file() else []
    else:
        jsonl_paths = [path for path in session_dir.rglob("*.jsonl") if path.is_file()]
    if not jsonl_paths:
        return None, None

    start_timestamp = min(_birth_or_change_timestamp(path) for path in jsonl_paths)
    end_timestamp = max(path.stat().st_mtime for path in jsonl_paths)
    return (
        datetime.fromtimestamp(start_timestamp, UTC),
        datetime.fromtimestamp(end_timestamp, UTC),
    )


def _birth_or_change_timestamp(path: Path) -> float:
    stat = path.stat()
    return getattr(stat, "st_birthtime", stat.st_ctime)


def _load_workspace_folder_path(workspace_json_path: Path) -> str | None:
    try:
        workspace_data = json.loads(workspace_json_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(workspace_data, dict):
        return None

    folder = workspace_data.get("folder")
    if not isinstance(folder, str) or not folder:
        return None

    parsed = urlparse(folder)
    if parsed.scheme == "file":
        return unquote(parsed.path)
    return folder


def _load_json_object(value: object) -> dict | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _parse_cursor_unix_ms(value: object) -> datetime | None:
    if not isinstance(value, int | float):
        return None
    return datetime.fromtimestamp(float(value) / 1000, UTC)


def _extract_toolformer_models(tool_data: dict) -> Counter[str]:
    models: Counter[str] = Counter()

    for field_name in ("model", "agentModel", "subagentModel"):
        field_value = tool_data.get(field_name)
        if isinstance(field_value, str) and field_value:
            models[field_value] += 1

    for field_name in ("rawArgs", "params"):
        field_value = tool_data.get(field_name)
        if not isinstance(field_value, str) or '"model"' not in field_value:
            continue
        parsed_value = _load_json_object(field_value)
        if parsed_value is None:
            continue
        for model_name in _iter_model_names(parsed_value):
            models[model_name] += 1

    return models


def _iter_model_names(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"model", "agentModel", "subagentModel"} and isinstance(child, str) and child:
                yield child
            yield from _iter_model_names(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_model_names(child)


def _project_slug_from_path(project_path: str) -> str:
    normalized = project_path.replace("\\", "/").strip()
    if normalized.startswith("file://"):
        normalized = normalized[7:]
    normalized = normalized.lstrip("/")
    return normalized.replace("/", "-").replace(":", "")


def _safe_int(value: object) -> int:
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_non_negative_int(value: object) -> int:
    return max(0, _safe_int(value))
