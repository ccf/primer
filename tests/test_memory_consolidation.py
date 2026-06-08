"""Tests for the memory consolidation engine (Plan 2b)."""

from primer.common.config import settings
from primer.common.models import MemoryEntry


def test_consolidation_settings_present():
    assert settings.memory_consolidation_enabled is True
    assert settings.memory_consolidation_interval_hours == 24
    assert settings.memory_min_corroboration == 2
    assert settings.memory_dedup_similarity == 0.85
    assert settings.memory_judge_max_calls_per_pass == 200
    assert settings.memory_judge_model  # non-empty
    assert settings.memory_embedding_model == "BAAI/bge-small-en-v1.5"
    assert settings.memory_embedding_dim == 384


def test_memory_entry_has_embedding_and_supersede_relationship(db_session):
    from primer.common.models import GitRepository, MemoryScope

    repo = GitRepository(full_name="acme/emb")
    db_session.add(repo)
    db_session.flush()
    scope = MemoryScope(kind="project", name="emb", repository_id=repo.id)
    db_session.add(scope)
    db_session.flush()

    original = MemoryEntry(
        scope_id=scope.id, kind="project_fact", title="o", body="ob", content_hash="oh"
    )
    db_session.add(original)
    db_session.flush()
    dup = MemoryEntry(
        scope_id=scope.id,
        kind="project_fact",
        title="d",
        body="db",
        content_hash="dh",
        superseded_by_id=original.id,
    )
    db_session.add(dup)
    db_session.flush()

    # self-relationship traversable
    assert dup.superseded_by.id == original.id
    # embedding column exists and accepts a list on sqlite (JSON variant)
    original.embedding = [0.1] * 384
    db_session.flush()
    assert len(original.embedding) == 384


from primer.server.services import memory_embedding_service as emb  # noqa: E402


def test_embed_texts_returns_vectors(monkeypatch):
    # Mock the model so CI never downloads sentence-transformers weights.
    class _FakeModel:
        def encode(self, texts, normalize_embeddings=True):
            return [[float(len(t))] * 384 for t in texts]

    monkeypatch.setattr(emb, "_get_model", lambda: _FakeModel())
    monkeypatch.setattr(emb, "embeddings_available", lambda: True)
    vecs = emb.embed_texts(["hello", "world!"])
    assert len(vecs) == 2
    assert len(vecs[0]) == 384


def test_embeddings_unavailable_returns_none(monkeypatch):
    monkeypatch.setattr(emb, "embeddings_available", lambda: False)
    assert emb.embed_texts(["x"]) is None


from primer.server.services.memory_consolidation_service import (  # noqa: E402
    _cosine,
    _jaccard,
    cluster_similar,
)


def test_cosine_and_jaccard():
    assert _cosine([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert abs(_cosine([1.0, 0.0], [0.0, 1.0])) < 1e-9
    assert _jaccard("the build cache resets", "the build cache resets nightly") > 0.5
    assert _jaccard("totally different", "nothing alike here") < 0.2


def test_cluster_similar_groups_by_threshold():
    # items: (id, embedding_or_None, body)
    items = [
        ("a", [1.0, 0.0], "run alembic before build"),
        ("b", [0.99, 0.01], "run alembic before build please"),
        ("c", [0.0, 1.0], "unrelated thing entirely"),
    ]
    clusters = cluster_similar(items, threshold=0.85)
    # a and b cluster; c alone
    assert ["a", "b"] in [sorted(g) for g in clusters]
    assert ["c"] in [sorted(g) for g in clusters]
