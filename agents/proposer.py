"""Structured proposals; provider output is data only and is never executed."""
import json
import os
import urllib.request
from .schemas import PatchProposal


class MockProposer:
    def propose(self, config, goal, feedback, iteration):
        proposals = []

        def visit(node, prefix=''):
            for key, val in node.items():
                path = f'{prefix}.{key}' if prefix else key
                if isinstance(val, dict):
                    visit(val, path)
                elif (
                    isinstance(val, (int, float))
                    and not isinstance(val, bool)
                    and path in goal.constraints.get('bounds', {})
                    and (goal.constraints.get('allowed_paths') is None or path in goal.constraints['allowed_paths'])
                ):
                    for factor in (0.95, 1.05):
                        value = val * factor
                        if isinstance(val, int):
                            value = round(value)
                        proposals.append(PatchProposal(name=f'{path} {factor:g} round {iteration+1}', changes=[{'path': path, 'value': value}], rationale='Test a modest change to this parameter.', predicted_tradeoffs='May change effectiveness in other scenarios.'))

        visit(config)
        if proposals:
            offset = (iteration * 2) % len(proposals)
            proposals = (proposals[offset:] + proposals[:offset])[:2]
        return proposals


class OpenAIProposer:
    def __init__(self, key, model):
        self.key, self.model = key, model

    def propose(self, config, goal, feedback, iteration):
        prompt = {'goal': goal.model_dump(), 'config': config, 'feedback': feedback, 'iteration': iteration, 'instruction': 'Return JSON object with proposals array of 2-4 objects: name, changes [{path, value}], rationale, predicted_tradeoffs. Paths are dot-separated existing config keys. Use constraints. Propose hypotheses based on feedback.'}
        body = json.dumps({'model': self.model, 'response_format': {'type': 'json_object'}, 'messages': [{'role': 'system', 'content': 'You propose safe game balance experiments. Output JSON only.'}, {'role': 'user', 'content': json.dumps(prompt)}]}).encode()
        req = urllib.request.Request('https://api.openai.com/v1/chat/completions', data=body, headers={'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.load(response)
        proposals = json.loads(data['choices'][0]['message']['content'])['proposals']
        if not 2 <= len(proposals) <= 4:
            raise ValueError('provider must return 2–4 proposals')
        return [PatchProposal.model_validate(p) for p in proposals]


def provider():
    key = os.getenv('OPENAI_API_KEY')
    return OpenAIProposer(key, os.getenv('OPENAI_MODEL', 'gpt-4o-mini')) if key else MockProposer()
