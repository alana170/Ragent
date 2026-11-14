"""Install the included recorded fallback run for the local saved-run browser."""
import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
source = root / 'docs' / 'recorded-demo'
run_id = 'e8c18635e27c470d9b459df4ea520245'
destination = root / 'results'
destination.mkdir(exist_ok=True)
run_file = destination / f'run_{run_id}.json'
if run_file.exists():
    raise SystemExit(f'{run_file} already exists; refusing to overwrite it.')
for kind, suffix in [('developer_run', 'json'), ('developer_report', 'html')]:
    target = destination / f'{kind}_{run_id}.{suffix}'
    if target.exists():
        raise SystemExit(f'{target} already exists; refusing to overwrite it.')
for kind, suffix in [('developer_run', 'json'), ('developer_report', 'html')]:
    name = f'{kind}_{run_id}.{suffix}'
    shutil.copyfile(source / name, destination / name)
run = json.loads((source / run_file.name).read_text(encoding='utf-8'))
run['report_path'] = str(destination / f'developer_report_{run_id}.html')
run['json_path'] = str(destination / f'developer_run_{run_id}.json')
run_file.write_text(json.dumps(run, indent=2, allow_nan=False) + '\n', encoding='utf-8')
print(f'Installed recorded fallback run {run_id}. Restart the server to load it.')
