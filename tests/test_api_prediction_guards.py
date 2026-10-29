"""Prediction guards: extrapolation warnings, impossible inputs, future batter dates and the active-player list.

Observed ranges are computed here from the deployment model's training rows, the archive end from
matches.csv and latest-season appearances from the match squads; none of it reuses the service.
"""
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from cricketlens import predict_wicket
from cricketlens.api.app import app

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
WICKET_MODEL = ROOT / "models" / "wicket_deployment_through_2026.joblib"
TRAINING_ROWS = DATA / "stage03_wicket_full_history_2008_2026.csv"

pytestmark = pytest.mark.skipif(not (WICKET_MODEL.is_file() and TRAINING_ROWS.is_file()),
                                reason="deployment model or its training rows not available")

BASE = dict(batting_team="Mumbai Indians", bowling_team="Chennai Super Kings", venue="Wankhede Stadium", innings=1)


@pytest.fixture(scope="module")
def ranges():
    rows = pd.read_csv(TRAINING_ROWS)
    rows["rr"] = rows.runs / rows.completed_overs
    return rows.groupby("completed_overs").agg(runs_min=("runs", "min"), runs_max=("runs", "max"),
                                               rr_min=("rr", "min"), rr_max=("rr", "max"),
                                               lor_min=("last_over_runs", "min"), lor_max=("last_over_runs", "max"))


def _wicket(**kw):
    body = dict(BASE, **kw)
    return body, client.post("/api/predict/wicket", json=body)


def _assert_probability_unchanged(body, response):
    assert response.status_code == 200, response.text
    assert response.json()["probability"] == predict_wicket.forecast(WICKET_MODEL, **body)["probability"]


def test_training_rows_are_the_deployment_training_set():
    import json
    report = json.loads((ROOT / "reports" / "stage_03" / "session_03" / "stage03_session03_final_results.json").read_text())
    assert len(pd.read_csv(TRAINING_ROWS, usecols=["season"])) == report["wicket"]["final_refit_2008_2026"]


def test_in_range_inputs_have_no_warning(ranges):
    overs = 10
    r = ranges.loc[overs]
    runs = int((r.runs_min + r.runs_max) // 2)
    body, res = _wicket(completed_overs=overs, runs=runs, wickets=3, last_over_runs=int(r.lor_max) // 2, last_over_wickets=0)
    _assert_probability_unchanged(body, res)
    check = res.json()["input_range"]
    assert check["checked"] and check["outside"] == [] and check["warning"] is None


def test_runs_above_observed_range_warn_with_the_range(ranges):
    overs = 2
    r = ranges.loc[overs]
    runs = int(r.runs_max) + 5  # still below the impossibility limit 36 x 2 + 30
    body, res = _wicket(completed_overs=overs, runs=runs, wickets=0, last_over_runs=20, last_over_wickets=0)
    _assert_probability_unchanged(body, res)
    check = res.json()["input_range"]
    flagged = {o["field"]: o for o in check["outside"]}
    assert set(flagged) == {"runs", "run_rate"}
    assert (flagged["runs"]["observed_min"], flagged["runs"]["observed_max"]) == (r.runs_min, r.runs_max)
    assert flagged["run_rate"]["observed_max"] == round(r.rr_max, 2)
    assert check["warning"] == ("These inputs are outside anything seen in 2008–2026 at this stage of an innings; "
                                "the estimate is an extrapolation.")


def test_runs_below_observed_range_warn(ranges):
    overs = 15
    r = ranges.loc[overs]
    body, res = _wicket(completed_overs=overs, runs=int(r.runs_min) - 1, wickets=9, last_over_runs=0, last_over_wickets=0)
    _assert_probability_unchanged(body, res)
    assert {o["field"] for o in res.json()["input_range"]["outside"]} == {"runs", "run_rate"}


def test_last_over_runs_above_observed_range_warn_alone(ranges):
    overs = 10
    r = ranges.loc[overs]
    body, res = _wicket(completed_overs=overs, runs=int(r.runs_max), wickets=2, last_over_runs=int(r.lor_max) + 3,
                        last_over_wickets=0)
    _assert_probability_unchanged(body, res)
    outside = res.json()["input_range"]["outside"]
    assert [o["field"] for o in outside] == ["last_over_runs"]
    assert (outside[0]["observed_min"], outside[0]["observed_max"]) == (r.lor_min, r.lor_max)


def test_boundaries_of_the_observed_range_do_not_warn(ranges):
    for overs in (1, 6, 19):
        r = ranges.loc[overs]
        _, res = _wicket(completed_overs=overs, runs=int(r.runs_max), wickets=1,
                         last_over_runs=min(int(r.lor_max), int(r.runs_max)), last_over_wickets=0)
        assert res.json()["input_range"]["outside"] == [], overs


@pytest.mark.parametrize("overs", [1, 5, 19])
def test_impossible_runs_are_rejected(overs):
    limit = 36 * overs + 30
    _, res = _wicket(completed_overs=overs, runs=limit + 1, wickets=0, last_over_runs=0, last_over_wickets=0)
    assert res.status_code == 422
    assert [e["loc"][-1] for e in res.json()["detail"]] == ["runs"]
    body, res = _wicket(completed_overs=overs, runs=limit, wickets=0, last_over_runs=0, last_over_wickets=0)
    _assert_probability_unchanged(body, res)
    assert res.json()["input_range"]["warning"] is not None  # possible, but far outside 2008–2026


def test_impossible_last_over_runs_are_rejected():
    _, res = _wicket(completed_overs=10, runs=150, wickets=0, last_over_runs=57, last_over_wickets=0)
    assert res.status_code == 422 and [e["loc"][-1] for e in res.json()["detail"]] == ["last_over_runs"]
    body, res = _wicket(completed_overs=10, runs=150, wickets=0, last_over_runs=56, last_over_wickets=0)
    _assert_probability_unchanged(body, res)


def test_rules_are_published_in_options():
    rules = client.get("/api/predict/options").json()["wicket_rules"]
    assert rules["runs"]["max"] == "36 x completed overs + 30"
    assert "at most 56" in rules["last_over_runs"]


# ------------------------------------------------------------------ batter date and active players

@pytest.fixture(scope="module")
def archive():
    m = pd.read_csv(DATA / "matches.csv")
    squads = pd.read_csv(ROOT / "data" / "derived" / "match_players.csv")
    latest = int(m.season.max())
    return {"end": m.date.max(), "latest": latest,
            "active": set(squads.loc[squads.season == latest, "player_id"].astype(str))}


def _batter(pid, date):
    return client.post("/api/predict/batter", json=dict(player_id=pid, batting_team="Mumbai Indians",
                                                        opponent="Chennai Super Kings", venue="Wankhede Stadium",
                                                        match_date=date))


def _day_after(iso):
    return (date.fromisoformat(iso) + timedelta(days=1)).isoformat()


def _id(name):
    return next(b["player_id"] for b in client.get("/api/predict/options").json()["batters"] if b["name"] == name)


def test_dates_up_to_the_archive_end_are_rejected(archive):
    tendulkar = _id("SR Tendulkar")
    # His last innings was years before the archive end, so the Stage 3 rule alone would accept these dates
    for when in ("2020-01-01", archive["end"]):
        res = _batter(tendulkar, when)
        assert res.status_code == 422
        assert archive["end"] in res.json()["detail"][0]["msg"]
    ok = _batter(tendulkar, _day_after(archive["end"]))
    assert ok.status_code == 200
    assert ok.json()["appeared_in_latest_season"] is False
    assert f"no {archive['latest']} appearance" in ok.json()["return_note"]


def test_active_player_has_no_return_note(archive):
    res = _batter(_id("RG Sharma"), _day_after(archive["end"]))
    assert res.status_code == 200
    assert res.json()["appeared_in_latest_season"] is True and res.json()["return_note"] is None


def test_default_batter_list_is_latest_season_players(archive):
    batters = client.get("/api/predict/options").json()["batters"]
    default = {b["player_id"] for b in batters if b["appeared_in_latest_season"]}
    assert default == {b["player_id"] for b in batters} & archive["active"]
    assert default and default < {b["player_id"] for b in batters}
    assert all(b["last_season"] == archive["latest"] for b in batters if b["appeared_in_latest_season"])
    assert all(b["last_season"] < archive["latest"] for b in batters if not b["appeared_in_latest_season"])
