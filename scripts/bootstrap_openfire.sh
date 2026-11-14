#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
if [[ -e openfire/.git ]] || [[ -f openfire/.git ]]; then
  echo 'OpenFire submodule already initialized.'
else
  # Pin upstream, and keep its original history and license intact.
  git submodule add https://github.com/rokasjasonas/openfire.git openfire
fi
git -C openfire fetch origin 7259140487946532af8310723392cca34a4fb0bb
git -C openfire checkout --detach 7259140487946532af8310723392cca34a4fb0bb
mkdir -p openfire/tests
cp godot_bridge/ragent_balance.gd godot_bridge/ragent_balance.tscn openfire/tests/
# Files copied into submodule remain local uncommitted changes; avoid committing
# the upstream submodule content unless you fork it and intend to maintain it.
echo 'Pinned OpenFire; copied local Godot headless scene. Commit .gitmodules + openfire gitlink on your RAGENT branch.'
