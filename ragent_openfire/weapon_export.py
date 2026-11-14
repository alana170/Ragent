"""Extract OpenFire WeaponDB.WEAPONS combat statistics without duplicating data.

This deliberately selects well-defined scalar keys; arbitrary GDScript is NOT
executed. Other Godot expressions (Vector3, resources) are not needed for duels.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

FIELDS = ('damage', 'fire_rate', 'range', 'pellets', 'spread_deg',
          'aim_spread_deg', 'mag_size', 'reload_time', 'reserve')
NUMERIC = re.compile(r'"([A-Za-z_]+)"\s*:\s*(-?\d+(?:\.\d+)?)')
ID = re.compile(r'"id"\s*:\s*"([^"\\]+)"')


def _dicts(source: str):
    anchor = re.search(r'const\s+WEAPONS\s*:\s*Array\s*\[\s*Dictionary\s*\]\s*=\s*\[', source)
    if not anchor:
        raise ValueError('WEAPONS typed array not found in weapon_db.gd')
    depth = 0
    start = None
    in_string = False
    escaped = False
    for i in range(anchor.end(), len(source)):
        c = source[i]
        if in_string:
            if escaped: escaped = False
            elif c == '\\': escaped = True
            elif c == '"': in_string = False
            continue
        if c == '"': in_string = True
        elif c == '{':
            if depth == 0: start = i
            depth += 1
        elif c == '}':
            depth -= 1
            if depth < 0: raise ValueError('unbalanced dictionary')
            if depth == 0 and start is not None:
                yield source[start:i+1]
                start = None
        elif c == ']' and depth == 0:
            return
    raise ValueError('unterminated WEAPONS array')


def extract_weapons(source: str) -> dict:
    result = {}
    for block in _dicts(source):
        mid = ID.search(block)
        if not mid: raise ValueError('Weapon missing id')
        values = {}
        for name, raw in NUMERIC.findall(block):
            if name in FIELDS:
                values[name] = float(raw) if '.' in raw else int(raw)
        weapon_id = mid.group(1)
        for mandatory in ('damage', 'fire_rate', 'range', 'pellets', 'spread_deg', 'mag_size'):
            if mandatory not in values: raise ValueError(f'{weapon_id}: missing {mandatory}')
        if weapon_id in result: raise ValueError(f'duplicate weapon id: {weapon_id}')
        result[weapon_id] = values
    if not result: raise ValueError('No weapon dictionaries parsed')
    return result


def export_file(source: str | Path, destination: str | Path) -> dict:
    weapons = extract_weapons(Path(source).read_text(encoding='utf-8'))
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({'source': 'OpenFire WeaponDB.WEAPONS', 'weapons': weapons}, indent=2) + '\n', encoding='utf-8')
    return weapons
