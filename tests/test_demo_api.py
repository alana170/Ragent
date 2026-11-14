import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from unittest.mock import patch

from ragent_openfire import gemini_client, web


def test_gemini_fallback_and_invalid_evidence(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(gemini_client, "load_environment", lambda: None)
    result, meta = gemini_client.explain({"baseline": {"value": 1}})
    assert meta["status"] == "fallback"
    assert result["facts"]["baseline"]["value"] == 1
    monkeypatch.setattr(gemini_client, "_call", lambda *args: ({"summary": "x", "tradeoffs": "x", "limitations": "x", "evidence_ids": ["invented"]}, {"status": "live"}))
    result, meta = gemini_client.explain({"baseline": {}})
    assert meta["status"] == "fallback"
    assert result["evidence_ids"] == ["baseline"]


def test_http_profile_assets_invalid_request_and_saved_run(tmp_path, monkeypatch):
    monkeypatch.setattr(web, "RESULTS_ROOT", tmp_path)
    monkeypatch.setattr(web, "RUNS", {})
    server = ThreadingHTTPServer(("127.0.0.1", 0), web.DeveloperHandler)
    server.weapons_path = server.policy_path = None
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = "http://127.0.0.1:%s" % server.server_port
    try:
        with urlopen(base + "/api/config?profile=valorant") as response:
            assert "vandal" in json.load(response)["weapons"]
        with urlopen(base + "/assets/vandal.png") as response:
            assert response.headers["Content-Type"] == "image/png"
        try: urlopen(base + "/assets/../index.html")
        except HTTPError as exc: assert exc.code == 404
        else: assert False
        request = Request(base + "/api/runs", data=b"[]", headers={"Content-Type": "application/json"})
        try: urlopen(request)
        except HTTPError as exc: assert exc.code == 400
        else: assert False
        run = {"id": "a" * 32, "status": "complete", "events": [], "replays": {"traces": {}}}
        web.save_run(tmp_path, run)
        web.RUNS.update(web.load_runs(tmp_path))
        with urlopen(base + "/api/runs/" + run["id"] + "/replays") as response:
            assert json.load(response) == run["replays"]
    finally:
        server.shutdown(); thread.join(); server.server_close()


def test_environment_loads_only_key_with_checkout_precedence(tmp_path, monkeypatch):
    local = tmp_path / 'worktree.env'
    primary = tmp_path / 'primary.env'
    local.write_text('OTHER_SETTING=ignored\n', encoding='utf-8')
    primary.write_text('GEMINI_API_KEY=primary-test-key\nOTHER_SETTING=ignored\n', encoding='utf-8')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('OTHER_SETTING', raising=False)
    monkeypatch.setattr(gemini_client, '_environment_paths', lambda: [local, primary])
    gemini_client.load_environment()
    import os
    assert os.environ['GEMINI_API_KEY'] == 'primary-test-key'
    assert 'OTHER_SETTING' not in os.environ
    monkeypatch.setenv('GEMINI_API_KEY', 'environment-test-key')
    local.write_text('GEMINI_API_KEY=local-test-key\n', encoding='utf-8')
    gemini_client.load_environment()
    assert os.environ['GEMINI_API_KEY'] == 'environment-test-key'
    monkeypatch.delenv('GEMINI_API_KEY')
    gemini_client.load_environment()
    assert os.environ['GEMINI_API_KEY'] == 'local-test-key'
