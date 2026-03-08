# Measurement Integrity Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Primer's session semantics trustworthy by unifying facet taxonomy, normalizing stored values, fixing downstream analytics, surfacing data-quality coverage, and adding confidence scoring for extracted facets.

**Architecture:** Introduce a single shared facet-taxonomy module that owns canonical outcome and goal-category normalization, then route all ingest, extraction, analytics, and recommendations through it. Add a small measurement-integrity service for admin-visible coverage and normalization operations, and store per-session facet confidence so the product can distinguish strong evidence from weak inference.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, pytest, React, TypeScript, TanStack Query.

**Design context:** `ROADMAP.md` under `Measurement Integrity & Data Foundation`

---

### Task 1: Create a Canonical Facet Taxonomy Module

**Files:**
- Create: `src/primer/common/facet_taxonomy.py`
- Modify: `src/primer/common/schemas.py`
- Modify: `src/primer/common/models.py`
- Test: `tests/test_facet_taxonomy.py`
- Test: `tests/test_facet_extraction.py`

**Step 1: Write the failing taxonomy tests**

Create `tests/test_facet_taxonomy.py` with coverage for:

```python
from primer.common.facet_taxonomy import (
    canonical_outcome,
    is_success_outcome,
    normalize_goal_categories,
)


def test_canonical_outcome_maps_legacy_values():
    assert canonical_outcome("fully_achieved") == "success"
    assert canonical_outcome("mostly_achieved") == "partial"
    assert canonical_outcome("partially_achieved") == "partial"
    assert canonical_outcome("not_achieved") == "failure"


def test_canonical_outcome_preserves_current_values():
    assert canonical_outcome("success") == "success"
    assert canonical_outcome("partial") == "partial"
    assert canonical_outcome("failure") == "failure"


def test_normalize_goal_categories_accepts_dict_and_list():
    assert normalize_goal_categories({"fix_bug": 2, "refactor": 1}) == ["fix_bug", "refactor"]
    assert normalize_goal_categories(["fix_bug", "refactor"]) == ["fix_bug", "refactor"]


def test_is_success_outcome_uses_canonical_mapping():
    assert is_success_outcome("fully_achieved") is True
    assert is_success_outcome("success") is True
    assert is_success_outcome("not_achieved") is False
```

Also extend `tests/test_facet_extraction.py` to expect canonical values at the payload boundary, not legacy values.

**Step 2: Run the targeted tests to confirm they fail**

Run: `pytest tests/test_facet_taxonomy.py tests/test_facet_extraction.py -v`

Expected: FAIL because `primer.common.facet_taxonomy` does not exist and the extraction tests still expect legacy values.

**Step 3: Implement the shared taxonomy helpers**

Create `src/primer/common/facet_taxonomy.py` with:

```python
CANONICAL_OUTCOME_ALIASES = {
    "success": "success",
    "fully_achieved": "success",
    "partial": "partial",
    "mostly_achieved": "partial",
    "partially_achieved": "partial",
    "failure": "failure",
    "not_achieved": "failure",
}


def canonical_outcome(value: str | None) -> str | None: ...
def is_success_outcome(value: str | None) -> bool: ...
def normalize_goal_categories(value: object) -> list[str] | None: ...
```

Keep this module framework-free so services and schemas can both import it.

**Step 4: Update schemas and model typing to match actual storage**

In `src/primer/common/schemas.py`:
- normalize `goal_categories` through the shared helper in `SessionFacetsPayload`
- normalize `outcome` through the shared helper
- prepare for a later `confidence_score` field by leaving the validator structure clean and centralized

In `src/primer/common/models.py`:
- change the `SessionFacets.goal_categories` annotation from `Mapped[dict | None]` to `Mapped[list[str] | None]`
- leave the DB column as `JSON` so no migration is needed for this typing fix alone

**Step 5: Re-run the focused tests**

Run: `pytest tests/test_facet_taxonomy.py tests/test_facet_extraction.py -v`

Expected: PASS

**Step 6: Commit**

```bash
git add src/primer/common/facet_taxonomy.py src/primer/common/schemas.py src/primer/common/models.py tests/test_facet_taxonomy.py tests/test_facet_extraction.py
git commit -m "fix: unify facet taxonomy helpers"
```

---

### Task 2: Normalize Facet Extraction and Ingest Writes

**Files:**
- Modify: `src/primer/server/services/facet_extraction_service.py`
- Modify: `src/primer/server/services/ingest_service.py`
- Test: `tests/test_facet_extraction.py`
- Test: `tests/test_ingest.py`

**Step 1: Write the failing ingest and extraction regression tests**

In `tests/test_facet_extraction.py`, add assertions that extracted facet payloads are canonicalized before persistence:

```python
def test_extracted_legacy_outcome_is_normalized(sample_facets_response):
    payload = _facets_dict_to_payload(sample_facets_response)
    assert payload.outcome == "success"
```

In `tests/test_ingest.py`, add an ingest case that posts:

```python
facets={
    "goal_categories": {"fix_bug": 1, "testing": 1},
    "outcome": "mostly_achieved",
}
```

and asserts the stored record contains:

```python
assert stored.goal_categories == ["fix_bug", "testing"]
assert stored.outcome == "partial"
```

**Step 2: Run the targeted tests**

Run: `pytest tests/test_facet_extraction.py tests/test_ingest.py -v`

Expected: FAIL because `_facets_dict_to_payload()` and `upsert_facets()` still pass through legacy values.

**Step 3: Update the extractor prompt and normalization path**

In `src/primer/server/services/facet_extraction_service.py`:
- update the prompt to request canonical outcomes: `success|partial|failure`
- request `goal_categories` as a list of strings, not a counted dict
- keep `_facets_dict_to_payload()` backward-compatible by normalizing legacy dicts and legacy outcome labels through `facet_taxonomy.py`

**Step 4: Normalize again at the server write boundary**

In `src/primer/server/services/ingest_service.py`:
- normalize `facets.goal_categories` and `facets.outcome` inside `upsert_facets()`
- keep this normalization even though the schema validator also normalizes, so direct service callers cannot bypass it accidentally

**Step 5: Re-run the targeted tests**

Run: `pytest tests/test_facet_extraction.py tests/test_ingest.py -v`

Expected: PASS

**Step 6: Commit**

```bash
git add src/primer/server/services/facet_extraction_service.py src/primer/server/services/ingest_service.py tests/test_facet_extraction.py tests/test_ingest.py
git commit -m "fix: normalize extracted and ingested facets"
```

---

### Task 3: Refactor Analytics and Insight Services to Shared Outcome Semantics

**Files:**
- Modify: `src/primer/server/services/analytics_service.py`
- Modify: `src/primer/server/services/session_insights_service.py`
- Modify: `src/primer/server/services/insights_service.py`
- Modify: `src/primer/server/services/engineer_profile_service.py`
- Modify: `src/primer/server/services/maturity_service.py`
- Modify: `src/primer/server/services/alerting_service.py`
- Modify: `src/primer/server/services/synthesis_service.py`
- Test: `tests/test_analytics.py`
- Test: `tests/test_session_insights.py`
- Test: `tests/test_engineer_profile.py`
- Test: `tests/test_growth.py`

**Step 1: Write failing regression tests around legacy and canonical outcomes**

Add targeted tests to confirm analytics behave the same whether stored facets use legacy or canonical values.

Examples:

```python
def test_overview_treats_fully_achieved_as_success(...):
    ...


def test_session_insights_goal_success_rate_uses_canonical_outcomes(...):
    ...


def test_engineer_profile_success_rate_uses_shared_helper(...):
    ...
```

At least one regression test should seed `SessionFacets(outcome="fully_achieved")` directly in the DB to prove the read path is resilient during backfill.

**Step 2: Run the targeted regression tests**

Run: `pytest tests/test_analytics.py tests/test_session_insights.py tests/test_engineer_profile.py tests/test_growth.py -v`

Expected: FAIL in at least one service because many code paths still use `== "success"` or ad hoc legacy tuple checks.

**Step 3: Replace inline success logic with shared helpers**

In every file above:
- replace `outcome == "success"` branches with `is_success_outcome(outcome)`
- replace direct counting expressions like `sum(1 for o in outcomes if o == "success")` with shared helper usage
- normalize lists of outcomes once at query-read boundaries where convenient

Do not create a second helper layer inside each service. Import the shared functions directly from `src/primer/common/facet_taxonomy.py`.

**Step 4: Stabilize session health scoring**

In `src/primer/server/services/session_insights_service.py`:
- make `compute_session_health_score()` use canonical outcomes
- stop assuming `primary_success` values are `full|partial|none` if the extractor still emits category-style values
- for this pass, treat `primary_success == "none"` as negative and any non-empty non-`none` value as positive

This keeps the health metric coherent without redesigning the `primary_success` taxonomy yet.

**Step 5: Re-run the regression suite**

Run: `pytest tests/test_analytics.py tests/test_session_insights.py tests/test_engineer_profile.py tests/test_growth.py -v`

Expected: PASS

**Step 6: Commit**

```bash
git add src/primer/server/services/analytics_service.py src/primer/server/services/session_insights_service.py src/primer/server/services/insights_service.py src/primer/server/services/engineer_profile_service.py src/primer/server/services/maturity_service.py src/primer/server/services/alerting_service.py src/primer/server/services/synthesis_service.py tests/test_analytics.py tests/test_session_insights.py tests/test_engineer_profile.py tests/test_growth.py
git commit -m "fix: use shared outcome semantics across analytics"
```

---

### Task 4: Add Facet Confidence Scoring to the Data Model and Extraction Flow

**Files:**
- Modify: `src/primer/common/models.py`
- Modify: `src/primer/common/schemas.py`
- Modify: `src/primer/server/services/facet_extraction_service.py`
- Modify: `src/primer/server/services/ingest_service.py`
- Create: `alembic/versions/<new_revision>_add_session_facet_confidence_score.py`
- Test: `tests/test_facet_extraction.py`
- Test: `tests/test_models.py`

**Step 1: Write the failing confidence-score tests**

Add tests that assert:

```python
payload = SessionFacetsPayload(confidence_score=0.82, outcome="success")
assert payload.confidence_score == 0.82
```

and:

```python
facets = db_session.query(SessionFacets).filter(...).one()
assert facets.confidence_score == 0.82
```

**Step 2: Run the targeted tests**

Run: `pytest tests/test_facet_extraction.py tests/test_models.py -v`

Expected: FAIL because `confidence_score` does not exist on the model or schema.

**Step 3: Add the schema and model field**

In `src/primer/common/models.py` add:

```python
confidence_score: Mapped[float | None] = mapped_column(Float)
```

In `src/primer/common/schemas.py` add:

```python
confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
```

to both `SessionFacetsPayload` and `SessionFacetsResponse`.

**Step 4: Update extraction and migration**

In `src/primer/server/services/facet_extraction_service.py`:
- extend the prompt schema to request `confidence_score`
- parse and pass it through `_facets_dict_to_payload()`

In `src/primer/server/services/ingest_service.py`:
- include `confidence_score` in the `upsert_facets()` field list

Create the Alembic migration to add `confidence_score` to `session_facets`.

**Step 5: Re-run the tests**

Run: `pytest tests/test_facet_extraction.py tests/test_models.py -v`

Expected: PASS

**Step 6: Commit**

```bash
git add src/primer/common/models.py src/primer/common/schemas.py src/primer/server/services/facet_extraction_service.py src/primer/server/services/ingest_service.py alembic/versions/*.py tests/test_facet_extraction.py tests/test_models.py
git commit -m "feat: store facet confidence scores"
```

---

### Task 5: Add Measurement Integrity Service, Coverage Stats, and Normalization Backfill

**Files:**
- Create: `src/primer/server/services/measurement_integrity_service.py`
- Modify: `src/primer/server/routers/admin.py`
- Modify: `src/primer/common/schemas.py`
- Test: `tests/test_admin.py`
- Test: `tests/test_facet_extraction.py`

**Step 1: Write the failing admin tests**

In `tests/test_admin.py`, add:

```python
def test_measurement_integrity_stats(client, admin_headers, engineer_with_key):
    r = client.get("/api/v1/admin/measurement-integrity", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert "facet_coverage_pct" in data
    assert "transcript_coverage_pct" in data
    assert "low_confidence_sessions" in data
```

and:

```python
def test_normalize_facets_endpoint_requires_admin(client):
    r = client.post("/api/v1/admin/normalize-facets")
    assert r.status_code in (401, 403)
```

**Step 2: Run the targeted admin tests**

Run: `pytest tests/test_admin.py tests/test_facet_extraction.py -v`

Expected: FAIL because the route and service do not exist.

**Step 3: Implement the new service and response schema**

Create `src/primer/server/services/measurement_integrity_service.py` with:
- `get_measurement_integrity_stats(db)` returning counts and percentages for:
  - `total_sessions`
  - `sessions_with_messages`
  - `sessions_with_facets`
  - `facet_coverage_pct`
  - `transcript_coverage_pct`
  - `low_confidence_sessions`
  - `legacy_outcome_sessions`
  - `legacy_goal_category_sessions`
- `normalize_existing_facets(db, limit: int | None = None, dry_run: bool = False)` that:
  - rewrites legacy outcomes to canonical outcomes
  - rewrites dict-based goal categories to list-based storage
  - leaves already-canonical rows untouched

Add a new response model in `src/primer/common/schemas.py`, for example:

```python
class MeasurementIntegrityStats(BaseModel):
    total_sessions: int
    sessions_with_messages: int
    sessions_with_facets: int
    facet_coverage_pct: float
    transcript_coverage_pct: float
    low_confidence_sessions: int
    legacy_outcome_sessions: int
    legacy_goal_category_sessions: int
```

**Step 4: Add admin routes**

In `src/primer/server/routers/admin.py`, add:
- `GET /api/v1/admin/measurement-integrity`
- `POST /api/v1/admin/normalize-facets`

Keep the normalization endpoint admin-only and support:
- `limit: int = Query(default=500, le=5000)`
- `dry_run: bool = Query(default=True)`

Return a summary payload with rows scanned, rows updated, and remaining legacy rows.

**Step 5: Re-run the targeted tests**

Run: `pytest tests/test_admin.py tests/test_facet_extraction.py -v`

Expected: PASS

**Step 6: Commit**

```bash
git add src/primer/server/services/measurement_integrity_service.py src/primer/server/routers/admin.py src/primer/common/schemas.py tests/test_admin.py tests/test_facet_extraction.py
git commit -m "feat: add measurement integrity admin tooling"
```

---

### Task 6: Surface Coverage and Confidence in the Admin UI and Recommendation Layer

**Files:**
- Modify: `src/primer/server/services/synthesis_service.py`
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/hooks/use-api-queries.ts`
- Modify: `frontend/src/components/admin/admin-system-tab.tsx`
- Modify: `frontend/src/App.test.tsx`
- Test: `tests/test_synthesis.py`

**Step 1: Write the failing recommendation and UI-facing tests**

In `tests/test_synthesis.py`, add a case where low-confidence or low-coverage data produces a measurement-integrity recommendation with explicit evidence.

Example:

```python
assert rec["category"] == "data_quality"
assert rec["evidence"]["facet_coverage_pct"] < 0.3
```

If there is no frontend test for `AdminSystemTab`, update `frontend/src/App.test.tsx` mocks so the new hook surface does not break existing rendering tests.

**Step 2: Run the targeted tests**

Run: `pytest tests/test_synthesis.py -v`

Expected: FAIL or require updates because the recommendation evidence and admin data hook surface do not exist yet.

**Step 3: Update backend recommendation logic**

In `src/primer/server/services/synthesis_service.py`:
- stop inferring facet coverage from `sum(overview.outcome_counts.values())`
- use the measurement-integrity service instead
- include confidence-aware evidence in low-quality-data recommendations
- keep recommendations informational for this pass; do not suppress the entire recommendation engine yet

**Step 4: Update frontend types, hook, and admin tab**

In `frontend/src/types/api.ts` add:

```ts
export interface MeasurementIntegrityStats {
  total_sessions: number
  sessions_with_messages: number
  sessions_with_facets: number
  facet_coverage_pct: number
  transcript_coverage_pct: number
  low_confidence_sessions: number
  legacy_outcome_sessions: number
  legacy_goal_category_sessions: number
}
```

In `frontend/src/hooks/use-api-queries.ts` add:

```ts
export function useMeasurementIntegrity() {
  return useQuery({
    queryKey: ["measurement-integrity"],
    queryFn: () => apiFetch<MeasurementIntegrityStats>("/api/v1/admin/measurement-integrity"),
  })
}
```

In `frontend/src/components/admin/admin-system-tab.tsx`:
- keep the existing system cards
- add a second section for measurement integrity with cards or compact rows for:
  - facet coverage
  - transcript coverage
  - low-confidence sessions
  - remaining legacy rows

**Step 5: Run the targeted verification commands**

Run:
- `pytest tests/test_synthesis.py -v`
- `cd frontend && npx tsc -b --noEmit`

Expected: PASS

**Step 6: Commit**

```bash
git add src/primer/server/services/synthesis_service.py frontend/src/types/api.ts frontend/src/hooks/use-api-queries.ts frontend/src/components/admin/admin-system-tab.tsx frontend/src/App.test.tsx tests/test_synthesis.py
git commit -m "feat: surface measurement integrity coverage"
```

---

### Final Verification

**Files:**
- Verify: `src/primer/common/facet_taxonomy.py`
- Verify: `src/primer/server/services/measurement_integrity_service.py`
- Verify: `src/primer/server/services/analytics_service.py`
- Verify: `frontend/src/components/admin/admin-system-tab.tsx`

**Step 1: Run the focused backend suite**

Run:

```bash
pytest tests/test_facet_extraction.py tests/test_ingest.py tests/test_analytics.py tests/test_session_insights.py tests/test_engineer_profile.py tests/test_growth.py tests/test_admin.py tests/test_synthesis.py -v
```

Expected: PASS

**Step 2: Run backend lint**

Run:

```bash
ruff check src tests
```

Expected: PASS

**Step 3: Run frontend type-check**

Run:

```bash
cd frontend && npx tsc -b --noEmit
```

Expected: PASS

**Step 4: Run the migration smoke test**

Run:

```bash
alembic upgrade head
pytest tests/test_models.py -v
```

Expected: PASS

**Step 5: Final commit if verification changes were needed**

```bash
git add -A
git commit -m "chore: finish measurement integrity foundation"
```
