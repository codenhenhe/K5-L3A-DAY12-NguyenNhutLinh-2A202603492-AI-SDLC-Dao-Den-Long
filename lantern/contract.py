"""Validation for the Phase 1 JSON input files."""
import json
import math
from pathlib import Path

from .game import BUTTONS, TUNING


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
    for key in (*BUTTONS, "dash"):
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


def read_scenario(path):
    document = read_json(path)
    require(isinstance(document, dict), "scenario: expected an object")
    for field in ("random_motes", "random_shades"):
        require(field not in document or type(document[field]) is bool, f"{field}: expected a boolean")
    if "time_left_s" in document:
        duration = document["time_left_s"]
        require(number(duration) and duration >= 0, "time_left_s: expected a non-negative number")
    player = document.get("player", {})
    require(isinstance(player, dict), "player: expected an object")
    if "pos" in player:
        require(vector(player["pos"], 3), "player.pos: expected [x, y, z]")
    for field, maximum in (("carried", TUNING["carry_capacity"]), ("flames", None)):
        require(field not in player or integer(player[field], maximum=maximum),
                f"player.{field}: invalid value")
    motes = document.get("motes", [])
    require(isinstance(motes, list) and all(vector(pos, 3) for pos in motes),
            "motes: expected an array of positions")
    for field in ("shades", "lanterns"):
        entries = document.get(field, [])
        require(isinstance(entries, list), f"{field}: expected an array")
        ids = set()
        for entry in entries:
            require(isinstance(entry, dict), f"{field}: expected objects")
            if field == "shades" or "pos" in entry:
                require(vector(entry.get("pos"), 3), f"{field}.pos: expected [x, y, z]")
            if field == "lanterns":
                require(entry.get("id") in ("L1", "L2", "L3", "L4", "L5"),
                        "lanterns.id: expected L1 through L5")
                if "deposited" in entry:
                    require(integer(entry["deposited"], maximum=TUNING["lantern_cost"]),
                            "lanterns.deposited: invalid amount")
                if "lit" in entry:
                    require(type(entry["lit"]) is bool, "lanterns.lit: expected a boolean")
            if "id" in entry:
                identifier = entry["id"]
                require(isinstance(identifier, str) and identifier and identifier not in ids,
                        f"{field}.id: expected a unique nonempty string")
                ids.add(identifier)
    return document
