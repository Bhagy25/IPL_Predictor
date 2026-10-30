"""Cross-origin access: the local dev server by default, CORS_ALLOW_ORIGINS otherwise, never credentials."""
import json
import os
import subprocess
import sys

from fastapi.testclient import TestClient

from cricketlens.api.app import app
from cricketlens.api.settings import cors_allow_origins

client = TestClient(app)
DEV = "http://localhost:5173"


def test_origins_parsed_from_the_environment_value():
    assert cors_allow_origins(" https://a.example , https://b.example/ ,,") == ["https://a.example", "https://b.example"]
    assert cors_allow_origins("") == []


def test_default_origins_are_the_local_dev_server(monkeypatch):
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    assert cors_allow_origins() == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_dev_server_origin_is_allowed_without_credentials():
    res = client.get("/openapi.json", headers={"Origin": DEV})
    assert res.headers.get("access-control-allow-origin") == DEV
    assert "access-control-allow-credentials" not in res.headers


def test_other_origins_are_not_allowed():
    res = client.get("/openapi.json", headers={"Origin": "https://elsewhere.example"})
    assert "access-control-allow-origin" not in res.headers


def test_preflight_allows_get_and_post_only():
    def preflight(method):
        return client.options("/api/predict/wicket", headers={
            "Origin": DEV, "Access-Control-Request-Method": method, "Access-Control-Request-Headers": "content-type"})
    ok = preflight("POST")
    assert ok.status_code == 200
    assert set(ok.headers["access-control-allow-methods"].split(", ")) == {"GET", "POST"}
    assert preflight("DELETE").status_code == 400


def test_environment_origins_replace_the_default():
    code = ("import json; from fastapi.testclient import TestClient; from cricketlens.api.app import app; c = TestClient(app); "
            "print(json.dumps([c.get('/openapi.json', headers={'Origin': o}).headers.get('access-control-allow-origin') "
            "for o in ('https://site.example', 'http://localhost:5173')]))")
    env = dict(os.environ, CORS_ALLOW_ORIGINS="https://site.example")
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    assert json.loads(out.stdout.strip().splitlines()[-1]) == ["https://site.example", None]
