"""Fixed-step simulation used by both the playable game and the grader."""
from dataclasses import dataclass
import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent.parent
TUNING = json.loads((ROOT / "game.contract.json").read_text())["tuning"]
HZ = 60
ISLAND_RADIUS = 36
SHORE_RADIUS = ISLAND_RADIUS - 0.8
# Keep a shade outside the true zone after JSONL coordinates round to millimetres.
ZONE_MARGIN = 0.001
BUTTONS = ("jump", "interact", "pulse")
DEFAULT_INPUT = dict(move=(0, 0), cam_yaw_deg=0, **dict.fromkeys(BUTTONS, False))


def distance(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def position(point):
    return [round(value, 3) for value in point]


def seconds_to_ticks(seconds):
    return math.ceil(seconds * HZ)


@dataclass
class Lantern:
    id: str
    pos: list
    deposited: int = 0
    lit: bool = False


@dataclass
class Mote:
    id: str
    pos: list


@dataclass
class Shade:
    id: str
    pos: list
    stunned_until: int = 0
    state: str = "chase"


class Game:
    def __init__(self, seed, scenario=None):
        settings = scenario or {}
        self.tick = 0
        self.duration = settings.get("time_left_s", TUNING["night1_duration_s"])
        self.state = "playing"
        self.score = 0
        self.pos = list(settings.get("player", {}).get("pos", (0, 0, 0)))
        self.carried = settings.get("player", {}).get("carried", 0)
        self.flames = settings.get("player", {}).get("flames", TUNING["flames"])
        self.vertical_speed = 0
        self.invulnerable_until = 0
        self.pulse_ready = 0
        self.previous = DEFAULT_INPUT.copy()
        self.events = []
        self.lanterns = [
            Lantern(f"L{i}", [x, 0, z])
            for i, (x, z) in enumerate(((0, 8), (13, 15), (16, -5), (-1, -17), (-15, 4)), 1)
        ]
        updates = {entry["id"]: entry for entry in settings.get("lanterns", ())}
        for lamp in self.lanterns:
            entry = updates.get(lamp.id, {})
            lamp.pos = list(entry.get("pos", lamp.pos))
            lamp.deposited = entry.get("deposited", TUNING["lantern_cost"] if entry.get("lit") else 0)
            lamp.lit = entry.get("lit", lamp.deposited >= TUNING["lantern_cost"])

        rng = random.Random(seed)
        points = []
        if settings.get("random_motes", True):
            for lamp in self.lanterns:
                for i in range(8):
                    angle = math.tau * i / 8 + rng.uniform(-0.17, 0.17)
                    radius = rng.uniform(2.7, 5.1)
                    x, _, z = lamp.pos
                    points.append((x + math.cos(angle) * radius, 0, z + math.sin(angle) * radius))
            points.extend((0, 0, z) for z in (1.6, 3.5, 5.4))
        points = settings.get("motes", points)
        self.motes = [Mote(f"M{i}", list(point)) for i, point in enumerate(points, 1)]
        spawn = []
        if settings.get("random_shades", True):
            angle = rng.uniform(-0.3, 0.3)
            spawn = [{"pos": [math.cos(a + angle) * 27, 0.8, math.sin(a + angle) * 27]}
                     for a in (0.3, 2.0, 4.4)]
        spawn = settings.get("shades", spawn)
        used_ids = {entry["id"] for entry in spawn if "id" in entry}
        self.shades = []
        next_id = 1
        for entry in spawn:
            if "id" in entry:
                shade_id = entry["id"]
            else:
                while f"S{next_id}" in used_ids:
                    next_id += 1
                shade_id = f"S{next_id}"
                next_id += 1
            self.shades.append(Shade(shade_id, list(entry["pos"])))

    @property
    def time_left(self):
        return self.duration - self.tick / HZ

    def event(self, name, **data):
        self.events.append(dict(type="event", tick=self.tick, name=name, data=data))

    def move(self, controls, jump):
        x, z = controls["move"]
        magnitude = max(1, math.hypot(x, z))
        theta = math.radians(controls["cam_yaw_deg"] % 360)
        step = TUNING["player_speed"] / (HZ * magnitude)
        # A scenario can place Mây beyond the shore. Preserve that position
        # until input moves Mây, and allow Mây to return toward the island.
        limit = max(SHORE_RADIUS, math.hypot(self.pos[0], self.pos[2]))
        self.pos[0] += (x * math.cos(theta) + z * math.sin(theta)) * step
        self.pos[2] += (-x * math.sin(theta) + z * math.cos(theta)) * step
        radius = math.hypot(self.pos[0], self.pos[2])
        if radius > limit:
            self.pos[0] *= limit / radius
            self.pos[2] *= limit / radius
        if jump and self.pos[1] <= 0:
            self.vertical_speed = 5.2
            self.event("jumped")
        if self.pos[1] > 0 or self.vertical_speed > 0:
            self.pos[1] = max(0, self.pos[1] + self.vertical_speed / HZ)
            self.vertical_speed -= 12 / HZ
            if self.pos[1] == 0:
                self.vertical_speed = 0

    def pickup(self):
        remaining = []
        for mote in self.motes:
            if self.carried < TUNING["carry_capacity"] and distance(self.pos, mote.pos) <= TUNING["pickup_radius"]:
                self.carried += 1
                self.score += TUNING["score"]["per_mote"]
                self.event("mote_picked", id=mote.id, carried=self.carried)
            else:
                remaining.append(mote)
        self.motes = remaining

    def deposit(self):
        lamp = min(
            (lamp for lamp in self.lanterns if not lamp.lit),
            key=lambda lamp: distance(lamp.pos, self.pos), default=None,
        )
        if lamp is None or distance(lamp.pos, self.pos) > TUNING["interact_radius"]:
            return
        amount = min(self.carried, TUNING["lantern_cost"] - lamp.deposited)
        if amount <= 0:
            return
        lamp.deposited += amount
        self.carried -= amount
        self.event("lantern_deposited", id=lamp.id, amount=amount,
                   deposited=lamp.deposited, carried=self.carried)
        if lamp.deposited == TUNING["lantern_cost"]:
            lamp.lit = True
            self.score += TUNING["score"]["per_lantern"]
            self.event("lantern_lit", id=lamp.id)

    def pulse(self):
        if self.tick < self.pulse_ready or self.carried < TUNING["pulse_cost"]:
            return
        self.carried -= TUNING["pulse_cost"]
        self.pulse_ready = self.tick + seconds_to_ticks(TUNING["pulse_cooldown_s"])
        self.event("pulse", carried=self.carried)
        for shade in self.shades:
            separation = distance(self.pos, shade.pos)
            if separation > TUNING["pulse_radius"]:
                continue
            dx = (shade.pos[0] - self.pos[0]) / separation if separation else 1
            dz = (shade.pos[2] - self.pos[2]) / separation if separation else 0
            push_distance = TUNING["pulse_push_m"]
            for entry, leave in self.shade_zone_intervals(shade.pos, dx, dz):
                # If the shade already touches the buffered zone, let it
                # keep moving away but prevent a push deeper into the zone.
                if leave > 0 and (entry >= 0 or entry + leave > 0):
                    push_distance = min(push_distance, max(0, entry))
            shade.pos[0] += dx * push_distance
            shade.pos[2] += dz * push_distance
            shade.stunned_until = self.tick + seconds_to_ticks(TUNING["pulse_stun_s"])
            shade.state = "stunned"
            self.score += TUNING["score"]["per_stun"]
            self.event("shade_stunned", id=shade.id)

    def protected(self, point):
        return any(lamp.lit and distance(lamp.pos, point) <= TUNING["safe_radius"]
                   for lamp in self.lanterns)

    def shade_zone_intervals(self, pos, dx, dz):
        """Yield where the line from pos in unit direction (dx, dz) meets lit zones."""
        radius = TUNING["safe_radius"] + ZONE_MARGIN
        for lamp in self.lanterns:
            if not lamp.lit:
                continue
            x, z = lamp.pos[0] - pos[0], lamp.pos[2] - pos[2]
            lateral = abs(x * dz - z * dx)
            if lateral <= radius:
                center = x * dx + z * dz
                half_chord = math.sqrt(radius**2 - lateral**2)
                yield center - half_chord, center + half_chord

    def repel_shade(self, shade, lamp):
        x, z = shade.pos[0] - lamp.pos[0], shade.pos[2] - lamp.pos[2]
        magnitude = math.hypot(x, z)
        dx, dz = (x / magnitude, z / magnitude) if magnitude else (1, 0)
        # Reach the end of the connected safe zone, including overlapping lamps.
        distance_out = 0
        for entry, leave in sorted(self.shade_zone_intervals(shade.pos, dx, dz)):
            if entry > distance_out:
                break
            distance_out = max(distance_out, leave)
        shade.pos[0] += dx * distance_out
        shade.pos[2] += dz * distance_out

    def move_shades(self):
        safe_player = self.protected(self.pos)
        for shade in self.shades:
            stunned = self.tick < shade.stunned_until
            near_lamp = next((lamp for lamp in self.lanterns
                              if lamp.lit and distance(lamp.pos, shade.pos) <= TUNING["safe_radius"]), None)
            if near_lamp:
                self.repel_shade(shade, near_lamp)
                shade.state = "stunned" if stunned else "repelled"
                continue
            if stunned:
                continue
            shade.state = "chase"
            separation = distance(shade.pos, self.pos)
            if separation:
                length = min(separation, TUNING["shade_speed"] / HZ)
                next_pos = [
                    shade.pos[0] + (self.pos[0] - shade.pos[0]) * length / separation,
                    shade.pos[1],
                    shade.pos[2] + (self.pos[2] - shade.pos[2]) * length / separation,
                ]
                if self.protected(next_pos):
                    shade.state = "repelled"
                    continue
                shade.pos = next_pos
            if (not safe_player and distance(shade.pos, self.pos) <= TUNING["shade_hit_radius"]
                    and self.tick >= self.invulnerable_until):
                self.flames -= 1
                self.invulnerable_until = self.tick + seconds_to_ticks(TUNING["invuln_s"])
                self.event("player_hit", id=shade.id, flames=self.flames, carried=self.carried)
                if self.flames == 0:
                    break

    def finish(self, state, reason):
        self.state = state
        if state == "won":
            self.score += max(0, math.floor(self.time_left)) * TUNING["score"]["per_second_left"]
            self.score += self.flames * TUNING["score"]["per_flame_left"]
        self.event(f"game_{state}", score=self.score, reason=reason)

    def step(self, controls):
        self.events = []
        if self.state != "playing":
            return self.events
        self.tick += 1
        if self.flames == 0:
            self.finish("lost", "no_flames")
            return self.events
        pressed = {key: controls[key] and not self.previous[key] for key in BUTTONS}
        self.previous = controls.copy()
        self.move(controls, pressed["jump"])
        self.pickup()
        if pressed["interact"]:
            self.deposit()
        if pressed["pulse"]:
            self.pulse()
        if all(lamp.lit for lamp in self.lanterns):
            self.finish("won", "all_lanterns")
        else:
            self.move_shades()
            if self.flames == 0 or self.time_left <= 0:
                self.finish("lost", "no_flames" if self.flames == 0 else "timeout")
        return self.events

    def snapshot(self):
        return {
            "type": "snapshot", "tick": self.tick, "sim_tick": self.tick,
            "state": self.state, "time_left_s": self.time_left, "score": self.score,
            "player": {"pos": position(self.pos), "flames": self.flames, "carried": self.carried},
            "lanterns": [{"id": lamp.id, "pos": position(lamp.pos), "lit": lamp.lit,
                          "deposited": lamp.deposited} for lamp in self.lanterns],
            "shades": [{"id": shade.id, "pos": position(shade.pos), "state": shade.state}
                       for shade in self.shades],
            "motes_active": len(self.motes),
            "motes": [{"id": mote.id, "pos": position(mote.pos)} for mote in self.motes],
        }

    def end(self):
        return dict(type="end", ticks=self.tick, state=self.state, score=self.score)
