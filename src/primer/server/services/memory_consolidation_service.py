"""Memory consolidation engine (Plan 2b): merge near-duplicate sketches, ground
corroboration, judge sketch->active, decay stale active entries. Runs as a
recurring background job per dirty scope. Spec §7.
"""

import logging
import math
import re

from sqlalchemy.orm import Session

from primer.common.config import settings
from primer.common.models import MemoryEntry, MemoryEvent, MemoryEvidence, MemoryScope
from primer.server.services import memory_embedding_service as emb

logger = logging.getLogger(__name__)


def _cosine(a: list[float], b: list[float]) -> float:
    # strict=True: callers only pass two real embeddings of equal width (the
    # load-time dim-assertion + the Vector(384) column guarantee it), so a length
    # mismatch is a "can't happen" invariant violation — fail loud, never return a
    # plausible-but-wrong score from a truncated dot product.
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", (text or "").lower()))


def _jaccard(text_a: str, text_b: str) -> float:
    ta, tb = _tokens(text_a), _tokens(text_b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _similarity(item_a: tuple, item_b: tuple) -> float:
    """item = (id, embedding|None, body). Cosine when both embeddings present,
    else keyword Jaccard."""
    _, emb_a, body_a = item_a
    _, emb_b, body_b = item_b
    if emb_a is not None and emb_b is not None:
        return _cosine(emb_a, emb_b)
    return _jaccard(body_a, body_b)


def cluster_similar(items: list[tuple], threshold: float) -> list[list[str]]:
    """Single-link clustering: ids transitively connected by pairwise similarity
    >= threshold land in one cluster (a~b and b~c groups a, b, c even if a~c is
    below threshold). items: list of (id, embedding|None, body). Returns lists of
    ids. O(n^2) per cluster — fine for the tens of sketches in a per-scope pass."""
    unassigned = list(items)
    clusters: list[list[str]] = []
    while unassigned:
        group = [unassigned.pop(0)]
        # Absorb until the group stops growing, re-testing previously-skipped
        # items against members added in earlier sweeps (transitive closure).
        absorbed = True
        while absorbed:
            absorbed = False
            rest = []
            for other in unassigned:
                if any(_similarity(member, other) >= threshold for member in group):
                    group.append(other)
                    absorbed = True
                else:
                    rest.append(other)
            unassigned = rest
        clusters.append([it[0] for it in group])
    return clusters


def _embed_entries(db: Session, entries: list[MemoryEntry]) -> None:
    """Populate `embedding` for entries missing it (postgres only)."""
    if not emb.embeddings_available():
        return
    missing = [e for e in entries if e.embedding is None]
    if not missing:
        return
    vectors = emb.embed_texts([f"{e.title}\n{e.body}" for e in missing])
    if vectors is None:
        return
    for entry, vec in zip(missing, vectors, strict=False):
        entry.embedding = vec
    db.flush()


def merge_sketches_in_scope(db: Session, scope: MemoryScope, threshold: float | None = None) -> int:
    """Step 1 (spec §7): collapse near-duplicate sketches in a scope into one
    canonical entry, reparenting evidence and marking the losers superseded.
    Returns the number of entries merged away."""
    thr = threshold if threshold is not None else settings.memory_dedup_similarity
    sketches = (
        db.query(MemoryEntry)
        .filter(MemoryEntry.scope_id == scope.id, MemoryEntry.status == "sketch")
        .all()
    )
    if len(sketches) < 2:
        return 0
    _embed_entries(db, sketches)
    by_id = {e.id: e for e in sketches}
    items = [(e.id, e.embedding, e.body) for e in sketches]
    clusters = cluster_similar(items, thr)

    merged = 0
    for group in clusters:
        if len(group) < 2:
            continue
        # canonical = oldest (stable); others fold into it as tombstones
        members = sorted((by_id[i] for i in group), key=lambda e: e.created_at)
        canonical, losers = members[0], members[1:]
        for loser in losers:
            db.query(MemoryEvidence).filter(MemoryEvidence.memory_id == loser.id).update(
                {MemoryEvidence.memory_id: canonical.id}
            )
            # Tombstone WITHOUT marking `rejected`. `rejected` is the judge's
            # sticky-block status, and content_hash is UNIQUE per scope — leaving
            # the loser on a rejected/retired row with its REAL hash would (a)
            # silently drop a future legitimate rediscovery of that exact body (the
            # (scope_id, content_hash) dedup lookup would find this row), and (b)
            # collide on the UNIQUE constraint. So RELEASE the real hash (namespace
            # it) and use terminal `retired` (NOT in _DEDUP_BLOCKING_STATUSES).
            loser.content_hash = f"merged:{loser.id}"
            loser.superseded_by_id = canonical.id
            loser.status = "retired"
            db.add(
                MemoryEvent(
                    memory_id=canonical.id,
                    event_kind="merged_into",
                    actor="system",
                    payload={"from": loser.id},
                )
            )
            merged += 1
    db.flush()
    return merged
