"""Extract structured metadata from Gemini CLI (Google) session files.

Gemini CLI has shipped more than one on-disk session shape:
- Older per-session JSON files under `~/.gemini/tmp/<hash>/chats/session-*.json`
- Newer shared logs under `~/.gemini/tmp/<hash>/logs.json`

The extractor supports both. Token data may come from inline usage metadata
or `~/.gemini/telemetry.log`; if neither is available, we gracefully degrade
to zero token counts.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path

from primer.hook.extractor import SessionMetadata

logger = logging.getLogger(__name__)

_LOG_SESSION_DELIMITER = "::"


class GeminiExtractor:
    """Extractor for Gemini CLI sessions (~/.gemini/)."""

    agent_type = "gemini_cli"

    def get_data_dir(self) -> Path:
        return Path.home() / ".gemini"

    def discover_sessions(self) -> list:
        """Discover Gemini CLI sessions from ~/.gemini/tmp/."""
        from primer.mcp.reader import LocalSession

        gemini_dir = self.get_data_dir()
        tmp_dir = gemini_dir / "tmp"
        if not tmp_dir.exists():
            return []

        results: list[LocalSession] = []
        seen_ids: set[str] = set()

        for session_file in tmp_dir.glob("*/chats/session-*.json"):
            session_id = session_file.stem
            if session_id in seen_ids:
                continue
            seen_ids.add(session_id)

            # Try to infer project path from parent directory structure
            project_path = self._infer_project_path(session_file)

            results.append(
                LocalSession(
                    session_id=session_id,
                    transcript_path=str(session_file),
                    facets_path=None,
                    has_facets=False,
                    project_path=project_path,
                    agent_type=self.agent_type,
                )
            )

        for log_file in tmp_dir.glob("*/logs.json"):
            results.extend(self._discover_log_sessions(log_file, seen_ids))
        return results

    def extract(self, transcript_path: str) -> SessionMetadata:
        """Parse a Gemini CLI session JSON file into SessionMetadata."""
        meta = SessionMetadata(agent_type=self.agent_type)
        tool_counter: Counter[str] = Counter()
        model_tokens: dict[str, dict[str, int]] = {}
        ordinal = 0

        path, selected_session_id = self._split_transcript_ref(transcript_path)
        if not path.exists():
            return meta

        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return meta

        if self._looks_like_logs_payload(data):
            return self._extract_logs_payload(path, data, selected_session_id)

        meta.session_id = selected_session_id or path.stem

        # Extract content array
        contents = data if isinstance(data, list) else data.get("contents", data.get("Content", []))
        if not isinstance(contents, list):
            return meta

        first_ts: datetime | None = None
        last_ts: datetime | None = None

        for content in contents:
            if not isinstance(content, dict):
                continue

            role = content.get("role", "")
            parts = content.get("parts", [])
            if not isinstance(parts, list):
                continue

            # Parse timestamps if present
            ts = self._parse_content_timestamp(content)
            if ts:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts

            if role == "user":
                meta.message_count += 1
                meta.user_message_count += 1
                text = self._extract_text_from_parts(parts)
                if text and not meta.first_prompt:
                    meta.first_prompt = text[:500]
                msg = self._build_message(ordinal, "human", parts)
                if msg:
                    meta.messages.append(msg)
                    ordinal += 1

            elif role == "model":
                meta.message_count += 1
                meta.assistant_message_count += 1
                # Count function calls as tool usage
                for part in parts:
                    if isinstance(part, dict) and "functionCall" in part:
                        fc = part["functionCall"]
                        tool_name = fc.get("name", "function_call")
                        tool_counter[tool_name] += 1
                        meta.tool_call_count += 1
                msg = self._build_message(ordinal, "assistant", parts)
                if msg:
                    meta.messages.append(msg)
                    ordinal += 1

            elif role == "function":
                # Function response — treated as tool result
                msg = self._build_tool_result(ordinal, parts)
                if msg:
                    meta.messages.append(msg)
                    ordinal += 1

        meta.tool_counts = dict(tool_counter)
        meta.started_at = first_ts
        meta.ended_at = last_ts
        if first_ts and last_ts:
            meta.duration_seconds = (last_ts - first_ts).total_seconds()

        # Try to load token data from metadata in the session file
        usage = (
            (data.get("usageMetadata") or data.get("usage_metadata", {}))
            if isinstance(data, dict)
            else {}
        )
        if usage:
            model = (
                data.get("model", "gemini-2.5-flash")
                if isinstance(data, dict)
                else "gemini-2.5-flash"
            )
            self._apply_usage(meta, model_tokens, model, usage)

        # Try telemetry as a fallback for token data
        if not model_tokens:
            telemetry_tokens = self._load_telemetry_tokens(path, meta.session_id)
            if telemetry_tokens:
                model_tokens.update(telemetry_tokens)
                for model_data in telemetry_tokens.values():
                    meta.input_tokens += model_data.get("input", 0)
                    meta.output_tokens += model_data.get("output", 0)
                    meta.cache_read_tokens += model_data.get("cache_read", 0)

        meta.model_tokens = model_tokens
        if model_tokens:
            meta.primary_model = max(
                model_tokens,
                key=lambda m: model_tokens[m].get("input", 0) + model_tokens[m].get("output", 0),
            )

        return meta

    def _discover_log_sessions(self, log_file: Path, seen_ids: set[str]) -> list:
        from primer.mcp.reader import LocalSession

        try:
            with open(log_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        if not self._looks_like_logs_payload(data):
            return []

        results: list[LocalSession] = []
        project_path = self._infer_project_path(log_file)
        ordered_session_ids: list[str] = []
        seen_in_file: set[str] = set()
        for entry in data:
            if not isinstance(entry, dict):
                continue
            session_id = entry.get("sessionId") or entry.get("session_id")
            if not isinstance(session_id, str) or not session_id or session_id in seen_in_file:
                continue
            seen_in_file.add(session_id)
            ordered_session_ids.append(session_id)

        for session_id in ordered_session_ids:
            if session_id in seen_ids:
                continue
            seen_ids.add(session_id)
            results.append(
                LocalSession(
                    session_id=session_id,
                    transcript_path=f"{log_file}{_LOG_SESSION_DELIMITER}{session_id}",
                    facets_path=None,
                    has_facets=False,
                    project_path=project_path,
                    agent_type=self.agent_type,
                )
            )
        return results

    def _extract_logs_payload(
        self,
        path: Path,
        data: list,
        selected_session_id: str | None,
    ) -> SessionMetadata:
        meta = SessionMetadata(agent_type=self.agent_type)
        tool_counter: Counter[str] = Counter()
        model_tokens: dict[str, dict[str, int]] = {}
        ordinal = 0
        first_ts: datetime | None = None
        last_ts: datetime | None = None

        entries = [entry for entry in data if isinstance(entry, dict)]
        if selected_session_id:
            entries = [
                entry
                for entry in entries
                if (entry.get("sessionId") or entry.get("session_id")) == selected_session_id
            ]

        if not entries:
            return meta

        meta.session_id = selected_session_id or str(entries[0].get("sessionId") or "")

        for entry in entries:
            entry_type = str(entry.get("type") or "").lower()
            message = entry.get("message")
            message_text = message[:2000] if isinstance(message, str) and message else None

            ts = self._parse_content_timestamp(entry)
            if ts:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts

            if entry_type == "user":
                if not message_text:
                    continue
                meta.message_count += 1
                meta.user_message_count += 1
                if not meta.first_prompt:
                    meta.first_prompt = message_text[:500]
                meta.messages.append(
                    {"ordinal": ordinal, "role": "human", "content_text": message_text}
                )
                ordinal += 1
                continue

            if entry_type in {"model", "assistant"}:
                if message_text:
                    meta.message_count += 1
                    meta.assistant_message_count += 1
                    meta.messages.append(
                        {"ordinal": ordinal, "role": "assistant", "content_text": message_text}
                    )
                    ordinal += 1
            elif entry_type in {"tool_result", "function", "function_response"} and message_text:
                meta.messages.append(
                    {
                        "ordinal": ordinal,
                        "role": "tool_result",
                        "tool_results": [
                            {
                                "name": entry.get("toolName")
                                or entry.get("tool_name")
                                or entry.get("name")
                                or "tool_result",
                                "output_preview": message_text[:500],
                            }
                        ],
                    }
                )
                ordinal += 1

            if entry_type in {"tool_call", "function_call"}:
                tool_name = (
                    entry.get("toolName")
                    or entry.get("tool_name")
                    or entry.get("name")
                    or "tool_call"
                )
                tool_counter[tool_name] += 1
                meta.tool_call_count += 1

            usage = entry.get("usageMetadata") or entry.get("usage_metadata")
            if isinstance(usage, dict):
                model = entry.get("model") or entry.get("modelName") or "gemini-2.5-flash"
                self._apply_usage(meta, model_tokens, str(model), usage)

        meta.tool_counts = dict(tool_counter)
        meta.started_at = first_ts
        meta.ended_at = last_ts
        if first_ts and last_ts:
            meta.duration_seconds = (last_ts - first_ts).total_seconds()

        if not model_tokens:
            telemetry_tokens = self._load_telemetry_tokens(path, meta.session_id)
            if telemetry_tokens:
                model_tokens.update(telemetry_tokens)
                for model_data in telemetry_tokens.values():
                    meta.input_tokens += model_data.get("input", 0)
                    meta.output_tokens += model_data.get("output", 0)
                    meta.cache_read_tokens += model_data.get("cache_read", 0)

        meta.model_tokens = model_tokens
        if model_tokens:
            meta.primary_model = max(
                model_tokens,
                key=lambda model: (
                    model_tokens[model].get("input", 0) + model_tokens[model].get("output", 0)
                ),
            )

        return meta

    @staticmethod
    def _split_transcript_ref(transcript_path: str) -> tuple[Path, str | None]:
        if _LOG_SESSION_DELIMITER not in transcript_path:
            return Path(transcript_path), None
        path_str, session_id = transcript_path.rsplit(_LOG_SESSION_DELIMITER, 1)
        return Path(path_str), session_id or None

    @staticmethod
    def _looks_like_logs_payload(data: object) -> bool:
        if not isinstance(data, list):
            return False
        return any(
            isinstance(entry, dict)
            and ("sessionId" in entry or "session_id" in entry)
            and ("message" in entry or "type" in entry)
            for entry in data
        )

    @staticmethod
    def _parse_content_timestamp(content: dict) -> datetime | None:
        for key in ("timestamp", "createTime", "create_time"):
            ts_str = content.get(key)
            if ts_str:
                try:
                    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass
        return None

    @staticmethod
    def _extract_text_from_parts(parts: list) -> str:
        texts = []
        for part in parts:
            if isinstance(part, dict):
                if "text" in part:
                    texts.append(part["text"])
            elif isinstance(part, str):
                texts.append(part)
        return " ".join(texts)

    @staticmethod
    def _build_message(ordinal: int, role: str, parts: list) -> dict | None:
        text_parts = []
        tool_calls = []
        for part in parts:
            if not isinstance(part, dict):
                continue
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                input_str = json.dumps(fc.get("args", {}))
                tool_calls.append(
                    {
                        "name": fc.get("name", "unknown"),
                        "input_preview": input_str[:500],
                    }
                )

        text = " ".join(text_parts)[:2000] if text_parts else None
        if not text and not tool_calls:
            return None

        msg: dict = {"ordinal": ordinal, "role": role}
        if text:
            msg["content_text"] = text
        if tool_calls:
            msg["tool_calls"] = tool_calls
        return msg

    @staticmethod
    def _build_tool_result(ordinal: int, parts: list) -> dict | None:
        for part in parts:
            if isinstance(part, dict) and "functionResponse" in part:
                fr = part["functionResponse"]
                name = fr.get("name", "unknown")
                response = json.dumps(fr.get("response", {}))
                return {
                    "ordinal": ordinal,
                    "role": "tool_result",
                    "tool_results": [{"name": name, "output_preview": response[:500]}],
                }
        return None

    @staticmethod
    def _apply_usage(
        meta: SessionMetadata,
        model_tokens: dict,
        model: str,
        usage: dict,
    ) -> None:
        if model not in model_tokens:
            model_tokens[model] = {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0}

        input_t = usage.get("input_token_count", usage.get("promptTokenCount", 0))
        output_t = usage.get("output_token_count", usage.get("candidatesTokenCount", 0))
        cached_t = usage.get("cached_content_token_count", usage.get("cachedContentTokenCount", 0))

        model_tokens[model]["input"] += input_t
        model_tokens[model]["output"] += output_t
        model_tokens[model]["cache_read"] += cached_t

        meta.input_tokens += input_t
        meta.output_tokens += output_t
        meta.cache_read_tokens += cached_t

    def _load_telemetry_tokens(
        self,
        session_path: Path,
        session_id: str,
    ) -> dict[str, dict[str, int]] | None:
        """Try to load token counts from ~/.gemini/telemetry.log (OpenTelemetry)."""
        telemetry_path = self.get_data_dir() / "telemetry.log"
        if not telemetry_path.exists():
            return None

        model_tokens: dict[str, dict[str, int]] = {}

        try:
            with open(telemetry_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    attrs = event.get("attributes", event.get("resourceAttributes", {}))
                    # Verify this event belongs to our session via exact match
                    event_session = attrs.get("session_id", event.get("session_id", ""))
                    if event_session != session_id:
                        continue
                    if not attrs:
                        continue

                    model = attrs.get("model", "gemini-2.5-flash")
                    if model not in model_tokens:
                        model_tokens[model] = {
                            "input": 0,
                            "output": 0,
                            "cache_read": 0,
                            "cache_creation": 0,
                        }

                    model_tokens[model]["input"] += attrs.get("input_token_count", 0)
                    model_tokens[model]["output"] += attrs.get("output_token_count", 0)
                    model_tokens[model]["cache_read"] += attrs.get("cached_content_token_count", 0)
        except OSError:
            return None

        return model_tokens if model_tokens else None

    @staticmethod
    def _infer_project_path(session_file: Path) -> str | None:
        """Try to infer project path from the hash directory structure.

        Gemini stores sessions under ~/.gemini/tmp/<project_hash>/... — the hash
        isn't reversible, so we return None unless we find a metadata file.
        """
        project_dir = (
            session_file.parent.parent
            if session_file.parent.name == "chats"
            else session_file.parent
        )
        meta_file = project_dir / "metadata.json"
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    data = json.load(f)
                return data.get("project_path") or data.get("cwd")
            except (json.JSONDecodeError, OSError):
                pass
        return None
