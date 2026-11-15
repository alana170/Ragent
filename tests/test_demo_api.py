import json
from pathlib import Path
import threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from unittest.mock import patch

from ragent_openfire import gemini_client, web


def test_bundled_demo_is_ready_for_the_saved_runs_menu():
    run = web.load_demo_run()
    assert run["is_demo"] is True
    assert run["label"] == "Spectre damage tuning"
    assert run["status"] == "complete"
    assert run["profile"] == "valorant"
    assert run["report_url"].endswith("/report")
    assert run["json_url"].endswith("/json")
    assert Path(run["report_path"]).is_file()
    assert json.loads(Path(run["json_path"]).read_text(encoding="utf-8"))["profile"] == "valorant"


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


def test_explanation_rejects_unverified_or_invented_numeric_claims(monkeypatch):
    facts = {'recommendation_verification': {'passed': False}}
    for summary in ('The recommendation passed.', 'The win rate is 99 percent.'):
        response = {'summary': summary, 'tradeoffs': 'Review tradeoffs.',
                    'limitations': 'Simulation only.', 'evidence_ids': ['recommendation_verification']}
        monkeypatch.setattr(gemini_client, '_call', lambda *args: (response, {'status': 'live'}))
        explanation, metadata = gemini_client.explain(facts)
        assert metadata['status'] == 'fallback'
        assert explanation['facts'] == facts


def test_valorant_editable_stats_are_bounded_and_search_covers_both_weapons():
    from ragent_openfire.agent import _heuristic_candidates
    _, weapons, policy = web.load_inputs(profile="valorant")
    fields = {"damage", "fire_rate", "mag_size", "reload_time"}
    assert set(policy["allowed_parameters"]) == {f"{weapon}.{field}" for weapon in ("vandal", "spectre") for field in fields}
    changed = web.apply_proposed_changes(weapons, {"vandal": {"damage": 41}, "spectre": {"mag_size": 31}}, policy["allowed_parameters"])
    assert changed["vandal"]["damage"] == 41 and changed["spectre"]["mag_size"] == 31
    candidates = _heuristic_candidates(changed, dict(policy, target_weapons=["vandal", "spectre"]))[:23]
    assert {next(iter(c["changes"])).split(".")[0] for c in candidates} == {"vandal", "spectre"}
    assert {next(iter(c["changes"])).split(".")[1] for c in candidates} == fields


def test_starter_runs_have_working_reports_and_downloads(monkeypatch):
    runs = web.load_runs(web.STARTER_RUNS_ROOT)
    assert len(runs) == 3
    assert all(run['status'] == 'complete' and run['profile'] == 'valorant' for run in runs.values())
    monkeypatch.setattr(web, 'RUNS', runs)
    server = ThreadingHTTPServer(('127.0.0.1', 0), web.DeveloperHandler)
    server.weapons_path = server.policy_path = None
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = 'http://127.0.0.1:%s' % server.server_port
        with urlopen(base + '/api/runs') as response:
            assert len(json.load(response)['runs']) == 3
        for run_id in runs:
            with urlopen(base + '/runs/' + run_id + '/report') as response:
                assert response.status == 200 and b'<html' in response.read().lower()
            with urlopen(base + '/runs/' + run_id + '/json') as response:
                assert json.load(response)['run_id'] == run_id
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
