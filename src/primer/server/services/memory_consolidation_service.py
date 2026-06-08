"""Memory consolidation engine (Plan 2b): merge near-duplicate sketches, ground
corroboration, judge sketch->active, decay stale active entries. Runs as a
recurring background job per dirty scope. Spec §7.
"""

import logging
import math
import re

logger = logging.getLogger(__name__)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
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
    """Greedy single-link clustering by pairwise similarity >= threshold.
    items: list of (id, embedding|None, body). Returns lists of ids."""
    unassigned = list(items)
    clusters: list[list[str]] = []
    while unassigned:
        seed = unassigned.pop(0)
        group = [seed]
        rest = []
        for other in unassigned:
            if any(_similarity(member, other) >= threshold for member in group):
                group.append(other)
            else:
                rest.append(other)
        clusters.append([it[0] for it in group])
        unassigned = rest
    return clusters
