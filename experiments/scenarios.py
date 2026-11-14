"""Scenario input helpers."""
import json


def load_scenarios(path):
    with open(path, encoding='utf-8') as source:
        scenarios = json.load(source)
    if not isinstance(scenarios, list) or any(not isinstance(s, dict) or 'id' not in s for s in scenarios):
        raise ValueError('scenarios must be a list of objects with an id')
    if len({s['id'] for s in scenarios}) != len(scenarios):
        raise ValueError('scenario ids must be unique')
    return scenarios
