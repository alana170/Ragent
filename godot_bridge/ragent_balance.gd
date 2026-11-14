extends Node
## RAGENT headless stat-duel cross-check for an OpenFire checkout.
## This invokes WeaponDB (real Godot autoload), but deliberately does NOT claim
## to run OpenFire's full 3D bot navigation, physics, or multiplayer sessions.
## Copy script and .tscn to OpenFire's tests/ folder, then run:
## godot --headless --path openfire res://tests/ragent_balance.tscn -- \
##   --config=/absolute/path/results/verified_stats.json --output=/absolute/path/results/godot_result.json

func _arg(key: String, default: String = "") -> String:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--" + key + "="):
			return arg.substr(key.length() + 3)
	return default

func _read_json(path: String) -> Variant:
	if path == "": return null
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null: return null
	return JSON.parse_string(file.get_as_text())

func _ready() -> void:
	call_deferred("_run")

func _run() -> void:
	var input_path := _arg("config", "")
	var out_path := _arg("output", "user://ragent_godot_results.json")
	var parsed = _read_json(input_path)
	if not parsed is Dictionary or not parsed.has("weapons"):
		push_error("RAGENT: --config must point to weapon JSON containing weapons{}")
		get_tree().quit(2)
		return
	var overrides: Dictionary = parsed["weapons"]
	var all_stats := {}
	for wid in WeaponDB.all_ids():
		var stats: Dictionary = WeaponDB.get_weapon(wid).duplicate(true)
		if overrides.has(wid):
			stats.merge(overrides[wid], true)
		all_stats[wid] = stats
	var cases := []
	for pair in [["rifle", "smg"], ["rifle", "shotgun"], ["rifle", "sniper"]]:
		for distance in [5.0, 15.0, 35.0]:
			var wins := {"a": 0, "b": 0, "draw": 0}
			var ttks := []
			var events := []
			for seed in range(20):
				for first in ["a", "b"]:
					var result := _duel(all_stats[pair[0]], all_stats[pair[1]], pair[0], pair[1], distance, seed, first)
					wins[result["winner"]] += 1
					if result["ttk_s"] > 0: ttks.append(result["ttk_s"])
					if seed == 0 and first == "a": events = result["events"]
			var total := wins["a"] + wins["b"] + wins["draw"]
			var mean_ttk := 0.0
			for t in ttks: mean_ttk += t
			if not ttks.is_empty(): mean_ttk /= ttks.size()
			cases.append({"a": pair[0], "b": pair[1], "range_m": distance,
				"a_win_rate": (wins["a"] + .5 * wins["draw"]) / float(total),
				"mean_ttk_s": mean_ttk, "matches": total, "events": events})
	var report := {"engine": "godot_stat_duels", "uses_actual_weapon_db": true,
		"full_3d_gameplay": false, "input": input_path, "cases": cases}
	var file := FileAccess.open(out_path, FileAccess.WRITE)
	if file == null:
		push_error("Could not write RAGENT output to " + out_path)
		get_tree().quit(3)
		return
	file.store_string(JSON.stringify(report, "  "))
	file.flush()
	print("RAGENT_GODOT: wrote ", out_path, " (", cases.size(), " matchup cases)")
	get_tree().quit(0)

func _duel(a: Dictionary, b: Dictionary, a_id: String, b_id: String, distance: float, seed: int, first: String) -> Dictionary:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed * 4001 + int(distance) * 43 + (1 if first == "a" else 2) * 113
	var hp := {"a": 100.0, "b": 100.0}
	var stats := {"a": a, "b": b}
	var weapon_ids := {"a": a_id, "b": b_id}
	var ammo := {"a": int(a.get("mag_size", 30)), "b": int(b.get("mag_size",30))}
	var ready := {"a": .14 if first == "a" else .27, "b": .14 if first == "b" else .27}
	var events := []
	var winner := "draw"
	var elapsed := 0.0
	for tick in 2500:
		var side := "a" if float(ready["a"]) <= float(ready["b"]) else "b"
		var other := "b" if side == "a" else "a"
		elapsed = ready[side]
		if elapsed > 18.0: break
		var w: Dictionary = stats[side]
		if ammo[side] <= 0:
			ready[side] += float(w.get("reload_time", 1.5))
			ammo[side] = int(w.get("mag_size",30))
			continue
		ammo[side] -= 1
		var spread := deg_to_rad(float(w.get("aim_spread_deg", w.get("spread_deg",1.0))))
		var radius := distance * tan(spread)
		var hit := clampf(.91 * exp(-.52 * pow(radius / .85, 1.4)), .04, .96)
		var dmg := 0.0
		for pellet in int(w.get("pellets",1)):
			if rng.randf() < hit:
				var falloff := 1.0 if distance <= float(w.get("range",40)) else maxf(.35, float(w.get("range",40)) / distance)
				dmg += float(w.get("damage",10)) * falloff
		hp[other] = maxf(0.0,float(hp[other]) - dmg)
		events.append({"time_s": snappedf(elapsed,.0001), "type": "shot", "attacker": side,
			"weapon": weapon_ids[side], "damage": dmg, "target_hp": hp[other],
			"positions": {"a": [0,0], "b": [distance,0]}})
		ready[side] += 1.0 / maxf(0.01,float(w.get("fire_rate",1)))
		if hp[other] <= 0:
			winner = side
			events.append({"time_s": elapsed, "type": "kill", "winner": side})
			break
	return {"winner":winner,"ttk_s":elapsed if winner != "draw" else -1.0,"events":events}
