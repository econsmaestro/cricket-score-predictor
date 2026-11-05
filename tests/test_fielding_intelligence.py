"""Synthetic tests validate mechanics, not empirical fielding improvement."""
from copy import deepcopy
from datetime import date
from dataclasses import asdict
import json
import zipfile

import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from app import db
from models import DiscoveredPlayer
from fielding_intelligence import models as fm
from fielding_intelligence.adapter import attach_shadow, predict_with_fielding
from fielding_intelligence.evaluation import activation_check, metrics
from fielding_intelligence.ingestion import ingest_archive, import_trials, parse_match
from fielding_intelligence.pressure import controlled_pressure, investigate_pressure
from fielding_intelligence.ratings import estimate, fielding_quality, learn_prior, probability_model
from fielding_intelligence.registry import ingest_registry, resolve_person
from fielding_intelligence.service import cached_quality, history_before


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    tables = [DiscoveredPlayer.__table__] + [
        getattr(fm, cls).__table__ for cls in (
            "FieldingPerson", "FieldingIdentifier", "FieldingAlias",
            "FieldingMatch", "FieldingTrial", "FieldingCache")]
    db.metadata.create_all(engine, tables=tables)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def raw():
    def delivery(kind=None, fielders=None, bowler="Bowler"):
        row = {"batter": "Batter", "bowler": bowler, "non_striker": "Other",
               "runs": {"batter": 0, "extras": 0, "total": 0}}
        if kind:
            row["wickets"] = [{"kind": kind, "player_out": "Batter",
                               "fielders": [{"name": n} for n in (fielders or [])]}]
        return row
    return {
        "meta": {"created": "2020-01-03", "revision": 1, "data_version": "1.1.0"},
        "info": {"dates": ["2020-01-01"], "match_type": "ODI", "gender": "male",
                 "teams": ["A", "B"], "players": {"A": ["Batter", "Other"],
                                                 "B": ["Bowler", "Fielder", "Keeper"]},
                 "registry": {"people": {"Batter": "aaaaaaaa", "Other": "bbbbbbbb",
                                          "Bowler": "cccccccc", "Fielder": "dddddddd",
                                          "Keeper": "eeeeeeee"}},
                 "venue": "Ground", "team_type": "international"},
        "innings": [{"team": "A", "overs": [{"over": 0, "deliveries": [
            delivery("caught", ["Fielder"]), delivery("caught and bowled"),
            delivery("run out", ["Fielder", "Keeper"]), delivery("stumped", ["Keeper"]),
            delivery(), delivery("retired hurt"),
        ]}]}],
    }


def trial(person="dddddddd", *, success=True, opportunity=True, event_id="1", **kwargs):
    return dict(
        source="licensed_test_fixture", event_id=event_id, kind="catch", match_id="old",
        event_date="2020-01-01", available_date="2020-01-02",
        match_format="ODI", gender="male", person_id=person, opportunity=opportunity,
        success=success, direct_hit=None, runs_saved=None,
        context={}, provenance="Synthetic test only, not real provider observations",
        exhaustive_delivery_coverage=True, **kwargs)


def test_registry_ids_aliases_and_existing_espn(session):
    session.add(DiscoveredPlayer(id=7, name="Same", espn_id="123"))
    session.flush()
    people = "identifier,name,unique_name,key_cricinfo\naaaaaaaa,Same,Same A,123\nbbbbbbbb,Same,Same B,456\n"
    names = "identifier,name\naaaaaaaa,Alias\nbbbbbbbb,Alias\n"
    report = ingest_registry(session, people, names)
    ingest_registry(session, people, names)
    assert report["people"] == 2
    assert session.scalar(select(func.count()).select_from(fm.FieldingPerson)) == 2
    assert session.get(fm.FieldingPerson, "aaaaaaaa").discovered_player_id == 7
    assert resolve_person(session, name="Same") is None
    assert resolve_person(session, name=" SAME ", roster_ids=["bbbbbbbb"]) == "bbbbbbbb"
    assert resolve_person(session, source="cricinfo", external_id="123") == "aaaaaaaa"


def test_registry_conflicting_external_identity_rejected(session):
    ingest_registry(session, "identifier,name,key_cricinfo\naaaaaaaa,A,1\n", "identifier,name\n")
    with pytest.raises(ValueError, match="Conflicting"):
        ingest_registry(session, "identifier,name,key_cricinfo\nbbbbbbbb,B,1\n", "identifier,name\n")


def test_successes_are_counts_not_opportunities(raw):
    match = parse_match(raw, "1")
    facts = match["facts"]["innings"][0]
    assert facts["observed"]["catch_dismissals"] == 2
    assert facts["observed"]["run_out_dismissals"] == 1
    assert facts["observed"]["wickets"] == 4  # retired hurt excluded
    assert facts["players"]["dddddddd"]["catches"] == 1
    assert facts["players"]["cccccccc"]["catches"] == 1  # caught and bowled
    assert facts["players"]["dddddddd"]["multi_fielder_run_out_involvements"] == 1
    assert facts["individual_delivery_exposure"] is None
    assert "direct_hits" in match["facts"]["unavailable"]
    assert "dropped_catches" in match["facts"]["unavailable"]


def test_team_wickets_and_penalty_runs(raw):
    delivery = raw["innings"][0]["overs"][0]["deliveries"][-1]
    delivery["wickets"][0]["kind"] = "obstructing the field"
    raw["innings"][0]["penalty_runs"] = {"pre": 5, "post": 5}
    totals = parse_match(raw, "1")["facts"]["innings"][0]["observed"]
    assert totals["wickets"] == 5
    assert totals["runs"] == 10


@pytest.mark.parametrize("kind", ["Test", "ODI", "T20", "MDM", "ODM"])
@pytest.mark.parametrize("gender", ["male", "female"])
def test_parser_preserves_format_gender_and_multiday_dates(raw, kind, gender):
    raw["info"].update(match_type=kind, gender=gender, dates=["2020-01-01", "2020-01-05"])
    parsed = parse_match(raw, "1")
    assert parsed["match_format"] == kind
    assert parsed["gender"] == gender
    assert parsed["end_date"] == date(2020, 1, 5)


def test_archive_idempotency_and_revision(session, raw, tmp_path):
    path = tmp_path / "sample.zip"
    def write():
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("1.json", json.dumps(raw))
    write()
    assert ingest_archive(session, path)["changed_matches"] == 1
    assert ingest_archive(session, path)["changed_matches"] == 0
    raw["meta"]["revision"] = 2
    write()
    assert ingest_archive(session, path)["revisions"] == 1
    raw["meta"]["revision"] = 1
    write()
    with pytest.raises(ValueError, match="downgrade"):
        ingest_archive(session, path)


def test_existing_replay_parser_accepts_explicit_archive(raw, tmp_path):
    from backtest_data import parse_matches
    raw["info"].update(overs=50, balls_per_over=6, outcome={"winner": "A"})
    # Produce a complete innings with checkpoints beyond 40 overs.
    delivery = deepcopy(raw["innings"][0]["overs"][0]["deliveries"][4])
    raw["innings"][0]["overs"] = [
        {"over": n, "deliveries": [deepcopy(delivery) for _ in range(6)]}
        for n in range(50)]
    path = tmp_path / "source.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("1.json", json.dumps(raw))
    matches = parse_matches(match_format="mens_odi", max_matches=1, archive_path=path)
    assert len(matches) == 1
    assert matches[0]["match_id"] == "1"
    assert matches[0]["actual_final_score"] == 0


def test_history_cutoff_excludes_same_day_multiday_and_unreleased(session, raw, tmp_path):
    parsed = parse_match(raw, "1")
    session.add(fm.FieldingMatch(**parsed))
    session.flush()
    assert history_before(session, "2020-01-02", "ODI", "male") == []  # source created later
    assert history_before(session, "2020-01-03", "ODI", "male") == []
    assert len(history_before(session, "2020-01-04", "ODI", "male")) == 1
    session.get(fm.FieldingMatch, "cricsheet:1").end_date = date(2020, 1, 5)
    session.flush()
    assert history_before(session, "2020-01-05", "ODI", "male") == []


def test_empty_data_does_not_manufacture_fqr():
    rating = fielding_quality([], person_id="dddddddd", as_of="2021-01-01",
                              match_format="ODI", gender="male")
    assert rating["fqr"] is None
    assert rating["catch"]["opportunity"]["mean"] is None
    assert rating["run_out"]["conversion"]["mean"] is None
    assert rating["component_confidence"]["ground_fielding"]["mean_95_percent_interval"] is None


def test_two_probabilities_do_not_confuse_opportunities_with_catches():
    rows = [trial(event_id=str(i), success=(i != 0) if i < 4 else None,
                  opportunity=i < 4) for i in range(10)]
    result = probability_model(rows, kind="catch", as_of="2021-01-01",
                               match_format="ODI", gender="male", person_id="dddddddd")
    assert result["opportunity"]["trials"] == 10
    assert result["opportunity"]["successes"] == 4
    assert result["conversion"]["trials"] == 4
    assert result["conversion"]["successes"] == 3
    assert result["successful_dismissal_probability_if_assigned"] == pytest.approx(
        result["opportunity"]["mean"] * result["conversion"]["mean"])
    # Success-only records that do not certify coverage cannot fit ability.
    for row in rows:
        row["exhaustive_delivery_coverage"] = False
    missing = probability_model(rows, kind="catch", as_of="2021-01-01",
                                match_format="ODI", gender="male", person_id="dddddddd")
    assert missing["conversion"]["mean"] is None


def test_probability_fit_excludes_future_and_other_cohorts():
    rows = [trial(), {**trial(event_id="2"), "event_date": "2030-01-01"},
            {**trial(event_id="3"), "available_date": "2030-01-01"},
            {**trial(event_id="4"), "match_format": "T20"},
            {**trial(event_id="5"), "gender": "female"}]
    result = probability_model(rows, kind="catch", as_of="2021-01-01",
                               match_format="ODI", gender="male", person_id="dddddddd")
    assert result["conversion"]["trials"] == 1


def test_shrinkage_and_sample_uncertainty():
    prior = learn_prior([(8, 10), (70, 100), (6, 10), (60, 100)])
    assert prior and all(x > 0 for x in prior)
    sparse, dense = estimate(1, 1, prior), estimate(80, 100, prior)
    assert sparse.mean < 1
    assert dense.upper - dense.lower < sparse.upper - sparse.lower
    assert learn_prior([(1, 1)]) is None


def test_trial_validation_and_cache_revision(session):
    session.add(fm.FieldingPerson(id="dddddddd", name="Fielder"))
    session.flush()
    import_trials(session, [trial()])
    result = cached_quality(session, "dddddddd", "2021-01-01", "ODI", "male")
    assert result["catch"]["conversion"]["trials"] == 1
    import_trials(session, [trial(event_id="2", success=False)])
    updated = cached_quality(session, "dddddddd", "2021-01-01", "ODI", "male")
    assert updated["catch"]["conversion"]["trials"] == 2
    assert updated["catch"]["conversion"]["mean"] < result["catch"]["conversion"]["mean"]
    for invalid in ({**trial(), "source": "cricsheet"}, {**trial(), "opportunity": False},
                    {**trial(), "success": "true"}, {**trial(), "person_id": "unknown"}):
        with pytest.raises(ValueError):
            import_trials(session, [invalid])
    with pytest.raises(ValueError, match="revision"):
        import_trials(session, [trial(success=False)])


def test_no_direct_hit_inferred_from_one_fielder():
    row = {**trial(), "kind": "run_out", "direct_hit": True}
    result = probability_model([row], kind="run_out", as_of="2021-01-01",
                               match_format="ODI", gender="male", person_id="dddddddd")
    assert result["observed_direct_hits"] == 1
    assert result["direct_hit_conversion"]["mean"] is None  # no throw-attempt denominator


def test_pressure_without_annotations_has_no_multiplier():
    result = investigate_pressure([{"runs": 0}] * 30)
    assert result["fpi"] is None
    assert result["applied_multiplier"] is None
    assert result["annotated_windows"] == 0


def pressure_rows():
    rows = []
    for fixture in range(8):
        for ball in range(30):
            rows.append({
                "date": f"2020-01-{fixture+1:02}", "match_id": str(fixture), "innings": 2,
                "over": ball/6, "wickets_before": ball//10, "score_before": ball,
                "required_run_rate_before": 7 + fixture/10, "fielding_coverage_complete": True,
                "runs": (ball+fixture) % 4, "team_wicket": ball in {12, 24},
                "fielding_event": "boundary_save" if ball == 10 else "none",
                "fielding_source": "synthetic_test_only",
            })
    return rows


def test_pressure_controls_and_disjoint_temporal_split():
    result = controlled_pressure(pressure_rows(), split_date="2020-01-05")
    assert result["training_matches"] == 4
    assert result["test_matches"] == 4
    assert "required run rate" in result["controls"]
    assert result["fpi"] is None
    assert result["with_fielding_events"]["subsequent_wicket_brier"] is not None


def test_pressure_missing_chase_rrr_not_filled():
    rows = pressure_rows()
    for row in rows:
        row["required_run_rate_before"] = None
    result = controlled_pressure(rows, split_date="2020-01-05")
    assert result["usable_windows"] == 0
    assert result["fpi"] is None


def test_shadow_preserves_entire_baseline(session):
    from prediction import MatchState, predict_score
    state = MatchState(current_score=150, wickets_fallen=3, overs_completed=30,
                       venue="Eden Park, Auckland", batsmen=[], bowlers=[],
                       match_format="mens_odi", fielding_team="Bangladesh")
    old = predict_score(state)
    shadow = predict_with_fielding(state, session, as_of="2021-01-01")
    assert asdict(shadow.baseline) == asdict(old)
    assert asdict(shadow.candidate) == asdict(old)
    assert shadow.diagnostics["applied"] is False
    assert old.fielding_efficiency == 0.80  # legacy engine untouched
    with pytest.raises(ValueError):
        attach_shadow(old, {"applied": True})


def test_metrics_and_activation_gate():
    rows = [{"match_id": "1", "predicted_score": 200, "actual_score": 210,
             "predicted_wickets": 7, "actual_wickets": 9, "low": 190, "high": 220},
            {"match_id": "2", "predicted_score": 200, "actual_score": 190,
             "predicted_wickets": 9, "actual_wickets": 7, "low": 195, "high": 220}]
    m = metrics(rows)
    assert m["score_mae"] == 10 and m["score_bias"] == 0
    assert m["wicket_mae"] == 2 and m["wicket_bias"] == 0
    assert m["exact_wicket_accuracy"] == 0 and m["interval_coverage"] == 0.5
    assert m["win_brier"] is None
    gate = activation_check(m, m, has_opportunity_data=False,
                           independent_holdout=False, interval_calibrated=False)
    assert not gate["approved"]
    assert "No score MAE improvement" in gate["reasons"]


def test_learning_rejects_future_features():
    from fielding_intelligence.learning import fit_residual_model, FEATURES, shadow_residual
    records = [{
        "format": "ODI", "gender": "male", "date": f"2020-01-{i+2:02}",
        "match_id": str(i), "label_available_date": f"2020-01-{i+2:02}",
        "latest_feature_evidence_date": "2020-01-01",
        "opportunity_data_validated": True, "features": dict.fromkeys(FEATURES, 0.7),
        "actual_score": 200+i, "actual_wickets": 7,
    } for i in range(6)]
    artifact = fit_residual_model(records, training_cutoff="2020-02-01")
    assert artifact["activation_allowed"] is False
    assert shadow_residual(artifact, records[0]["features"])["applied"] is False
    records[0]["latest_feature_evidence_date"] = records[0]["date"]
    with pytest.raises(ValueError, match="leakage"):
        fit_residual_model(records, training_cutoff="2020-02-01")


def test_research_api_reports_missing_evidence_without_touching_predictions(session, client, monkeypatch):
    from types import SimpleNamespace
    from fielding_intelligence import api
    monkeypatch.setattr(api, "db", SimpleNamespace(session=session))
    session.add(fm.FieldingPerson(id="dddddddd", name="Fielder"))
    session.flush()
    status = client.get("/api/fielding/status")
    assert status.status_code == 200
    assert status.json["live_predictions_modified"] is False
    assert status.json["labelled_opportunity_trials"] == 0
    player = client.get("/api/fielding/players/dddddddd?format=mens_odi&as_of=2021-01-01")
    assert player.status_code == 200
    assert player.json["rating"]["fqr"] is None
    assert player.json["rating"]["component_confidence"]["catching"]["mean"] is None
    assert client.get("/api/fielding/players/dddddddd?format=unknown").status_code == 400
    assert client.get("/api/fielding/players/dddddddd?as_of=not-a-date").status_code == 400
    assert client.get("/api/fielding/players/unknown").status_code == 404
    import_trials(session, [
        {**trial(), "exhaustive_delivery_coverage": False},
        {**trial(event_id="ground", opportunity=None, success=None),
         "kind": "ground", "runs_saved": 2, "exhaustive_delivery_coverage": False},
    ])
    counts = client.get("/api/fielding/status").json
    assert counts["imported_event_records"] == 2
    assert counts["labelled_opportunity_trials"] == 1
    assert counts["complete_delivery_opportunity_records"] == 0
