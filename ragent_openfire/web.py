"""Loopback-only developer UI for testing proposed weapon-stat changes."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import threading
import uuid
from urllib.parse import urlsplit, parse_qs
import mimetypes

from . import gemini_client
from .run_store import save_run, load_runs, atomic_write
from .replay import make_replays

from .reports import proposal_html_report
from .agent import optimize
from .simulation import balance_violations, regression_violations, run_suite, validate_weapons

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / 'web'
RESULTS_ROOT = ROOT / 'results'
STARTER_RUNS_ROOT = ROOT / 'fixtures' / 'starter_runs'
LOCK = threading.Lock()
RUNS = {}
ACTIVE_RUN = None


PROFILES = {
    "openfire": ("fixtures/openfire_weapons_snapshot.json", "configs/openfire_balance_policy.json"),
    "valorant": ("fixtures/valorant_weapons_snapshot.json", "configs/valorant_balance_policy.json"),
}

def load_inputs(weapons_path=None, policy_path=None, profile="openfire"):
    if profile not in PROFILES:
        raise ValueError("Unknown profile")
    source_path = Path(weapons_path) if weapons_path else ROOT / PROFILES[profile][0]
    config_path = Path(policy_path) if policy_path else ROOT / PROFILES[profile][1]
    weapon_document = json.loads(source_path.read_text(encoding='utf-8'))
    policy = json.loads(config_path.read_text(encoding='utf-8'))
    if not isinstance(weapon_document, dict) or not isinstance(policy, dict):
        raise ValueError('Weapon data and policy must be JSON objects')
    weapons = weapon_document.get('weapons')
    validate_weapons(weapons)
    if not isinstance(policy.get('allowed_parameters'), dict):
        raise ValueError('Policy must define allowed_parameters')
    for path, bounds in policy['allowed_parameters'].items():
        if not isinstance(bounds, list) or len(bounds) != 2:
            raise ValueError(f'Invalid bounds for {path}')
        weapon, field = path.split('.', 1)
        if weapon not in weapons or field not in weapons[weapon]:
            raise ValueError(f'Policy parameter is missing from weapon data: {path}')
    return weapon_document, weapons, policy


def apply_proposed_changes(weapons, changes, allowed_parameters):
    if not isinstance(changes, dict) or not changes:
        raise ValueError('Enter at least one proposed stat change')
    updated = deepcopy(weapons)
    for weapon_id, fields in changes.items():
        if not isinstance(fields, dict) or not fields:
            raise ValueError(f'Changes for {weapon_id} must be a non-empty object')
        for field, value in fields.items():
            path = f'{weapon_id}.{field}'
            if path not in allowed_parameters:
                raise ValueError(f'Change is not allowed by policy: {path}')
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f'{path} must be a finite number')
            minimum, maximum = allowed_parameters[path]
            if not minimum <= value <= maximum:
                raise ValueError(f'{path} must be between {minimum} and {maximum}')
            original = weapons[weapon_id][field]
            if isinstance(original, int) and not isinstance(original, bool):
                if int(value) != value:
                    raise ValueError(f'{path} must be a whole number')
                value = int(value)
            updated[weapon_id][field] = value
    validate_weapons(updated)
    return updated


def evaluate_proposal(weapons, policy, changes, matches, progress=None, profile="openfire", seed_offset=0, gemini_enabled=True):
    if isinstance(matches, bool) or not isinstance(matches, int) or not 1 <= matches <= 100:
        raise ValueError('matches must be a whole number from 1 to 100')
    proposed = apply_proposed_changes(weapons, changes, policy['allowed_parameters'])
    log_progress = progress or (lambda _message: None)
    phases = [
        ('Training baseline', weapons, range(seed_offset, seed_offset + matches)),
        ('Training proposal', proposed, range(seed_offset, seed_offset + matches)),
        ('Held-out baseline', weapons, range(seed_offset + 100000, seed_offset + 100000 + matches)),
        ('Held-out proposal', proposed, range(seed_offset + 100000, seed_offset + 100000 + matches)),
    ]
    results = {}
    for phase, config, seeds in phases:
        log_progress(f'{phase}: running seeded matchups')

        def on_case(done, total, row):
            log_progress(f'{phase} {done}/{total}: {row["a"]} vs {row["b"]} · {row["range_m"]}m · {row["strategy"]}')

        results[phase] = run_suite(config, policy, seeds, trace_one=False, progress=on_case)
    training_issues = balance_violations(results['Training proposal'], policy)
    training_regressions = regression_violations(results['Training baseline'], results['Training proposal'], policy)
    heldout_issues = balance_violations(results['Held-out proposal'], policy)
    heldout_regressions = regression_violations(results['Held-out baseline'], results['Held-out proposal'], policy)
    verification = {
        'passed': not training_issues and not training_regressions and not heldout_issues and not heldout_regressions,
        'training': {'violations': training_issues, 'regressions': training_regressions, 'seed_count': matches},
        'held_out': {'violations': heldout_issues, 'regressions': heldout_regressions, 'seed_count': matches},
        'duels_per_phase': results['Held-out proposal']['summary']['duels'],
    }
    recommendation_policy = dict(policy, target_weapons=list(changes))
    log_progress('Agent recommendation: searching bounded stat combinations')
    recommendation = optimize(
        proposed, recommendation_policy,
        progress=log_progress,
        allow_llm=gemini_enabled, original_baseline=weapons, seed_offset=seed_offset,
        suggestion_provider=(lambda w, p, d: gemini_client.suggest(w, p, d, changes, profile)) if gemini_enabled else None,
    )
    relevant_paths = set()
    if recommendation.get('chosen'):
        relevant_paths.update(recommendation['chosen']['changes'])
    for weapon_id, fields in changes.items():
        relevant_paths.update(f'{weapon_id}.{field}' for field in fields)
    final_stats = {}
    for path in sorted(relevant_paths):
        weapon_id, field = path.split('.', 1)
        final_stats.setdefault(weapon_id, {})[field] = recommendation['patched_weapons'][weapon_id][field]
    agent_recommendation = {
        'agent_mode': recommendation['agent_mode'],
        'candidate_accepted': recommendation['candidate_accepted'],
        'search_budget': recommendation['search_budget'],
        'changes': (recommendation.get('chosen') or {}).get('changes', {}),
        'final_stats': final_stats,
        'verification': recommendation['verification'],
        'before': recommendation['before'],
        'after': recommendation['after'],
        'rationale': (recommendation.get('chosen') or {}).get('rationale', ''),
        'candidates': recommendation['candidates'],
        'model': recommendation.get('model_status'),
        'chosen': recommendation.get('chosen'),
    }
    facts = {'baseline': results['Held-out baseline']['summary'], 'proposal': results['Held-out proposal']['summary'],
             'recommendation_baseline': recommendation['before']['summary'],
             'recommendation_proposal': recommendation['proposal_before']['summary'],
             'recommendation': recommendation['after']['summary'],
             'seed_context': {'baseline_and_proposal': 'proposal holdout', 'recommendation_baseline_and_proposal_and_recommendation': 'independent final holdout'}, 'proposal_verification': verification,
             'recommendation_verification': recommendation['verification']}
    if gemini_enabled:
        explanation, explanation_model = gemini_client.explain(facts)
    else:
        explanation, explanation_model = gemini_client.explain_fallback(facts)
    agent_recommendation['explanation'] = explanation
    agent_recommendation['explanation_model'] = explanation_model
    replays = make_replays(weapons, proposed, recommendation['patched_weapons'], policy, seed=seed_offset + 300000)
    return {
        'profile': profile, 'seed_ranges': {'discovery': [seed_offset, seed_offset + int(policy.get('search_seeds', 24)) - 1], 'proposal_holdout': [seed_offset + 100000, seed_offset + 100000 + matches - 1], 'recommendation_holdout': [recommendation['verification']['final_seeds']['start'], recommendation['verification']['final_seeds']['end_exclusive'] - 1]},
        'replays': replays, 'explanation': explanation, 'explanation_model': explanation_model,
        'source': 'developer-proposed stat changes',
        'matches': matches,
        'changes': changes,
        'before': results['Held-out baseline'],
        'after': results['Held-out proposal'],
        'verification': verification,
        'recommendation': agent_recommendation,
    }


def _append_event(run_id, message):
    with LOCK:
        run = RUNS[run_id]
        run['events'].append({'time': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'message': message})
        save_run(RESULTS_ROOT, run)


def _run_worker(run_id, weapons, policy, changes, matches, document, profile, seed_offset, gemini_enabled):
    global ACTIVE_RUN
    try:
        report = evaluate_proposal(weapons, policy, changes, matches, lambda message: _append_event(run_id, message), profile, seed_offset, gemini_enabled)
        report.update({"profile_source": document, "policy": policy, "run_id": run_id})
        json_path = RESULTS_ROOT / f'developer_run_{run_id}.json'
        html_path = RESULTS_ROOT / f'developer_report_{run_id}.html'
        RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
        atomic_write(json_path, json.dumps(report, indent=2, allow_nan=False) + '\n')
        proposal_html_report(report, html_path)
        with LOCK:
            RUNS[run_id].update({'status': 'complete', 'passed': report['verification']['passed'],
                                 'verification': report['verification'], 'summary': report['after']['summary'],
                                 'before': report['before'], 'after': report['after'],
                                 'result': report, 'replays': report['replays'], 'explanation': report['explanation'],
                                 'recommendation': {
                                     **report['recommendation'],
                                     'agent_mode': report['recommendation']['agent_mode'],
                                     'candidate_accepted': report['recommendation']['candidate_accepted'],
                                     'search_budget': report['recommendation']['search_budget'],
                                     'rationale': report['recommendation']['rationale'],
                                     'changes': report['recommendation']['changes'],
                                     'final_stats': report['recommendation']['final_stats'],
                                     'baseline_summary': report['recommendation']['before']['summary'],
                                     'summary': report['recommendation']['after']['summary'],
                                     'verification': report['recommendation']['verification'],
                                 },
                                 'report_path': str(html_path), 'json_path': str(json_path),
                                 'report_url': f'/runs/{run_id}/report', 'json_url': f'/runs/{run_id}/json'})
        _append_event(run_id, f'Run complete · guardrails {"PASSED" if report["verification"]["passed"] else "NEEDS REVIEW"}')
    except Exception as error:
        with LOCK:
            RUNS[run_id].update({'status': 'failed', 'error': f'{type(error).__name__}: {error}'})
        _append_event(run_id, f'Run failed · {type(error).__name__}: {error}')
    finally:
        with LOCK:
            ACTIVE_RUN = None


class DeveloperHandler(BaseHTTPRequestHandler):
    server_version = 'RAGENTDeveloperUI/1.0'

    def _send(self, status, content_type, body):
        data = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def _json(self, status, value):
        self._send(status, 'application/json; charset=utf-8', json.dumps(value, allow_nan=False))

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/':
            self._send(200, 'text/html; charset=utf-8', (WEB_ROOT / 'index.html').read_text(encoding='utf-8'))
            return
        assets = {'/app.css': ('app.css', 'text/css; charset=utf-8'),
                  '/app.js': ('app.js', 'text/javascript; charset=utf-8')}
        if path in assets:
            asset, content_type = assets[path]
            asset_path = WEB_ROOT / asset
            if not asset_path.is_file():
                self._json(503, {'error': 'React app bundle is missing; run npm install and npm run build first'})
                return
            self._send(200, content_type, asset_path.read_bytes())
            return
        if path.startswith('/assets/'):
            try:
                manifest = json.loads((WEB_ROOT / 'assets/manifest.json').read_text(encoding='utf-8'))
                allowed = {entry['path'] for entry in manifest['assets'].values()}
                relative = path.removeprefix('/assets/')
                if relative not in allowed: raise ValueError('Unknown asset')
                asset = (WEB_ROOT / 'assets' / relative).resolve()
                if not asset.is_relative_to((WEB_ROOT / 'assets').resolve()) or not asset.is_file(): raise ValueError('Missing asset')
                self._send(200, mimetypes.guess_type(asset.name)[0] or 'application/octet-stream', asset.read_bytes())
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                self._json(404, {'error': 'Asset unavailable'})
            return
        if path == '/api/content':
            try: self._json(200, json.loads((WEB_ROOT / 'assets/manifest.json').read_text(encoding='utf-8')))
            except (OSError, ValueError): self._json(503, {'error': 'Content manifest unavailable'})
            return
        if path == '/api/runs':
            with LOCK: self._json(200, {'runs': [dict(r) for r in RUNS.values()]})
            return
        if path == '/api/config':
            try:
                profile = parse_qs(urlsplit(self.path).query).get('profile', ['openfire'])[0]
                _document, weapons, policy = load_inputs(self.server.weapons_path, self.server.policy_path, profile)
                self._json(200, {'profile': profile, 'profiles': list(PROFILES), 'source': _document, 'weapons': weapons, 'allowed_parameters': policy['allowed_parameters'],
                                 'ranges': policy.get('ranges', [5, 15, 35]),
                                 'strategies': policy.get('strategies', ['aggressive', 'defensive', 'flanker']),
                                 'default_matches': min(24, int(policy.get('verification_seeds', 24)))})
            except (OSError, ValueError, json.JSONDecodeError) as error:
                self._json(500, {'error': str(error)})
            return
        if path.startswith('/api/runs/'):
            parts = path.removeprefix('/api/runs/').split('/')
            run_id = parts[0]
            with LOCK:
                run = RUNS.get(run_id)
                if run is None:
                    self._json(404, {'error': 'Unknown run'})
                    return
                if len(parts) == 2 and parts[1] == 'replays':
                    if 'replays' not in run: self._json(404, {'error': 'Replays unavailable'})
                    else: self._json(200, run['replays'])
                elif len(parts) == 1: self._json(200, dict(run))
                else: self._json(404, {'error': 'Not found'})
            return
        if path.startswith('/runs/'):
            parts = path.strip('/').split('/')
            if len(parts) == 3 and parts[1] in RUNS:
                with LOCK:
                    run = RUNS[parts[1]]
                    file_path = run.get('report_path' if parts[2] == 'report' else 'json_path' if parts[2] == 'json' else '')
                if file_path:
                    file_path = ROOT / file_path
                if not file_path or not Path(file_path).is_file():
                    self._json(404, {'error': 'Report is not available'})
                    return
                if parts[2] == 'report':
                    self._send(200, 'text/html; charset=utf-8', Path(file_path).read_text(encoding='utf-8'))
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Disposition', 'attachment; filename="developer_run.json"')
                self.end_headers()
                self.wfile.write(Path(file_path).read_bytes())
                return
        self._json(404, {'error': 'Not found'})

    def do_POST(self):
        global ACTIVE_RUN
        if self.path != '/api/runs':
            self._json(404, {'error': 'Not found'})
            return
        length = self.headers.get('Content-Length')
        if not length or not length.isdigit() or int(length) > 16384:
            self._json(400, {'error': 'Request body must be no larger than 16 KB'})
            return
        try:
            payload = json.loads(self.rfile.read(int(length)))
            if not isinstance(payload, dict): raise ValueError('Request body must be a JSON object')
            profile = payload.get('profile', 'openfire')
            if not isinstance(profile, str): raise ValueError('profile must be a string')
            gemini_enabled = payload.get('gemini_enabled', True)
            if not isinstance(gemini_enabled, bool): raise ValueError('gemini_enabled must be a boolean')
            _document, weapons, policy = load_inputs(self.server.weapons_path, self.server.policy_path, profile)
            changes = payload.get('changes')
            matches = payload.get('matches')
            proposed = apply_proposed_changes(weapons, changes, policy['allowed_parameters'])
            if isinstance(matches, bool) or not isinstance(matches, int) or not 1 <= matches <= 100:
                raise ValueError('matches must be a whole number from 1 to 100')
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            self._json(400, {'error': str(error)})
            return
        with LOCK:
            if ACTIVE_RUN is not None:
                self._json(409, {'error': 'A simulation is already running'})
                return
            run_id = uuid.uuid4().hex
            ACTIVE_RUN = run_id
            seed_offset = int(run_id[:8], 16) * 1000000
            RUNS[run_id] = {'id': run_id, 'status': 'running', 'events': [],
                            'changes': changes, 'matches': matches, 'profile': profile, 'seed_offset': seed_offset, 'gemini_enabled': gemini_enabled, 'profile_source': _document, 'policy': policy, 'report_url': None, 'json_url': None}
        _append_event(run_id, f'Accepted {len(changes)} weapon change(s); {matches} seeds per case.')
        thread = threading.Thread(target=_run_worker, args=(run_id, weapons, policy, changes, matches, _document, profile, seed_offset, gemini_enabled), daemon=True)
        thread.start()
        self._json(202, {'id': run_id, 'status': 'running'})

    def log_message(self, fmt, *args):
        print(f'[{self.log_date_time_string()}] {fmt % args}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--weapons', help='Exported weapon JSON; defaults to the included snapshot')
    parser.add_argument('--policy', help='Balance policy JSON; defaults to the included policy')
    args = parser.parse_args()
    load_inputs(args.weapons, args.policy)
    RUNS.update(load_runs(STARTER_RUNS_ROOT))
    RUNS.update(load_runs(RESULTS_ROOT))
    server = ThreadingHTTPServer(('127.0.0.1', args.port), DeveloperHandler)
    server.weapons_path = args.weapons
    server.policy_path = args.policy
    print(f'RAGENT developer UI: http://127.0.0.1:{args.port}')
    print('Bound to localhost only; press Ctrl+C to stop.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopping RAGENT developer UI.')
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
