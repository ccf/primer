"""Tests for the memory consolidation engine (Plan 2b)."""

from primer.common.config import settings
from primer.common.models import MemoryEntry, MemoryEvent, MemoryEvidence
from primer.server.services import memory_embedding_service as emb
from primer.server.services.memory_consolidation_service import (
    _cosine,
    _jaccard,
    _parse_judge_response,
    cluster_similar,
    compute_corroboration,
    judge_sketch,
    merge_sketches_in_scope,
)


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


def test_cluster_similar_is_transitive_regardless_of_order():
    # a~b and b~c each cluster (cos ~0.71), but a~c is 0 (orthogonal). True
    # single-link must still group all three transitively via b — even when the
    # bridging item (b) is visited last, which defeats a single-pass absorb.
    a = [1.0, 1.0, 0.0]
    b = [0.0, 1.0, 0.0]  # ~a and ~c
    c = [0.0, 1.0, 1.0]
    items = [("a", a, "x"), ("c", c, "z"), ("b", b, "y")]  # bridge 'b' last
    clusters = cluster_similar(items, threshold=0.7)
    assert [sorted(g) for g in clusters] == [["a", "b", "c"]]


def _scope_with_sketches(db_session, bodies):
    from primer.common.models import Engineer, GitRepository, MemoryScope

    repo = GitRepository(full_name="acme/merge")
    eng = Engineer(name="M", email="mm@x.io")
    db_session.add_all([repo, eng])
    db_session.flush()
    scope = MemoryScope(kind="project", name="merge", repository_id=repo.id)
    db_session.add(scope)
    db_session.flush()
    from primer.server.services.memory_service import create_sketch

    for i, body in enumerate(bodies):
        create_sketch(
            db_session,
            scope=scope,
            card={"kind": "project_fact", "title": f"t{i}", "body": body},
            origin="passive_extraction",
            engineer_id=eng.id,
            session_id=None,
            citation={"excerpt": "x"},
        )
    return scope, eng


def test_merge_collapses_near_duplicates(db_session, monkeypatch):
    import primer.server.services.memory_consolidation_service as cons

    # Force keyword path (no embeddings) for a deterministic sqlite test.
    monkeypatch.setattr(cons, "_embed_entries", lambda db, entries: None)
    scope, _eng = _scope_with_sketches(
        db_session,
        [
            "Run alembic upgrade head before make build every time.",
            "Run alembic upgrade head before make build, always.",
            "The staging database resets nightly at 0200 UTC.",
        ],
    )
    merged = merge_sketches_in_scope(db_session, scope, threshold=0.5)
    db_session.flush()
    survivors = (
        db_session.query(MemoryEntry)
        .filter(MemoryEntry.scope_id == scope.id, MemoryEntry.superseded_by_id.is_(None))
        .count()
    )
    assert survivors == 2  # one alembic + the staging fact
    assert merged >= 1
    assert (
        db_session.query(MemoryEvent).filter(MemoryEvent.event_kind == "merged_into").count() >= 1
    )
    losers = (
        db_session.query(MemoryEntry)
        .filter(MemoryEntry.scope_id == scope.id, MemoryEntry.superseded_by_id.isnot(None))
        .all()
    )
    assert losers and all(le.status == "retired" for le in losers)
    assert all(le.content_hash.startswith("merged:") for le in losers)


def test_merge_does_not_block_future_rediscovery(db_session, monkeypatch):
    # A future session re-deriving a merged-away loser's exact body must NOT be
    # silently dropped — it creates a fresh sketch (the loser's hash was released).
    import primer.server.services.memory_consolidation_service as cons
    from primer.server.services.memory_service import create_sketch

    monkeypatch.setattr(cons, "_embed_entries", lambda db, entries: None)
    loser_body = "Run alembic upgrade head before make build, always."
    scope, eng = _scope_with_sketches(
        db_session,
        ["Run alembic upgrade head before make build every time.", loser_body],
    )
    merge_sketches_in_scope(db_session, scope, threshold=0.5)
    db_session.flush()
    entry, created = create_sketch(
        db_session,
        scope=scope,
        card={"kind": "project_fact", "title": "again", "body": loser_body},
        origin="passive_extraction",
        engineer_id=eng.id,
        session_id=None,
        citation={"x": 1},
    )
    assert (entry, created) != (None, False)  # NOT silently dropped
    assert entry is not None


def test_corroboration_counts_distinct_independent_engineers(db_session):
    from primer.common.models import Engineer, GitRepository, MemoryScope
    from primer.server.services.memory_service import create_sketch

    repo = GitRepository(full_name="acme/corr")
    e1 = Engineer(name="E1", email="e1@x.io")
    e2 = Engineer(name="E2", email="e2@x.io")
    db_session.add_all([repo, e1, e2])
    db_session.flush()
    scope = MemoryScope(kind="project", name="corr", repository_id=repo.id)
    db_session.add(scope)
    db_session.flush()
    card = {"kind": "project_fact", "title": "t", "body": "Same corroborated fact here."}
    entry, _ = create_sketch(
        db_session,
        scope=scope,
        card=card,
        origin="passive_extraction",
        engineer_id=e1.id,
        session_id=None,
        citation={"x": 1},
    )
    create_sketch(
        db_session,
        scope=scope,
        card=card,
        origin="passive_extraction",
        engineer_id=e2.id,
        session_id=None,
        citation={"x": 2},
    )
    db_session.add(
        MemoryEvidence(
            memory_id=entry.id,
            evidence_kind="transcript_citation",
            engineer_id=e1.id,
            independent=False,
        )
    )
    db_session.flush()

    n = compute_corroboration(db_session, entry)
    assert n == 2  # e1 + e2 distinct independent; the exposed row ignored
    assert entry.corroboration_count == 2


def test_parse_judge_response():
    assert _parse_judge_response('ok: {"accept": true, "rationale": "specific"}') == {
        "accept": True,
        "rationale": "specific",
    }
    assert _parse_judge_response("garbage") is None


def test_judge_promotes_or_rejects(db_session, monkeypatch):
    import primer.server.services.memory_consolidation_service as cons
    from primer.common.models import Engineer, GitRepository, MemoryScope
    from primer.server.services.memory_service import create_sketch

    repo = GitRepository(full_name="acme/judge")
    eng = Engineer(name="J", email="j@x.io")
    db_session.add_all([repo, eng])
    db_session.flush()
    scope = MemoryScope(kind="project", name="judge", repository_id=repo.id)
    db_session.add(scope)
    db_session.flush()
    entry, _ = create_sketch(
        db_session,
        scope=scope,
        card={"kind": "anti_pattern", "title": "t", "body": "Don't skip migrations before build."},
        origin="passive_extraction",
        engineer_id=eng.id,
        session_id=None,
        citation={"x": 1},
    )

    monkeypatch.setattr(
        cons, "_call_judge_api", lambda prompt: {"accept": True, "rationale": "good"}
    )
    promoted = judge_sketch(db_session, entry)
    assert promoted is True
    assert entry.status == "active"
    assert entry.activated_at is not None
    assert entry.activation_baseline is not None
    assert entry.judge_critique == "good"
    assert (
        db_session.query(MemoryEvent).filter(MemoryEvent.event_kind == "promoted_to_active").count()
        == 1
    )

    entry2, _ = create_sketch(
        db_session,
        scope=scope,
        card={"kind": "project_fact", "title": "t2", "body": "Write good code always."},
        origin="passive_extraction",
        engineer_id=eng.id,
        session_id=None,
        citation={"x": 1},
    )
    monkeypatch.setattr(
        cons, "_call_judge_api", lambda prompt: {"accept": False, "rationale": "trivial"}
    )
    assert judge_sketch(db_session, entry2) is False
    assert entry2.status == "rejected"
    assert entry2.judge_critique == "trivial"


def test_judge_api_failure_leaves_sketch_unchanged(db_session, monkeypatch):
    import primer.server.services.memory_consolidation_service as cons
    from primer.common.models import Engineer, GitRepository, MemoryScope
    from primer.server.services.memory_service import create_sketch

    repo = GitRepository(full_name="acme/jfail")
    eng = Engineer(name="J", email="jf@x.io")
    db_session.add_all([repo, eng])
    db_session.flush()
    scope = MemoryScope(kind="project", name="jfail", repository_id=repo.id)
    db_session.add(scope)
    db_session.flush()
    entry, _ = create_sketch(
        db_session,
        scope=scope,
        card={"kind": "project_fact", "title": "t", "body": "A real durable project fact."},
        origin="passive_extraction",
        engineer_id=eng.id,
        session_id=None,
        citation={"x": 1},
    )
    monkeypatch.setattr(cons, "_call_judge_api", lambda prompt: None)  # API error
    assert judge_sketch(db_session, entry) is False
    assert entry.status == "sketch"  # unchanged — retried next pass
