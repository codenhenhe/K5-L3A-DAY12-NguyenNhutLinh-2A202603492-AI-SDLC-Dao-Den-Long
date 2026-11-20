"""The three layouts in Ticket-02. Coordinates use metres and Y-up."""
from dataclasses import dataclass
import math


def ring(x, z, radius, count, start=0, height=0, step=None):
    increment = 360 / count if step is None else step
    return tuple(
        (x + radius * math.cos(math.radians(start + i * increment)), height,
         z + radius * math.sin(math.radians(start + i * increment)))
        for i in range(count)
    )


@dataclass(frozen=True)
class Layout:
    islands: tuple
    lanterns: tuple
    motes: tuple
    mist: tuple
    shade_period: int
    max_shades: int
    start: tuple = (0, 0, 0)
    pads: tuple = ()
    charms: tuple = ()

    def view(self):
        return {"islands": self.islands, "pads": [pad[0] for pad in self.pads],
                "charms": self.charms}


LAYOUTS = {
    1: Layout(
        ((0, 0, 40),),
        ((0, 0, 25), (23.8, 0, 7.7), (14.7, 0, -20.2), (-14.7, 0, -20.2), (-23.8, 0, 7.7)),
        ring(0, 0, 12, 8) + ring(0, 0, 33, 16),
        ring(0, 0, 37, 12, 15), 8, 6,
    ),
    2: Layout(
        ((0, 0, 28), (70, 0, 28)),
        ((0, 0, 20), (17, 0, -10), (-17, 0, -10), (70, 0, 20), (87, 0, -10), (53, 0, -10)),
        tuple(pos for x in (0, 70) for pos in ring(x, 0, 10, 4) + ring(x, 0, 22, 8)),
        ring(0, 0, 26, 8, 22.5) + ring(70, 0, 26, 8, 22.5), 7, 8,
        pads=(((20, 0, 18), (70, 0), 24, 14), ((50, 0, -18), (0, 0), 24, 14)),
        charms=((35, 0, 0),),
    ),
    3: Layout(
        ((0, 0, 45),),
        ((0, 6, 6), (18, 3, 10), (-18, 3, 10), (35, 0, -10), (-35, 0, -10), (20, 0, -35), (-20, 0, -35)),
        ring(0, 0, 34, 18) + ring(0, 0, 18, 8, 20, 3, 20) + ring(0, 0, 5, 4, 45, 6),
        ring(0, 0, 43, 16), 6, 10,
        start=(0, 0, -12), pads=(((0, 3, 13), (0, 0), 8, 12),),
        charms=((30, 0, 25), (-30, 0, 25)),
    ),
}

RAMPS = tuple((math.cos(math.radians(a)), math.sin(math.radians(a))) for a in (30, 150))


def ground(night, x, z):
    """Return the top of the terrain, or None over the cloud sea."""
    if night == 2 and 26 <= x <= 44 and abs(z) <= 2:
        return 0
    if not any(math.hypot(x - cx, z - cz) <= radius for cx, cz, radius in LAYOUTS[night].islands):
        return None
    if night != 3:
        return 0
    radius = math.hypot(x, z)
    if radius <= 8:
        return 6
    for dx, dz in RAMPS:
        along, side = x * dx + z * dz, -x * dz + z * dx
        if 23.9 <= along <= 30 and abs(side) <= 1.5:
            return min(3, (30 - along) / 2)
    return 3 if z > 0 and 12 <= radius <= 24 else 0
