"use strict";

const canvas = document.querySelector("#island");
const ctx = canvas.getContext("2d");
const fields = Object.fromEntries(["flames", "motes", "lamps", "time", "score", "notice", "curtain", "title",
    "description", "start"].map(id => [id, document.getElementById(id)]));

const STEP = 1000 / 60;
const TAU = 2 * Math.PI;
const bound = new Set(["KeyW", "KeyA", "KeyS", "KeyD", "ArrowLeft", "ArrowRight", "Space", "KeyE", "KeyF"]);
const keys = new Set();
let snapshot, tuning, session;
let radius = 36;
let yaw = 0, accumulator = 0, last = 0, busy = false, running = false;
let pulseAt = -Infinity, hitAt = -Infinity;
let facing = 0;
let viewport = {width: 900, height: 600};
const lanternPlaces = [[0, 8], [13, 15], [16, -5], [-1, -17], [-15, 4]];
const preview = {player: {pos: [0, 0, 0]}, lanterns: lanternPlaces.map(([x, z], i) => ({
    id: "L" + (i + 1), pos: [x, 0, z], lit: i === 0, deposited: 0
})), shades: [], motes: []};

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
    for (const [at, color] of [[0, "#11152e"], [0.37, "#333659"], [0.65, "#82718a"], [1, "#282942"]]) {
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
        glow(0, 0, 150 + (i % 3) * 42, "#dec0da66", "#dec0da00");
        ctx.restore();
    }
}

function drawIsland(cam, lit) {
    const edge = ring([0, 0, 0], radius, 64);
    const {height} = viewport;
    cam.worldPolygon(edge.map(([x, y, z]) => [x, y - 1.9, z]), "#222b41");
    const grass = ctx.createLinearGradient(0, height * 0.45, 0, height);
    grass.addColorStop(0, lit ? "#485147" : "#323b43");
    grass.addColorStop(1, lit > 2 ? "#514d40" : "#293b3c");
    cam.worldPolygon(edge, null, grass);
    for (const [x, y, z, size] of rocks) {
        cam.worldPolygon(ring([x, y, z], size, 4, x), (size > 0.25 ? "#7a766b55" : "#142f3277"));
    }
}

function drawPlant(cam, plant) {
    const [x, y, z] = plant.pos, s = plant.size;
    if (plant.tree) {
        frustum(cam, plant.pos, 0.21 * s, 0.12 * s, s * 2.2, ["#4d3d41", "#634c47"], 5);
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
    frustum(cam, [x, y + 0.24, z], 0.21, 0.13, 2.0, ["#644955", "#996e61", "#483c50"], 6);
    frustum(cam, [x, y + 2.2, z], 0.60, 0.84, 0.37, ["#775052", "#b48260"], 6);
    frustum(cam, [x, y + 2.56, z], 0.76, 0.68, 0.70,
        lamp.lit ? ["#ffb94d", "#ffe4a7", "#ffc571"] : ["#68516c", "#89687c", "#63506a"], 6);
    frustum(cam, [x, y + 3.26, z], 0.89, 0.18, 0.45, ["#733e50", "#ac6562", "#844757"], 6);
    if (at && lamp.lit) glow(at[0], at[1], at[2] * 2.9, "#ffd0738c", "#ed873800");
}

function drawMote(cam, mote, now) {
    const [x, y, z] = mote.pos;
    const at = cam.project([x, y + 0.67 + 0.14 * Math.sin(now * 0.004 + x + z), z]);
    if (!at) return;
    const [sx, sy, scale] = at;
    const r = Math.max(1.2, scale * 0.09);
    glow(sx, sy, r * 5, "#f4bd60a8", "#fd9a2d00");
    dot(sx, sy, r, "#fff2a9");
}

function drawShade(cam, shade, now) {
    const [x, y, z] = shade.pos;
    const at = cam.project([x, y + Math.sin(now * 0.005 + x) * 0.14, z]);
    if (!at) return;
    const [sx, sy, scale] = at, r = Math.max(3, scale * 0.54);
    const stunned = shade.state === "stunned";
    glow(sx, sy, r * 2.3, stunned ? "#ffa84d7c" : "#792baa9c", "#6a358700");
    ctx.fillStyle = stunned ? "#746180" : "#1c1432";
    ctx.beginPath();
    ctx.ellipse(sx, sy, r, r * 1.28, Math.sin(now * 0.003) * 0.16, 0, TAU);
    ctx.fill();
    const eyes = stunned ? "#ffd477" : "#de8bf4";
    dot(sx - r * 0.35, sy - r * 0.18, Math.max(1, r * 0.11), eyes);
    dot(sx + r * 0.35, sy - r * 0.18, Math.max(1, r * 0.11), eyes);
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
    frustum(cam, [x, y + 0.34, z], 0.40, 0.28, 0.73, ["#cb6857", "#f7a378", "#b84e56"], 8);
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
    const cam = camera(pos);
    drawSky(now);
    const lit = world.lanterns.filter(lamp => lamp.lit);
    drawIsland(cam, lit.length);
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
        if (depth > 0.15) objects.push({depth, drawObject});
    };
    for (const plant of plants) queue(plant.pos, () => drawPlant(cam, plant));
    for (const lamp of world.lanterns) queue(lamp.pos, () => drawLamp(cam, lamp));
    for (const mote of world.motes) queue(mote.pos, () => drawMote(cam, mote, now));
    for (const shade of world.shades) queue(shade.pos, () => drawShade(cam, shade, now));
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
}

function updateHUD() {
    const {player, lanterns, score, time_left_s: time} = snapshot;
    fields.flames.textContent = "✦".repeat(player.flames) + "·".repeat(tuning.flames - player.flames);
    fields.motes.textContent = player.carried + "/" + tuning.carry_capacity;
    fields.lamps.textContent = lanterns.filter(lamp => lamp.lit).length + "/" + lanterns.length;
    const seconds = Math.ceil(Math.max(0, time));
    fields.time.textContent = Math.floor(seconds / 60) + ":" + String(seconds % 60).padStart(2, "0");
    fields.score.textContent = score;
    const nearby = lanterns.filter(lamp => !lamp.lit &&
        Math.hypot(lamp.pos[0] - player.pos[0], lamp.pos[2] - player.pos[2]) <= tuning.interact_radius)
        .sort((a, b) => Math.hypot(a.pos[0] - player.pos[0], a.pos[2] - player.pos[2]) -
            Math.hypot(b.pos[0] - player.pos[0], b.pos[2] - player.pos[2]))[0];
    fields.notice.textContent = nearby && running
        ? (player.carried ? "E · Nạp đèn " : "Cần thêm đom đóm · ") + nearby.deposited + "/" + tuning.lantern_cost
        : "";
}

async function request(path, data) {
    const response = await fetch(path, {
        method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Không kết nối được với trò chơi");
    return result;
}

function showResult(title, description) {
    running = false;
    fields.notice.textContent = "";
    fields.title.textContent = title;
    fields.description.textContent = description;
    fields.start.textContent = "Chơi lại";
    fields.curtain.hidden = false;
    fields.start.focus();
}

async function start() {
    fields.start.disabled = true;
    try {
        const result = await request("/api/start", {session});
        ({session, snapshot, tuning, island_radius: radius} = result);
        yaw = facing = accumulator = 0;
        pulseAt = hitAt = -Infinity;
        keys.clear();
        running = true;
        fields.curtain.hidden = true;
        updateHUD();
    } catch (error) {
        showResult("Chưa vào được đảo", error.message);
    } finally {
        fields.start.disabled = false;
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
    try {
        const result = await request("/api/step", {session, ticks, controls: {
            move, cam_yaw_deg: yaw * 180 / Math.PI, jump: keys.has("Space"),
            interact: keys.has("KeyE"), pulse: keys.has("KeyF")
        }});
        snapshot = result.snapshot;
        for (const event of result.events) {
            if (event.name === "pulse") pulseAt = performance.now();
            if (event.name === "player_hit") hitAt = performance.now();
        }
        updateHUD();
        if (snapshot.state === "won") showResult("Đảo Bến đã sáng!", "Mây đã thắp cả năm đèn. Điểm: " + snapshot.score + ".");
        if (snapshot.state === "lost") {
            const reason = snapshot.player.flames === 0 ? "Ngọn lửa cuối đã tắt." : "Mây đã hết thời gian.";
            showResult("Đêm còn dài", reason + " Điểm: " + snapshot.score + ".");
        }
    } catch (error) {
        showResult("Mất kết nối", error.message);
    } finally {
        busy = false;
    }
}

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
    }
    draw(now);
    requestAnimationFrame(animate);
}

window.addEventListener("keydown", event => {
    if (running && bound.has(event.code)) {
        event.preventDefault();
        keys.add(event.code);
    }
});
window.addEventListener("keyup", event => keys.delete(event.code));
window.addEventListener("blur", () => keys.clear());
fields.start.addEventListener("click", start);
requestAnimationFrame(animate);
