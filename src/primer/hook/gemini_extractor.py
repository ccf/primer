"""Extract structured metadata from Gemini CLI (Google) session files.

Gemini CLI stores sessions as JSON files at:
    ~/.gemini/tmp/<project_hash>/chats/session-*.json

Each file is a JSON object with a `Content[]` array. Messages have:
- role: "user", "model", or "function"
- parts: array with text, functionCall, or functionResponse

Token data may come from ~/.gemini/telemetry.log (OpenTelemetry events),
but we gracefully degrade to zero token counts if unavailable.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path

from primer.hook.extractor import SessionMetadata

logger = logging.getLogger(__name__)


class GeminiExtractor:
    """Extractor for Gemini CLI sessions (~/.gemini/)."""

    agent_type = "gemini_cli"

    def get_data_dir(self) -> Path:
        return Path.home() / ".gemini"

    def discover_sessions(self) -> list:
        """Discover Gemini CLI sessions from ~/.gemini/tmp/*/chats/."""
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
        return results

    def extract(self, transcript_path: str) -> SessionMetadata:
        """Parse a Gemini CLI session JSON file into SessionMetadata."""
        meta = SessionMetadata(agent_type=self.agent_type)
        tool_counter: Counter[str] = Counter()
        model_tokens: dict[str, dict[str, int]] = {}
        ordinal = 0

        path = Path(transcript_path)
        if not path.exists():
            return meta

        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return meta

        meta.session_id = path.stem

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
            telemetry_tokens = self._load_telemetry_tokens(path)
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

    def _load_telemetry_tokens(self, session_path: Path) -> dict[str, dict[str, int]] | None:
        """Try to load token counts from ~/.gemini/telemetry.log (OpenTelemetry)."""
        telemetry_path = self.get_data_dir() / "telemetry.log"
        if not telemetry_path.exists():
            return None

        session_id = session_path.stem
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

        Gemini uses ~/.gemini/tmp/<project_hash>/chats/ — the hash isn't
        reversible, so we return None unless we find a metadata file.
        """
        project_dir = session_file.parent.parent
        meta_file = project_dir / "metadata.json"
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    data = json.load(f)
                return data.get("project_path") or data.get("cwd")
            except (json.JSONDecodeError, OSError):
                pass
        return None
