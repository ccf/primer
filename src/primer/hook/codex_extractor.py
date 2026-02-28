"""Extract structured metadata from Codex CLI (OpenAI) JSONL session transcripts.

Codex CLI stores sessions as JSONL rollout files at:
    ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl

Each line is a JSON object with a `timestamp` and a variant type:
- SessionMeta: id, cwd, cli_version, model
- TurnContext: model, approval_policy
- EventMsg: UserMessage, AgentMessage, ExecCommandBegin/End
- ResponseItem: function_call responses
- token_count: cumulative token usage (requires delta computation)
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
        first_ts: datetime | None = None
        last_ts: datetime | None = None
        ordinal = 0

        # Track cumulative tokens per model for delta computation
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

                self._process_entry(
                    entry, meta, tool_counter, model_tokens, prev_cumulative, ordinal
                )

                # Collect messages
                msg = self._extract_message(entry, ordinal)
                if msg:
                    meta.messages.append(msg)
                    ordinal += 1

        meta.tool_counts = dict(tool_counter)
        meta.model_tokens = model_tokens
        meta.started_at = first_ts
        meta.ended_at = last_ts
        if first_ts and last_ts:
            meta.duration_seconds = (last_ts - first_ts).total_seconds()

        if model_tokens:
            meta.primary_model = max(
                model_tokens,
                key=lambda m: model_tokens[m].get("input", 0) + model_tokens[m].get("output", 0),
            )

        return meta

    def _process_entry(
        self,
        entry: dict,
        meta: SessionMetadata,
        tool_counter: Counter,
        model_tokens: dict,
        prev_cumulative: dict,
        ordinal: int,
    ) -> None:
        """Process a single Codex CLI JSONL entry."""
        # SessionMeta — session-level info
        session_meta = entry.get("SessionMeta") or entry.get("session_meta")
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
                if model not in model_tokens:
                    model_tokens[model] = {
                        "input": 0,
                        "output": 0,
                        "cache_read": 0,
                        "cache_creation": 0,
                    }
            return

        # TurnContext — model and approval policy
        turn_ctx = entry.get("TurnContext") or entry.get("turn_context")
        if turn_ctx:
            if "model" in turn_ctx:
                model = turn_ctx["model"]
                if model not in model_tokens:
                    model_tokens[model] = {
                        "input": 0,
                        "output": 0,
                        "cache_read": 0,
                        "cache_creation": 0,
                    }
            if "approval_policy" in turn_ctx:
                meta.permission_mode = turn_ctx["approval_policy"]
            return

        # EventMsg — messages and commands
        event = entry.get("EventMsg") or entry.get("event")
        if event:
            event_type = event.get("type", "")
            if event_type == "UserMessage" or "UserMessage" in event:
                meta.message_count += 1
                meta.user_message_count += 1
                text = event.get("text") or event.get("UserMessage", {}).get("text", "")
                if text and not meta.first_prompt:
                    meta.first_prompt = text[:500]
            elif event_type == "AgentMessage" or "AgentMessage" in event:
                meta.message_count += 1
                meta.assistant_message_count += 1
            elif event_type == "ExecCommandBegin" or "ExecCommandBegin" in event:
                tool_counter["exec_command"] += 1
                meta.tool_call_count += 1
            return

        # ResponseItem — function calls
        resp_item = entry.get("ResponseItem") or entry.get("response_item")
        if resp_item:
            if resp_item.get("type") == "function_call" or "function_call" in resp_item:
                fc = resp_item.get("function_call", resp_item)
                tool_name = fc.get("name", "function_call")
                tool_counter[tool_name] += 1
                meta.tool_call_count += 1
            return

        # Token counts — cumulative, need delta computation
        token_data = entry.get("token_count") or entry.get("TokenCount")
        if token_data:
            model = token_data.get("model", "unknown")
            if model not in model_tokens:
                model_tokens[model] = {
                    "input": 0,
                    "output": 0,
                    "cache_read": 0,
                    "cache_creation": 0,
                }

            if model not in prev_cumulative:
                prev_cumulative[model] = {"input": 0, "output": 0, "cache_read": 0}
            prev = prev_cumulative[model]

            curr_input = token_data.get("input_tokens", 0)
            curr_output = token_data.get("output_tokens", 0)
            curr_cached = token_data.get("cached_input_tokens", 0)

            delta_input = max(0, curr_input - prev["input"])
            delta_output = max(0, curr_output - prev["output"])
            delta_cached = max(0, curr_cached - prev["cache_read"])

            model_tokens[model]["input"] += delta_input
            model_tokens[model]["output"] += delta_output
            model_tokens[model]["cache_read"] += delta_cached

            meta.input_tokens += delta_input
            meta.output_tokens += delta_output
            meta.cache_read_tokens += delta_cached

            prev["input"] = curr_input
            prev["output"] = curr_output
            prev["cache_read"] = curr_cached

    @staticmethod
    def _parse_timestamp(entry: dict) -> datetime | None:
        ts_str = entry.get("timestamp")
        if ts_str:
            try:
                return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        return None

    @staticmethod
    def _extract_message(entry: dict, ordinal: int) -> dict | None:
        event = entry.get("EventMsg") or entry.get("event")
        if not event:
            return None

        event_type = event.get("type", "")
        if event_type == "UserMessage" or "UserMessage" in event:
            text = event.get("text") or event.get("UserMessage", {}).get("text", "")
            if text:
                return {"ordinal": ordinal, "role": "human", "content_text": text[:2000]}
        elif event_type == "AgentMessage" or "AgentMessage" in event:
            text = event.get("text") or event.get("AgentMessage", {}).get("text", "")
            if text:
                return {"ordinal": ordinal, "role": "assistant", "content_text": text[:2000]}
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
                    session_meta = entry.get("SessionMeta") or entry.get("session_meta")
                    if session_meta:
                        sid = session_meta.get("id")
                        cwd = session_meta.get("cwd")
                        return (sid or rollout_file.stem, cwd)
            # Fallback: use filename stem
            return (rollout_file.stem, None)
        except OSError:
            return (None, None)
