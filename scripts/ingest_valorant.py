#!/usr/bin/env python3
"""Regenerate the offline demo fixture and artwork manifest from pinned inputs.

Run from the repository root: python3 scripts/ingest_valorant.py
This deliberately does not fetch the network or silently update the snapshot.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'fixtures/valorant_source_snapshot.json'
ASSETS = ROOT / 'web/assets'


def positive(value, label, *, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{label} must be finite and positive')
    if integer and int(value) != value:
        raise ValueError(f'{label} must be an integer')
    return int(value) if integer else value


def build():
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    selected = {w['displayName'].lower(): w for w in source['weapons']}
    if set(selected) != {'vandal', 'spectre'} or len(source['weapons']) != 2:
        raise ValueError('Snapshot must contain exactly Vandal and Spectre')
    weapons = {}
    assets = {}
    for name, raw in selected.items():
        stats = raw['weaponStats']
        # At 10m with the selected closing strategies, range stays in this band.
        bands = [r for r in stats['damageRanges'] if r['rangeStartMeters'] <= 10 < r['rangeEndMeters']]
        if len(bands) != 1:
            raise ValueError(f'{name}: expected one damage range covering 10m')
        weapons[name] = {
            'damage': positive(bands[0]['bodyDamage'], f'{name}.bodyDamage'),
            'fire_rate': positive(stats['fireRate'], f'{name}.fireRate'),
            'mag_size': positive(stats['magazineSize'], f'{name}.magazineSize', integer=True),
            'reload_time': positive(stats['reloadTimeSeconds'], f'{name}.reloadTimeSeconds'),
            'pellets': positive(stats['shotgunPelletCount'], f'{name}.shotgunPelletCount', integer=True),
            # Explicit model assumptions, not derived from firstBulletAccuracy.
            'range': 50, 'spread_deg': 1.3, 'aim_spread_deg': 0.3,
        }
        path = ASSETS / f'{name}.png'
        assets[name] = {'path': f'{name}.png', 'url': f'/assets/{name}.png',
                        'source_url': raw['displayIcon'],
                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'content_type': 'image/png', 'label': raw['displayName']}
    assumptions = [
        'Body damage only at 10m; aggressive and flanker strategies close distance, keeping encounters within the Spectre 0–15m band.',
        'Range 50m and spread 1.3 degrees / aimed spread 0.3 degrees are simulator assumptions, not VALORANT accuracy measurements.',
        'The engine uses 100 health, no armor or headshots, simplified hit probability and range falloff, assumed reaction and movement, and no agent abilities.',
        'Outcomes are simulated illustrative duels, not observed VALORANT balance or telemetry.',
    ]
    snapshot = {'source': 'Valorant-API weapon catalog (unofficial)', 'profile_id': 'valorant',
                'source_url': source['source_url'], 'retrieved_at': source['retrieved_at'],
                'version': source['version']['version'], 'catalog_sha256': source['catalog_sha256'],
                'damage_context': 'body damage at 10 meters', 'assumptions': assumptions, 'weapons': weapons}
    manifest = {'profile_id': 'valorant', 'source': 'Valorant-API (unofficial); game artwork © Riot Games',
                'retrieved_at': source['retrieved_at'], 'version': source['version']['version'], 'assets': assets}
    (ROOT / 'fixtures/valorant_weapons_snapshot.json').write_text(json.dumps(snapshot, indent=2)+'\n', encoding='utf-8')
    (ASSETS / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    build()
