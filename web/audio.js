"use strict";

const sound = (() => {
    let context, master, timer, volume = 0.45, playing = false, note = 0;
    const effects = {
        mote_picked: [659, 880], lantern_lit: [392, 523, 659, 784], pulse: [330, 180, 520],
        player_hit: [160, 95], jumped: [330, 520], dash: [240, 680],
        game_won: [392, 523, 659, 784, 1047], game_lost: [440, 330, 220],
        shade_spawned: [125, 178], countdown: [650], wind: [185, 228, 160],
        charm_picked: [523, 784, 1047], drifter_steal: [470, 275], drifter_drop: [490, 720],
    };
    function gain(value) {
        volume = value;
        if (master) master.gain.setTargetAtTime(volume, context.currentTime, 0.02);
    }
    function tone(frequency, delay, duration, level, shape = "sine") {
        if (!context || !master || context.state !== "running") return;
        const start = context.currentTime + delay;
        const osc = context.createOscillator(), envelope = context.createGain();
        osc.type = shape;
        osc.frequency.value = frequency;
        envelope.gain.setValueAtTime(0.0001, start);
        envelope.gain.exponentialRampToValueAtTime(level, start + 0.025);
        envelope.gain.exponentialRampToValueAtTime(0.0001, start + duration);
        osc.connect(envelope).connect(master);
        osc.start(start);
        osc.stop(start + duration);
    }
    function unlock() {
        if (!context) {
            if (!window.AudioContext) return;
            context = new AudioContext();
            master = context.createGain();
            master.gain.value = volume;
            master.connect(context.destination);
        }
        context.resume().catch(() => {});
        if (!timer) timer = setInterval(() => {
            if (!playing) return;
            const notes = [130.81, 196, 261.63, 293.66, 261.63, 196, 146.83, 174.61];
            const f = notes[note++ % notes.length];
            tone(f, 0, 1.6, 0.038);
            tone(f * 2, 0.12, 1.2, 0.018);
        }, 800);
    }
    return {gain, unlock, playing(value) { playing = value; }, effect(name) {
        const notes = effects[name];
        if (!notes) return;
        notes.forEach((f, i) => tone(f, i * 0.075, 0.25, 0.1, name === "player_hit" ? "triangle" : "sine"));
    }};
})();
