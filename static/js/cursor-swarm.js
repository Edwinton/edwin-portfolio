/*!
 * CursorSwarm v1.0.0
 * A swarm of "agent" cursors that build your page, piece by piece, as you scroll.
 * Zero dependencies. MIT License.
 *
 *   <script src="cursor-swarm.js"></script>
 *   <script>new CursorSwarm({ cursors: 3 }).init();</script>
 */
(function (root, factory) {
    if (typeof module === 'object' && module.exports) module.exports = factory();
    else if (typeof define === 'function' && define.amd) define([], factory);
    else root.CursorSwarm = factory();
})(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    const VERSION = '1.0.0';
    const PALETTE = ['#ff5e00', '#3be8ff', '#c6ff3b', '#ff3bd4', '#ffd23b', '#8b5cff', '#3bff9d', '#ff3b5c'];
    // built-in palettes. `mono` generates shades of one color; `hud` themes the status pill
    const PALETTES = {
        default: { colors: PALETTE },
        neon: { colors: ['#39ff14', '#ff00e6', '#00f0ff', '#fff200', '#ff3131', '#bc13fe'] },
        pastel: { colors: ['#ffadad', '#ffd6a5', '#fdffb6', '#caffbf', '#9bf6ff', '#bdb2ff', '#ffc6ff'] },
        sunset: { colors: ['#ff6b35', '#ef476f', '#ffd166', '#f7c59f', '#9d4edd'] },
        ocean: { colors: ['#00b4d8', '#90e0ef', '#0077b6', '#48cae4', '#caf0f8'] },
        forest: { colors: ['#52b788', '#95d5b2', '#2d6a4f', '#b7e4c7', '#d8f3dc'] },
        candy: { colors: ['#ff70a6', '#ff9770', '#ffd670', '#e9ff70', '#70d6ff'] },
        mono: { mono: '#9a9a9a' },
        ink: { colors: ['#111111', '#444444', '#777777'], hud: { background: 'rgba(255,255,255,.85)', color: '#111', mute: '#666', border: 'rgba(0,0,0,.12)' } }
    };
    const ROLE_OF = { frame: 'layout', pop: 'layout', type: 'type', words: 'type', media: 'media' };
    const VERB = { frame: 'drawing', pop: 'spawning', type: 'writing', words: 'writing', media: 'placing' };
    const MOD = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent) ? '⌘' : 'Ctrl+';
    const OFF = 'translate(-9999px,-9999px)'; // where overlay pieces wait until they're positioned
    const chance = v => (v === true ? null : +v || 0); // null = use the default probability
    const TYPES = ['frame', 'pop', 'type', 'words', 'media'];
    const MEDIA_TAGS = { IMG: 1, VIDEO: 1, CANVAS: 1, IFRAME: 1, OBJECT: 1, EMBED: 1, svg: 1, SVG: 1 };
    const CONTROL_TAGS = { BUTTON: 1, INPUT: 1, SELECT: 1, TEXTAREA: 1, PROGRESS: 1, METER: 1 };
    const NO_SPLIT = { SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, TEXTAREA: 1, SELECT: 1, OPTION: 1, svg: 1, SVG: 1, TEMPLATE: 1 };
    const SKIP = 'script,style,noscript,template,link,meta,head,br,wbr,source,track,[data-cs-ignore],.cs-layer,.cs-hud';

    const DEFAULTS = {
        cursors: 3,                 // number of agents
        agents: null,               // [{ name, color, role, x, y }] per-agent overrides
        names: null,                // array or fn(i) => name
        palette: 'default',         // preset name | 'mono:#hex' | [colors] | { colors, mono, hud }
        colors: null,               // explicit colors (override the palette's), cycled across agents
        startPosition: 'center',    // 'center' | 'random' | 'corners' | 'top' | 'bottom' | 'left' | 'right' | 'outside' | {x,y} | [{x,y}] | fn(i, n)
        root: null,                 // element or selector to build (default: document.body)
        targets: null,              // selector: only build these elements (type auto-detected)
        ignore: null,               // selector: never touch these (plus [data-cs-ignore])
        frames: true,               // draw boxes (cards, buttons with backgrounds/borders…)
        deconstruct: true,          // un-build elements when scrolling back above them
        exitAfterBuild: false,      // true | 'edge' | 'home': where agents go when they run out of work
        idle: 'dim',                // 'dim' | 'stay' | 'hide': look of an idle agent
        spawn: true,                // spawn animation on init
        speed: 1,                   // global speed multiplier
        adaptiveSpeed: true,        // speed up when the backlog grows (fast scrolling)
        maxSpeed: 4,
        trigger: 0.88,              // build when an element's top crosses this viewport fraction
        typeDuration: 1.6,          // max seconds to type one block
        hud: true,                  // status pill with the current job and build progress
        hudPosition: 'bottom-left', // 'bottom-left' | 'bottom-right' | 'top-left' | 'top-right'
        labels: true,               // name tag next to each cursor
        marquee: true,              // selection box while measuring an element
        guides: true,               // crosshair guide lines while measuring
        sparks: true,               // particles when an element is finished
        caret: true,                // blinking caret while typing
        copyPaste: false,           // true | 0..1: repeated siblings (cards, chips…) are sometimes copied from an
                                    // already built one, dragged into place and then changed into the real content
        relocation: false,          // true | 0..1: some elements are built out of place, then dragged into position
        zIndex: 2147483000,
        respectReducedMotion: true, // do nothing for prefers-reduced-motion users
        onBuild: null,              // (el, type, agent) => {}
        onUnbuild: null,
        onIdle: null,               // (agent) => {}
        onDone: null                // () => {} every element built
    };

    /* ================= utils ================= */
    const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
    const lerp = (a, b, t) => a + (b - a) * t;
    const EASE = {
        none: t => t,
        in: t => t * t * t,
        out: t => 1 - Math.pow(1 - t, 3),
        out3: t => 1 - Math.pow(1 - t, 4),
        inOut: t => (t < .5 ? 8 * t * t * t * t : 1 - Math.pow(-2 * t + 2, 4) / 2),
        back: t => { const c1 = 2.4, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); }
    };
    const alpha = c => {
        if (!c || c === 'transparent') return 0;
        const m = c.match(/rgba?\(([^)]+)\)/);
        if (!m) return 1;
        const p = m[1].split(/[\s,/]+/).filter(Boolean);
        return p.length > 3 ? parseFloat(p[3]) : 1;
    };
    const toPx = (v, total) => {
        if (typeof v === 'number') return v;
        if (typeof v === 'string' && v.trim().endsWith('%')) return parseFloat(v) / 100 * total;
        return parseFloat(v) || 0;
    };
    const resolveEl = v => (typeof v === 'string' ? document.querySelector(v) : v);

    /* ================= colors ================= */
    const rgbCache = new Map();
    // any CSS color -> [r, g, b] (lets the browser do the parsing)
    const toRgb = c => {
        if (rgbCache.has(c)) return rgbCache.get(c);
        const probe = document.createElement('i');
        probe.style.color = c;
        probe.style.display = 'none';
        document.documentElement.appendChild(probe);
        const m = getComputedStyle(probe).color.match(/[\d.]+/g) || [0, 0, 0];
        probe.remove();
        const out = m.slice(0, 3).map(Number);
        rgbCache.set(c, out);
        return out;
    };
    const luminance = c => {
        const [r, g, b] = toRgb(c).map(v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); });
        return .2126 * r + .7152 * g + .0722 * b;
    };
    // readable text (and cursor outline) on top of a color
    const inkOn = c => (luminance(c) > .22 ? '#000' : '#fff');
    const toHsl = c => {
        const [r, g, b] = toRgb(c).map(v => v / 255);
        const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn;
        let h = 0;
        const sat = d ? d / (1 - Math.abs(2 * l - 1)) : 0;
        if (d) h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
        return [Math.round((h * 60 + 360) % 360), sat * 100, l * 100];
    };
    const hsl = (h, s, l, a) => `hsl(${h} ${s.toFixed(1)}% ${l.toFixed(1)}%${a != null ? ` / ${a}` : ''})`;
    /** n shades of one color: the color itself first, then lighter / darker steps around it. */
    const monoShades = (base, n = 5) => {
        const [h, sat, l] = toHsl(base);
        const out = [base];
        for (let k = 1; out.length < n && k < 12; k++) {
            [l + k * 13, l - k * 13].forEach(v => { if (out.length < n && v >= 14 && v <= 92) out.push(hsl(h, sat, v)); });
        }
        while (out.length < n) out.push(out[out.length % Math.max(1, out.length - 1)]);
        return out;
    };
    const resolvePalette = (p, n) => {
        if (typeof p === 'string') {
            const t = p.trim();
            if (/^mono[:(]/i.test(t)) p = { mono: t.replace(/^mono[:(]\s*|\)$/gi, '') };
            else if (t.includes(',')) p = { colors: t.split(',').map(x => x.trim()) };
            else p = PALETTES[t] || (window.CSS && window.CSS.supports('color', t) ? { mono: t } : PALETTES.default);
        } else if (Array.isArray(p)) p = { colors: p };
        p = p || PALETTES.default;
        const colors = p.mono ? monoShades(p.mono, Math.max(n, 3)) : (p.colors && p.colors.length ? p.colors : PALETTE);
        let hud = p.hud || null;
        if (!hud && p.mono) {
            const [h, sat] = toHsl(p.mono);
            hud = { background: hsl(h, sat * .5, 8, .8), color: hsl(h, sat * .4, 92), mute: hsl(h, sat * .4, 65), border: hsl(h, sat * .6, 60, .2) };
        }
        return { colors, hud };
    };
    const label = el => {
        if (el.dataset.csLabel) return el.dataset.csLabel;
        const tag = el.tagName.toLowerCase();
        if (el.id) return `${tag}#${el.id}`.slice(0, 28);
        const cls = typeof el.className === 'string' && el.className.trim().split(/\s+/).find(c => !c.startsWith('cs-'));
        return (cls ? `${tag}.${cls}` : tag).slice(0, 28);
    };

    /* ================= styles ================= */
    const CSS = `
.cs-layer{position:fixed;inset:0;pointer-events:none;overflow:hidden;contain:strict}
.cs-layer *{box-sizing:border-box}
.cs-cur{position:absolute;top:0;left:0;will-change:transform;filter:drop-shadow(0 4px 12px rgba(0,0,0,.45));transition:opacity .4s ease}
.cs-cur svg{display:block}.cs-cur path{transition:fill .4s ease,stroke .4s ease}
.cs-cur span{position:absolute;left:18px;top:20px;white-space:nowrap;font:700 10px/1 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:.08em;background:var(--c);color:var(--ink,#000);padding:4px 7px;transition:opacity .4s ease,background .4s ease,color .4s ease}
.cs-cur.cs-flip span{left:auto;right:4px}
.cs-cur em{position:absolute;left:18px;top:-18px;font:700 10px/1 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-style:normal;letter-spacing:.04em;white-space:nowrap;background:#111;color:#fff;border:1px solid var(--c);border-radius:3px;padding:3px 6px;opacity:0;transform:translateY(4px);transition:opacity .2s ease,transform .2s ease}
.cs-cur.cs-flip em{left:auto;right:4px}
.cs-cur.cs-key em{opacity:1;transform:none}
.cs-drop{position:absolute;top:0;left:0;border:1.5px dashed var(--c);background:color-mix(in srgb,var(--c) 7%,transparent);border-radius:4px;opacity:0;transition:opacity .3s ease}
.cs-ghost{pointer-events:none!important;transition:none!important}
.cs-cur.cs-dim{opacity:.45}.cs-cur.cs-dim span{opacity:0}
.cs-cur.cs-hidden{opacity:0}
.cs-mq{position:absolute;top:0;left:0;border:1px dashed var(--c);background:color-mix(in srgb,var(--c) 8%,transparent);opacity:0}
.cs-mq i{position:absolute;width:7px;height:7px;background:#fff;border:1px solid var(--c)}
.cs-mq i:nth-of-type(1){left:-4px;top:-4px}.cs-mq i:nth-of-type(2){right:-4px;top:-4px}
.cs-mq i:nth-of-type(3){left:-4px;bottom:-4px}.cs-mq i:nth-of-type(4){right:-4px;bottom:-4px}
.cs-mq b{position:absolute;left:50%;bottom:-24px;transform:translateX(-50%);font:500 10px/1 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:var(--c);color:var(--ink,#000);padding:3px 6px;white-space:nowrap}
.cs-gd{position:absolute;top:0;left:0;opacity:0}
.cs-gd.cs-h{width:100%;border-top:1px solid var(--c)}.cs-gd.cs-v{height:100%;border-left:1px solid var(--c)}
.cs-caret{position:absolute;top:0;left:0;width:2px;height:20px;background:var(--c);box-shadow:0 0 10px var(--c);opacity:0}
.cs-caret::after{content:"";position:absolute;inset:0;background:inherit;animation:cs-blink .9s steps(1) infinite}
.cs-box{position:absolute;top:0;left:0}
.cs-box i{position:absolute;background:var(--c)}
.cs-box .t,.cs-box .b{left:0;right:0;height:1px}.cs-box .t{top:0;transform-origin:left}.cs-box .b{bottom:0;transform-origin:right}
.cs-box .l,.cs-box .r{top:0;bottom:0;width:1px}.cs-box .r{right:0;transform-origin:top}.cs-box .l{left:0;transform-origin:bottom}
.cs-box .f{inset:0;opacity:0}
.cs-scan{position:absolute;top:0;left:0;background:var(--c);box-shadow:0 0 24px 6px var(--c)}
.cs-spark{position:absolute;top:0;left:0;width:5px;height:5px;background:var(--c)}
@keyframes cs-blink{50%{opacity:0}}
.cs-c{opacity:0}
.cs-w{display:inline-block;opacity:0;transform:translateY(.3em);transition:opacity .35s ease,transform .35s ease}
.cs-c.cs-on,.cs-w.cs-on{opacity:1;transform:none}
.cs-frame-off{background-color:transparent!important;background-image:none!important;border-color:transparent!important;box-shadow:none!important;outline-color:transparent!important;-webkit-backdrop-filter:none!important;backdrop-filter:none!important}
.cs-frame-fade{transition:background-color .7s ease,border-color .7s ease,box-shadow .7s ease,outline-color .7s ease!important}
.cs-hud{position:fixed;display:flex;align-items:center;gap:10px;max-width:calc(100vw - 24px);padding:9px 14px;font:500 10px/1.2 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--cs-hud-fg,#f1efe9);background:var(--cs-hud-bg,rgba(10,10,10,.72));border:1px solid var(--cs-hud-line,rgba(255,255,255,.12));-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);pointer-events:none;transition:opacity .4s ease,background .4s ease,color .4s ease}
.cs-hud i{width:7px;height:7px;border-radius:50%;flex:none;background:currentColor;transition:background .3s}
.cs-hud .cs-st{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:46ch;color:var(--cs-hud-mute,#a3a29d)}
.cs-hud .cs-pct{margin-left:4px;min-width:5ch;text-align:right}
html.cs-cloak body{visibility:hidden}
`;
    const injectStyle = () => {
        if (document.getElementById('cursor-swarm-style')) return;
        const s = document.createElement('style');
        s.id = 'cursor-swarm-style';
        s.textContent = CSS;
        (document.head || document.documentElement).appendChild(s);
    };

    /* ================= clock: one rAF loop, pausable, speed-aware ================= */
    class Clock {
        constructor(rate) {
            this.rate = rate;
            this.list = new Set();
            this.paused = false;
            this.instant = false;
            this.raf = 0;
            this.tracks = new Set();
            this.loop = this.loop.bind(this);
        }
        /** call fn every frame until the returned function is called */
        track(fn) {
            this.tracks.add(fn);
            fn();
            this.start();
            return () => this.tracks.delete(fn);
        }
        tween(dur, ease, fn) {
            return new Promise(res => {
                if (this.instant || dur <= 0) { if (fn) fn(1); res(); return; }
                ease = ease || EASE.none;
                if (fn) fn(ease(0)); // first frame right away: nothing is ever painted before it's positioned
                this.list.add({ t: 0, dur, ease, fn, res });
                this.start();
            });
        }
        wait(s) { return this.tween(s, null, null); }
        start() {
            if (this.raf || this.paused) return;
            this.last = performance.now();
            this.raf = requestAnimationFrame(this.loop);
        }
        loop(now) {
            const dt = Math.min(.05, (now - this.last) / 1000);
            this.last = now;
            const k = dt * this.rate();
            for (const tw of [...this.list]) {
                tw.t += k;
                const p = Math.min(1, tw.t / tw.dur);
                if (tw.fn) tw.fn(tw.ease(p));
                if (p >= 1) { this.list.delete(tw); tw.res(); }
            }
            this.tracks.forEach(f => f());
            this.raf = (this.list.size || this.tracks.size) && !this.paused ? requestAnimationFrame(this.loop) : 0;
        }
        pause() { this.paused = true; cancelAnimationFrame(this.raf); this.raf = 0; }
        resume() { this.paused = false; if (this.list.size || this.tracks.size) this.start(); }
        flush() {
            this.instant = true;
            for (const tw of [...this.list]) { if (tw.fn) tw.fn(1); tw.res(); }
            this.list.clear();
            this.tracks.clear();
            cancelAnimationFrame(this.raf); this.raf = 0;
        }
    }

    /* ================= CursorSwarm ================= */
    class CursorSwarm {
        constructor(options = {}) {
            this.opts = Object.assign({}, DEFAULTS, options);
            this.state = 'idle';            // idle | running | paused | stopped | destroyed
            this.records = [];
            this.byEl = new Map();
            this.agents = [];
            this._events = {};
            this._mediaN = 0;
            this._bgCache = new WeakMap();
            this._wasDone = false;
            this._resumers = [];
            this.clock = new Clock(() => this._rate());
        }

        /* ---------- public API ---------- */
        init() {
            if (this.state !== 'idle') return this;
            const html = document.documentElement;
            const reduce = this.opts.respectReducedMotion && window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
            if (reduce || !document.body) { html.classList.remove('cs-cloak'); this.state = 'stopped'; return this; }
            injectStyle();
            this.root = resolveEl(this.opts.root) || document.body;
            this.state = 'running';

            this.layer = document.createElement('div');
            this.layer.className = 'cs-layer';
            this.layer.setAttribute('aria-hidden', 'true');
            this.layer.style.zIndex = this.opts.zIndex;
            document.body.appendChild(this.layer);
            if (this.opts.hud) this._makeHud();

            html.classList.remove('cs-cloak'); // must be visible to be detected; nothing paints before we return OR WILL DIE!
            this._collect(this.root);
            this._makeAgents();
            this._paintHud();

            this._io = new IntersectionObserver(entries => this._onIntersect(entries), {
                rootMargin: `0px 0px -${Math.round((1 - this.opts.trigger) * 100)}% 0px`
            });
            this.records.forEach(r => this._io.observe(r.el));
            this._onScroll = () => {
                if (this._scrollQueued) return;
                this._scrollQueued = true;
                setTimeout(() => { this._scrollQueued = false; this._sweep(); }, 90);
            };
            addEventListener('scroll', this._onScroll, { passive: true });
            addEventListener('resize', this._onScroll, { passive: true });
            requestAnimationFrame(() => this._sweep());
            this._updateHud();
            this._emit('start');
            return this;
        }

        pause() {
            if (this.state !== 'running') return this;
            this.state = 'paused';
            this.clock.pause();
            this._emit('pause');
            return this;
        }

        resume() {
            if (this.state !== 'paused') return this;
            this.state = 'running';
            this.clock.resume();
            const r = this._resumers; this._resumers = [];
            r.forEach(f => f());
            this._emit('resume');
            return this;
        }

        toggle() { return this.state === 'paused' ? this.resume() : this.pause(); }

        /** Stop the swarm. By default everything still pending is revealed instantly. */
        stop({ reveal = true } = {}) {
            if (this.state === 'stopped' || this.state === 'destroyed' || this.state === 'idle') return this;
            const wasPaused = this.state === 'paused';
            this.state = 'stopped';
            this._teardownWatchers();
            this.clock.flush();
            if (wasPaused) { const r = this._resumers; this._resumers = []; r.forEach(f => f()); }
            this.records.forEach(r => { r.waiters.splice(0).forEach(f => f()); });
            if (reveal) this.records.forEach(r => this._finish(r));
            this.agents.forEach(a => a.cur.classList.add('cs-hidden'));
            if (this.hud) this.hud.style.opacity = 0;
            setTimeout(() => {
                if (this.layer) this.layer.remove();
                if (this.hud) this.hud.remove();
            }, 450);
            this._emit('stop');
            return this;
        }

        /** Stop and restore the DOM to how it was before init(). Sometimes it will show laggy and it is not fixed yet. */
        destroy() {
            if (this.state === 'destroyed') return this;
            this.stop({ reveal: true });
            this.records.forEach(r => this._restore(r));
            if (this.layer) this.layer.remove();
            if (this.hud) this.hud.remove();
            this.records = [];
            this.byEl.clear();
            this.state = 'destroyed';
            this._emit('destroy');
            return this;
        }

        /** Instantly build everything (the swarm keeps running for later jobs when needed). */
        buildAll() {
            this.records.forEach(r => { r.want = 'built'; if (!r.active) this._finish(r); });
            this._updateHud();
            return this;
        }

        /** Scan the root again and pick up elements added since init(). */
        refresh() {
            if (this.state !== 'running' && this.state !== 'paused') return this;
            const before = this.records.length;
            this._collect(this.root);
            this.records.slice(before).forEach(r => this._io.observe(r.el));
            this._sweep();
            this._updateHud();
            return this;
        }

        /** Manually register an element, optionally forcing its type. */
        add(el, type) {
            el = resolveEl(el);
            if (!el || this.byEl.has(el) || this.state === 'idle') return this;
            const cs = getComputedStyle(el);
            const t = TYPES.includes(type) ? type : this._detect(el, cs, false);
            if (!t) return this;
            this._unprepared = [];
            const recs = this._register(el, t, cs, this._containersOf(el));
            recs.forEach(r => { this._prepare(r, r.cs); delete r.cs; this._io.observe(r.el); });
            this._sweep();
            return this;
        }

        setSpeed(v) { this.opts.speed = Math.max(.05, +v || 1); return this; }

        /** Recolor the swarm live: a preset name, 'mono:#hex', a color list or { colors, mono, hud }. */
        setPalette(palette, { keepColors = false } = {}) {
            this.opts.palette = palette;
            if (!keepColors) this.opts.colors = null;
            if (!this.agents.length) return this;
            this._palette = resolvePalette(palette, this.agents.length);
            const colors = this._colors();
            this.agents.forEach((a, i) => { if (!a.fixedColor) this._paint(a, colors[i % colors.length]); });
            this._paintHud();
            this._emit('palette', this._palette);
            return this;
        }

        /** The colors the agents are currently using. */
        get colors() { return this.agents.map(a => a.color); }

        get progress() {
            const n = this.records.length;
            return n ? this.records.filter(r => r.state === 'built').length / n : 1;
        }

        on(ev, fn) { (this._events[ev] = this._events[ev] || []).push(fn); return this; }
        off(ev, fn) { this._events[ev] = (this._events[ev] || []).filter(f => f !== fn); return this; }

        /* ---------- EVENTS ---------- */
        _emit(ev, ...args) {
            (this._events[ev] || []).forEach(f => { try { f(...args); } catch (e) { console.error(e); } });
            const cb = this.opts['on' + ev[0].toUpperCase() + ev.slice(1)];
            if (typeof cb === 'function') { try { cb(...args); } catch (e) { console.error(e); } }
        }

        /* ---------- DETECTION ---------- */
        _skipped(el) {
            return el.matches(SKIP) || (this.opts.ignore && el.matches(this.opts.ignore));
        }

        _effectiveBg(el) {
            for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
                if (this._bgCache.has(n)) return this._bgCache.get(n);
                const c = getComputedStyle(n).backgroundColor;
                if (alpha(c) > .05) { this._bgCache.set(n, c); return c; }
            }
            return 'rgb(255, 255, 255)';
        }

        _hasBox(el, cs) {
            const border = ['Top', 'Right', 'Bottom', 'Left'].some(s =>
                parseFloat(cs['border' + s + 'Width']) > 0 && cs['border' + s + 'Style'] !== 'none' && alpha(cs['border' + s + 'Color']) > .05);
            if (border || cs.boxShadow !== 'none' || /gradient/.test(cs.backgroundImage)) return true;
            if (alpha(cs.backgroundColor) <= .05) return false;
            const parentBg = el.parentElement ? this._effectiveBg(el.parentElement) : '';
            return cs.backgroundColor !== parentBg;
        }

        _directText(el) {
            for (const n of el.childNodes) if (n.nodeType === 3 && n.nodeValue.trim()) return true;
            return false;
        }

        _detect(el, cs, mediaOnly) {
            const tag = el.tagName;
            const R = el.getBoundingClientRect();
            if (MEDIA_TAGS[tag]) {
                const small = R.width > 0 && R.width < 48 && R.height < 48;
                if (small) return mediaOnly ? null : 'pop';
                return 'media';
            }
            if (mediaOnly) return null;
            if (!R.width && !R.height) return null;
            if (CONTROL_TAGS[tag]) return 'pop';
            const box = this.opts.frames && this._hasBox(el, cs);
            const text = this._directText(el);
            if (box && R.width <= 480 && R.height <= 72 && (text || tag === 'A')) return 'pop';
            if (text) {
                const big = /^H[1-3]$/.test(tag) || parseFloat(cs.fontSize) >= 28;
                return big && el.textContent.trim().length <= 140 ? 'type' : 'words';
            }
            if (/url\(/.test(cs.backgroundImage) && R.width > 80 && R.height > 80) return 'media';
            if (box) {
                const wrapper = el === document.body || el === document.documentElement ||
                    (R.width >= innerWidth * .97 && R.height >= document.documentElement.scrollHeight * .6);
                return wrapper ? null : 'frame';
            }
            return null;
        }

        _containersOf(el) {
            const out = [];
            for (let n = el.parentElement; n; n = n.parentElement) {
                (this.byEl.get(n) || []).forEach(r => { if (r.type === 'frame' || (r.type === 'media' && !MEDIA_TAGS[n.tagName])) out.unshift(r); });
            }
            return out;
        }
        /* ---------- COLLECTION ---------- */

        _collect(rootEl) {
            // detect everything first: hiding a box early would fool the detection of its children
            this._unprepared = [];
            this._detectAll(rootEl);
            this._unprepared.forEach(r => { this._prepare(r, r.cs); delete r.cs; });
            this._unprepared = [];
        }

        _detectAll(rootEl) {
            const only = this.opts.targets;
            if (only) {
                rootEl.querySelectorAll(only).forEach(el => {
                    if (this.byEl.has(el) || this._skipped(el)) return;
                    const cs = getComputedStyle(el);
                    const explicit = el.getAttribute('data-cs');
                    const t = TYPES.includes(explicit) ? explicit : (this._detect(el, cs, false) || (this._directText(el) ? 'words' : 'pop'));
                    this._register(el, t, cs, this._containersOf(el));
                });
                return;
            }
            const visit = (el, containers, mediaOnly) => {
                if (this._skipped(el)) return;
                const cs = getComputedStyle(el);
                if (cs.display === 'none' || cs.visibility === 'hidden') return;
                if (el.tagName === 'PICTURE') { [...el.children].forEach(c => visit(c, containers, mediaOnly)); return; }
                const explicit = el.getAttribute('data-cs');
                if (explicit === 'skip') return;
                let next = containers, descend = true, childMediaOnly = mediaOnly;
                if (!this.byEl.has(el)) {
                    const t = explicit === 'none' ? null : TYPES.includes(explicit) ? explicit : this._detect(el, cs, mediaOnly);
                    if (t) {
                        const recs = this._register(el, t, cs, containers);
                        recs.forEach(r => { if (r.type === 'frame' || (r.type === 'media' && !MEDIA_TAGS[el.tagName])) next = next.concat(r); });
                        if (t === 'pop' || MEDIA_TAGS[el.tagName]) descend = false;
                        if (t === 'type' || t === 'words') childMediaOnly = true;
                    }
                } else {
                    (this.byEl.get(el) || []).forEach(r => { if (r.type === 'frame' || r.type === 'media') next = next.concat(r); });
                    if (this.byEl.get(el).some(r => r.parts)) childMediaOnly = true;
                }
                if (descend) [...el.children].forEach(c => visit(c, next, childMediaOnly));
            };
            if (rootEl === document.body || rootEl === document.documentElement) [...rootEl.children].forEach(c => visit(c, [], false));
            else visit(rootEl, [], false);
        }

        _register(el, type, cs, containers) {
            const recs = [];
            const make = (t, cont) => {
                const rec = { el, type: t, label: label(el), state: 'empty', want: 'empty', queued: false, active: false, containers: cont, waiters: [], saved: {}, cs };
                this._unprepared.push(rec);
                this.records.push(rec);
                const list = this.byEl.get(el) || [];
                list.push(rec);
                this.byEl.set(el, list);
                recs.push(rec);
                return rec;
            };
            // a big box with its own text: draw the box, then write inside it
            if ((type === 'type' || type === 'words') && this.opts.frames && this._hasBox(el, cs)) {
                const f = make('frame', containers);
                make(type, containers.concat(f));
            } else make(type, containers);
            return recs;
        }

        /* ---------- STATE PER_TYPE ---------- */
        _split(el, words) {
            const parts = [], swaps = [];
            const walk = node => [...node.childNodes].forEach(n => {
                if (n.nodeType === 3) {
                    if (!n.nodeValue.trim()) return;
                    const frag = document.createDocumentFragment(), made = [];
                    n.nodeValue.split(/(\s+)/).forEach(w => {
                        if (!w) return;
                        if (/^\s+$/.test(w)) { const t = document.createTextNode(w); frag.append(t); made.push(t); return; }
                        if (words) {
                            const s = document.createElement('span'); s.className = 'cs-w'; s.textContent = w;
                            frag.append(s); made.push(s); parts.push(s);
                        } else {
                            for (const ch of Array.from(w)) {
                                const s = document.createElement('span'); s.className = 'cs-c'; s.textContent = ch;
                                frag.append(s); made.push(s); parts.push(s);
                            }
                        }
                    });
                    // inside flex/grid every span would become its own item: keep the text as one inline box
                    if (/flex|grid/.test(getComputedStyle(node).display)) {
                        const box = document.createElement('span');
                        box.append(frag);
                        made.length = 0; made.push(box);
                        swaps.push({ orig: n, made });
                        n.replaceWith(box);
                        return;
                    }
                    swaps.push({ orig: n, made });
                    n.replaceWith(frag);
                } else if (n.nodeType === 1 && !NO_SPLIT[n.tagName] && !n.matches('[data-cs-ignore]') && !this.byEl.has(n)) walk(n);
            });
            walk(el);
            return { parts, swaps };
        }

        _prepare(rec, cs) {
            const el = rec.el, s = rec.saved;
            if (rec.type === 'type' || rec.type === 'words') {
                const { parts, swaps } = this._split(el, rec.type === 'words');
                if (!parts.length) { rec.type = 'pop'; return this._prepare(rec, cs); }
                rec.parts = parts; rec.swaps = swaps;
            } else if (rec.type === 'media') {
                rec.dir = el.dataset.csDir || 'lrt'[this._mediaN++ % 3];
                s.clipPath = el.style.clipPath;
                el.style.clipPath = this._clip(rec.dir, 0);
                if (!MEDIA_TAGS[el.tagName]) rec.img = el.querySelector(':scope > img, :scope > picture > img');
            } else if (rec.type === 'pop') {
                s.opacity = el.style.opacity; s.scale = el.style.scale;
                el.style.opacity = 0; el.style.scale = .4;
            } else if (rec.type === 'frame') {
                el.classList.add('cs-frame-off');
            }
        }

        _clip(dir, p) {
            const v = ((1 - p) * 100).toFixed(2) + '%';
            if (dir === 'r') return `inset(0 0 0 ${v})`;
            if (dir === 't') return `inset(0 0 ${v} 0)`;
            return `inset(0 ${v} 0 0)`;
        }

        _finish(rec) {
            const el = rec.el, s = rec.saved;
            if (rec.parts) rec.parts.forEach(p => p.classList.add('cs-on'));
            this._undisplace(rec);
            if (rec.type === 'media' && !rec.revealing) { el.style.clipPath = s.clipPath || ''; if (rec.img) rec.img.style.scale = ''; }
            if (rec.type === 'pop') { el.style.opacity = s.opacity || ''; el.style.scale = s.scale || ''; }
            if (rec.type === 'frame') el.classList.remove('cs-frame-off');
            this._setState(rec, 'built');
        }

        _reset(rec) {
            const el = rec.el;
            this._undisplace(rec);
            if (rec.parts) rec.parts.forEach(p => p.classList.remove('cs-on'));
            if (rec.type === 'media') el.style.clipPath = this._clip(rec.dir, 0);
            if (rec.type === 'pop') { el.style.opacity = 0; el.style.scale = .4; }
            if (rec.type === 'frame') el.classList.add('cs-frame-off');
            this._setState(rec, 'empty');
        }

        _restore(rec) {
            const el = rec.el, s = rec.saved;
            this._undisplace(rec);
            if (rec.swaps) rec.swaps.forEach(({ orig, made }) => { if (made[0] && made[0].parentNode) { made[0].before(orig); made.forEach(m => m.remove()); } });
            if (rec.type === 'media') { el.style.clipPath = s.clipPath || ''; if (rec.img) rec.img.style.scale = ''; }
            if (rec.type === 'pop') { el.style.opacity = s.opacity || ''; el.style.scale = s.scale || ''; }
            el.classList.remove('cs-frame-off', 'cs-frame-fade');
        }

        _setState(rec, st) {
            if (rec.state === st) { this._notify(rec); return; }
            rec.state = st;
            this._notify(rec);
            this._emit(st === 'built' ? 'build' : 'unbuild', rec.el, rec.type, rec.agent ? rec.agent.name : null);
            this._updateHud();
            const done = this.records.every(r => r.state === 'built');
            if (done && !this._wasDone) this._emit('done');
            this._wasDone = done;
        }

        _notify(rec) { rec.waiters.splice(0).forEach(f => f()); }

        /* ---------- AGENTES IA BONITOS Y CHULOS ---------- */
        _makeAgents() {
            const o = this.opts;
            const cfgs = Array.isArray(o.agents) && o.agents.length ? o.agents : [];
            const n = Math.max(1, cfgs.length || Math.round(o.cursors) || 1);
            const roleSets = n === 1 ? [['layout', 'type', 'media']]
                : n === 2 ? [['type'], ['layout', 'media']]
                    : Array.from({ length: n }, (_, i) => [['layout', 'type', 'media'][i % 3]]);
            this._palette = resolvePalette(o.palette, n);
            const colors = this._colors();
            for (let i = 0; i < n; i++) {
                const c = cfgs[i] || {};
                const name = c.name || (typeof o.names === 'function' ? o.names(i) : Array.isArray(o.names) && o.names[i]) || `AGENT·${String(i + 1).padStart(2, '0')}`;
                const color = c.color || colors[i % colors.length];
                const roles = c.role ? [].concat(c.role) : roleSets[i];
                const a = { name, color, roles, q: [], busy: false, i, fixedColor: !!c.color, els: [] };
                const mk = (cls, inner) => { const d = document.createElement('div'); d.className = cls; d.style.transform = OFF; if (inner) d.innerHTML = inner; this.layer.appendChild(d); a.els.push(d); return d; };
                a.gh = mk('cs-gd cs-h'); a.gv = mk('cs-gd cs-v'); a.caret = mk('cs-caret');
                a.mq = mk('cs-mq', '<i></i><i></i><i></i><i></i><b></b>'); a.lbl = a.mq.querySelector('b');
                a.cur = mk('cs-cur', `<svg width="22" height="22" viewBox="0 0 24 24"><path d="M3 2l7.6 19.2 2.7-8 7.9-2.8z" stroke-width="1.3" stroke-linejoin="round"/></svg>${o.labels ? `<span></span>` : ''}<em></em>`);
                if (o.labels) a.cur.querySelector('span').textContent = name;
                a.path = a.cur.querySelector('path');
                a.kbd = a.cur.querySelector('em');
                this._paint(a, color);
                a.home = this._startPos(i, n, c);
                this._place(a, a.home.x, a.home.y);
                this.agents.push(a);
            }
            this.agents.forEach(a => { a.ready = this._spawn(a); });
        }

        _colors() {
            const o = this.opts;
            return Array.isArray(o.colors) && o.colors.length ? o.colors : this._palette.colors;
        }

        _paint(a, color) {
            a.color = color;
            const ink = inkOn(color);
            a.els.forEach(d => { d.style.setProperty('--c', color); d.style.setProperty('--ink', ink); });
            a.path.setAttribute('fill', color);
            a.path.setAttribute('stroke', ink);
        }

        _paintHud() {
            if (!this.hud) return;
            const h = (this._palette && this._palette.hud) || {};
            [['bg', h.background], ['fg', h.color], ['mute', h.mute], ['line', h.border]].forEach(([k, v]) => {
                if (v) this.hud.style.setProperty('--cs-hud-' + k, v); else this.hud.style.removeProperty('--cs-hud-' + k);
            });
        }

        _startPos(i, n, c) {
            const W = innerWidth, H = innerHeight;
            const norm = p => ({ x: toPx(p.x, W), y: toPx(p.y, H) });
            if (c.x != null || c.y != null) return norm({ x: c.x != null ? c.x : '50%', y: c.y != null ? c.y : '50%' });
            const sp = this.opts.startPosition;
            if (typeof sp === 'function') return norm(sp(i, n));
            if (Array.isArray(sp)) return norm(sp[i % sp.length]);
            if (sp && typeof sp === 'object') return norm(sp);
            const spread = (k, len) => (k + 1) / (len + 1);
            switch (sp) {
                case 'random': return { x: W * (.12 + Math.random() * .76), y: H * (.15 + Math.random() * .7) };
                case 'corners': {
                    const C = [[.08, .1], [.92, .1], [.92, .9], [.08, .9]][i % 4];
                    return { x: W * C[0] - (C[0] > .5 ? 30 : 0), y: H * C[1] };
                }
                case 'top': return { x: W * spread(i, n), y: 70 };
                case 'bottom': return { x: W * spread(i, n), y: H - 70 };
                case 'left': return { x: 40, y: H * spread(i, n) };
                case 'right': return { x: W - 70, y: H * spread(i, n) };
                case 'outside': {
                    const side = i % 4;
                    const t = spread(Math.floor(i / 4), Math.ceil(n / 4));
                    return [{ x: -60, y: H * t }, { x: W + 60, y: H * t }, { x: W * t, y: -60 }, { x: W * t, y: H + 60 }][side];
                }
                default: {
                    const gap = Math.min(110, (W * .7) / n);
                    return { x: W / 2 + (i - (n - 1) / 2) * gap - 12, y: H / 2 - 24 };
                }
            }
        }

        async _spawn(a) {
            const on = this.opts.spawn && this.opts.startPosition !== 'outside';
            if (!on) { this._idleLook(a, true); return; }
            a.cur.style.opacity = 0;
            a.cur.style.scale = 0;
            await this.clock.wait(.25 + a.i * .3);
            const mq = a.mq.style;
            mq.opacity = 1;
            await this.clock.tween(.35, EASE.out, p => {
                const s = 44 * p;
                mq.transform = `translate(${a.x - 14}px,${a.y - 14}px)`;
                mq.width = s + 'px'; mq.height = s + 'px';
                a.lbl.textContent = `${Math.round(s)} × ${Math.round(s)}`;
            });
            this.clock.tween(.3, EASE.out, p => { mq.opacity = 1 - p; });
            await this.clock.tween(.45, EASE.back, p => { a.cur.style.opacity = Math.min(1, p * 2); a.cur.style.scale = p; });
            a.cur.style.opacity = ''; a.cur.style.scale = '';
            this._idleLook(a, true);
        }

        _place(a, x, y) {
            a.x = x; a.y = y;
            a.cur.style.transform = `translate(${x - 3}px,${y - 2}px)`;
            a.cur.classList.toggle('cs-flip', x > innerWidth - 110);
        }

        _idleLook(a, on) {
            a.cur.classList.toggle('cs-dim', on && this.opts.idle === 'dim');
            a.cur.classList.toggle('cs-hidden', on && this.opts.idle === 'hide');
        }

        _rate() {
            const o = this.opts;
            if (!o.adaptiveSpeed) return o.speed;
            const backlog = this.agents.reduce((n, a) => n + a.q.length, 0);
            return o.speed * Math.min(1 + backlog * .45, o.maxSpeed);
        }

        _travel(a, target, dur = .5) {
            const sx = a.x, sy = a.y;
            return this.clock.tween(dur, EASE.inOut, p => { const t = target(); this._place(a, lerp(sx, t.x, p), lerp(sy, t.y, p)); });
        }

        _say(a, verb, what) {
            if (!this.hud) return;
            this.hudSt.textContent = `${a.name} › ${verb} <${what}/>`;
            this.hudDot.style.background = a.color;
        }

        /* ---------- SCHEDULING ---------- */
        _onIntersect(entries) {
            if (this.state !== 'running' && this.state !== 'paused') return;
            entries.forEach(e => {
                const recs = this.byEl.get(e.target) || [];
                if (e.isIntersecting) recs.forEach(r => this._dispatch(r, true));
                else if (this.opts.deconstruct && e.rootBounds && e.boundingClientRect.top >= e.rootBounds.bottom) recs.forEach(r => this._dispatch(r, false));
            });
        }

        // // catches what IntersectionObserver can't: jumps past elements and the very bottom of the page
        _sweep() {
            if (this.state !== 'running' && this.state !== 'paused') return;
            const doc = document.documentElement;
            const atBottom = scrollY + innerHeight >= doc.scrollHeight - 4;
            const line = innerHeight * this.opts.trigger;
            this.records.forEach(r => {
                if (r.want === 'built') return;
                const R = r.el.getBoundingClientRect();
                if (!R.width && !R.height) return;
                if (R.bottom < 0 && R.top < line) { if (!r.queued && !r.active) { r.want = 'built'; this._finish(r); } }
                else if (atBottom && R.top < innerHeight && R.bottom > 0) this._dispatch(r, true);
            });
        }

        _dispatch(rec, build) {
            if (this.state !== 'running' && this.state !== 'paused') return;
            const want = build ? 'built' : 'empty';
            if (rec.want !== want) { rec.want = want; this._notify(rec); }
            if (rec.queued || rec.active || rec.state === want) return;
            if (build) rec.containers.forEach(c => { if (c.state !== 'built') this._dispatch(c, true); });
            const role = ROLE_OF[rec.type];
            const load = a => a.q.length + (a.busy ? 1 : 0);
            const pref = this.agents.filter(a => a.roles.includes(role));
            const best = list => list.reduce((m, a) => (load(a) < load(m) ? a : m));
            let a = pref.length ? best(pref) : best(this.agents);
            if (load(a) >= 2) { const g = best(this.agents); if (load(g) < load(a)) a = g; }
            rec.queued = true;
            rec.agent = a;
            a.q.push(rec);
            this._pump(a);
        }

        _alive() { return this.state === 'running' || this.state === 'paused'; }

        _gate() {
            return this.state === 'paused' ? new Promise(r => this._resumers.push(r)) : null;
        }

        async _awaitContainers(rec, a) {
            for (const c of rec.containers) {
                let guard = Date.now();
                while (this._alive() && c.state !== 'built' && rec.want === 'built') {
                    // the box is stuck behind us in our own queue (or taking too long): just finish it
                    if ((c.agent === a && c.queued) || (!c.queued && !c.active) || Date.now() - guard > (c.copyRoll ? 9000 : 4000)) {
                        if (c.queued && c.agent) { c.agent.q.splice(c.agent.q.indexOf(c), 1); c.queued = false; }
                        if (!c.active) { c.want = 'built'; this._finish(c); }
                        break;
                    }
                    await new Promise(r => { c.waiters.push(r); setTimeout(r, 500); });
                }
            }
        }

        _inView(el) {
            const R = el.getBoundingClientRect();
            return !(R.bottom < -40 || R.top > innerHeight + 40 || R.right < 0 || R.left > innerWidth || (!R.width && !R.height));
        }

        async _pump(a) {
            if (a.busy || !this._alive()) return;
            a.busy = true;
            await a.ready;
            this._idleLook(a, false);
            a.cur.classList.remove('cs-hidden');
            for (; ;) {
                while (a.q.length && this._alive()) {
                    const g = this._gate(); if (g) await g;
                    if (!this._alive()) break;
                    const rec = a.q.shift();
                    rec.queued = false;
                    a.parked = false;
                    if (rec.state === rec.want) continue;
                    if (rec.want === 'built') await this._awaitContainers(rec, a);
                    if (!this._alive()) break;
                    const want = rec.want;
                    if (rec.state === want) continue;
                    if (!this._inView(rec.el)) { want === 'built' ? this._finish(rec) : this._reset(rec); continue; }
                    const src = want === 'built' && this._copySource(rec);
                    if (src === 'wait') {
                        rec.copyWaits = (rec.copyWaits || 0) + 1;
                        rec.queued = true;
                        a.q.push(rec);
                        await this.clock.wait(a.q[0] === rec ? .25 : .1);
                        continue;
                    }
                    rec.copyRoll = null; rec.copyWaits = 0;
                    const reloc = want === 'built' && !src && this._wantsRelocation(rec);
                    this._say(a, src ? 'copy-pasting' : want === 'built' ? VERB[rec.type] : 'removing', rec.label);
                    rec.active = true;
                    try {
                        if (src) await this._copy(a, rec, src);
                        else {
                            if (reloc) this._displace(a, rec);
                            await (want === 'built' ? this._jobs : this._unjobs)[rec.type].call(this, a, rec);
                            if (reloc && this._alive()) { this._say(a, 'moving', rec.label); await this._relocate(a, rec); }
                        }
                    } catch (e) { console.error('[CursorSwarm]', e); }
                    rec.active = false;
                    if (!this._alive()) break;
                    want === 'built' ? this._finish(rec) : this._reset(rec);
                    // the visitor changed direction mid-job: queue the opposite pass
                    if (rec.want !== want) { rec.queued = true; a.q.push(rec); }
                }
                if (!this._alive()) break;
                const exit = this.opts.exitAfterBuild;
                if (exit && !a.parked) {
                    await this.clock.wait(.6);
                    if (a.q.length) continue;
                    const home = exit === 'home';
                    const side = a.x < innerWidth / 2 ? -80 : innerWidth + 80;
                    await this._travel(a, () => (home ? a.home : { x: side, y: a.y }), .7);
                    a.parked = true;
                    if (a.q.length) continue;
                }
                break;
            }
            a.busy = false;
            if (!this._alive()) return;
            if (a.q.length) { this._pump(a); return; }
            this._idleLook(a, true);
            if (this.hud && this.agents.every(x => !x.busy)) {
                this.hudSt.textContent = this.progress >= .999 ? 'all agents idle · page built' : 'all agents idle';
                this.hudDot.style.background = '';
            }
            this._emit('idle', a);
        }

        /* ---------- COPY & PASTE ---------- */
        _key(a, text) {
            if (text) a.kbd.textContent = text;
            a.cur.classList.toggle('cs-key', !!text);
        }

        _signature(el) {
            const cls = typeof el.className === 'string' ? el.className.split(/\s+/).filter(c => c && !c.startsWith('cs-')).sort().join('.') : '';
            return el.tagName + '|' + cls;
        }

        _tree(rec) { return [rec].concat(this.records.filter(r => r !== rec && r.containers.includes(rec))); }

        // a built twin of `rec` that can be copied: same tag + classes, same parent, fully built and on screen
        _copySource(rec) {
            const o = this.opts, el = rec.el, force = el.dataset.csCopy;
            if (force === 'false' || (!o.copyPaste && force !== 'true')) return null;
            if (!['frame', 'pop', 'media'].includes(rec.type) || !el.parentElement) return null;
            if ((this.byEl.get(el) || [])[0] !== rec) return null;
            if (rec.copyRoll == null) { const p = chance(o.copyPaste); rec.copyRoll = force === 'true' || Math.random() < (p == null ? .5 : p); }
            if (!rec.copyRoll) return null;
            const sig = this._signature(el), sibs = [...el.parentElement.children];
            const me = sibs.indexOf(el);
            const twins = sibs.filter(s => s !== el && !s.classList.contains('cs-ghost') && this._signature(s) === sig && this.byEl.has(s) && this._inView(s));
            const ok = twins.filter(s => this.byEl.get(s).every(r => this._tree(r).every(t => t.state === 'built' && !t.active && t.want === 'built')));
            if (ok.length) return ok.sort((x, y) => Math.abs(sibs.indexOf(x) - me) - Math.abs(sibs.indexOf(y) - me))[0];
            // a twin is still being built: worth waiting a moment for it
            const pending = twins.some(s => this.byEl.get(s).some(r => r.want === 'built'));
            return pending && (rec.copyWaits || 0) < 40 ? 'wait' : null;
        }

        // build `rec` (and everything inside it) at once, without animation
        _finishTree(rec) {
            this._tree(rec).forEach(r => {
                r.want = 'built';
                if (r.queued && r.agent) { const q = r.agent.q, i = q.indexOf(r); if (i > -1) q.splice(i, 1); r.queued = false; }
                if (r === rec || !r.active) this._finish(r);
            });
        }

        async _copy(a, rec, src) {
            const el = rec.el, sr = () => src.getBoundingClientRect(), tr = () => el.getBoundingClientRect();
            const center = R => ({ x: R.left + R.width * .5, y: R.top + R.height * .5 });
            await this._travel(a, () => center(sr()), .45);

            // select the original
            const sel = this._mk('cs-drop', a.color);
            const stopSel = this.clock.track(() => { const R = sr(); Object.assign(sel.style, { transform: `translate(${R.left - 3}px,${R.top - 3}px)`, width: R.width + 6 + 'px', height: R.height + 6 + 'px' }); });
            sel.style.opacity = 1;
            this._key(a, MOD + 'C');
            await this.clock.wait(.35);

            // the copy lives next to the original so the page's own CSS still applies to it
            const S = sr(), ghost = src.cloneNode(true);
            ghost.setAttribute('data-cs-ignore', '');
            ghost.setAttribute('aria-hidden', 'true');
            ghost.removeAttribute('id');
            ghost.querySelectorAll('[id]').forEach(n => n.removeAttribute('id'));
            ghost.classList.remove('cs-frame-fade');
            ghost.classList.add('cs-ghost');
            Object.assign(ghost.style, {
                position: 'absolute', left: '0px', top: '0px', margin: '0', boxSizing: 'border-box', zIndex: 2147482000,
                width: S.width + 'px', height: S.height + 'px', translate: '0px 0px', rotate: '0deg', scale: '', opacity: '0', clipPath: '',
                boxShadow: '0 26px 60px -18px rgba(0,0,0,.55)', outline: `1.5px solid ${a.color}`, outlineOffset: '2px'
            });
            src.parentElement.appendChild(ghost);
            let tx = 0, ty = 0;
            const put = (x, y, w, h) => {
                if (w != null) { ghost.style.width = w + 'px'; ghost.style.height = h + 'px'; }
                const g = ghost.getBoundingClientRect();
                tx += x - g.left; ty += y - g.top;
                ghost.style.translate = `${tx}px ${ty}px`;
            };
            try {
                // peel the copy off the original
                await this.clock.tween(.3, EASE.out, p => {
                    const R = sr();
                    put(R.left + 14 * p, R.top + 14 * p);
                    ghost.style.opacity = .92 * p;
                    this._place(a, R.left + R.width * .5 + 14 * p, R.top + R.height * .5 + 14 * p);
                });
                stopSel(); sel.style.opacity = 0;
                this._key(a, 'drag');

                // drag it to where the new element goes, resizing on the way
                const drop = this._mk('cs-drop', a.color);
                const stopDrop = this.clock.track(() => { const R = tr(); Object.assign(drop.style, { transform: `translate(${R.left}px,${R.top}px)`, width: R.width + 'px', height: R.height + 'px' }); });
                drop.style.opacity = 1;
                await this.clock.tween(.7, EASE.inOut, p => {
                    const A = sr(), B = tr();
                    const x = lerp(A.left + 14, B.left, p), y = lerp(A.top + 14, B.top, p);
                    const w = lerp(A.width, B.width, p), h = lerp(A.height, B.height, p);
                    put(x, y, w, h);
                    this._place(a, x + w * .5, y + h * .5);
                });
                stopDrop(); drop.style.opacity = 0;
                setTimeout(() => drop.remove(), 400);

                // paste, then turn the copy into the real content
                this._key(a, MOD + 'V');
                this._finishTree(rec);
                this._spark(tr(), a.color);
                await this.clock.wait(.2);
                this._key(a, 'edit');
                await this.clock.tween(.45, EASE.out, p => {
                    const B = tr();
                    put(B.left, B.top, B.width, B.height);
                    ghost.style.opacity = .92 * (1 - p);
                    ghost.style.filter = `blur(${4 * p}px)`;
                    this._place(a, B.left + B.width * .5, B.top + B.height * .5);
                });
            } finally {
                stopSel(); sel.remove();
                ghost.remove();
                this._key(a, null);
            }
        }

        /* ---------- RELOCATION ---------- */
        _wantsRelocation(rec) {
            const o = this.opts, el = rec.el, force = el.dataset.csRelocate;
            if (force === 'false' || (!o.relocation && force !== 'true')) return false;
            if (!['frame', 'pop', 'media', 'type'].includes(rec.type)) return false;
            if ((this.byEl.get(el) || [])[0] !== rec) return false; // one move per element
            if (rec.containers.some(c => c.offset)) return false;   // its box is already being moved
            const R = el.getBoundingClientRect();
            if (force !== 'true') {
                if (R.width > innerWidth * .85 || R.height > innerHeight * .7) return false;
                if (/fixed|sticky/.test(getComputedStyle(el).position)) return false;
                const p = chance(o.relocation);
                if (Math.random() >= (p == null ? .3 : p)) return false;
            }
            return true;
        }

        // push the element out of place (staying inside the viewport) and mark where it belongs
        _displace(a, rec) {
            const el = rec.el, R = el.getBoundingClientRect(), s = rec.saved;
            const rnd = (lo, hi) => (lo + Math.random() * (hi - lo)) * (Math.random() < .5 ? -1 : 1);
            const dx = clamp(rnd(50, 130), -R.left + 8, Math.max(-R.left + 8, innerWidth - R.right - 8));
            const dy = rnd(30, 90);
            const rot = rnd(2, rec.type === 'type' ? 3 : 7);
            if (!('translate' in s)) { s.translate = el.style.translate; s.rotate = el.style.rotate; }
            el.style.translate = `${dx}px ${dy}px`;
            el.style.rotate = `${rot}deg`;
            const doc = { left: R.left + scrollX, top: R.top + scrollY, width: R.width, height: R.height };
            const drop = this._mk('cs-drop', a.color);
            const stop = this.clock.track(() => Object.assign(drop.style, { transform: `translate(${doc.left - scrollX}px,${doc.top - scrollY}px)`, width: doc.width + 'px', height: doc.height + 'px' }));
            drop.style.opacity = .8;
            rec.offset = { dx, dy, rot, drop, stop };
        }

        async _relocate(a, rec) {
            const el = rec.el, o = rec.offset;
            if (!o) return;
            const R = () => el.getBoundingClientRect();
            const c = () => ({ x: R().left + R().width * .5, y: R().top + R().height * .5 });
            await this._travel(a, c, .35);
            this._key(a, 'move');
            await this.clock.wait(.12);
            await this.clock.tween(.65, EASE.inOut, p => {
                const k = 1 - p;
                el.style.translate = `${o.dx * k}px ${o.dy * k}px`;
                el.style.rotate = `${o.rot * k}deg`;
                const C = c();
                this._place(a, C.x, C.y);
            });
            this._key(a, null);
            this._spark(R(), a.color);
            this._undisplace(rec);
        }

        _undisplace(rec) {
            const o = rec.offset;
            if (!o) return;
            o.stop();
            o.drop.style.opacity = 0;
            setTimeout(() => o.drop.remove(), 350);
            rec.el.style.translate = rec.saved.translate || '';
            rec.el.style.rotate = rec.saved.rotate || '';
            rec.offset = null;
        }

        /* ---------- VISUALS ---------- */
        _mk(cls, color) {
            const d = document.createElement('div');
            d.className = cls;
            d.style.transform = OFF;
            d.style.setProperty('--c', color);
            this.layer.appendChild(d);
            return d;
        }

        _visible(R) {
            const top = Math.max(R.top, -2), bottom = Math.min(R.bottom, innerHeight + 2);
            const left = Math.max(R.left, -2), right = Math.min(R.right, innerWidth + 2);
            return { left, top, right: Math.max(left, right), bottom: Math.max(top, bottom), width: Math.max(0, right - left), height: Math.max(0, bottom - top) };
        }

        _spark(R, color) {
            if (!this.opts.sparks) return;
            R = this._visible(R);
            [[R.left, R.top], [R.right, R.top], [R.left, R.bottom], [R.right, R.bottom]].forEach(([x, y]) => {
                for (let k = 0; k < 3; k++) {
                    const s = this._mk('cs-spark', color);
                    const ang = Math.random() * Math.PI * 2, dist = 16 + Math.random() * 32;
                    this.clock.tween(.7, EASE.out3, p => {
                        s.style.transform = `translate(${x + Math.cos(ang) * dist * p}px,${y + Math.sin(ang) * dist * p}px) rotate(${180 * p}deg) scale(${1 - p})`;
                        s.style.opacity = 1 - p;
                    }).then(() => s.remove());
                }
            });
        }

        async _marquee(a, rec) {
            const r = () => this._visible(rec.el.getBoundingClientRect());
            await this._travel(a, () => ({ x: r().left, y: r().top }));
            const o = this.opts, mq = a.mq.style;
            if (o.marquee) mq.opacity = 1;
            if (o.guides) { a.gh.style.opacity = .45; a.gv.style.opacity = .45; }
            const tick = p => {
                const R = r(), w = R.width * p, h = R.height * p;
                if (o.marquee) {
                    mq.transform = `translate(${R.left}px,${R.top}px)`;
                    mq.width = w + 'px'; mq.height = h + 'px';
                    a.lbl.textContent = `${Math.round(w)} × ${Math.round(h)}`;
                }
                if (o.guides) { a.gh.style.transform = `translateY(${R.top}px)`; a.gv.style.transform = `translateX(${R.left}px)`; }
                this._place(a, R.left + w, R.top + h);
            };
            await this.clock.tween(.45, EASE.out, tick);
            return () => {
                this.clock.tween(.45, null, () => tick(1));
                this.clock.wait(.2).then(() => this.clock.tween(.35, null, p => {
                    const v = 1 - p;
                    if (o.marquee) mq.opacity = v;
                    if (o.guides) { a.gh.style.opacity = .45 * v; a.gv.style.opacity = .45 * v; }
                }));
            };
        }

        _caretAt(a, R) {
            if (!this.opts.caret) return;
            const s = a.caret.style;
            s.transform = `translate(${R.right + 1}px,${R.top}px)`;
            s.height = R.height + 'px';
        }

        get _jobs() {
            return {
                async frame(a, rec) {
                    const el = rec.el, release = await this._marquee(a, rec);
                    const box = this._mk('cs-box', a.color);
                    box.innerHTML = '<i class="t"></i><i class="r"></i><i class="b"></i><i class="l"></i><i class="f"></i>';
                    const lines = [...box.children].slice(0, 4), flash = box.lastChild;
                    flash.style.background = a.color;
                    const T = 1.5;
                    this.clock.tween(T, null, p => {
                        const t = p * T, R = el.getBoundingClientRect();
                        Object.assign(box.style, { transform: `translate(${R.left}px,${R.top}px)`, width: R.width + 'px', height: R.height + 'px' });
                        lines.forEach((l, i) => {
                            const k = EASE.inOut(clamp((t - i * .06) / .45, 0, 1));
                            l.style.transform = i % 2 ? `scaleY(${k})` : `scaleX(${k})`;
                        });
                        flash.style.opacity = .16 * (1 - clamp(t / .7, 0, 1));
                        box.style.opacity = 1 - clamp((t - 1) / .5, 0, 1);
                    }).then(() => box.remove());
                    el.classList.add('cs-frame-fade');
                    el.classList.remove('cs-frame-off');
                    setTimeout(() => el.classList.remove('cs-frame-fade'), 800);
                    this._spark(el.getBoundingClientRect(), a.color);
                    release();
                    await this.clock.wait(.25);
                },
                async media(a, rec) {
                    const el = rec.el, release = await this._marquee(a, rec), dir = rec.dir;
                    const scan = this._mk('cs-scan', a.color);
                    rec.revealing = this.clock.tween(.8, EASE.inOut, p => {
                        const R = el.getBoundingClientRect();
                        el.style.clipPath = this._clip(dir, p);
                        if (dir === 't') Object.assign(scan.style, { transform: `translate(${R.left}px,${R.top + R.height * p}px)`, width: R.width + 'px', height: '3px' });
                        else Object.assign(scan.style, { transform: `translate(${dir === 'r' ? R.right - R.width * p : R.left + R.width * p}px,${R.top}px)`, width: '3px', height: R.height + 'px' });
                    }).then(() => {
                        scan.remove();
                        rec.revealing = null;
                        if (rec.state === 'built') el.style.clipPath = rec.saved.clipPath || '';
                    });
                    if (rec.img) this.clock.tween(1.2, EASE.out, p => { rec.img.style.scale = 1.3 - .3 * p; }).then(() => { if (rec.img) rec.img.style.scale = ''; });
                    this._spark(el.getBoundingClientRect(), a.color);
                    release();
                    await this.clock.wait(.35);
                },
                async pop(a, rec) {
                    const el = rec.el, R = () => el.getBoundingClientRect();
                    await this._travel(a, () => ({ x: R().left + R().width * .5, y: R().top + R().height * .6 }), .35);
                    await this.clock.tween(.35, EASE.back, p => { el.style.opacity = clamp(p, 0, 1); el.style.scale = .4 + .6 * p; });
                },
                async type(a, rec) {
                    const parts = rec.parts, n = parts.length;
                    const per = Math.min(rec.type === 'words' ? .06 : .03, this.opts.typeDuration / n);
                    const at = i => parts[clamp(i, 0, n - 1)].getBoundingClientRect();
                    await this._travel(a, () => { const R = at(0); return { x: R.left, y: R.top + R.height * .7 }; }, .45);
                    if (this.opts.caret) a.caret.style.opacity = 1;
                    let k = 0;
                    await this.clock.tween(n * per, null, p => {
                        const target = Math.ceil(p * n);
                        while (k < target) parts[k++].classList.add('cs-on');
                        const R = at(k - 1);
                        this._caretAt(a, R);
                        this._place(a, lerp(a.x, R.right + 8, .35), lerp(a.y, R.top + R.height * .7, .35));
                    });
                    await this.clock.wait(.2);
                    a.caret.style.opacity = 0;
                },
                get words() { return this.type; }
            };
        }

        get _unjobs() {
            return {
                async frame(a, rec) {
                    const el = rec.el, r = () => this._visible(el.getBoundingClientRect());
                    await this._travel(a, () => ({ x: r().right, y: r().bottom }), .35);
                    el.classList.add('cs-frame-fade', 'cs-frame-off');
                    setTimeout(() => el.classList.remove('cs-frame-fade'), 800);
                    await this.clock.tween(.35, EASE.in, p => this._place(a, lerp(r().right, r().left, p), lerp(r().bottom, r().top, p)));
                },
                async media(a, rec) {
                    const el = rec.el, r = () => this._visible(el.getBoundingClientRect()), dir = rec.dir;
                    if (rec.revealing) await rec.revealing;
                    await this._travel(a, () => ({ x: r().right, y: r().top + r().height * .5 }), .35);
                    const scan = this._mk('cs-scan', a.color);
                    await this.clock.tween(.5, EASE.in, p => {
                        const R = el.getBoundingClientRect(), q = 1 - p;
                        el.style.clipPath = this._clip(dir, q);
                        if (dir === 't') Object.assign(scan.style, { transform: `translate(${R.left}px,${R.top + R.height * q}px)`, width: R.width + 'px', height: '3px' });
                        else Object.assign(scan.style, { transform: `translate(${dir === 'r' ? R.right - R.width * q : R.left + R.width * q}px,${R.top}px)`, width: '3px', height: R.height + 'px' });
                        this._place(a, lerp(r().right, r().left, p), r().top + r().height * .5);
                    });
                    scan.remove();
                },
                async pop(a, rec) {
                    const el = rec.el, R = () => el.getBoundingClientRect();
                    await this._travel(a, () => ({ x: R().left + R().width * .5, y: R().top + R().height * .6 }), .25);
                    await this.clock.tween(.2, EASE.in, p => { el.style.opacity = 1 - p; el.style.scale = 1 - .6 * p; });
                },
                // backspace
                async type(a, rec) {
                    const parts = rec.parts, n = parts.length;
                    const per = Math.min(rec.type === 'words' ? .025 : .012, this.opts.typeDuration * .5 / n);
                    const at = i => parts[clamp(i, 0, n - 1)].getBoundingClientRect();
                    await this._travel(a, () => { const R = at(n - 1); return { x: R.right + 8, y: R.top + R.height * .7 }; }, .35);
                    if (this.opts.caret) a.caret.style.opacity = 1;
                    let k = n;
                    await this.clock.tween(n * per, null, p => {
                        const target = n - Math.ceil(p * n);
                        while (k > target) parts[--k].classList.remove('cs-on');
                        const R = at(k - 1), x = k ? R.right : at(0).left - 1;
                        this._caretAt(a, { right: x, top: R.top, height: R.height });
                        this._place(a, lerp(a.x, x + 8, .35), lerp(a.y, R.top + R.height * .7, .35));
                    });
                    a.caret.style.opacity = 0;
                },
                get words() { return this.type; }
            };
        }

        /* ---------- HUD ---------- */
        _makeHud() {
            const h = document.createElement('div');
            h.className = 'cs-hud';
            h.setAttribute('aria-hidden', 'true');
            h.style.zIndex = this.opts.zIndex + 1;
            const [v, x] = String(this.opts.hudPosition).split('-');
            h.style[v === 'top' ? 'top' : 'bottom'] = '12px';
            h.style[x === 'right' ? 'right' : 'left'] = '12px';
            h.innerHTML = '<i></i><span class="cs-st">booting agents…</span><b class="cs-pct">0%</b>';
            document.body.appendChild(h);
            this.hud = h;
            this.hudDot = h.querySelector('i');
            this.hudSt = h.querySelector('.cs-st');
            this.hudPct = h.querySelector('.cs-pct');
        }

        _updateHud() {
            if (!this.hud) return;
            const p = this.progress;
            this.hudPct.textContent = p > .999 ? 'BUILT ✓' : Math.round(p * 100) + '%';
        }

        _teardownWatchers() {
            if (this._io) this._io.disconnect();
            removeEventListener('scroll', this._onScroll);
            removeEventListener('resize', this._onScroll);
        }
    }

    CursorSwarm.version = VERSION;
    CursorSwarm.defaults = DEFAULTS;
    /** Built-in palettes; add your own: CursorSwarm.palettes.brand = { colors: [...] } */
    CursorSwarm.palettes = PALETTES;
    /** Shades of a single color, e.g. CursorSwarm.mono('#ff5e00', 4) */
    CursorSwarm.mono = monoShades;
    /** Black or white, whichever reads better on top of `color`. */
    CursorSwarm.inkOn = inkOn;
    /** Hide the page until init() runs (call it as early as possible, e.g. in <head>). */
    CursorSwarm.cloak = () => { injectStyle(); document.documentElement.classList.add('cs-cloak'); };

    /* ================= zero-JS auto init for easy setup: <script src="cursor-swarm.js" data-auto data-cursors="4"> ================= */
    const script = typeof document !== 'undefined' && document.currentScript;
    if (script && script.hasAttribute('data-auto')) {
        const opts = {};
        for (const [k, raw] of Object.entries(script.dataset)) {
            if (k === 'auto') continue;
            let v = raw;
            if (v === 'true' || v === '') v = true;
            else if (v === 'false') v = false;
            else if (v !== '' && !isNaN(+v)) v = +v;
            else if (/^(colors|names)$/.test(k)) v = v.split(',').map(s => s.trim());
            opts[k] = v;
        }
        CursorSwarm.cloak();
        setTimeout(() => document.documentElement.classList.remove('cs-cloak'), 3000); // safety net
        const go = () => { window.cursorSwarm = new CursorSwarm(opts).init(); };
        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go, { once: true });
        else go();
    }

    return CursorSwarm;
});

/* If you are reading this is because the author of this website did not use the minified version of CursorSwarm. So I will add some extra Bytes to this file 🫪👀🐒 */