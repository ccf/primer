"""Extract structured metadata from session transcripts.

Provides the SessionExtractor protocol and ClaudeCodeExtractor implementation.
Module-level functions (extract_from_jsonl, load_facets, etc.) are kept as
backward-compatible aliases.
"""

from __future__ import annotations

import json
import logging
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


class SessionExtractor(Protocol):
    """Protocol that all agent extractors must implement."""

    agent_type: str

    def discover_sessions(self) -> list:
        """Return list of LocalSession objects found on disk."""
        ...

    def extract(self, transcript_path: str) -> SessionMetadata:
        """Parse a transcript file and return SessionMetadata."""
        ...

    def get_data_dir(self) -> Path:
        """Return the root data directory for this agent."""
        ...


@dataclass
class SessionMetadata:
    session_id: str = ""
    project_path: str = ""
    project_name: str = ""
    git_branch: str = ""
    git_remote_url: str = ""
    agent_type: str = "claude_code"
    agent_version: str = ""
    permission_mode: str = ""
    end_reason: str = ""
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: float | None = None
    message_count: int = 0
    user_message_count: int = 0
    assistant_message_count: int = 0
    tool_call_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    primary_model: str = ""
    billing_mode: str = ""
    first_prompt: str = ""
    summary: str = ""
    tool_counts: dict[str, int] = field(default_factory=dict)
    model_tokens: dict[str, dict[str, int]] = field(default_factory=dict)
    messages: list[dict] = field(default_factory=list)
    commits: list[dict] = field(default_factory=list)

    def to_ingest_payload(self, api_key: str, facets: dict | None = None) -> dict:
        payload: dict = {
            "session_id": self.session_id,
            "api_key": api_key,
            "project_path": self.project_path or None,
            "project_name": self.project_name or None,
            "git_branch": self.git_branch or None,
            "agent_type": self.agent_type,
            "agent_version": self.agent_version or None,
            "permission_mode": self.permission_mode or None,
            "end_reason": self.end_reason or None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_seconds": self.duration_seconds,
            "message_count": self.message_count,
            "user_message_count": self.user_message_count,
            "assistant_message_count": self.assistant_message_count,
            "tool_call_count": self.tool_call_count,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "primary_model": self.primary_model or None,
            "billing_mode": self.billing_mode or None,
            "first_prompt": self.first_prompt[:500] if self.first_prompt else None,
            "summary": self.summary or None,
            "tool_usages": [
                {"tool_name": name, "call_count": count} for name, count in self.tool_counts.items()
            ],
            "model_usages": [
                {
                    "model_name": name,
                    "input_tokens": tokens.get("input", 0),
                    "output_tokens": tokens.get("output", 0),
                    "cache_read_tokens": tokens.get("cache_read", 0),
                    "cache_creation_tokens": tokens.get("cache_creation", 0),
                }
                for name, tokens in self.model_tokens.items()
            ],
        }
        if self.messages:
            payload["messages"] = self.messages
        if self.git_remote_url:
            payload["git_remote_url"] = self.git_remote_url
        if self.commits:
            payload["commits"] = self.commits
        if facets:
            payload["facets"] = facets
        return payload


def _run_git(args: list[str], cwd: str) -> str | None:
    """Run a git command and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def capture_git_info(cwd: str, started_at: datetime | None) -> dict:
    """Capture git branch, remote, and commits made during the session."""
    info: dict = {"branch": "", "remote_url": "", "commits": []}

    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    if branch:
        info["branch"] = branch

    remote_url = _run_git(["remote", "get-url", "origin"], cwd)
    if remote_url:
        info["remote_url"] = remote_url

    if not started_at:
        return info

    since = started_at.isoformat()
    # Use record separator (%x1e) + unit separator (%x1f) to avoid pipe-in-message issues
    log_output = _run_git(
        [
            "log",
            "--all",
            f"--since={since}",
            "--format=%x1e%H%x1f%s%x1f%an%x1f%ae%x1f%aI",
            "--numstat",
        ],
        cwd,
    )
    if not log_output:
        return info

    commits: list[dict] = []
    current: dict | None = None

    for line in log_output.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("\x1e"):
            parts = line[1:].split("\x1f")
            if len(parts) >= 5 and current:
                commits.append(current)
            if len(parts) >= 5:
                current = {
                    "sha": parts[0],
                    "message": parts[1],
                    "author_name": parts[2],
                    "author_email": parts[3],
                    "committed_at": parts[4],
                    "files_changed": 0,
                    "lines_added": 0,
                    "lines_deleted": 0,
                }
        elif current and "\t" in line:
            # numstat line: added\tdeleted\tfilename
            numparts = line.split("\t")
            if len(numparts) >= 2:
                try:
                    added = int(numparts[0]) if numparts[0] != "-" else 0
                    deleted = int(numparts[1]) if numparts[1] != "-" else 0
                    current["files_changed"] += 1
                    current["lines_added"] += added
                    current["lines_deleted"] += deleted
                except ValueError:
                    pass

    if current:
        commits.append(current)

    info["commits"] = commits
    return info


def extract_from_jsonl(transcript_path: str) -> SessionMetadata:
    """Parse a JSONL transcript file and extract session metadata."""
    meta = SessionMetadata()
    tool_counter: Counter[str] = Counter()
    model_tokens: dict[str, dict[str, int]] = {}
    first_ts: datetime | None = None
    last_ts: datetime | None = None
    first_user_prompt_found = False
    ordinal = 0

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

            _process_entry(
                entry,
                meta,
                tool_counter,
                model_tokens,
                first_ts,
                last_ts,
                first_user_prompt_found,
            )

            # Track timestamps
            ts = _parse_timestamp(entry)
            if ts:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts

            # Track first user prompt
            if not first_user_prompt_found and entry.get("type") == "human":
                text = _extract_text(entry)
                if text:
                    meta.first_prompt = text[:500]
                    first_user_prompt_found = True

            # Collect messages
            msg = _extract_message(entry, ordinal)
            if msg:
                meta.messages.append(msg)
                ordinal += 1

    meta.tool_counts = dict(tool_counter)
    meta.model_tokens = model_tokens
    meta.started_at = first_ts
    meta.ended_at = last_ts
    if first_ts and last_ts:
        meta.duration_seconds = (last_ts - first_ts).total_seconds()

    # Determine primary model
    if model_tokens:
        meta.primary_model = max(
            model_tokens,
            key=lambda m: model_tokens[m].get("input", 0) + model_tokens[m].get("output", 0),
        )

    return meta


def _process_entry(
    entry: dict,
    meta: SessionMetadata,
    tool_counter: Counter,
    model_tokens: dict,
    first_ts,
    last_ts,
    first_user_prompt_found,
) -> None:
    """Process a single JSONL entry."""
    entry_type = entry.get("type", "")

    # Count messages
    if entry_type == "human":
        meta.message_count += 1
        meta.user_message_count += 1
    elif entry_type == "assistant":
        meta.message_count += 1
        meta.assistant_message_count += 1

    # Extract session metadata from summary/system entries
    if entry_type == "summary" or entry_type == "system":
        if "sessionId" in entry:
            meta.session_id = entry["sessionId"]
        if "cwd" in entry:
            meta.project_path = entry["cwd"]
            meta.project_name = Path(entry["cwd"]).name
        if "version" in entry:
            meta.agent_version = entry["version"]
        if "permissionMode" in entry:
            meta.permission_mode = entry["permissionMode"]

    # Tool calls
    if entry_type == "assistant":
        content = entry.get("message", {}).get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_name = block.get("name", "unknown")
                    tool_input = block.get("input", {})
                    if isinstance(tool_input, dict):
                        if tool_name == "Task":
                            sub_type = tool_input.get("subagent_type") or ""
                            if sub_type:
                                tool_name = f"Task:{sub_type}"
                        elif tool_name == "Skill":
                            skill_name = tool_input.get("skill") or ""
                            if skill_name:
                                tool_name = f"Skill:{skill_name}"
                    tool_counter[tool_name] += 1
                    meta.tool_call_count += 1

    # Token usage
    msg = entry.get("message")
    usage = msg.get("usage", {}) if isinstance(msg, dict) else {}
    if usage:
        model = entry.get("message", {}).get("model", "unknown")
        if model not in model_tokens:
            model_tokens[model] = {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0}
        model_tokens[model]["input"] += usage.get("input_tokens", 0)
        model_tokens[model]["output"] += usage.get("output_tokens", 0)
        model_tokens[model]["cache_read"] += usage.get("cache_read_input_tokens", 0)
        model_tokens[model]["cache_creation"] += usage.get("cache_creation_input_tokens", 0)
        meta.input_tokens += usage.get("input_tokens", 0)
        meta.output_tokens += usage.get("output_tokens", 0)
        meta.cache_read_tokens += usage.get("cache_read_input_tokens", 0)
        meta.cache_creation_tokens += usage.get("cache_creation_input_tokens", 0)


def _parse_timestamp(entry: dict) -> datetime | None:
    """Try to parse a timestamp from an entry."""
    for key in ("timestamp", "createdAt"):
        ts_str = entry.get(key)
        if ts_str:
            try:
                return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
    return None


def _extract_text(entry: dict) -> str:
    """Extract text content from a message entry."""
    msg = entry.get("message", entry)
    content = msg.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
            elif isinstance(block, str):
                texts.append(block)
        return " ".join(texts)
    return ""


def _extract_message(entry: dict, ordinal: int) -> dict | None:
    """Extract a transcript message from a JSONL entry."""
    entry_type = entry.get("type", "")

    if entry_type == "human":
        text = _extract_text(entry)
        if not text:
            return None
        return {
            "ordinal": ordinal,
            "role": "human",
            "content_text": text[:2000],
        }

    if entry_type == "assistant":
        content = entry.get("message", {}).get("content", [])
        text_parts = []
        tool_calls = []
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        input_str = json.dumps(block.get("input", {}))
                        tool_calls.append(
                            {
                                "name": block.get("name", "unknown"),
                                "input_preview": input_str[:500],
                            }
                        )
                elif isinstance(block, str):
                    text_parts.append(block)
        elif isinstance(content, str):
            text_parts.append(content)

        msg = entry.get("message", {})
        usage = msg.get("usage", {})
        return {
            "ordinal": ordinal,
            "role": "assistant",
            "content_text": " ".join(text_parts)[:2000] if text_parts else None,
            "tool_calls": tool_calls or None,
            "token_count": usage.get("output_tokens"),
            "model": msg.get("model"),
        }

    if entry_type == "tool_result":
        content = entry.get("content", entry.get("message", {}).get("content", ""))
        output = ""
        tool_name = entry.get("name", entry.get("tool_name", "unknown"))
        if isinstance(content, str):
            output = content
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    output += block.get("text", "")
        return {
            "ordinal": ordinal,
            "role": "tool_result",
            "tool_results": [{"name": tool_name, "output_preview": output[:500]}],
        }

    return None


def load_facets(session_id: str) -> dict | None:
    """Load facets from ~/.claude/usage-data/facets/{session_id}.json if they exist."""
    facets_path = Path.home() / ".claude" / "usage-data" / "facets" / f"{session_id}.json"
    if not facets_path.exists():
        return None
    try:
        with open(facets_path) as f:
            data = json.load(f)
        # Map to our schema field names
        return {
            "underlying_goal": data.get("underlyingGoal"),
            "goal_categories": data.get("goalCategories"),
            "outcome": data.get("outcome"),
            "session_type": data.get("sessionType"),
            "primary_success": data.get("primarySuccess"),
            "agent_helpfulness": data.get("claudeHelpfulness"),
            "brief_summary": data.get("briefSummary"),
            "user_satisfaction_counts": data.get("userSatisfactionCounts"),
            "friction_counts": data.get("frictionCounts"),
            "friction_detail": data.get("frictionDetail"),
        }
    except (json.JSONDecodeError, OSError):
        return None


class ClaudeCodeExtractor:
    """Extractor for Claude Code sessions (~/.claude/)."""

    agent_type = "claude_code"

    def get_data_dir(self) -> Path:
        return Path.home() / ".claude"

    def discover_sessions(self) -> list:
        """Discover Claude Code sessions from ~/.claude/usage-data/session-meta/."""
        from primer.mcp.reader import LocalSession

        data_dir = self.get_data_dir()
        meta_dir = data_dir / "usage-data" / "session-meta"
        facets_dir = data_dir / "usage-data" / "facets"
        projects_dir = data_dir / "projects"

        if not meta_dir.exists():
            return []

        results: list[LocalSession] = []
        for meta_file in meta_dir.glob("*.json"):
            session_id = meta_file.stem
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            project_path = meta.get("project_path")
            transcript_path = self._find_transcript(projects_dir, session_id, project_path)
            if not transcript_path:
                continue

            facets_path = facets_dir / f"{session_id}.json"
            has_facets = facets_path.exists()
            results.append(
                LocalSession(
                    session_id=session_id,
                    transcript_path=str(transcript_path),
                    facets_path=str(facets_path) if has_facets else None,
                    has_facets=has_facets,
                    project_path=project_path,
                    agent_type=self.agent_type,
                )
            )
        return results

    def extract(self, transcript_path: str) -> SessionMetadata:
        return extract_from_jsonl(transcript_path)

    @staticmethod
    def _find_transcript(
        projects_dir: Path, session_id: str, project_path: str | None
    ) -> Path | None:
        if project_path:
            dir_name = project_path.replace("/", "-")
            candidate = projects_dir / dir_name / f"{session_id}.jsonl"
            if candidate.exists():
                return candidate
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if not project_dir.is_dir():
                    continue
                candidate = project_dir / f"{session_id}.jsonl"
                if candidate.exists():
                    return candidate
        return None
