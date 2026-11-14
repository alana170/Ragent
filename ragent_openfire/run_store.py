"""Atomic, local storage for dashboard run state and artifacts."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile

_RUN_ID = re.compile(r'^[0-9a-f]{32}$')


def atomic_write(path, data):
    """Replace a UTF-8 file only after its complete contents are on disk."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_run(root, run):
    run_id = run['id']
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError('Invalid run id')
    atomic_write(Path(root) / f'run_{run_id}.json', json.dumps(run, indent=2, allow_nan=False) + '\n')


def load_runs(root):
    """Load persisted states; unfinished work becomes explicitly interrupted."""
    runs = {}
    for path in Path(root).glob('run_*.json'):
        try:
            run = json.loads(path.read_text(encoding='utf-8'))
            run_id = run['id']
            if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id) or path.name != f'run_{run_id}.json':
                continue
            if run.get('status') == 'running':
                run['status'] = 'interrupted'
                run['error'] = 'Server stopped before the run completed.'
                save_run(root, run)
            runs[run_id] = run
        except (OSError, ValueError, TypeError, KeyError):
            continue
    return runs
