"""Extract structured metadata from Codex CLI (OpenAI) session transcripts.

Codex rollout files have evolved over time. We support both:
- legacy variant-key JSONL entries like ``SessionMeta`` / ``EventMsg``
- current envelope entries shaped like ``{"type": "...", "payload": {...}}``

Current rollout files live at:
    ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path

from primer.hook.extractor import SessionMetadata

logger = logging.getLogger(__name__)


class CodexExtractor:
    """Extractor for Codex CLI sessions (~/.codex/)."""

    agent_type = "codex_cli"

    def get_data_dir(self) -> Path:
        return Path.home() / ".codex"

    def discover_sessions(self) -> list:
        """Discover Codex CLI sessions from ~/.codex/sessions/."""
        from primer.mcp.reader import LocalSession

        sessions_dir = self.get_data_dir() / "sessions"
        if not sessions_dir.exists():
            return []

        results: list[LocalSession] = []
        seen_ids: set[str] = set()

        for rollout_file in sessions_dir.glob("**/rollout-*.jsonl"):
            session_id, project_path = self._extract_session_meta(rollout_file)
            if not session_id or session_id in seen_ids:
                continue
            seen_ids.add(session_id)
            results.append(
                LocalSession(
                    session_id=session_id,
                    transcript_path=str(rollout_file),
                    facets_path=None,
                    has_facets=False,
                    project_path=project_path,
                    agent_type=self.agent_type,
                )
            )
        return results

    def extract(self, transcript_path: str) -> SessionMetadata:
        """Parse a Codex CLI rollout JSONL file into SessionMetadata."""
        meta = SessionMetadata(agent_type=self.agent_type)
        tool_counter: Counter[str] = Counter()
        model_tokens: dict[str, dict[str, int]] = {}
        call_id_to_tool: dict[str, str] = {}
        first_ts: datetime | None = None
        last_ts: datetime | None = None
        ordinal = 0
        current_model: str | None = None

        # Track cumulative totals when the source only reports running totals.
        prev_cumulative: dict[str, dict[str, int]] = {}

        path = Path(transcript_path)
        if not path.exists():
            return meta

        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                ts = self._parse_timestamp(entry)
                if ts:
                    if first_ts is None:
                        first_ts = ts
                    last_ts = ts

                current_model = self._process_entry(
                    entry,
                    meta,
                    tool_counter,
                    model_tokens,
                    prev_cumulative,
                    current_model,
                    call_id_to_tool,
                )

                # Collect messages
                msg = self._extract_message(entry, ordinal, current_model, call_id_to_tool)
                if msg:
                    meta.messages.append(msg)
                    ordinal += 1

        meta.tool_counts = dict(tool_counter)
        meta.model_tokens = model_tokens
        meta.started_at = meta.started_at or first_ts
        meta.ended_at = last_ts
        if meta.started_at and last_ts:
            meta.duration_seconds = (last_ts - meta.started_at).total_seconds()

        if model_tokens:
            meta.primary_model = max(
                model_tokens,
                key=lambda m: model_tokens[m].get("input", 0) + model_tokens[m].get("output", 0),
            )
        elif current_model:
            meta.primary_model = current_model

        return meta

    def _process_entry(
        self,
        entry: dict,
        meta: SessionMetadata,
        tool_counter: Counter,
        model_tokens: dict,
        prev_cumulative: dict,
        current_model: str | None,
        call_id_to_tool: dict[str, str],
    ) -> str | None:
        """Process a single Codex CLI JSONL entry."""
        # SessionMeta — session-level info
        session_meta = self._extract_session_meta_payload(entry)
        if session_meta:
            if "id" in session_meta:
                meta.session_id = session_meta["id"]
            if "cwd" in session_meta:
                meta.project_path = session_meta["cwd"]
                meta.project_name = Path(session_meta["cwd"]).name
            if "cli_version" in session_meta:
                meta.agent_version = session_meta["cli_version"]
            if "model" in session_meta:
                model = session_meta["model"]
                current_model = model
                if model not in model_tokens:
                    model_tokens[model] = {
                        "input": 0,
                        "output": 0,
                        "cache_read": 0,
                        "cache_creation": 0,
                    }
            if meta.started_at is None:
                meta.started_at = self._parse_nested_timestamp(session_meta.get("timestamp"))
            return current_model

        # TurnContext — model and approval policy
        turn_ctx = self._extract_turn_context_payload(entry)
        if turn_ctx:
            if "model" in turn_ctx:
                model = turn_ctx["model"]
                current_model = model
                if model not in model_tokens:
                    model_tokens[model] = {
                        "input": 0,
                        "output": 0,
                        "cache_read": 0,
                        "cache_creation": 0,
                    }
            if "approval_policy" in turn_ctx:
                meta.permission_mode = turn_ctx["approval_policy"]
            if "cwd" in turn_ctx and not meta.project_path:
                meta.project_path = turn_ctx["cwd"]
                meta.project_name = Path(turn_ctx["cwd"]).name
            return current_model

        # EventMsg — messages and commands
        event = self._extract_event_payload(entry)
        if event:
            event_type = str(event.get("type", "")).lower()
            if event_type == "user_message":
                meta.message_count += 1
                meta.user_message_count += 1
                text = self._extract_event_text(event)
                if text and not meta.first_prompt:
                    meta.first_prompt = text[:500]
            elif event_type == "agent_message":
                meta.message_count += 1
                meta.assistant_message_count += 1
            elif event_type in {"exec_command_begin", "execcommandbegin"}:
                tool_counter["exec_command"] += 1
                meta.tool_call_count += 1
            elif event_type == "token_count":
                self._apply_token_usage(
                    meta,
                    model_tokens,
                    prev_cumulative,
                    event,
                    current_model,
                )
            return current_model

        # ResponseItem — function calls
        resp_item = self._extract_response_item_payload(entry)
        if resp_item:
            if resp_item.get("type") == "function_call" or "function_call" in resp_item:
                fc = resp_item.get("function_call", resp_item)
                tool_name = fc.get("name", "function_call")
                tool_counter[tool_name] += 1
                meta.tool_call_count += 1
                call_id = resp_item.get("call_id") or fc.get("call_id")
                if call_id:
                    call_id_to_tool[call_id] = tool_name
            return current_model

        # Token counts — cumulative, need delta computation
        token_data = entry.get("token_count") or entry.get("TokenCount")
        if token_data:
            self._apply_token_usage(
                meta,
                model_tokens,
                prev_cumulative,
                token_data,
                current_model,
            )
        return current_model

    @staticmethod
    def _parse_timestamp(entry: dict) -> datetime | None:
        ts_str = entry.get("timestamp")
        if ts_str:
            try:
                return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        return None

    def _extract_message(
        self,
        entry: dict,
        ordinal: int,
        current_model: str | None,
        call_id_to_tool: dict[str, str],
    ) -> dict | None:
        event = self._extract_event_payload(entry)
        if not event:
            resp_item = self._extract_response_item_payload(entry)
            if not resp_item:
                return None
            return self._extract_response_item_message(
                resp_item, ordinal, current_model, call_id_to_tool
            )

        event_type = str(event.get("type", "")).lower()
        if event_type == "user_message":
            text = self._extract_event_text(event)
            if text:
                return {"ordinal": ordinal, "role": "human", "content_text": text[:2000]}
        elif event_type == "agent_message":
            text = self._extract_event_text(event)
            if text:
                msg: dict = {"ordinal": ordinal, "role": "assistant", "content_text": text[:2000]}
                if current_model:
                    msg["model"] = current_model
                return msg
        return None

    @staticmethod
    def _extract_session_meta(rollout_file: Path) -> tuple[str | None, str | None]:
        """Extract session ID and project path from the first SessionMeta entry.

        Returns (session_id, project_path). Reads the file once.
        """
        try:
            with open(rollout_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    session_meta = CodexExtractor._extract_session_meta_payload(entry)
                    if session_meta:
                        sid = session_meta.get("id")
                        cwd = session_meta.get("cwd")
                        return (sid or rollout_file.stem, cwd)
            # Fallback: use filename stem
            return (rollout_file.stem, None)
        except OSError:
            return (None, None)

    @staticmethod
    def _extract_session_meta_payload(entry: dict) -> dict | None:
        if isinstance(entry.get("type"), str) and entry.get("type") == "session_meta":
            payload = entry.get("payload")
            return payload if isinstance(payload, dict) else None

        session_meta = entry.get("SessionMeta") or entry.get("session_meta")
        return session_meta if isinstance(session_meta, dict) else None

    @staticmethod
    def _extract_turn_context_payload(entry: dict) -> dict | None:
        if isinstance(entry.get("type"), str) and entry.get("type") == "turn_context":
            payload = entry.get("payload")
            return payload if isinstance(payload, dict) else None

        turn_ctx = entry.get("TurnContext") or entry.get("turn_context")
        return turn_ctx if isinstance(turn_ctx, dict) else None

    @staticmethod
    def _extract_event_payload(entry: dict) -> dict | None:
        if isinstance(entry.get("type"), str) and entry.get("type") == "event_msg":
            payload = entry.get("payload")
            return payload if isinstance(payload, dict) else None

        event = entry.get("EventMsg") or entry.get("event")
        if not isinstance(event, dict):
            return None
        if "UserMessage" in event and isinstance(event["UserMessage"], dict):
            return {"type": "user_message", **event["UserMessage"]}
        if "AgentMessage" in event and isinstance(event["AgentMessage"], dict):
            return {"type": "agent_message", **event["AgentMessage"]}
        if "ExecCommandBegin" in event and isinstance(event["ExecCommandBegin"], dict):
            return {"type": "exec_command_begin", **event["ExecCommandBegin"]}
        if "ExecCommandEnd" in event and isinstance(event["ExecCommandEnd"], dict):
            return {"type": "exec_command_end", **event["ExecCommandEnd"]}

        normalized_event = dict(event)
        event_type = normalized_event.get("type")
        if isinstance(event_type, str):
            legacy_type_map = {
                "UserMessage": "user_message",
                "AgentMessage": "agent_message",
                "ExecCommandBegin": "exec_command_begin",
                "ExecCommandEnd": "exec_command_end",
                "TokenCount": "token_count",
            }
            normalized_event["type"] = legacy_type_map.get(event_type, event_type)
        return normalized_event

    @staticmethod
    def _extract_response_item_payload(entry: dict) -> dict | None:
        if isinstance(entry.get("type"), str) and entry.get("type") == "response_item":
            payload = entry.get("payload")
            return payload if isinstance(payload, dict) else None

        resp_item = entry.get("ResponseItem") or entry.get("response_item")
        return resp_item if isinstance(resp_item, dict) else None

    @staticmethod
    def _parse_nested_timestamp(value: object) -> datetime | None:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None
        return None

    @staticmethod
    def _extract_event_text(event: dict) -> str:
        for key in ("message", "text"):
            value = event.get(key)
            if isinstance(value, str) and value:
                return value

        text_elements = event.get("text_elements")
        if isinstance(text_elements, list):
            texts = [part for part in text_elements if isinstance(part, str)]
            if texts:
                return "\n".join(texts)

        return ""

    @staticmethod
    def _ensure_model_bucket(model_tokens: dict, model: str) -> None:
        if model not in model_tokens:
            model_tokens[model] = {
                "input": 0,
                "output": 0,
                "cache_read": 0,
                "cache_creation": 0,
            }

    def _apply_token_usage(
        self,
        meta: SessionMetadata,
        model_tokens: dict,
        prev_cumulative: dict,
        token_data: dict,
        current_model: str | None,
    ) -> None:
        model = token_data.get("model") or current_model or "unknown"
        self._ensure_model_bucket(model_tokens, model)

        info = token_data.get("info") if isinstance(token_data.get("info"), dict) else None
        if info:
            last_usage = info.get("last_token_usage")
            if isinstance(last_usage, dict):
                delta_input = int(last_usage.get("input_tokens", 0) or 0)
                delta_output = int(last_usage.get("output_tokens", 0) or 0)
                delta_cached = int(last_usage.get("cached_input_tokens", 0) or 0)
            else:
                totals = info.get("total_token_usage") or {}
                delta_input, delta_output, delta_cached = self._compute_token_deltas(
                    model,
                    totals,
                    prev_cumulative,
                )
        else:
            delta_input, delta_output, delta_cached = self._compute_token_deltas(
                model,
                token_data,
                prev_cumulative,
            )

        model_tokens[model]["input"] += delta_input
        model_tokens[model]["output"] += delta_output
        model_tokens[model]["cache_read"] += delta_cached

        meta.input_tokens += delta_input
        meta.output_tokens += delta_output
        meta.cache_read_tokens += delta_cached

    @staticmethod
    def _compute_token_deltas(
        model: str,
        totals: dict,
        prev_cumulative: dict,
    ) -> tuple[int, int, int]:
        if model not in prev_cumulative:
            prev_cumulative[model] = {"input": 0, "output": 0, "cache_read": 0}
        prev = prev_cumulative[model]

        curr_input = int(totals.get("input_tokens", 0) or 0)
        curr_output = int(totals.get("output_tokens", 0) or 0)
        curr_cached = int(totals.get("cached_input_tokens", 0) or 0)

        delta_input = max(0, curr_input - prev["input"])
        delta_output = max(0, curr_output - prev["output"])
        delta_cached = max(0, curr_cached - prev["cache_read"])

        prev["input"] = curr_input
        prev["output"] = curr_output
        prev["cache_read"] = curr_cached

        return delta_input, delta_output, delta_cached

    @staticmethod
    def _extract_response_item_message(
        resp_item: dict,
        ordinal: int,
        current_model: str | None,
        call_id_to_tool: dict[str, str],
    ) -> dict | None:
        resp_type = resp_item.get("type")
        if resp_type == "function_call" or "function_call" in resp_item:
            fc = resp_item.get("function_call", resp_item)
            input_preview = fc.get("arguments") or resp_item.get("arguments") or ""
            msg: dict = {
                "ordinal": ordinal,
                "role": "assistant",
                "tool_calls": [
                    {
                        "name": fc.get("name", "function_call"),
                        "input_preview": str(input_preview)[:500],
                    }
                ],
            }
            if current_model:
                msg["model"] = current_model
            return msg

        if resp_type == "function_call_output":
            call_id = resp_item.get("call_id")
            tool_name = call_id_to_tool.get(call_id or "", "function_call")
            output = resp_item.get("output")
            if not isinstance(output, str) or not output:
                return None
            return {
                "ordinal": ordinal,
                "role": "tool_result",
                "tool_results": [{"name": tool_name, "output_preview": output[:500]}],
            }

        return None
