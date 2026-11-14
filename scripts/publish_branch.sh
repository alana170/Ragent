#!/usr/bin/env bash
# Run from the Ragent repository root AFTER unpacking this overlay.
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
BRANCH="feat/openfire-balance-ci"
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git switch "$BRANCH"
else
  git switch -c "$BRANCH"
fi
bash scripts/bootstrap_openfire.sh
python3 -m unittest discover -s tests -p 'test_openfire_bridge.py' -v
python3 -m ragent_openfire.cli export \
  --source openfire/scripts/autoload/weapon_db.gd \
  --output results/openfire_weapons.json
python3 -m ragent_openfire.cli plant \
  --weapons results/openfire_weapons.json --output results/openfire_planted.json
python3 -m ragent_openfire.cli optimize \
  --weapons results/openfire_planted.json \
  --policy configs/openfire_balance_policy.json \
  --output results/openfire_agent.json --html results/openfire_report.html \
  --patched results/openfire_verified.json
# Add only source files. Generated measurements intentionally remain local.
git add .gitmodules openfire ragent_openfire configs/openfire_balance_policy.json \
  godot_bridge scripts docs/OPENFIRE.md tests/test_openfire_bridge.py \
  .github/workflows/openfire-balance.yml fixtures/openfire_weapons_snapshot.json \
  frontend web package.json package-lock.json README_OPENFIRE_OVERLAY.md
if ! git diff --cached --quiet; then
  git commit -m "feat: add OpenFire stat-duel balance QA integration"
fi
printf '\nReady to publish. Review first: git status && git show --stat --oneline HEAD\n'
printf 'Then push: git push -u origin %s\n' "$BRANCH"
