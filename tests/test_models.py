from primer.common.models import Engineer, Session, SessionFacets, Team, ToolUsage


def test_create_team(db_session):
    team = Team(name="Platform")
    db_session.add(team)
    db_session.flush()
    assert team.id is not None
    assert team.name == "Platform"


def test_create_engineer_with_team(db_session):
    team = Team(name="Backend")
    db_session.add(team)
    db_session.flush()
    eng = Engineer(name="Alice", email="alice@co.com", team_id=team.id, api_key_hash="fakehash")
    db_session.add(eng)
    db_session.flush()
    assert eng.team_id == team.id
    assert eng.team.name == "Backend"


def test_session_facets_relationship(db_session):
    team = Team(name="T")
    db_session.add(team)
    db_session.flush()
    eng = Engineer(name="Bob", email="bob@co.com", team_id=team.id, api_key_hash="h")
    db_session.add(eng)
    db_session.flush()
    sess = Session(id="sess-1", engineer_id=eng.id)
    db_session.add(sess)
    db_session.flush()
    facets = SessionFacets(session_id=sess.id, outcome="success", brief_summary="Did stuff")
    db_session.add(facets)
    db_session.flush()
    assert sess.facets.outcome == "success"


def test_session_facets_confidence_score_persists(db_session):
    team = Team(name="Confidence Team")
    db_session.add(team)
    db_session.flush()
    eng = Engineer(name="Dana", email="dana@co.com", team_id=team.id, api_key_hash="h")
    db_session.add(eng)
    db_session.flush()
    sess = Session(id="sess-confidence", engineer_id=eng.id)
    db_session.add(sess)
    db_session.flush()
    facets = SessionFacets(
        session_id=sess.id,
        outcome="success",
        brief_summary="Stored with confidence",
        confidence_score=0.82,
    )
    db_session.add(facets)
    db_session.flush()

    stored = db_session.query(SessionFacets).filter(SessionFacets.session_id == sess.id).one()
    assert stored.confidence_score == 0.82


def test_tool_usage(db_session):
    team = Team(name="TT")
    db_session.add(team)
    db_session.flush()
    eng = Engineer(name="Carol", email="carol@co.com", team_id=team.id, api_key_hash="h")
    db_session.add(eng)
    db_session.flush()
    sess = Session(id="sess-2", engineer_id=eng.id)
    db_session.add(sess)
    db_session.flush()
    tu = ToolUsage(session_id=sess.id, tool_name="Read", call_count=15)
    db_session.add(tu)
    db_session.flush()
    assert sess.tool_usages[0].tool_name == "Read"
    assert sess.tool_usages[0].call_count == 15
