import secrets
import uuid
from datetime import datetime, timedelta

import bcrypt

from primer.common.models import (
    Engineer,
    Session,
    SessionFacets,
    Team,
)


def _make_engineer(db_session, team, *, name="Eng", email=None, role="engineer"):
    """Create an engineer with a bcrypt-hashed API key, return (engineer, raw_key)."""
    raw_key = f"primer_{secrets.token_urlsafe(32)}"
    hashed = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()
    eng = Engineer(
        name=name,
        email=email or f"{name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}@test.com",
        team_id=team.id,
        api_key_hash=hashed,
        role=role,
    )
    db_session.add(eng)
    db_session.flush()
    return eng, raw_key


def _create_session(db_session, engineer, **kwargs):
    """Create a minimal session with sensible defaults."""
    sid = kwargs.pop("session_id", str(uuid.uuid4()))
    session = Session(
        id=sid,
        engineer_id=engineer.id,
        message_count=kwargs.pop("message_count", 10),
        user_message_count=kwargs.pop("user_message_count", 5),
        assistant_message_count=kwargs.pop("assistant_message_count", 5),
        tool_call_count=kwargs.pop("tool_call_count", 3),
        input_tokens=kwargs.pop("input_tokens", 1000),
        output_tokens=kwargs.pop("output_tokens", 500),
        duration_seconds=kwargs.pop("duration_seconds", 120.0),
        has_facets=kwargs.pop("has_facets", True),
        **kwargs,
    )
    db_session.add(session)
    db_session.flush()
    return session


def _add_outcome(db_session, session, outcome):
    """Add a SessionFacets row with the given outcome."""
    db_session.add(SessionFacets(session_id=session.id, outcome=outcome))
    db_session.flush()


class TestTimeToTeamAverage:
    def _setup_team(self, db_session, n_engineers=2):
        """Create a team with n engineers, return (team, [(eng, key), ...])."""
        team = Team(name=f"Rampup Team {uuid.uuid4().hex[:6]}")
        db_session.add(team)
        db_session.flush()

        pairs = []
        for i in range(n_engineers):
            eng, key = _make_engineer(db_session, team, name=f"RampEng {i}")
            pairs.append((eng, key))
        return team, pairs

    def test_basic_rampup(self, client, db_session, admin_headers):
        """Two engineers in same team, sessions across weeks with varying outcomes.

        Engineer 0 (experienced): mixed results -- 2 success, 2 partial.
        Engineer 1 (ramping): week 0 failure, then all successes weeks 1-3.
        Team avg success = 5/8 = 0.625.
        New engineer rolling: w0=0/1=0%, w1=1/2=50%, w2=2/3=67% >= 62.5%.
        So weeks_to_match = 2 for the new engineer.
        """
        team, pairs = self._setup_team(db_session, n_engineers=2)
        eng_exp, _ = pairs[0]
        eng_new, _ = pairs[1]

        base_date = datetime(2026, 1, 5, 10, 0)  # Monday

        # Experienced engineer: 2 success + 2 partial across 4 weeks
        exp_outcomes = ["success", "success", "partial", "partial"]
        for w, outcome in enumerate(exp_outcomes):
            s = _create_session(
                db_session,
                eng_exp,
                started_at=base_date + timedelta(weeks=w),
            )
            _add_outcome(db_session, s, outcome)

        # New engineer: 1 failure in week 0, then successes in weeks 1-3
        s0 = _create_session(
            db_session,
            eng_new,
            started_at=base_date + timedelta(hours=1),
        )
        _add_outcome(db_session, s0, "failure")

        for w in range(1, 4):
            s = _create_session(
                db_session,
                eng_new,
                started_at=base_date + timedelta(weeks=w, hours=1),
            )
            _add_outcome(db_session, s, "success")

        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/time-to-team-average?team_id={team.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        assert data["total_engineers"] == 2
        assert data["team_avg_success_rate"] > 0

        # Experienced engineer should match immediately (week 0)
        exp_entry = next(e for e in data["engineers"] if e["engineer_id"] == eng_exp.id)
        assert exp_entry["weeks_to_team_average"] == 0

        # New engineer should eventually match (rolling crosses team avg)
        new_entry = next(e for e in data["engineers"] if e["engineer_id"] == eng_new.id)
        assert new_entry["weeks_to_team_average"] is not None
        assert new_entry["weeks_to_team_average"] >= 1
        assert len(new_entry["weekly_success_rates"]) >= 2

    def test_never_matched(self, client, db_session, admin_headers):
        """Engineer never reaches team average -- weeks_to_team_average is None."""
        team, pairs = self._setup_team(db_session, n_engineers=2)
        eng_good, _ = pairs[0]
        eng_bad, _ = pairs[1]

        base_date = datetime(2026, 1, 5, 10, 0)

        # Good engineer: all successes
        for w in range(4):
            s = _create_session(
                db_session,
                eng_good,
                started_at=base_date + timedelta(weeks=w),
            )
            _add_outcome(db_session, s, "success")

        # Bad engineer: all failures
        for w in range(4):
            s = _create_session(
                db_session,
                eng_bad,
                started_at=base_date + timedelta(weeks=w, hours=1),
            )
            _add_outcome(db_session, s, "failure")

        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/time-to-team-average?team_id={team.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        bad_entry = next(e for e in data["engineers"] if e["engineer_id"] == eng_bad.id)
        # Team avg is 0.5 (4 success / 8 total), bad engineer never reaches it
        assert bad_entry["weeks_to_team_average"] is None
        assert bad_entry["current_success_rate"] == 0.0

    def test_immediate_match(self, client, db_session, admin_headers):
        """First week already matches team average -- returns 0."""
        team, pairs = self._setup_team(db_session, n_engineers=2)
        eng1, _ = pairs[0]
        eng2, _ = pairs[1]

        base_date = datetime(2026, 1, 5, 10, 0)

        # Both engineers succeed from week 0
        for eng in [eng1, eng2]:
            for w in range(3):
                s = _create_session(
                    db_session,
                    eng,
                    started_at=base_date + timedelta(weeks=w, hours=eng is eng2),
                )
                _add_outcome(db_session, s, "success")

        db_session.flush()

        r = client.get(
            f"/api/v1/analytics/time-to-team-average?team_id={team.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        # Both should match at week 0
        for entry in data["engineers"]:
            assert entry["weeks_to_team_average"] == 0

    def test_team_scoping(self, client, db_session, admin_headers):
        """Only team members included in results when team_id is specified."""
        # Team A
        team_a = Team(name=f"Scope A {uuid.uuid4().hex[:6]}")
        db_session.add(team_a)
        db_session.flush()
        eng_a, _ = _make_engineer(db_session, team_a, name="ScopeA Eng")

        # Team B
        team_b = Team(name=f"Scope B {uuid.uuid4().hex[:6]}")
        db_session.add(team_b)
        db_session.flush()
        eng_b, _ = _make_engineer(db_session, team_b, name="ScopeB Eng")

        base_date = datetime(2026, 1, 5, 10, 0)

        for eng in [eng_a, eng_b]:
            for w in range(3):
                s = _create_session(
                    db_session,
                    eng,
                    started_at=base_date + timedelta(weeks=w),
                )
                _add_outcome(db_session, s, "success")

        db_session.flush()

        # Query scoped to team A
        r = client.get(
            f"/api/v1/analytics/time-to-team-average?team_id={team_a.id}",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        engineer_ids = [e["engineer_id"] for e in data["engineers"]]
        assert eng_a.id in engineer_ids
        assert eng_b.id not in engineer_ids
        assert data["total_engineers"] == 1

    def test_empty(self, client, admin_headers):
        """No sessions returns empty response."""
        r = client.get(
            "/api/v1/analytics/time-to-team-average",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()

        assert data["engineers"] == []
        assert data["team_avg_success_rate"] == 0.0
        assert data["avg_weeks_to_match"] is None
        assert data["engineers_who_matched"] == 0
        assert data["total_engineers"] == 0
