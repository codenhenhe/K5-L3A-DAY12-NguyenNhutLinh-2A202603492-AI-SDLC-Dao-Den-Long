"""Fixed-step game shared by headless and browser play."""
from dataclasses import dataclass
import json
import math
from pathlib import Path
import random
import re

from .maps import LAYOUTS, ground

ROOT = Path(__file__).resolve().parent.parent
TUNING = json.loads((ROOT / "game.contract.json").read_text())["tuning"]
HZ = 60
DT = 1 / HZ
BUTTONS = ("jump", "interact", "pulse", "dash", "pause")
DEFAULT_INPUT = dict(move=(0, 0), cam_yaw_deg=0, **dict.fromkeys(BUTTONS, False))
SHADE_STATES = ("spawning", "wander", "chase", "recoil", "stunned", "drain")
DRIFTER_STATES = ("idle", "chase", "flee", "removed")

GRAVITY = 20
JUMP_SPEED = 7
VERTICAL_REACH = 1.5
MOTE_SPAWN_TICKS = 240
DROPPED_TTL = 480
SHADE_SPAWNING_TICKS = 30
PULSE_PUSH_TICKS = 15
RECOIL_TICKS = 60
EVICTION_TICKS = 30
RESPAWN_TICKS = 60
CHARM_TICKS = 600
CHARM_RESPAWN = 2700
CHARM_SPEED = 7.2
ZONE_MARGIN = 0.001
FUEL_MAX = round(TUNING["fuel_max"] * HZ)
FUEL_PER_MOTE = round(TUNING["fuel_per_mote"] * HZ)
LOW_FUEL = round(TUNING["low_fuel_threshold"] * HZ)
DRAIN_RANGE = 2
DRAIN_CHASE_RANGE = 6


def carry_capacity(successful_lights):
    return min(TUNING["capacity_max"], TUNING["carry_capacity"] + 2 * successful_lights)


def distance(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def direction(a, b, fallback=(0, 1)):
    dx, dz = b[0] - a[0], b[2] - a[2]
    length = math.hypot(dx, dz)
    return (dx / length, dz / length) if length else fallback


def position(point):
    return [round(value, 3) for value in point]


def ticks(seconds):
    return math.ceil(seconds * HZ)


def id_order(entity):
    match = re.fullmatch(r"([^0-9]*)([0-9]+)", entity.id)
    if match:
        prefix, sequence = match.groups()
        sequence = sequence.lstrip("0") or "0"
        return prefix, len(sequence), sequence, entity.id
    return entity.id, 0, "", entity.id


@dataclass
class Lantern:
    id: str
    pos: list
    deposited: int = 0
    lit: bool = False
    fuel_units: int = 0
    ever_lit: bool = False
    relit_count: int = 0

    @property
    def fuel(self):
        return round(self.fuel_units / HZ, 1)

    @property
    def weak(self):
        return self.lit and 0 < self.fuel_units < LOW_FUEL

    @property
    def safe(self):
        return self.lit and self.fuel_units >= LOW_FUEL

    @property
    def light_cost(self):
        return TUNING["relight_cost" if self.ever_lit else "lantern_cost"]

    @property
    def can_receive(self):
        return self.fuel_units < FUEL_MAX if self.lit else self.deposited < self.light_cost


@dataclass
class Mote:
    id: str
    pos: list
    kind: str = "random"
    ttl: int | None = None


@dataclass
class Shade:
    id: str
    pos: list
    state: str = "wander"
    remaining: int = 0
    heading: tuple = (0, 1)
    impulse: tuple = (0, 0)
    impulse_ticks: int = 0
    evict_ticks: int = 0
    evicting: bool = False
    evict_heading: tuple = (1, 0)
    target_lantern_id: str | None = None
    drain_ticks: int = 0
    just_unstunned: bool = False


@dataclass
class Drifter:
    id: str
    pos: list
    state: str = "idle"
    stolen: int = 0
    remaining: int = 0
    heading: tuple = (0, 1)


@dataclass
class Charm:
    id: str
    pos: list
    available: bool = True
    remaining: int = 0


class Game:
    def __init__(self, seed, scenario=None, night=1):
        config = scenario or {}
        self.night = night
        self.layout = LAYOUTS[night]
        self.tick = self.sim_tick = self.score = 0
        self.duration = config.get("time_left_s", TUNING[f"night{night}_duration_s"])
        self.state = "playing"
        self.events = []
        self.rng = random.Random(seed)
        self.wind_rng = random.Random(seed + 131)
        self.wind_enabled = config.get("wind_enabled", night == 3)
        self.wind_angle = 0
        self.wind_active = False
        self.wind_warning = False
        player = config.get("player", {})
        self.pos = list(player.get("pos", self.layout.start))
        self.vel = [0.0, 0.0, 0.0]
        self.facing = (0, 1)
        floor = ground(night, self.pos[0], self.pos[2])
        self.grounded = floor is not None and math.isclose(self.pos[1], floor, abs_tol=1e-9)
        self.carried = player.get("carried", 0)
        self.successful_lights = player.get("successful_lights", 0)
        self.flames = player.get("flames", TUNING["flames"])
        self.invuln = player.get("invuln_ticks", 0)
        self.pulse_cd = player.get("pulse_cd_ticks", 0)
        self.dash_cd = player.get("dash_cd_ticks", 0)
        self.charm_ticks = player.get("charm_ticks", 0)
        self.dash_ticks = 0
        self.dash_heading = self.facing
        self.launch = None
        self.respawn_ticks = 0
        self.previous = DEFAULT_INPUT.copy()
        self.random_motes = config.get("random_motes", True)
        self.random_shades = config.get("random_shades", True)
        self.random_drifters = config.get("random_drifters", night != 1)
        self.issued_ids = {"M": set(), "S": set(), "D": set(), "C": set()}
        self.next_id = dict.fromkeys(self.issued_ids, 1)

        overrides = {entry["id"]: entry for entry in config.get("lanterns", ())}
        self.lanterns = []
        for i, pos in enumerate(self.layout.lanterns, 1):
            name = f"L{i}"
            entry = overrides.get(name, {})
            was_lit = entry.get("ever_lit", False)
            cost = TUNING["relight_cost" if was_lit else "lantern_cost"]
            deposited = entry.get("deposited", TUNING["lantern_cost"] if entry.get("lit") else 0)
            lit = entry.get("lit", deposited >= cost)
            fuel_units = round(entry.get("fuel", TUNING["fuel_max"]) * HZ) if lit else 0
            self.lanterns.append(Lantern(name, list(entry.get("pos", pos)), deposited,
                                         lit, fuel_units, was_lit or lit))
        self.lantern_by_id = {lamp.id: lamp for lamp in self.lanterns}
        self.required_lights = math.ceil(TUNING["win_ratio"] * len(self.lanterns))

        points = self.rng.sample(self.layout.motes, 20) if self.random_motes else ()
        self.motes = [Mote(self.identifier("M"), list(pos)) for pos in config.get("motes", points)]
        shades = config.get("shades", ())
        self.reserve("S", shades)
        self.shades = [Shade(self.identifier("S", entry.get("id")), list(entry["pos"]),
                             entry.get("state", "chase"), entry.get("state_ticks_left", 0),
                             target_lantern_id=entry.get("target_lantern_id"))
                       for entry in shades]
        for shade in self.shades:
            if shade.state == "drain" and shade.target_lantern_id is None:
                target = self.nearest_lantern(shade.pos, (lamp for lamp in self.lanterns if lamp.weak))
                if target is not None and distance(target.pos, shade.pos) <= DRAIN_RANGE:
                    shade.target_lantern_id = target.id
        drifters = config.get("drifters", ())
        self.reserve("D", drifters)
        self.drifters = [
            Drifter(self.identifier("D", entry.get("id")), list(entry["pos"]), entry.get("state", "idle"),
                    entry.get("stolen", 0), entry.get("state_ticks_left", 240 if entry.get("state") == "flee" else 0))
            for entry in drifters if entry.get("state") != "removed"
        ]
        charms = config.get("charms", tuple({"pos": pos} for pos in self.layout.charms))
        self.reserve("C", charms)
        self.charms = []
        for entry in charms:
            name = self.identifier("C", entry.get("id"))
            index = int(name[1:]) - 1 if name.startswith("C") and name[1:].isdigit() else -1
            pos = entry.get("pos", self.layout.charms[index] if 0 <= index < len(self.layout.charms) else (0, 0, 0))
            available = entry.get("available", True)
            self.charms.append(Charm(name, list(pos), available,
                                     entry.get("respawn_ticks", 0 if available else CHARM_RESPAWN)))

    def reserve(self, prefix, entries):
        self.issued_ids[prefix].update(entry["id"] for entry in entries if "id" in entry)

    def identifier(self, prefix, explicit=None):
        if explicit is not None:
            return explicit
        while True:
            name = f"{prefix}{self.next_id[prefix]}"
            self.next_id[prefix] += 1
            if name not in self.issued_ids[prefix]:
                self.issued_ids[prefix].add(name)
                return name

    @property
    def time_left(self):
        return self.duration - self.sim_tick / HZ

    @property
    def capacity(self):
        return carry_capacity(self.successful_lights)

    def event(self, name, **data):
        self.events.append(dict(type="event", tick=self.tick, name=name, data=data))

    def counters(self):
        self.invuln = max(0, self.invuln - 1)
        self.dash_cd = max(0, self.dash_cd - 1)
        self.pulse_cd = max(0, self.pulse_cd - 1)
        self.charm_ticks = max(0, self.charm_ticks - 1)
        for shade in self.shades:
            shade.just_unstunned = False
            shade.remaining = max(0, shade.remaining - 1)
            if shade.state in ("stunned", "spawning", "recoil") and not (shade.remaining or shade.impulse_ticks):
                shade.just_unstunned = shade.state == "stunned"
                shade.state = "wander"
        for mote in self.motes:
            if mote.ttl is not None:
                mote.ttl -= 1
        self.motes = [mote for mote in self.motes if mote.ttl is None or mote.ttl > 0]
        for charm in self.charms:
            if not charm.available:
                charm.remaining = max(0, charm.remaining - 1)
                charm.available = not charm.remaining
        for drifter in self.drifters:
            if drifter.state == "flee":
                drifter.remaining -= 1
                if drifter.remaining <= 0:
                    drifter.state = "removed"
        self.drifters = [drifter for drifter in self.drifters if drifter.state != "removed"]
        if self.wind_enabled:
            offset = self.sim_tick % (30 * HZ)
            if offset == 28 * HZ:
                self.wind_angle = self.wind_rng.randrange(360)
            self.wind_warning = offset >= 28 * HZ
            self.wind_active = self.sim_tick >= 30 * HZ and offset < 5 * HZ

    def drain_target(self, shade):
        lamp = self.lantern_by_id.get(shade.target_lantern_id)
        if lamp is not None and lamp.weak and distance(lamp.pos, shade.pos) <= DRAIN_RANGE:
            return lamp
        return None

    def consume_fuel(self):
        drainers = {}
        for shade in self.shades:
            if shade.state == "drain":
                lamp = self.drain_target(shade)
                if lamp is not None:
                    shade.drain_ticks += 1
                    drainers.setdefault(lamp.id, []).append(shade)
        for lamp in self.lanterns:
            if not lamp.lit:
                continue
            shades = drainers.get(lamp.id, ())
            consumed = round(TUNING["fuel_decay_per_s"] + len(shades) * TUNING["drain_per_s"])
            lamp.fuel_units = max(0, lamp.fuel_units - consumed)
            for shade in shades:
                if shade.drain_ticks % HZ == 0:
                    self.event("fuel_drain", lantern_id=lamp.id, shade_id=shade.id, fuel=lamp.fuel)
            if lamp.fuel_units == 0:
                lamp.lit = False
                lamp.deposited = 0
                self.event("lantern_out", lantern_id=lamp.id)

    def pad_launch(self):
        if not self.grounded:
            return False
        for pos, (x, z), speed, vertical in self.layout.pads:
            if abs(self.pos[1] - pos[1]) < 0.05 and distance(self.pos, pos) <= 1:
                dx, dz = direction(pos, (x, 0, z))
                self.launch = (dx * speed, dz * speed)
                self.vel[1] = vertical
                self.grounded = False
                self.event("jumped")
                return True
        return False

    def move(self, controls, pressed):
        x, z = controls["move"]
        magnitude = max(1, math.hypot(x, z))
        angle = math.radians(controls["cam_yaw_deg"] % 360)
        dx = (x * math.cos(angle) + z * math.sin(angle)) / magnitude
        dz = (-x * math.sin(angle) + z * math.cos(angle)) / magnitude
        if dx or dz:
            self.facing = direction((0, 0, 0), (dx, 0, dz))
        if pressed["dash"] and not self.dash_ticks and (not self.dash_cd or self.charm_ticks):
            self.dash_ticks = ticks(TUNING["dash_duration_s"])
            self.dash_cd = 0 if self.charm_ticks else ticks(TUNING["dash_cooldown_s"])
            self.dash_heading = self.facing
            self.event("dash")
        launched = self.pad_launch()
        if pressed["jump"] and self.grounded:
            self.grounded = False
            self.vel[1] = JUMP_SPEED
            self.event("jumped")
        speed = CHARM_SPEED if self.charm_ticks else TUNING["player_speed"]
        vx, vz = dx * speed, dz * speed
        if self.launch:
            vx, vz = self.launch
        if self.dash_ticks:
            vx, vz = (axis * TUNING["dash_speed"] for axis in self.dash_heading)
            self.dash_ticks -= 1
            dashing = True
        else:
            dashing = False
        if self.wind_active:
            angle = math.radians(self.wind_angle)
            vx += 2 * math.cos(angle)
            vz += 2 * math.sin(angle)

        x0, y0, z0 = self.pos
        x, z = x0 + vx * DT, z0 + vz * DT
        old_floor = ground(self.night, x0, z0)
        floor = ground(self.night, x, z)
        # A small climb is a ramp sample; larger rises are vertical faces.
        if (floor is not None and floor > y0 + 0.25
                and old_floor != floor and (self.grounded or floor > y0 + max(0, self.vel[1]) * DT)):
            x, z, floor = x0, z0, old_floor
            vx = vz = 0
        if self.night == 3 and 6 <= y0 <= 14 and math.hypot(x, z) < 2:
            x, z, floor = x0, z0, old_floor
            vx = vz = 0
        self.pos[0], self.pos[2] = x, z
        self.vel[0], self.vel[2] = vx, vz

        if dashing and not (self.grounded and floor == y0):
            self.grounded = floor is not None and floor == y0
        elif self.grounded and floor is not None and abs(floor - y0) <= 0.25:
            self.pos[1] = floor
            self.vel[1] = 0
        else:
            self.grounded = False
            self.pos[1] += self.vel[1] * DT - GRAVITY * DT * DT / 2
            self.vel[1] -= GRAVITY * DT
            if floor is not None and self.vel[1] <= 0 and self.pos[1] <= floor <= y0 + 1e-9:
                self.pos[1] = floor
                self.vel[1] = 0
                self.grounded = True
                self.launch = None
        if not launched:
            self.pad_launch()
        # Integration around exactly -10 can accumulate floating-point noise.
        if self.pos[1] < -10 - 1e-9 and TUNING["fall_enabled"]:
            self.fall()

    def fall(self):
        lost = self.carried
        self.carried = 0
        self.flames = max(0, self.flames - 1)
        self.vel[:] = (0, 0, 0)
        self.grounded = False
        self.launch = None
        self.dash_ticks = 0
        self.respawn_ticks = RESPAWN_TICKS if self.flames else 0
        self.event("player_hit", reason="fall", lost=lost, flames=self.flames, carried=self.carried)

    def recover(self):
        if not self.respawn_ticks:
            return False
        self.respawn_ticks -= 1
        if not self.respawn_ticks:
            self.pos[:] = self.layout.start
            self.vel[:] = (0, 0, 0)
            self.facing = (0, 1)
            self.grounded = True
            self.invuln = ticks(TUNING["invuln_s"])
        return True

    def in_reach(self, pos, radius):
        return distance(self.pos, pos) <= radius and abs(self.pos[1] - pos[1]) <= VERTICAL_REACH

    def pickup(self):
        keep = []
        for mote in self.motes:
            if self.carried < self.capacity and self.in_reach(mote.pos, TUNING["pickup_radius"]):
                self.carried += 1
                self.event("mote_picked", id=mote.id, carried=self.carried)
            else:
                keep.append(mote)
        self.motes = keep
        for charm in self.charms:
            if charm.available and self.in_reach(charm.pos, TUNING["pickup_radius"]):
                self.charm_ticks = CHARM_TICKS
                self.dash_cd = 0
                charm.available, charm.remaining = False, CHARM_RESPAWN
                self.event("charm_picked", charm_id=charm.id, charm_ticks=CHARM_TICKS)

    @staticmethod
    def nearest_lantern(pos, lamps, metric=distance):
        return min(lamps, key=lambda lamp: (metric(lamp.pos, pos), id_order(lamp)), default=None)

    def deposit(self):
        if not self.carried:
            return
        lamp = self.nearest_lantern(self.pos, (lamp for lamp in self.lanterns if lamp.can_receive), math.dist)
        if lamp is None or math.dist(lamp.pos, self.pos) > TUNING["interact_radius"]:
            return
        if lamp.lit:
            missing = FUEL_MAX - lamp.fuel_units
            amount = min(self.carried, (missing + FUEL_PER_MOTE - 1) // FUEL_PER_MOTE)
        else:
            amount = min(self.carried, lamp.light_cost - lamp.deposited)
        self.carried -= amount
        self.score += amount * TUNING["score"]["per_mote"]
        if lamp.lit:
            lamp.fuel_units = min(FUEL_MAX, lamp.fuel_units + amount * FUEL_PER_MOTE)
            self.event("refuel", lantern_id=lamp.id, amount=amount, fuel=lamp.fuel)
            return
        lamp.deposited += amount
        self.event("lantern_deposited", id=lamp.id, amount=amount, deposited=lamp.deposited, carried=self.carried)
        if lamp.deposited == lamp.light_cost:
            relight = lamp.ever_lit
            lamp.lit = True
            lamp.ever_lit = True
            lamp.fuel_units = FUEL_MAX
            lamp.relit_count += int(relight)
            self.successful_lights += 1
            self.score += TUNING["score"]["per_relight" if relight else "per_lantern"]
            self.event("lantern_lit", id=lamp.id, relight=relight)

    def zone(self, pos):
        return next((lamp for lamp in self.lanterns if lamp.safe
                     and distance(lamp.pos, pos) <= TUNING["safe_radius"]), None)

    def zone_intervals(self, point, dx, dz):
        radius = TUNING["safe_radius"] + ZONE_MARGIN
        for lamp in self.lanterns:
            if lamp.safe:
                x, z = lamp.pos[0] - point[0], lamp.pos[2] - point[2]
                lateral = abs(x * dz - z * dx)
                if lateral <= radius:
                    along = x * dx + z * dz
                    extent = math.sqrt(radius**2 - lateral**2)
                    yield along - extent, along + extent

    def clear_zones(self):
        for shade in self.shades:
            lamp = self.zone(shade.pos)
            shade.evicting = lamp is not None
            if lamp is None:
                shade.evict_ticks = 0
            elif not shade.evict_ticks:
                shade.evict_ticks = EVICTION_TICKS
                shade.evict_heading = direction(lamp.pos, shade.pos, (1, 0))

    def evict_shade(self, shade):
        dx, dz = shade.evict_heading
        exit_distance = 0
        for entry, leave in sorted(self.zone_intervals(shade.pos, dx, dz)):
            if entry > exit_distance:
                break
            exit_distance = max(exit_distance, leave)
        length = exit_distance / shade.evict_ticks
        shade.pos[0] += dx * length
        shade.pos[2] += dz * length
        shade.evict_ticks -= 1

    def pulse(self):
        if self.pulse_cd or self.carried < TUNING["pulse_cost"]:
            return
        self.carried -= TUNING["pulse_cost"]
        self.pulse_cd = ticks(TUNING["pulse_cooldown_s"])
        self.event("pulse", carried=self.carried)
        center = (self.pos[0], self.pos[1] + 0.8, self.pos[2])
        for shade in self.shades:
            if math.dist(center, shade.pos) > TUNING["pulse_radius"]:
                continue
            dx, dz = direction(self.pos, shade.pos, (1, 0))
            points = TUNING["score"]["per_drain_stun" if shade.state == "drain" else "per_stun"]
            shade.state = "stunned"
            shade.target_lantern_id = None
            shade.drain_ticks = 0
            shade.remaining = ticks(TUNING["pulse_stun_s"])
            shade.impulse = (dx * TUNING["pulse_push_m"] / PULSE_PUSH_TICKS,
                              dz * TUNING["pulse_push_m"] / PULSE_PUSH_TICKS)
            shade.impulse_ticks = PULSE_PUSH_TICKS
            self.score += points
            self.event("shade_stunned", id=shade.id)
        for drifter in self.drifters:
            if math.dist(center, drifter.pos) > TUNING["pulse_radius"]:
                continue
            if drifter.state == "chase":
                self.send_fleeing(drifter, 240)
            elif drifter.state == "flee" and drifter.stolen:
                amount = drifter.stolen
                self.drop(drifter.pos, amount)
                drifter.stolen = 0
                drifter.remaining = 120
                self.event("drifter_drop", drifter_id=drifter.id, amount=amount)

    def drop(self, pos, count, spread=False):
        for _ in range(count):
            x, y, z = pos
            if spread:
                angle = self.rng.uniform(0, math.tau)
                radius = self.rng.uniform(1.5, 2.5)
                x += math.cos(angle) * radius
                z += math.sin(angle) * radius
            floor = ground(self.night, x, z)
            point = [x, y if floor is None else floor, z]
            self.motes.append(Mote(self.identifier("M"), point, "dropped", DROPPED_TTL))

    def displace_shade(self, shade, dx, dz, length):
        """Move a shade up to length, stopping at lit zones and terrain."""
        if length <= 0:
            return True
        for entry, leave in self.zone_intervals(shade.pos, dx, dz):
            if leave > 0 and (entry >= 0 or entry + leave > 0):
                length = min(length, max(0, entry))
        if not length:
            return False
        x, z = shade.pos[0] + dx * length, shade.pos[2] + dz * length
        floor = ground(self.night, x, z)
        previous_floor = ground(self.night, shade.pos[0], shade.pos[2])
        if (floor is None or (previous_floor is not None and floor - previous_floor > 0.25)
                or (self.night == 3 and floor == 6 and math.hypot(x, z) < 2)):
            return False
        shade.pos = [x, shade.pos[1] if floor == previous_floor else floor + 0.8, z]
        return True

    def move_shades(self):
        for shade in self.shades:
            separation = distance(self.pos, shade.pos)
            stopped_draining = False
            if shade.state == "drain":
                if self.drain_target(shade) is None:
                    shade.state = "wander"
                    stopped_draining = True
                elif not self.respawn_ticks and separation <= DRAIN_CHASE_RANGE:
                    shade.state = "chase"
                else:
                    continue
                shade.target_lantern_id = None
                shade.drain_ticks = 0
            if shade.evicting:
                self.evict_shade(shade)
                shade.impulse_ticks = max(0, shade.impulse_ticks - 1)
                continue
            if shade.state == "recoil" and not shade.impulse_ticks and shade.remaining:
                # A scenario may inject recoil without a preceding hit.
                dx, dz = direction(self.pos, shade.pos, (1, 0))
                shade.impulse = (dx * 2 / RECOIL_TICKS, dz * 2 / RECOIL_TICKS)
                shade.impulse_ticks = shade.remaining
            if shade.impulse_ticks:
                dx, dz = shade.impulse
                length = math.hypot(dx, dz)
                if length and not self.displace_shade(shade, dx / length, dz / length, length):
                    shade.impulse = (0, 0)
                shade.impulse_ticks -= 1
                if shade.state == "recoil" and not shade.impulse_ticks and not shade.remaining:
                    shade.state = "wander"
                continue
            if shade.state in ("spawning", "stunned", "recoil") or stopped_draining or shade.just_unstunned:
                continue
            if self.respawn_ticks or separation > 18:
                shade.state = "wander"
            if shade.state == "wander":
                weak = self.nearest_lantern(shade.pos, (lamp for lamp in self.lanterns if lamp.weak))
                if weak is not None:
                    gap = distance(shade.pos, weak.pos)
                    if gap > DRAIN_RANGE:
                        speed = 4.5 if self.night == 3 else TUNING["shade_speed"]
                        dx, dz = direction(shade.pos, weak.pos)
                        self.displace_shade(shade, dx, dz, min(gap, speed * DT))
                    if distance(weak.pos, shade.pos) <= DRAIN_RANGE:
                        self.start_drain(shade, weak)
                    continue
            if not self.respawn_ticks and separation <= 12:
                shade.state = "chase"
            speed = 4.5 if self.night == 3 else TUNING["shade_speed"]
            if shade.state == "chase":
                dx, dz = direction(shade.pos, self.pos, (0, 0))
                self.displace_shade(shade, dx, dz, min(separation, speed * DT))
                continue
            target = self.nearest_lantern(shade.pos, (lamp for lamp in self.lanterns if not lamp.lit))
            if target is None:
                dx, dz = shade.heading
                if not self.displace_shade(shade, dx, dz, speed * DT):
                    shade.heading = (-dz, dx)
                continue
            dx, dz = direction(shade.pos, target.pos, (0, 0))
            self.displace_shade(shade, dx, dz, min(distance(shade.pos, target.pos), speed * DT))

    @staticmethod
    def start_drain(shade, lamp):
        shade.state = "drain"
        shade.target_lantern_id = lamp.id
        shade.drain_ticks = 0

    def send_fleeing(self, drifter, duration):
        drifter.state = "flee"
        drifter.remaining = duration
        drifter.heading = direction(self.pos, drifter.pos, drifter.heading)

    def move_drifters(self):
        for drifter in self.drifters:
            if drifter.state == "flee":
                dx, dz = direction(self.pos, drifter.pos, drifter.heading)
                speed = 7
            elif self.carried >= 5 and distance(self.pos, drifter.pos) <= 15:
                drifter.state = "chase"
                dx, dz = direction(drifter.pos, self.pos, (0, 0))
                speed = 7
            else:
                drifter.state = "idle"
                dx, dz = drifter.heading
                speed = 2
            x, z = drifter.pos[0] + dx * speed * DT, drifter.pos[2] + dz * speed * DT
            if drifter.state == "idle" and ground(self.night, x, z) is None:
                drifter.heading = (-dz, dx)
            else:
                drifter.pos[0], drifter.pos[2] = x, z

    def collisions(self):
        for drifter in sorted(self.drifters, key=id_order):
            if drifter.state == "chase" and self.carried and distance(self.pos, drifter.pos) <= 1.2:
                amount = min(3, self.carried)
                self.carried -= amount
                drifter.stolen = amount
                self.send_fleeing(drifter, 240)
                self.event("drifter_steal", drifter_id=drifter.id, amount=amount, carried=self.carried)
        if self.invuln or not self.flames or self.zone(self.pos) is not None:
            return
        for shade in sorted(self.shades, key=id_order):
            if (shade.evicting or shade.state not in ("chase", "wander")
                    or not self.in_reach(shade.pos, TUNING["shade_hit_radius"])):
                continue
            self.flames -= 1
            self.invuln = ticks(TUNING["invuln_s"])
            shade.state = "recoil"
            shade.remaining = RECOIL_TICKS
            dx, dz = direction(self.pos, shade.pos, (1, 0))
            shade.impulse = (dx * 2 / RECOIL_TICKS, dz * 2 / RECOIL_TICKS)
            shade.impulse_ticks = RECOIL_TICKS
            lost = math.floor(self.carried * TUNING["hit_drop_ratio"])
            self.carried -= lost
            self.drop(self.pos, lost, spread=True)
            self.event("player_hit", id=shade.id, flames=self.flames, carried=self.carried)
            break

    def spawn(self):
        if self.random_motes and len(self.motes) < 30 and self.sim_tick % MOTE_SPAWN_TICKS == 0:
            occupied = {tuple(mote.pos) for mote in self.motes if mote.kind == "random"}
            available = [pos for pos in self.layout.motes if pos not in occupied]
            if available:
                self.motes.append(Mote(self.identifier("M"), list(self.rng.choice(available))))
        first = 5 * HZ
        if self.random_shades and self.sim_tick >= first and (self.sim_tick - first) % (self.layout.shade_period * HZ) == 0:
            count = 2 if self.sim_tick == first else 1
            occupied = {(shade.pos[0], shade.pos[2]) for shade in self.shades}
            eligible = [point for point in self.layout.mist if self.zone(point) is None
                        and (point[0], point[2]) not in occupied
                        and (self.night != 1 or distance(point, self.pos) >= 15)]
            count = min(count, self.layout.max_shades - len(self.shades), len(eligible))
            for x, y, z in self.rng.sample(eligible, max(0, count)):
                name = self.identifier("S")
                self.shades.append(Shade(name, [x, y + 0.8, z], "spawning", SHADE_SPAWNING_TICKS))
                self.event("shade_spawned", id=name)
        if self.random_drifters and self.night != 1 and self.sim_tick % 1200 == 0 and len(self.drifters) < 2:
            x, y, z = self.rng.choice(self.layout.mist)
            self.drifters.append(Drifter(self.identifier("D"), [x, y + 1, z],
                                         heading=direction((0, 0, 0), (-z, 0, x))))

    def finish(self, state, reason):
        self.state = state
        if state == "won":
            score = TUNING["score"]
            self.score += sum(score["per_dawn_lantern"] + (lamp.fuel_units // HZ) * score["per_dawn_fuel"]
                              for lamp in self.lanterns if lamp.lit)
            self.score += self.flames * score["per_flame_left"]
        self.event("game_over", state=state, score=self.score, reason=reason)

    def step(self, controls):
        self.events = []
        if self.state in ("won", "lost"):
            return self.events
        self.tick += 1
        pressed = {key: controls[key] and not self.previous[key] for key in BUTTONS}
        self.previous = controls.copy()
        if pressed["pause"]:
            if self.state == "playing":
                self.state = "paused"
                self.event("paused")
                return self.events
            self.state = "playing"
            self.event("resumed")
        if self.state == "paused":
            return self.events
        self.sim_tick += 1
        self.counters()
        self.consume_fuel()
        available = self.flames and not self.recover()
        if available:
            self.move(controls, pressed)
        available = available and self.flames and not self.respawn_ticks
        if available:
            self.pickup()
            if pressed["interact"]:
                self.deposit()
        if self.flames:
            self.clear_zones()
            if available and pressed["pulse"]:
                self.pulse()
            self.move_shades()
            self.move_drifters()
            if available:
                self.collisions()
            self.spawn()
        if not self.flames:
            self.finish("lost", "no_flames")
        elif self.time_left <= 0:
            if sum(lamp.lit for lamp in self.lanterns) >= self.required_lights:
                self.finish("won", "dawn_survived")
            else:
                self.finish("lost", "dawn")
        return self.events

    def snapshot(self):
        return {
            "type": "snapshot", "night": self.night, "tick": self.tick, "sim_tick": self.sim_tick,
            "state": self.state, "time_left_s": self.time_left, "score": self.score,
            "wind": {"active": self.wind_active, "dir_deg": self.wind_angle},
            "player": {
                "pos": position(self.pos), "vel": position(self.vel), "grounded": self.grounded,
                "flames": self.flames, "carried": self.carried, "capacity": self.capacity,
                "invuln": bool(self.invuln),
                "dash_cd_s": self.dash_cd / HZ, "pulse_cd_s": self.pulse_cd / HZ,
                "charm_s": self.charm_ticks / HZ,
            },
            "lanterns": [{"id": l.id, "pos": position(l.pos), "lit": l.lit, "deposited": l.deposited,
                          "fuel": l.fuel, "ever_lit": l.ever_lit, "relit_count": l.relit_count}
                         for l in self.lanterns],
            "shades": [{"id": s.id, "pos": position(s.pos), "state": s.state} for s in self.shades],
            "motes_active": len(self.motes),
            "motes": [{"id": m.id, "pos": position(m.pos), "kind": m.kind,
                       "ttl_s": None if m.ttl is None else m.ttl / HZ} for m in self.motes],
            "drifters": [{"id": d.id, "pos": position(d.pos), "state": d.state, "stolen": d.stolen}
                         for d in self.drifters],
            "charms": [{"id": c.id, "available": c.available, "respawn_s": c.remaining / HZ}
                       for c in self.charms],
        }

    def end(self):
        return dict(type="end", ticks=self.tick, state=self.state, score=self.score)
