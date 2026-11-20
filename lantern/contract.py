"""Validation for the headless JSON input files."""
import json
import math
from pathlib import Path

from .game import BUTTONS, DRIFTER_STATES, SHADE_STATES, TUNING, carry_capacity
from .maps import LAYOUTS


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def integer(value, minimum=0, maximum=None):
    return type(value) is int and value >= minimum and (maximum is None or value <= maximum)


def vector(value, length):
    return isinstance(value, list) and len(value) == length and all(number(n) for n in value)


def reject_json_constant(token):
    raise ValueError(f"{token} is not a JSON value")


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=reject_json_constant)
    except (ValueError, OverflowError) as error:
        raise ValueError(f"{path}: invalid JSON") from error


def validate_controls(frame):
    if "move" in frame:
        move = frame["move"]
        require(vector(move, 2) and all(-1 <= n <= 1 for n in move),
                "move: expected two numbers in [-1, 1]")
    if "cam_yaw_deg" in frame:
        require(number(frame["cam_yaw_deg"]), "cam_yaw_deg: expected a finite number")
    for key in BUTTONS:
        if key in frame:
            require(type(frame[key]) is bool, f"{key}: expected a boolean")


def read_inputs(path):
    document = read_json(path)
    require(isinstance(document, dict) and isinstance(document.get("frames"), list),
            "inputs: expected an object with a frames array")
    last = -1
    for frame in document["frames"]:
        require(isinstance(frame, dict) and integer(frame.get("tick")), "frames: invalid tick")
        require(frame["tick"] > last, "frames: ticks must increase strictly")
        last = frame["tick"]
        validate_controls(frame)
    return document["frames"]


def read_scenario(path, night=1):
    document = read_json(path)
    require(isinstance(document, dict), "scenario: expected an object")
    for field in ("random_motes", "random_shades", "random_drifters", "wind_enabled"):
        require(field not in document or type(document[field]) is bool, f"{field}: expected a boolean")
    if "time_left_s" in document:
        duration = document["time_left_s"]
        require(number(duration) and duration >= 0, "time_left_s: expected a non-negative number")
    player = document.get("player", {})
    require(isinstance(player, dict), "player: expected an object")
    if "pos" in player:
        require(vector(player["pos"], 3), "player.pos: expected [x, y, z]")
    lights = player.get("successful_lights", 0)
    require(integer(lights), "player.successful_lights: expected a non-negative integer")
    for field, maximum in (("carried", carry_capacity(lights)), ("flames", None),
                           ("invuln_ticks", None), ("dash_cd_ticks", None),
                           ("pulse_cd_ticks", None), ("charm_ticks", None)):
        require(field not in player or integer(player[field], maximum=maximum),
                f"player.{field}: invalid value")
    motes = document.get("motes", [])
    require(isinstance(motes, list) and all(vector(pos, 3) for pos in motes),
            "motes: expected an array of positions")
    lantern_ids = {f"L{i}" for i in range(1, len(LAYOUTS[night].lanterns) + 1)}
    for field in ("shades", "lanterns", "drifters", "charms"):
        entries = document.get(field, [])
        require(isinstance(entries, list), f"{field}: expected an array")
        ids = set()
        for entry in entries:
            require(isinstance(entry, dict), f"{field}: expected objects")
            if field in ("shades", "drifters") or "pos" in entry:
                require(vector(entry.get("pos"), 3), f"{field}.pos: expected [x, y, z]")
            if field == "lanterns":
                require(isinstance(entry.get("id"), str) and entry["id"] in lantern_ids,
                        "lanterns.id: unknown lantern for this night")
                if "deposited" in entry:
                    require(integer(entry["deposited"], maximum=TUNING["lantern_cost"]),
                            "lanterns.deposited: invalid amount")
                for flag in ("lit", "ever_lit"):
                    require(flag not in entry or type(entry[flag]) is bool, f"lanterns.{flag}: expected a boolean")
                if "fuel" in entry:
                    fuel = entry["fuel"]
                    require(number(fuel) and 0 <= fuel <= TUNING["fuel_max"],
                            "lanterns.fuel: out of range")
            if field in ("shades", "drifters"):
                states = SHADE_STATES if field == "shades" else DRIFTER_STATES
                require("state" not in entry or entry["state"] in states, f"{field}.state: invalid state")
                require("state_ticks_left" not in entry or integer(entry["state_ticks_left"]),
                        f"{field}.state_ticks_left: expected a non-negative integer")
            if field == "drifters" and "stolen" in entry:
                require(integer(entry["stolen"], maximum=3), "drifters.stolen: expected 0 through 3")
            if field == "shades" and "target_lantern_id" in entry:
                target = entry["target_lantern_id"]
                require(target is None or (isinstance(target, str) and target in lantern_ids),
                        "shades.target_lantern_id: unknown lantern for this night")
            if field == "charms":
                require("available" not in entry or type(entry["available"]) is bool,
                        "charms.available: expected a boolean")
                require("respawn_ticks" not in entry or integer(entry["respawn_ticks"]),
                        "charms.respawn_ticks: expected a non-negative integer")
            if "id" in entry:
                identifier = entry["id"]
                require(isinstance(identifier, str) and identifier and identifier not in ids,
                        f"{field}.id: expected a unique nonempty string")
                ids.add(identifier)
    return document
