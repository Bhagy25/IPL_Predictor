"""Prediction endpoints checked against the Stage 3 inference functions and the Stage 3 reports.

Expected probabilities come from calling predict_wicket.forecast() and forecast_future_batter.forecast()
directly with the deployment artifacts; expected evaluation numbers come from the official report JSON
and are recomputed here from the per-example holdout CSVs with sklearn and numpy, not the service.
"""
import hashlib
import json
import shutil
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.metrics import roc_auc_score

from cricketlens import forecast_future_batter, predict_wicket
from cricketlens.api import routes_predict
from cricketlens.api.app import app
from cricketlens.api.services.prediction_service import PredictionService

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
DATA = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "stage_03" / "session_03"
WICKET_MODEL = MODELS / "wicket_deployment_through_2026.joblib"
BATTER_MODEL = MODELS / "batter_deployment_through_2026.joblib"
ARTIFACTS = sorted(MODELS.glob("*.joblib"))

pytestmark = pytest.mark.skipif(not (WICKET_MODEL.is_file() and BATTER_MODEL.is_file()),
                                reason="deployment model artifacts not available")


def _sha(paths):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


# Taken when this module is imported, before any test in the session runs
HASHES_BEFORE = _sha(ARTIFACTS)
OFFICIAL = json.loads((REPORT / "stage03_session03_final_results.json").read_text(encoding="utf-8"))

WICKET_CASES = [
    dict(batting_team="Mumbai Indians", bowling_team="Chennai Super Kings", venue="Wankhede Stadium", innings=1,
         completed_overs=1, runs=6, wickets=0, last_over_runs=6, last_over_wickets=0),
    dict(batting_team="Royal Challengers Bengaluru", bowling_team="Kolkata Knight Riders", venue="Eden Gardens",
         innings=2, completed_overs=10, runs=84, wickets=3, last_over_runs=7, last_over_wickets=1),
    dict(batting_team="Gujarat Titans", bowling_team="Lucknow Super Giants", venue="Narendra Modi Stadium, Ahmedabad",
         innings=1, completed_overs=17, runs=151, wickets=7, last_over_runs=12, last_over_wickets=2),
    dict(batting_team="Punjab Kings", bowling_team="Delhi Capitals", venue="Arun Jaitley Stadium", innings=2,
         completed_overs=19, runs=180, wickets=9, last_over_runs=0, last_over_wickets=0),
    dict(batting_team="Sunrisers Hyderabad", bowling_team="Rajasthan Royals", venue="Sharjah Cricket Stadium",
         innings=1, completed_overs=5, runs=0, wickets=0, last_over_runs=0, last_over_wickets=0),
]
WICKET_DEFAULT = WICKET_CASES[0]


def _eligible_history():
    """Eligible innings per player, computed here: D/L-marked and no-result matches dropped."""
    bats = pd.read_csv(DATA / "batter_innings.csv", dtype={"batter_id": str})
    m = pd.read_csv(DATA / "matches.csv")[["match_id", "outcome_method", "outcome_type"]]
    h = bats.merge(m, on="match_id")
    dls = h.outcome_method.fillna("").str.strip().str.upper().isin(["D/L", "DLS", "D/L METHOD", "DLS METHOD"])
    nr = h.outcome_type.fillna("").str.lower().str.contains("no result", regex=False)
    return h[~dls & ~nr]


@pytest.fixture(scope="module")
def history():
    return _eligible_history()


@pytest.fixture(scope="module")
def batter_cases(history):
    """Kohli, Rohit Sharma, Bumrah (a bowler with few innings), a retired player and a 2026 debutant."""
    first = history.groupby("batter_id").date.min()
    debutant = sorted(first[first >= "2026-01-01"].index)[0]
    by_name = lambda name: history[history.batter == name].batter_id.iloc[0]  # noqa: E731
    return [
        (by_name("V Kohli"), "Royal Challengers Bengaluru", "Mumbai Indians", "M Chinnaswamy Stadium"),
        (by_name("RG Sharma"), "Mumbai Indians", "Chennai Super Kings", "Wankhede Stadium"),
        (by_name("JJ Bumrah"), "Mumbai Indians", "Gujarat Titans", "Narendra Modi Stadium, Ahmedabad"),
        (by_name("SR Tendulkar"), "Mumbai Indians", "Rajasthan Royals", "Sawai Mansingh Stadium"),
        (debutant, "Sunrisers Hyderabad", "Punjab Kings", "Rajiv Gandhi International Stadium, Uppal"),
    ]


def _batter_body(case, date="2027-04-10"):
    pid, team, opp, venue = case
    return dict(player_id=pid, batting_team=team, opponent=opp, venue=venue, match_date=date)


def _direct_batter(body):
    return forecast_future_batter.forecast(
        model_path=BATTER_MODEL, batters_path=DATA / "batter_innings.csv", matches_path=DATA / "matches.csv",
        batter_id=body["player_id"], opponent=body["opponent"], venue=body["venue"],
        batting_team=body["batting_team"], match_date=body["match_date"])


# ------------------------------------------------------------------ predictions equal the Stage 3 functions

@pytest.mark.parametrize("case", WICKET_CASES, ids=["over1", "middle", "death-7down", "over19-9down", "zero"])
def test_wicket_endpoint_equals_stage3_forecast(case):
    r = client.post("/api/predict/wicket", json=case)
    assert r.status_code == 200, r.text
    got = r.json()
    expected = predict_wicket.forecast(WICKET_MODEL, **case)
    for key in ("probability", "event", "model", "training_end", "status"):
        assert got[key] == expected[key], key
    # One decimal with halves rounded up: 0.2045 -> 20.5
    pct = (Decimal(str(expected["probability"])) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    assert got["probability_pct"] == float(pct)
    assert got["inputs"] == case
    assert got["version"] == "deployment_refit_2008_2026" and got["training_span"] == "2008–2026"
    assert "not live" in got["notice"]


def test_wicket_teams_are_not_swapped():
    """Swapping the two teams changes the inputs the function sees, so the service must pass them through as named."""
    case = WICKET_CASES[1]
    swapped = dict(case, batting_team=case["bowling_team"], bowling_team=case["batting_team"])
    a, b = (client.post("/api/predict/wicket", json=c).json()["probability"] for c in (case, swapped))
    assert a == predict_wicket.forecast(WICKET_MODEL, **case)["probability"]
    assert b == predict_wicket.forecast(WICKET_MODEL, **swapped)["probability"]
    assert a != b


def test_batter_endpoint_equals_stage3_forecast(batter_cases, history):
    for case in batter_cases:
        body = _batter_body(case)
        r = client.post("/api/predict/batter", json=body)
        assert r.status_code == 200, r.text
        got, expected = r.json(), _direct_batter(body)
        for key in ("chance_30_plus", "chance_50_plus", "prior_eligible_innings", "player_id", "date", "version",
                    "model_train_end"):
            assert got[key] == expected[key], (case, key)
        assert got["chance_50_plus"] <= got["chance_30_plus"]
        rows = history[history.batter_id == case[0]].sort_values(["date", "match_id", "innings"])
        assert got["prior_eligible_innings"] == len(rows)
        assert got["form_context"]["latest_innings_date"] == rows.date.iloc[-1]
        assert [i["runs"] for i in got["form_context"]["recent_innings"]] == rows.runs.iloc[::-1].head(5).tolist()
        assert "playing XI" in got["scope"]


def test_debutant_has_only_2026_history(batter_cases, history):
    pid = batter_cases[-1][0]
    assert history[history.batter_id == pid].date.min() >= "2026-01-01"
    bumrah = history[history.batter_id == batter_cases[2][0]]
    assert len(bumrah) < len(history[history.batter_id == batter_cases[0][0]]) / 3


def test_p50_never_exceeds_p30(history):
    ids = history.groupby("batter_id").size().sort_values()
    sample = list(ids.index[:: max(1, len(ids) // 20)])
    for pid in sample:
        body = dict(player_id=pid, batting_team="Chennai Super Kings", opponent="Mumbai Indians",
                    venue="Wankhede Stadium", match_date="2027-04-10")
        got = client.post("/api/predict/batter", json=body).json()
        assert got["chance_50_plus"] <= got["chance_30_plus"], pid
    holdout = pd.read_csv(REPORT / "batter" / "batter_holdout_forecasts_2026.csv")
    assert (holdout.probability_50_plus <= holdout.probability_30_plus).all()


# ------------------------------------------------------------------ validation

def _fields(response):
    assert response.status_code == 422, response.text
    return {e["loc"][-1] for e in response.json()["detail"]}


@pytest.mark.parametrize("change, field", [
    ({"completed_overs": 0}, "completed_overs"),
    ({"completed_overs": 20}, "completed_overs"),
    ({"wickets": 10}, "wickets"),
    ({"runs": 20, "last_over_runs": 21}, "last_over_runs"),
    ({"wickets": 1, "last_over_wickets": 2}, "last_over_wickets"),
    ({"bowling_team": "Mumbai Indians"}, "bowling_team"),
    ({"venue": "Lord's"}, "venue"),
    ({"batting_team": "Deccan Chargers"}, "batting_team"),
    ({"bowling_team": "Mumbai Indianz"}, "bowling_team"),
    ({"innings": 3}, "innings"),
    ({"runs": -1}, "runs"),
])
def test_wicket_validation(change, field):
    assert field in _fields(client.post("/api/predict/wicket", json=dict(WICKET_DEFAULT, **change)))


def test_wicket_validation_matches_stage3_rules():
    """Every numeric input the API rejects is also rejected by predict_wicket.forecast() itself."""
    for change in ({"completed_overs": 0}, {"completed_overs": 20}, {"wickets": 10},
                   {"runs": 20, "last_over_runs": 21}, {"innings": 3}, {"bowling_team": "Mumbai Indians"}):
        with pytest.raises(ValueError):
            predict_wicket.forecast(WICKET_MODEL, **dict(WICKET_DEFAULT, **change))


@pytest.mark.parametrize("change, field", [
    ({"match_date": "2020-04-01"}, "match_date"),
    ({"match_date": "2026-05-31"}, "match_date"),
    ({"match_date": "31/05/2027"}, "match_date"),
    ({"player_id": "00000000"}, "player_id"),
    ({"opponent": "Royal Challengers Bengaluru"}, "opponent"),
    ({"venue": "Lord's"}, "venue"),
    ({"batting_team": "Gujarat Lions"}, "batting_team"),
])
def test_batter_validation(batter_cases, change, field):
    assert field in _fields(client.post("/api/predict/batter", json=dict(_batter_body(batter_cases[0]), **change)))


def test_batter_date_rule_matches_stage3(batter_cases, history):
    """The latest eligible innings date itself is rejected by both; the next day is accepted by both."""
    case = batter_cases[0]
    latest = history[history.batter_id == case[0]].date.max()
    with pytest.raises(ValueError):
        _direct_batter(_batter_body(case, latest))
    assert client.post("/api/predict/batter", json=_batter_body(case, latest)).status_code == 422
    next_day = (date.fromisoformat(latest) + timedelta(days=1)).isoformat()
    assert client.post("/api/predict/batter", json=_batter_body(case, next_day)).status_code == 200


def test_missing_and_mistyped_fields_are_422():
    assert client.post("/api/predict/wicket", json={}).status_code == 422
    assert client.post("/api/predict/wicket", json=dict(WICKET_DEFAULT, runs="lots")).status_code == 422
    assert client.post("/api/predict/batter", json={"player_id": "x"}).status_code == 422


# ------------------------------------------------------------------ options

def test_options_match_model_categories(history):
    o = client.get("/api/predict/options").json()
    saved = joblib.load(WICKET_MODEL)
    enc = saved["model"].named_steps["features"].named_transformers_["categories"]
    cats = dict(zip(["batting_team", "bowling_team", "phase", "venue_canonical"], enc.categories_))
    assert len(o["teams"]) == 10
    assert {t["name"] for t in o["teams"]} <= set(cats["batting_team"])
    assert {v["name"] for v in o["venues"]} == set(cats["venue_canonical"])
    matches = pd.read_csv(DATA / "matches.csv")
    assert sum(v["matches"] for v in o["venues"]) == len(matches)
    assert {v["name"] for v in o["venues"] if v["used_in_latest_season"]} == set(
        matches[matches.season == matches.season.max()].venue_canonical)
    assert {b["player_id"] for b in o["batters"]} == set(history.batter_id)
    latest = history.groupby("batter_id").date.max()
    assert all(b["latest_innings_date"] == latest[b["player_id"]] for b in o["batters"])
    assert o["wicket_rules"]["completed_overs"] == {"min": 1, "max": 19}


# ------------------------------------------------------------------ metadata and holdout replay

def test_models_metadata_equals_report():
    m = client.get("/api/predict/models").json()
    assert "not the deployment" in m["holdout_statement"] or "never the deployment" in m["holdout_statement"]
    for item in m["models"]:
        section = OFFICIAL[item["kind"]]
        assert item["selected_name"] == section["selected_name_from_2025_only"] == item["name"]
        for api_key, json_key in (("holdout_2026", "holdout_2026"), ("holdout_2026_constant", "holdout_constant"),
                                  ("validation_2025_constant", "constant_validation_2025")):
            assert item[api_key] == section[json_key]
        assert item["validation_2025"] == section["candidate_validation_2025"]
        assert item["rows"]["test_2026_rows"] == section["test_2026_rows"]
        assert item["rows"]["final_refit_2008_2026"] == section["final_refit_2008_2026"]
        assert item["features"] == section["selected_features"]
        assert item["training_end"] == 2026 and item["available"]


def _calibration(y, p, bins):
    df = pd.DataFrame({"y": y, "p": p})
    df["bin"] = np.minimum((df.p * bins).astype(int), bins - 1)
    return df.groupby("bin").agg(n=("y", "size"), pred=("p", "mean"), obs=("y", "mean")).reset_index()


def test_replay_summary_recomputed_from_csv_equals_official():
    r = client.get("/api/predict/holdout-replay").json()
    assert r["label"] == "2026 holdout replay — model trained through 2025"
    w = pd.read_csv(REPORT / "wicket" / "wicket_holdout_forecasts_2026.csv")
    y, p = w.wicket_next_over.to_numpy(), np.clip(w.predicted_wicket_probability.to_numpy(), 1e-6, 1 - 1e-6)
    official = OFFICIAL["wicket"]["holdout_2026"]
    mine = {"rows": len(w), "event_rate": y.mean(), "brier_score": np.mean((p - y) ** 2),
            "log_loss": -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)), "roc_auc": roc_auc_score(y, p)}
    for k, v in mine.items():
        assert v == pytest.approx(official[k], abs=1e-6), k
        assert r["wicket"]["computed"][k] == pytest.approx(official[k], abs=1e-6), k
    assert r["wicket"]["check"]["matches_official"] and r["wicket"]["check"]["mismatched"] == []

    b = pd.read_csv(REPORT / "batter" / "batter_holdout_forecasts_2026.csv")
    p30, p50, cls = b.probability_30_plus.to_numpy(), b.probability_50_plus.to_numpy(), b.milestone_class.to_numpy()
    probs = np.clip(np.column_stack([1 - p30, p30 - p50, p50]), 1e-8, 1)
    probs = probs / probs.sum(axis=1, keepdims=True)
    official = OFFICIAL["batter"]["holdout_2026"]
    mine = {"rows": len(b), "observed_30_rate": (cls >= 1).mean(), "observed_50_rate": (cls == 2).mean(),
            "brier_30": np.mean((p30 - (cls >= 1)) ** 2), "brier_50": np.mean((p50 - (cls == 2)) ** 2),
            "multiclass_log_loss": -np.mean(np.log(probs[np.arange(len(cls)), cls])),
            "roc_auc_30": roc_auc_score(cls >= 1, p30), "roc_auc_50": roc_auc_score(cls == 2, p50)}
    mine["avg_milestone_brier"] = (mine["brier_30"] + mine["brier_50"]) / 2
    for k, v in mine.items():
        assert v == pytest.approx(official[k], abs=1e-6), k
        assert r["batter"]["computed"][k] == pytest.approx(official[k], abs=1e-6), k
    assert r["batter"]["check"]["matches_official"]

    # Calibration bins equal the saved Stage 3 calibration tables and an independent binning
    saved_w = pd.read_csv(REPORT / "wicket" / "wicket_holdout_calibration_2026.csv")
    api_w = r["wicket"]["computed"]["calibration"]
    assert [c["bin"] for c in api_w] == saved_w.bin.tolist() and [c["n"] for c in api_w] == saved_w.n.tolist()
    assert np.allclose([c["observed_rate"] for c in api_w], saved_w.observed_frequency, atol=1e-12)
    mine_w = _calibration(w.wicket_next_over, w.predicted_wicket_probability, 10)
    assert mine_w.n.tolist() == saved_w.n.tolist()
    saved_b = pd.read_csv(REPORT / "batter" / "batter_holdout_calibration_2026.csv")
    api_b = r["batter"]["computed"]["calibration"]
    assert [(c["milestone"], c["bin"], c["n"]) for c in api_b] == list(zip(saved_b.milestone, saved_b.bin, saved_b.n))
    assert np.allclose([c["avg_predicted"] for c in api_b], saved_b.predicted, atol=1e-12)


def test_replay_matches_and_rows_equal_csv():
    r = client.get("/api/predict/holdout-replay").json()
    # round_trip: compare the exact probabilities written by Stage 3
    w = pd.read_csv(REPORT / "wicket" / "wicket_holdout_forecasts_2026.csv", float_precision="round_trip")
    b = pd.read_csv(REPORT / "batter" / "batter_holdout_forecasts_2026.csv", dtype={"batter_id": str},
                    float_precision="round_trip")
    ids = [m["match_id"] for m in r["matches"]]
    assert set(ids) == set(w.match_id) | set(b.match_id)
    assert len(set(w.match_id)) == OFFICIAL["wicket"]["test_2026_matches"]
    assert len(set(b.match_id)) == OFFICIAL["batter"]["test_2026_matches"]
    assert sum(m["wicket_checkpoints"] for m in r["matches"]) == len(w)
    assert sum(m["batter_forecasts"] for m in r["matches"]) == len(b)
    innings = pd.read_csv(DATA / "innings.csv")
    for mid in (ids[0], ids[len(ids) // 2], ids[-1]):
        d = client.get(f"/api/predict/holdout-replay/{mid}").json()
        rows_w, rows_b = w[w.match_id == mid], b[b.match_id == mid]
        assert len(d["wickets"]) == len(rows_w) and len(d["batters"]) == len(rows_b)
        assert sorted(x["predicted_probability"] for x in d["wickets"]) == sorted(rows_w.predicted_wicket_probability)
        assert sum(x["wicket_fell"] for x in d["wickets"]) == rows_w.wicket_next_over.sum()
        assert [x["actual_runs"] for x in d["batters"]] == rows_b.actual_runs.tolist()
        assert [x["probability_30_plus"] for x in d["batters"]] == rows_b.probability_30_plus.tolist()
        teams = innings[innings.match_id == mid].set_index("innings").batting_team
        assert all(x["batting_team"] == teams[x["innings"]] for x in d["wickets"] + d["batters"])
    assert client.get("/api/predict/holdout-replay/1").status_code == 404


# ------------------------------------------------------------------ unavailable artifacts

@pytest.fixture
def broken_models(tmp_path, monkeypatch):
    """A service whose model folder has the batter deployment model only with a wrong version, and no wicket model."""
    saved = joblib.load(BATTER_MODEL)
    joblib.dump(dict(saved, version="holdout_eval_pre2026"), tmp_path / BATTER_MODEL.name)
    service = PredictionService(model_dir=tmp_path)
    monkeypatch.setattr("cricketlens.api.services.prediction_service.prediction_service", service)
    return service


def test_missing_or_invalid_artifact_returns_503(broken_models, batter_cases):
    r = client.post("/api/predict/wicket", json=WICKET_DEFAULT)
    assert r.status_code == 503 and "unavailable" in r.json()["detail"]
    r = client.post("/api/predict/batter", json=_batter_body(batter_cases[0]))
    assert r.status_code == 503 and "deployment_refit_2008_2026" in r.json()["detail"]
    assert client.get("/api/predict/options").status_code == 503
    health = client.get("/api/health").json()
    assert health["status"] == "degraded"
    assert health["prediction_models"]["wicket"]["available"] is False
    assert health["prediction_models"]["batter"]["available"] is False
    models = client.get("/api/predict/models").json()
    assert [m["available"] for m in models["models"]] == [False, False]


def test_artifact_deleted_after_startup_returns_503(tmp_path, monkeypatch):
    shutil.copy(WICKET_MODEL, tmp_path / WICKET_MODEL.name)
    service = PredictionService(model_dir=tmp_path)
    service.ensure_loaded()
    (tmp_path / WICKET_MODEL.name).unlink()
    monkeypatch.setattr("cricketlens.api.services.prediction_service.prediction_service", service)
    assert client.post("/api/predict/wicket", json=WICKET_DEFAULT).status_code == 503


def test_health_reports_models_available():
    health = client.get("/api/health").json()
    assert all(m["available"] for m in health["prediction_models"].values())
    assert routes_predict.router.prefix == "/api/predict"


# ------------------------------------------------------------------ the models are never modified

def test_zz_model_files_unchanged():
    assert len(ARTIFACTS) == 4
    assert _sha(ARTIFACTS) == HASHES_BEFORE
