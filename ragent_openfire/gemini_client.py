"""Bounded Gemini calls. Credentials stay in the server process."""
from __future__ import annotations
import json
import os
import time

MODEL = 'gemini-3.5-flash-lite'
TIMEOUT_MS = 15000
MAX_OUTPUT_TOKENS = 1024


def load_environment():
    try:
        from dotenv import load_dotenv
        load_dotenv(override=False)
    except ImportError:
        pass


def _call(purpose, payload, schema):
    meta = {'purpose': purpose, 'model': MODEL, 'timeout_ms': TIMEOUT_MS,
            'max_output_tokens': MAX_OUTPUT_TOKENS, 'retries': 0, 'status': 'fallback'}
    load_environment()
    if not os.getenv('GEMINI_API_KEY'):
        meta['reason'] = 'missing_credentials'
        return None, meta
    started = time.monotonic()
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=os.environ['GEMINI_API_KEY'], http_options={'timeout': TIMEOUT_MS, 'retry_options': {'attempts': 1}})
        response = client.models.generate_content(model=MODEL, contents=json.dumps(payload, allow_nan=False),
            config=types.GenerateContentConfig(response_mime_type='application/json', response_schema=schema,
                                               max_output_tokens=MAX_OUTPUT_TOKENS, temperature=0))
        value = json.loads(response.text)
        meta['status'] = 'live'
        return value, meta
    except Exception as exc:
        # Exception messages may contain URLs, request details or credentials.
        meta['reason'] = type(exc).__name__
        code = getattr(exc, 'code', None)
        if isinstance(code, int): meta['http_status'] = code
        return None, meta
    finally:
        meta['latency_ms'] = round((time.monotonic() - started) * 1000)


def suggest(weapons, policy, discovery, changes=None, profile=None):
    schema = {'type': 'OBJECT', 'properties': {'candidates': {'type': 'ARRAY', 'items': {
        'type': 'OBJECT', 'properties': {'edits': {'type': 'ARRAY', 'items': {'type': 'OBJECT',
        'properties': {'path': {'type': 'STRING'}, 'value': {'type': 'NUMBER'}}, 'required': ['path', 'value']}},
        'rationale': {'type': 'STRING'}}, 'required': ['edits', 'rationale']}}}, 'required': ['candidates']}
    payload = {'task': 'Suggest up to four small stat patches for code to validate and simulate. Use only allowed paths and bounds.',
               'profile': profile, 'submitted_changes': changes, 'weapons': weapons,
               'allowed_parameters': policy['allowed_parameters'], 'discovery': discovery}
    result, meta = _call('candidates', payload, schema)
    candidates = []
    try:
        if result is not None:
            raw = result['candidates']
            if not isinstance(raw, list): raise ValueError('invalid candidates')
            for item in raw[:4]:
                edits = item['edits']
                if not isinstance(edits, list) or not edits: raise ValueError('invalid edits')
                patch = {edit['path']: edit['value'] for edit in edits}
                if len(patch) != len(edits): raise ValueError('duplicate paths')
                candidates.append({'changes': patch, 'rationale': str(item['rationale'])[:500], 'source': 'gemini'})
    except (KeyError, TypeError, ValueError):
        candidates = []
        meta.update(status='fallback', reason='malformed_response')
    return candidates, meta


def explain(facts):
    schema = {'type': 'OBJECT', 'properties': {'summary': {'type': 'STRING'}, 'tradeoffs': {'type': 'STRING'},
              'limitations': {'type': 'STRING'}, 'evidence_ids': {'type': 'ARRAY', 'items': {'type': 'STRING'}}},
              'required': ['summary', 'tradeoffs', 'limitations', 'evidence_ids']}
    payload = {'task': 'Explain the code-determined verdict in plain text. Do not invent numbers or override the verdict. Cite evidence IDs.', 'facts': facts}
    value, meta = _call('explanation', payload, schema)
    try:
        if value is not None:
            ids = value['evidence_ids']
            if not isinstance(ids, list) or not ids or any(i not in facts for i in ids): raise ValueError('invalid evidence IDs')
            if any(not isinstance(value[k], str) or len(value[k]) > 1500 for k in ('summary','tradeoffs','limitations')): raise ValueError('invalid text')
            result = {k: value[k] for k in ('summary','tradeoffs','limitations','evidence_ids')}
            meta['validated_response'] = result
            return dict(result, facts=facts), meta
    except (KeyError, TypeError, ValueError):
        meta.update(status='fallback', reason='malformed_response')
    return {'summary': 'Review the code-determined verification result before playtesting.',
            'tradeoffs': 'Compare the proposal and final recommendation against the original baseline.',
            'limitations': 'Seeded weapon duels are an approximation, not live gameplay.',
            'evidence_ids': list(facts), 'facts': facts}, meta


def explain_fallback(facts):
    return ({'summary': 'Review the code-determined verification result before playtesting.',
             'tradeoffs': 'Compare the proposal and final recommendation against the original baseline.',
             'limitations': 'Seeded weapon duels are an approximation, not live gameplay.',
             'evidence_ids': list(facts), 'facts': facts},
            {'purpose': 'explanation', 'status': 'fallback', 'reason': 'disabled', 'model': MODEL})
