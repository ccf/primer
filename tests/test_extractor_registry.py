from primer.hook.codex_extractor import CodexExtractor
from primer.hook.extractor import ClaudeCodeExtractor
from primer.hook.extractor_registry import get_all_extractors, get_extractor_for
from primer.hook.gemini_extractor import GeminiExtractor


def test_get_all_extractors():
    extractors = get_all_extractors()
    assert len(extractors) == 3
    types = {e.agent_type for e in extractors}
    assert types == {"claude_code", "codex_cli", "gemini_cli"}


def test_get_extractor_for_claude():
    ext = get_extractor_for("claude_code")
    assert ext is not None
    assert isinstance(ext, ClaudeCodeExtractor)
    assert ext.agent_type == "claude_code"


def test_get_extractor_for_codex():
    ext = get_extractor_for("codex_cli")
    assert ext is not None
    assert isinstance(ext, CodexExtractor)
    assert ext.agent_type == "codex_cli"


def test_get_extractor_for_gemini():
    ext = get_extractor_for("gemini_cli")
    assert ext is not None
    assert isinstance(ext, GeminiExtractor)
    assert ext.agent_type == "gemini_cli"


def test_get_extractor_for_unknown():
    ext = get_extractor_for("unknown_agent")
    assert ext is None
