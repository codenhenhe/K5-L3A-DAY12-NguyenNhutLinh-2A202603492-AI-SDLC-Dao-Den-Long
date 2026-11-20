"use strict";

const canvas = document.querySelector("#island");
const ctx = canvas.getContext("2d");
const fields = Object.fromEntries(["flames", "motes", "lamps", "time", "score", "notice", "curtain", "title",
    "description", "hud", "actions", "eyebrow", "settings", "volume", "sensitivity", "night-label",
    "dash-cd", "pulse-cd", "wind", "charm-timer", "benchmark", "controls"]
    .map(id => [id, document.getElementById(id)]));

const STEP = 1000 / 60;
const TAU = 2 * Math.PI;
const palette = {
    sky: "#0E1430", fog: "#1B2350",
    grass: "#2F5D50", sand: "#C9B48A", wood: "#6B4A2F", cloudSea: "#12384A",
    lamp: "#FFB347", lampCore: "#FFE9B0", lampOff: "#5B5F6E",
    moteCore: "#FFF6C2", moteGlow: "#FFE58A",
    shade: "#120A1A", shadeOutline: "#7A3CFF", shadeStunned: "#3A3450",
    mayShirt: "#E8E2D0", red: "#C8102E", gold: "#F2C14E", drifter: "#8FA3B8",
};
const actions = {jump: ["Space"], interact: ["KeyE"], pulse: ["KeyF"],
    dash: ["ShiftLeft", "ShiftRight"], pause: ["Escape", "KeyP"]};
const bound = new Set(["KeyW", "KeyA", "KeyS", "KeyD", "ArrowLeft", "ArrowRight", ...Object.values(actions).flat()]);
const keys = new Set();
const latched = new Set();
let snapshot, tuning, session;
let layout = {islands: [[0, 0, 40]], pads: [], charms: []};
let yaw = 0, accumulator = 0, last = 0, busy = false, running = false;
let pulseAt = -Infinity, hitAt = -Infinity;
let facing = 0;
let viewport = {width: 900, height: 600};
let night = 1, screen = "menu", settingsBack = "menu", windWarning = false, previousSecond = Infinity;
let totalScore = 0;
const nights = [
    {name: "Đảo Bến", quote: "Đom đóm vẫn nhớ đường về. Con hãy mang chúng tới năm ngọn đèn."},
    {name: "Đảo Sương", quote: "Cầu tre nối hai bờ. Nếu gặp Gió Lạc, hãy giữ ánh sáng thật gần."},
    {name: "Đảo Chuông", quote: "Theo dốc lên triền cao. Khi gió lặng, hãy thắp đèn cạnh tháp chuông."}
];
const lanternPlaces = [[0, 25], [23.8, 7.7], [14.7, -20.2], [-14.7, -20.2], [-23.8, 7.7]];
const preview = {player: {pos: [0, 0, 0]}, lanterns: lanternPlaces.map(([x, z], i) => ({
    id: "L" + (i + 1), pos: [x, 0, z], lit: i === 0, deposited: 0
})), shades: [], motes: [], drifters: [], charms: [], wind: {active: false}};

const plants = Array.from({length: 44}, (_, i) => {
    const a = i * 2.3999632;
    const r = 15 + (i * 13 % 19);
    return {pos: [Math.cos(a) * r, 0, Math.sin(a) * r], size: 0.65 + (i * 7 % 11) / 12, tree: i % 3 === 0};
});
const stars = Array.from({length: 95}, (_, i) => [((i * 307) % 977) / 977, ((i * 191) % 991) / 991, i % 7 === 0]);
const rocks = Array.from({length: 133}, (_, i) => {
    const a = i * 2.3999632;
    const r = 35 * Math.sqrt(((i * 79) % 139) / 139);
    return [r * Math.cos(a), 0.015, r * Math.sin(a), 0.1 + (i * 7 % 10) / 32];
});

function resize() {
    const scale = Math.min(devicePixelRatio || 1, 2);
    viewport = {width: canvas.clientWidth, height: canvas.clientHeight};
    canvas.width = Math.max(1, Math.round(viewport.width * scale));
    canvas.height = Math.max(1, Math.round(viewport.height * scale));
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
}
window.addEventListener("resize", resize);
resize();

function polygon(points, color) {
    if (points.length < 3) return;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(points[0][0], points[0][1]);
    for (const [x, y] of points.slice(1)) ctx.lineTo(x, y);
    ctx.closePath();
    ctx.fill();
}

function camera(player) {
    const forward = [Math.sin(yaw), Math.cos(yaw)];
    const distanceBack = 9.6, height = 6.2;
    const shoulder = 1.25;
    const origin = [player[0] - forward[0] * distanceBack + forward[1] * shoulder,
        player[1] + height, player[2] - forward[1] * distanceBack - forward[0] * shoulder];
    const pitch = 0.38;
    const cosPitch = Math.cos(pitch), sinPitch = Math.sin(pitch);
    const focal = viewport.height * 0.96;
    const cx = viewport.width / 2, cy = viewport.height * 0.49;
    function local([x, y, z]) {
        const dx = x - origin[0], dy = y - origin[1], dz = z - origin[2];
        const ahead = dx * forward[0] + dz * forward[1];
        return [dx * forward[1] - dz * forward[0], dy * cosPitch + ahead * sinPitch,
            ahead * cosPitch - dy * sinPitch];
    }
    function screen([x, y, z]) {
        return [cx + x * focal / z, cy - y * focal / z, focal / z];
    }
    function worldPolygon(points, color, gradient = null) {
        const near = 0.20;
        const vertices = points.map(local);
        const clipped = [];
        for (let i = 0; i < vertices.length; i++) {
            const a = vertices[i], b = vertices[(i + 1) % vertices.length];
            if (a[2] >= near) clipped.push(a);
            if ((a[2] >= near) !== (b[2] >= near)) {
                const t = (near - a[2]) / (b[2] - a[2]);
                clipped.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, near]);
            }
        }
        polygon(clipped.map(screen), gradient || color);
    }
    function project(point) {
        const location = local(point);
        return location[2] > 0.2 ? screen(location) : null;
    }
    return {local, project, worldPolygon};
}

function ring([x, y, z], size, sides = 32, rotation = 0) {
    return Array.from({length: sides}, (_, index) => [
        x + size * Math.cos(index * TAU / sides + rotation), y,
        z + size * Math.sin(index * TAU / sides + rotation)
    ]);
}

function solid(cam, base, top, colors) {
    const sides = base.map((point, i) => {
        const j = (i + 1) % base.length;
        const face = [point, base[j], top[j], top[i]];
        const depth = face.reduce((sum, vertex) => sum + cam.local(vertex)[2], 0);
        return {face, depth, color: colors[i % colors.length]};
    });
    sides.sort((a, b) => b.depth - a.depth).forEach(side => cam.worldPolygon(side.face, side.color));
    cam.worldPolygon(top, colors[colors.length - 1]);
}

function frustum(cam, [x, y, z], from, to, height, colors, edges = 8, angle = 0) {
    solid(cam, ring([x, y, z], from, edges, angle), ring([x, y + height, z], to, edges, angle), colors);
}

function glow(x, y, size, from, edge) {
    if (size <= 0 || !Number.isFinite(size)) return;
    const grad = ctx.createRadialGradient(x, y, 0, x, y, size);
    grad.addColorStop(0, from);
    grad.addColorStop(1, edge);
    ctx.fillStyle = grad;
    ctx.fillRect(x - size, y - size, size * 2, size * 2);
}

function dot(x, y, size, color) {
    ctx.beginPath();
    ctx.arc(x, y, size, 0, TAU);
    ctx.fillStyle = color;
    ctx.fill();
}

function drawSky(now) {
    const {width, height} = viewport;
    const sky = ctx.createLinearGradient(0, 0, 0, height);
    for (const [at, color] of [[0, palette.sky], [.38, palette.sky], [.53, palette.fog],
        [.66, palette.cloudSea], [1, palette.cloudSea]]) {
        sky.addColorStop(at, color);
    }
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, width, height);
    for (const [u, v, bright] of stars) {
        const x = (((u - yaw / TAU) % 1) + 1) % 1 * width;
        dot(x, v * height * 0.47, bright ? 1.5 : 0.7, bright ? "#f6e5c0c7" : "#d8dcec87");
    }
    const moonX = width * (0.72 - 0.16 * Math.sin(yaw)), moonY = height * 0.23;
    glow(moonX, moonY, 112, "#ffe5b154", "#ffe5b100");
    dot(moonX, moonY, Math.max(19, height * 0.044), "#fff1c8");
    for (let i = 0; i < 13; i++) {
        const x = ((width * i * 0.113 + now * (0.003 + (i % 4) * 0.001)) % (width + 240)) - 120;
        const y = height * (0.51 + (i % 4) * 0.046);
        ctx.save();
        ctx.translate(x, y);
        ctx.scale(1, 0.24);
        glow(0, 0, 150 + (i % 3) * 42, palette.fog + "c9", palette.fog + "00");
        ctx.restore();
    }
}

function drawIsland(cam, lit, count) {
    const ambient = 0.15 + 0.55 * lit / count;
    const grass = "rgb(" + palette.grass.slice(1).match(/../g)
        .map(channel => Math.round(parseInt(channel, 16) * (.94 + .15 * ambient))) + ")";
    const islands = [...layout.islands].sort((a, b) => cam.local([b[0], 0, b[1]])[2] - cam.local([a[0], 0, a[1]])[2]);
    for (const [cx, cz, radius] of islands) {
        cam.worldPolygon(ring([cx, -1.9, cz], radius, 64), "#222b41");
        cam.worldPolygon(ring([cx, 0, cz], radius, 64), palette.sand);
        cam.worldPolygon(ring([cx, .002, cz], radius - .85, 64), grass);
        for (const [x, y, z, size] of rocks) {
            if (Math.hypot(x, z) >= radius - 1 || (night === 3 && (Math.hypot(x, z) <= 8 ||
                (z > 0 && Math.hypot(x, z) >= 12 && Math.hypot(x, z) <= 24)))) continue;
            if (!cam.project([x + cx, y, z + cz])) continue;
            cam.worldPolygon(ring([x + cx, y, z + cz], size, 4, x), size > 0.25 ? "#7a766b55" : "#142f3277");
        }
    }
    if (night === 2) {
        for (let i = 26; i < 44; i += 0.6) {
            const end = Math.min(44, i + 0.54);
            cam.worldPolygon([[i, 0.03, -2], [end, 0.03, -2], [end, 0.03, 2], [i, 0.03, 2]],
                Math.floor(i * 3) % 2 ? palette.wood : "#745033");
        }
    } else if (night === 3) {
        const arc = (r, y, start, end) => Array.from({length: 25}, (_, i) => {
            const a = start + (end - start) * i / 24;
            return [r * Math.cos(a), y, r * Math.sin(a)];
        });
        const outer = arc(24, 3, 0, Math.PI);
        const inner = arc(12, 3, Math.PI, 0);
        for (const edge of [outer, inner]) {
            for (let i = 0; i < edge.length - 1; i++) {
                const a = edge[i], b = edge[i + 1];
                cam.worldPolygon([a, b, [b[0], 0, b[2]], [a[0], 0, a[2]]], i % 2 ? "#4f4759" : "#514a60");
            }
        }
        cam.worldPolygon([...outer, ...inner], grass);
        for (const angle of [30, 150]) {
            const a = angle * Math.PI / 180, x = Math.cos(a), z = Math.sin(a);
            const at = (radius, side, y) => [x * radius - z * side, y, z * radius + x * side];
            cam.worldPolygon([at(24, -1.5, 3), at(24, 1.5, 3), at(30, 1.5, 0.02), at(30, -1.5, 0.02)], palette.wood);
        }
        solid(cam, ring([0, 0, 0], 8, 32), ring([0, 6, 0], 8, 32), ["#4f4757", "#5b5160", grass]);
    }
    for (const [x, y, z] of layout.pads) {
        cam.worldPolygon(ring([x, y + 0.025, z], 1, 14), "#d19353");
        cam.worldPolygon(ring([x, y + 0.035, z], 0.75, 4), "#f0bd6a");
    }
}

function drawPlant(cam, plant) {
    const [x, y, z] = plant.pos, s = plant.size;
    if (plant.tree) {
        frustum(cam, plant.pos, 0.21 * s, 0.12 * s, s * 2.2, [palette.wood, "#745033"], 5);
        frustum(cam, [x, y + s * 1.0, z], 1.4 * s, 0.07, s * 2.3, ["#23424c", "#375d5b", "#305154"], 6);
        frustum(cam, [x, y + s * 1.9, z], 0.95 * s, 0.02, s * 2.0, ["#365e60", "#446d69", "#31535e"], 6);
    } else {
        frustum(cam, plant.pos, s * 0.43, s * 0.17, s * 0.44, ["#555770", "#62617b", "#414b63"], 5);
    }
}

function drawLamp(cam, lamp) {
    const [x, y, z] = lamp.pos;
    const at = cam.project([x, y + 2.7, z]);
    frustum(cam, lamp.pos, 0.82, 0.63, 0.24, ["#566175", "#71778a", "#43495e"], 6);
    frustum(cam, [x, y + 0.24, z], 0.21, 0.13, 2.0, [palette.wood, "#745033"], 6);
    frustum(cam, [x, y + 2.2, z], 0.60, 0.84, 0.37, ["#775052", "#b48260"], 6);
    frustum(cam, [x, y + 2.56, z], 0.76, 0.68, 0.70,
        lamp.lit ? [palette.lamp, "#f4a741", palette.lamp] : [palette.lampOff, "#606473", palette.lampOff], 6);
    frustum(cam, [x, y + 3.26, z], 0.89, 0.18, 0.45, ["#733e50", "#ac6562", "#844757"], 6);
    if (at && lamp.lit) {
        glow(at[0], at[1], at[2] * 2.9, palette.lamp + "8c", palette.lamp + "00");
        dot(at[0], at[1], Math.max(1, at[2] * .11), palette.lampCore);
    }
}

function drawMote(cam, mote, now) {
    const [x, y, z] = mote.pos;
    const at = cam.project([x, y + 0.67 + 0.14 * Math.sin(now * 0.004 + x + z), z]);
    if (!at) return;
    const [sx, sy, scale] = at;
    const r = Math.max(1.2, scale * 0.09);
    glow(sx, sy, r * 5, palette.moteGlow, palette.moteGlow + "00");
    dot(sx, sy, r, palette.moteCore);
}

function drawShade(cam, shade, now) {
    const [x, y, z] = shade.pos;
    const at = cam.project([x, y + Math.sin(now * 0.005 + x) * 0.14, z]);
    if (!at) return;
    const [sx, sy, scale] = at, r = Math.max(3, scale * 0.54);
    const stunned = shade.state === "stunned";
    glow(sx, sy, r * 2.3, palette.shadeOutline + "8c", palette.shadeOutline + "00");
    ctx.fillStyle = stunned ? palette.shadeStunned : palette.shade;
    ctx.beginPath();
    ctx.ellipse(sx, sy, r, r * 1.28, Math.sin(now * 0.003) * 0.16, 0, TAU);
    ctx.fill();
    ctx.strokeStyle = palette.shadeOutline;
    ctx.lineWidth = Math.max(1, r * .075);
    ctx.stroke();
    const eyes = stunned ? "#ffd477" : "#de8bf4";
    dot(sx - r * 0.35, sy - r * 0.18, Math.max(1, r * 0.11), eyes);
    dot(sx + r * 0.35, sy - r * 0.18, Math.max(1, r * 0.11), eyes);
}

function drawDrifter(cam, drifter, now) {
    const at = cam.project(drifter.pos);
    if (!at) return;
    const [x, y, scale] = at, size = Math.max(3, scale * 0.55);
    const wave = Math.sin(now / 160) * size * 0.47;
    glow(x, y, size * 3, "#8ba9b871", "#8ba9b800");
    polygon([[x - 2 * size, y + wave], [x - size, y - size * 0.55],
        [x + 1.5 * size, y - size * .25], [x + size, y + size * .5],
        [x - size * .6, y + size * .2]], palette.drifter);
    if (drifter.stolen) dot(x + size * .3, y, size * 0.18, "#ffc561");
}

function drawCharm(cam, pos, now) {
    const at = cam.project([pos[0], pos[1] + 0.7 + Math.sin(now / 240) * 0.12, pos[2]]);
    if (!at) return;
    const [x, y, s] = at, r = Math.max(3, s * 0.28);
    glow(x, y, r * 3, "#e78a5484", "#e78a5400");
    polygon([[x, y - r * 1.3], [x + r * 0.6, y], [x, y + r * 1.3], [x - r * .6, y]], palette.gold);
    polygon([[x, y - r], [x + r * .42, y], [x, y + r], [x - r * .42, y]], palette.red);
}

function drawMay(cam, pos, now) {
    const [x, y, z] = pos;
    const walking = running && movement().some(Boolean);
    const gait = walking ? 0.22 * Math.sin(now * 0.016) : 0;
    for (const side of [-1, 1]) {
        const dx = Math.cos(facing) * side * 0.16 + Math.sin(facing) * side * gait;
        const dz = -Math.sin(facing) * side * 0.16 + Math.cos(facing) * side * gait;
        frustum(cam, [x + dx, y, z + dz], 0.12, 0.11, 0.48, ["#2c2940", "#454059"], 6);
    }
    frustum(cam, [x, y + 0.34, z], 0.40, 0.28, 0.73, [palette.mayShirt, "#ddd6c2"], 8);
    frustum(cam, [x, y + 0.94, z], .32, .27, .14, [palette.red], 8);
    frustum(cam, [x, y + 0.98, z], 0.23, 0.23, 0.36, ["#d89f79", "#efbc90", "#583d4f"], 8);
    frustum(cam, [x, y + 1.28, z], 0.57, 0.025, 0.40, ["#c99a54", "#ffdf91", "#d4a75e"], 10);
    const lampPos = [x + 0.56 * Math.cos(facing), y + 0.95, z - 0.56 * Math.sin(facing)];
    const light = cam.project(lampPos);
    const knot = cam.project([lampPos[0], y + 1.29, lampPos[2]]);
    if (light && knot) {
        ctx.strokeStyle = "#684734";
        ctx.lineWidth = Math.max(1, light[2] * 0.026);
        ctx.beginPath();
        ctx.moveTo(knot[0], knot[1]);
        ctx.lineTo(light[0], light[1] - light[2] * 0.19);
        ctx.stroke();
        glow(light[0], light[1], 0.94 * light[2], "#ffb73c99", "#ffc75600");
        frustum(cam, lampPos, 0.10, 0.11, 0.21, ["#ffbc59", "#ffe6a0", "#fff3c0"], 6);
    }
}

function draw(now) {
    const world = snapshot || preview;
    const pos = world.player.pos;
    const cam = camera([pos[0], Math.max(0, pos[1]), pos[2]]);
    drawSky(now);
    const lit = world.lanterns.filter(lamp => lamp.lit);
    drawIsland(cam, lit.length, world.lanterns.length);
    for (const lamp of lit) {
        const place = cam.project(lamp.pos);
        if (place) {
            ctx.save();
            ctx.translate(place[0], place[1]);
            ctx.scale(1, 0.40);
            glow(0, 0, Math.min(350, place[2] * 4.6), "#ffc36571", "#ef9e4200");
            ctx.restore();
        }
    }
    const objects = [];
    const queue = (point, drawObject) => {
        const depth = cam.local(point)[2];
        const at = cam.project(point);
        if (at && at[0] > -250 && at[0] < viewport.width + 250) objects.push({depth, drawObject});
    };
    for (const [x, z, radius] of layout.islands) {
        for (const plant of plants) {
            const [px, , pz] = plant.pos;
            if (Math.hypot(px, pz) >= radius - 2) continue;
            if (night === 3 && pz > 0 && Math.hypot(px, pz) <= 31) continue;
            const pos = [x + px, 0, z + pz];
            queue(pos, () => drawPlant(cam, {...plant, pos}));
        }
    }
    for (const lamp of world.lanterns) queue(lamp.pos, () => drawLamp(cam, lamp));
    for (const mote of world.motes) queue(mote.pos, () => drawMote(cam, mote, now));
    for (const shade of world.shades) queue(shade.pos, () => drawShade(cam, shade, now));
    for (const drifter of world.drifters) queue(drifter.pos, () => drawDrifter(cam, drifter, now));
    for (const charm of world.charms) {
        const location = layout.charms[Number(charm.id.slice(1)) - 1];
        if (charm.available && location) queue(location, () => drawCharm(cam, location, now));
    }
    if (night === 3) queue([0, 6, 0], () => {
        frustum(cam, [0, 6, 0], 2, 2, 7, ["#646079", "#777083", "#534f65"], 12);
        frustum(cam, [0, 13, 0], 2, .15, 1, ["#824954", "#a46464"], 12);
    });
    queue(pos, () => drawMay(cam, pos, now));
    objects.sort((a, b) => b.depth - a.depth).forEach(object => object.drawObject());
    const elapsed = now - pulseAt;
    if (elapsed < 650) {
        const size = 0.35 + 5 * elapsed / 650;
        const outer = ring([pos[0], 0.04, pos[2]], size, 36);
        const inner = ring([pos[0], 0.04, pos[2]], size - 0.17, 36);
        for (let i = 0; i < outer.length; i++) {
            const j = (i + 1) % outer.length;
            cam.worldPolygon([outer[i], outer[j], inner[j], inner[i]], "rgba(255,209,114," + (1 - elapsed / 650) + ")");
        }
    }
    if (now - hitAt < 350) {
        ctx.fillStyle = "rgba(108,52,150," + (0.26 * (1 - (now - hitAt) / 350)) + ")";
        ctx.fillRect(0, 0, viewport.width, viewport.height);
    }
    if (running) {
        drawGuide(cam, world);
        if (world.wind.active || windWarning) drawLeaves(now, world.wind.dir_deg);
    }
}

function nearestLantern(world) {
    const [x, , z] = world.player.pos;
    let nearest = null, closest = Infinity;
    for (const lamp of world.lanterns) {
        const range = Math.hypot(x - lamp.pos[0], z - lamp.pos[2]);
        if (!lamp.lit && range < closest) {
            nearest = lamp;
            closest = range;
        }
    }
    return nearest;
}

function drawGuide(cam, world) {
    const target = nearestLantern(world);
    if (!target) return;
    const [x, y, z] = target.pos;
    const at = cam.project([x, y + 3, z]);
    const {width, height} = viewport;
    if (at && at[0] >= 0 && at[0] <= width && at[1] >= 0 && at[1] <= height) return;
    const [side, up, ahead] = cam.local([x, y + 3, z]);
    const angle = ahead < 0 ? (side < 0 ? -2.3 : 2.3) : Math.atan2(side, up);
    const px = width / 2 + Math.sin(angle) * (width / 2 - 45);
    const py = height / 2 - Math.cos(angle) * Math.max(50, height / 2 - 125);
    ctx.save();
    ctx.translate(px, py);
    ctx.rotate(angle);
    dot(0, 0, 17, "#24213ce8");
    polygon([[0, -12], [8, 6], [0, 3], [-8, 6]], "#ffe1a0");
    ctx.restore();
}

function drawLeaves(now, directionDeg) {
    const {width, height} = viewport, angle = directionDeg * Math.PI / 180 - yaw;
    ctx.save();
    ctx.fillStyle = "#edbf6cad";
    for (let i = 0; i < 28; i++) {
        const x = ((i * 191 + now * (.21 * Math.cos(angle) + .06)) % width + width) % width;
        const y = ((i * 83 + now * (.08 * Math.sin(angle) + .02)) % height + height) % height;
        ctx.beginPath();
        ctx.ellipse(x, y, 3 + i % 4, 1.4, angle + Math.sin(now / 100 + i), 0, TAU);
        ctx.fill();
    }
    ctx.restore();
}

let settings = {volume: .45, sensitivity: 1};
try {
    const saved = JSON.parse(localStorage.getItem("lantern-settings"));
    for (const [key, min, max] of [["volume", 0, 1], ["sensitivity", .25, 2.5]]) {
        if (Number.isFinite(saved?.[key])) settings[key] = Math.min(max, Math.max(min, saved[key]));
    }
} catch { /* Storage may be disabled by browser preferences. */ }
sound.gain(settings.volume);
for (const key of Object.keys(settings)) {
    const input = fields[key];
    input.value = settings[key];
    input.addEventListener("input", () => {
        settings[key] = Number(input.value);
        sound.gain(settings.volume);
        try { localStorage.setItem("lantern-settings", JSON.stringify(settings)); } catch {}
    });
}

function setText(field, value) {
    if (field.textContent !== String(value)) field.textContent = value;
}

function updateHUD() {
    const {player, lanterns, score, time_left_s: time, wind} = snapshot;
    if (fields.flames.children.length !== tuning.flames) {
        fields.flames.replaceChildren(...Array.from({length: tuning.flames}, () => {
            const icon = document.createElement("span");
            icon.textContent = "✦";
            return icon;
        }));
    }
    [...fields.flames.children].forEach((icon, index) => icon.classList.toggle("empty", index >= player.flames));
    fields.flames.setAttribute("aria-label", player.flames + " ngọn lửa");
    if (fields.motes.children.length !== tuning.carry_capacity) {
        fields.motes.replaceChildren(...Array.from({length: tuning.carry_capacity}, () => document.createElement("i")));
    }
    [...fields.motes.children].forEach((cell, index) => cell.classList.toggle("filled", index < player.carried));
    fields.motes.setAttribute("aria-label", player.carried + "/" + tuning.carry_capacity + " đom đóm");
    setText(fields.lamps, lanterns.filter(lamp => lamp.lit).length + "/" + lanterns.length);
    const seconds = Math.ceil(Math.max(0, time));
    setText(fields.time, Math.floor(seconds / 60) + ":" + String(seconds % 60).padStart(2, "0"));
    fields.time.classList.toggle("urgent", seconds <= 30);
    if (seconds >= 1 && seconds <= 10 && seconds !== previousSecond && running) sound.effect("countdown");
    previousSecond = seconds;
    setText(fields.score, score);
    setText(fields["dash-cd"], player.dash_cd_s ? player.dash_cd_s.toFixed(1) + "s" : "Sẵn sàng");
    setText(fields["pulse-cd"], player.pulse_cd_s ? player.pulse_cd_s.toFixed(1) + "s" :
        player.carried >= tuning.pulse_cost ? "Sẵn sàng" : tuning.pulse_cost + " đốm");
    const charm = fields["charm-timer"];
    charm.hidden = player.charm_s <= 0;
    setText(charm, "Bùa gió " + Math.ceil(player.charm_s) + "s");
    const [x, y, z] = player.pos;
    const nearby = lanterns.map(lamp => ({lamp, distance: Math.hypot(x - lamp.pos[0], y - lamp.pos[1], z - lamp.pos[2])}))
        .filter(entry => !entry.lamp.lit && entry.distance <= tuning.interact_radius)
        .sort((a, b) => a.distance - b.distance)[0]?.lamp;
    setText(fields.notice, y < -10 ? "Mây đang trở về đảo…" :
        nearby && running ? "E — Nạp ánh sáng (" + nearby.deposited + "/" + tuning.lantern_cost + ")" : "");
    fields.wind.hidden = !wind.active && !windWarning;
    setText(fields.wind, wind.active ? "Gió mạnh" : "Gió mạnh sắp đến");
}

async function request(path, data) {
    const response = await fetch(path, {
        method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Không kết nối được với trò chơi");
    return result;
}

function overlay(id, title, description, buttons, eyebrow = "") {
    screen = id;
    running = false;
    sound.playing(false);
    fields.curtain.hidden = false;
    fields.settings.hidden = id !== "settings";
    fields.eyebrow.hidden = !eyebrow;
    setText(fields.eyebrow, eyebrow);
    setText(fields.title, title);
    setText(fields.description, description);
    fields.actions.replaceChildren(...buttons.map(([label, action], index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = label;
        if (index) button.classList.add("secondary");
        button.addEventListener("click", action);
        return button;
    }));
    fields.actions.firstElementChild?.focus();
}

function showMenu() {
    snapshot = null;
    night = 1;
    totalScore = 0;
    yaw = 0;
    layout = {islands: [[0, 0, 40]], pads: [], charms: []};
    fields.hud.hidden = true;
    overlay("menu", "Đảo Đèn Lồng", "Theo Mây qua ba đêm, gom đom đóm và thắp đèn tìm đường về bình minh.",
        [["Bắt đầu", () => showIntro(1)], ["Cài đặt", () => showSettings("menu")]]);
}

function showIntro(targetNight) {
    night = targetNight;
    const current = nights[night - 1];
    overlay("intro", current.name, "Ông Đăng: “" + current.quote + "”",
        [["Vào đảo", start], ["Về menu", showMenu]], "ĐÊM " + night);
}

function showPause() {
    overlay("pause", "Tạm dừng", "Đêm " + night + " · " + nights[night - 1].name,
        [["Tiếp tục", resume], ["Chơi lại Đêm", start], ["Cài đặt", () => showSettings("pause")],
            ["Về menu", showMenu]]);
}

function showSettings(back) {
    settingsBack = back;
    overlay("settings", "Cài đặt", "Điều chỉnh âm lượng và độ nhạy khi kéo chuột.",
        [["Quay lại", () => settingsBack === "pause" ? showPause() : showMenu()]]);
}

function showEnd() {
    const {state, score} = snapshot;
    if (state === "won") {
        totalScore += score;
        if (night === 3) {
            overlay("dawn", "Bình Minh", "Cả ba hòn đảo đã sáng đèn. Tổng điểm: " + totalScore + ".",
                [["Về menu", showMenu]], "ĐẢO ĐÃ SÁNG");
        } else {
            overlay("result", "Đêm " + night + " đã sáng!", "Điểm Đêm: " + score + " · Tổng: " + totalScore,
                [["Đêm kế tiếp", () => showIntro(night + 1)], ["Về menu", showMenu]]);
        }
    } else {
        const reason = snapshot.player.flames === 0 ? "Ngọn lửa cuối đã tắt." : "Mây đã hết thời gian.";
        overlay("result", "Đêm còn dài", reason + " Điểm Đêm: " + score + ".",
            [["Chơi lại Đêm", start], ["Về menu", showMenu]]);
    }
}

function activate() {
    screen = "playing";
    running = true;
    accumulator = 0;
    keys.clear();
    latched.clear();
    fields.curtain.hidden = true;
    fields.hud.hidden = false;
    sound.playing(true);
    updateHUD();
}

async function start() {
    if (busy) return;
    busy = true;
    sound.unlock();
    try {
        const result = await request("/api/start", {session, night});
        ({session, snapshot, tuning, layout, wind_warning: windWarning} = result);
        yaw = facing = 0;
        pulseAt = hitAt = -Infinity;
        previousSecond = Infinity;
        setText(fields["night-label"], "ĐÊM " + night + " · " + nights[night - 1].name.toUpperCase());
        activate();
    } catch (error) {
        overlay("error", "Chưa vào được đảo", error.message, [["Thử lại", start], ["Về menu", showMenu]]);
    } finally {
        busy = false;
    }
}

async function resume() {
    if (busy) return;
    busy = true;
    try {
        await request("/api/step", {session, ticks: 1, controls: {pause: false}});
        const result = await request("/api/step", {session, ticks: 1, controls: {pause: true}});
        ({snapshot, wind_warning: windWarning} = result);
        if (snapshot.state === "playing") activate();
        else showEnd();
    } catch (error) {
        overlay("error", "Mất kết nối", error.message, [["Chơi lại Đêm", start], ["Về menu", showMenu]]);
    } finally {
        busy = false;
    }
}

function movement() {
    return [Number(keys.has("KeyD")) - Number(keys.has("KeyA")),
        Number(keys.has("KeyW")) - Number(keys.has("KeyS"))];
}

async function advance(ticks) {
    busy = true;
    const move = movement();
    if (move.some(Boolean)) facing = yaw + Math.atan2(move[0], move[1]);
    const controls = {move, cam_yaw_deg: yaw * 180 / Math.PI};
    for (const [action, codes] of Object.entries(actions)) {
        controls[action] = latched.delete(action) || codes.some(code => keys.has(code));
    }
    try {
        const result = await request("/api/step", {session, ticks, controls});
        if (result.wind_warning && !windWarning) sound.effect("wind");
        ({snapshot, wind_warning: windWarning} = result);
        for (const event of result.events) {
            sound.effect(event.name);
            if (event.name === "pulse") pulseAt = performance.now();
            if (event.name === "player_hit") hitAt = performance.now();
        }
        updateHUD();
        if (snapshot.state === "paused") showPause();
        if (snapshot.state === "won" || snapshot.state === "lost") showEnd();
    } catch (error) {
        overlay("error", "Mất kết nối", error.message, [["Chơi lại Đêm", start], ["Về menu", showMenu]]);
    } finally {
        busy = false;
    }
}

const benchmark = new URLSearchParams(location.search).has("benchmark");
let measureStart = 0, measured = 0;
function animate(now) {
    const elapsed = Math.min(100, now - (last || now));
    last = now;
    if (running && !document.hidden) {
        yaw += (Number(keys.has("ArrowRight")) - Number(keys.has("ArrowLeft"))) * elapsed * 0.0017;
        accumulator += elapsed;
        const ticks = Math.min(6, Math.floor(accumulator / STEP));
        if (!busy && ticks > 0) {
            accumulator -= ticks * STEP;
            advance(ticks);
        }
        if (benchmark) {
            if (!measureStart) measureStart = now;
            measured++;
            if (now - measureStart >= 5000) {
                fields.benchmark.hidden = false;
                setText(fields.benchmark, (measured * 1000 / (now - measureStart)).toFixed(1) + " FPS · " +
                    viewport.width + "×" + viewport.height);
                measureStart = now;
                measured = 0;
            }
        }
    } else {
        measureStart = measured = 0;
    }
    draw(now);
    requestAnimationFrame(animate);
}

window.addEventListener("keydown", event => {
    if (screen === "pause" && !event.repeat && actions.pause.includes(event.code)) {
        event.preventDefault();
        resume();
    } else if (running && bound.has(event.code)) {
        event.preventDefault();
        keys.add(event.code);
        if (!event.repeat) {
            for (const [action, codes] of Object.entries(actions)) if (codes.includes(event.code)) latched.add(action);
        }
    }
});
window.addEventListener("keyup", event => keys.delete(event.code));
window.addEventListener("blur", () => keys.clear());
let pointerX = null;
canvas.addEventListener("pointerdown", event => {
    if (!running || event.button !== 0) return;
    pointerX = event.clientX;
    canvas.setPointerCapture(event.pointerId);
});
canvas.addEventListener("pointermove", event => {
    if (!running || pointerX === null) return;
    yaw += (event.clientX - pointerX) * 0.006 * settings.sensitivity;
    pointerX = event.clientX;
});
canvas.addEventListener("lostpointercapture", () => { pointerX = null; });
showMenu();
requestAnimationFrame(animate);
