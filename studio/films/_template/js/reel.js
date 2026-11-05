// Shabd Sketch · शब्द-चित्र — the generic reel. Everything comes from spec.json and the voice lengths (vo/dur.json):
//   from / to   the two words as [before, changing part, after]; the changing part is red and may be empty on one side:
//               a swap (स → अ), an insertion (कल → काल: from part ""), or a removal (हार → हर: to part "")
//   lines       the narration in order: {id, text, write?, clear?, cue?, gap?}
//               write  = a short line the pencil writes while it is said;  clear = fade the written lines first
//               cue    = "lift" (the red part shows itself: lifts and wobbles, or appears above the word),
//                        "swap" (the old part flies out, the new one drops in, the rest slides over),
//                        "resolve" (the scene's turn: the figure gets up)
//   scene       a module in js/scenes/ that draws the illustration (default.js: a person on a step)
// The camera, the headline's moves, the pencil, the written lines and every sound cue follow from those times.
import * as K from './scene.js';
const { lerp, clamp, ss } = K;
const ctx = document.getElementById('c').getContext('2d');
const PAPER = K.bakePaper();
const SPEC = await (await fetch('spec.json')).json();
const VO = await (await fetch('vo/dur.json')).json();
const EV = [], T = {};
const vo = (L, t) => { T[L.id + 's'] = t; T[L.id] = t + VO[L.id]; EV.push({ t, type: 'vo', id: L.id }, { t: t - .05, type: 'sub', t1: t + VO[L.id] + .3, hi: L.text }); return T[L.id]; };
const at = (id, f) => T[id + 's'] + VO[id] * f;
const eob = u => { u = clamp(u); const c = 1.6; return 1 + (c + 1) * Math.pow(u - 1, 3) + c * Math.pow(u - 1, 2); };
document.title = SPEC.title || document.title;

// ───────── the headline: pieces of the two words, rendered once (so matras and marks keep their real shapes)
const [pre, pa, post] = SPEC.from, [, pb] = SPEC.to;
const wA = pre + pa + post, wB = pre + pb + post;
// Reels safe zone (spec.safe, default on): Instagram's buttons cover the right 230 px and the caption the bottom, so all text
// stays in x 0…850, y 230…1440. spec.hook = {text, until}: a hook card on screen from frame 1 until line `until` ends.
const SAFE = SPEC.safe !== false, CX = SAFE ? 455 : 540, MAXW = SAFE ? 740 : 940, HOOK = SPEC.hook || null;
const SZ = Math.round(Math.min(330, MAXW * 330 / Math.max(K.adv(wA, 330), K.adv(wB, 330)))), BY = HOOK ? 610 : 470;
const xA = CX - K.adv(wA, SZ) / 2, xB = CX - K.adv(wB, SZ) / 2;
const BAND = [BY - SZ * 1.25, SZ * 1.75];
function piece(draw) {                                   // a band of the page holding one piece, plus its ink bounding box
  const c = new OffscreenCanvas(K.W, Math.ceil(BAND[1])), x = c.getContext('2d', { willReadFrequently: true });
  x.translate(0, -BAND[0]); draw(x);
  const d = x.getImageData(0, 0, K.W, c.height).data; let x0 = 1e9, x1 = -1, y0 = 1e9, y1 = -1;
  for (let y = 0; y < c.height; y += 2) for (let i = 0; i < K.W; i += 2) if (d[4 * (y * K.W + i) + 3] > 40) { x0 = Math.min(x0, i); x1 = Math.max(x1, i); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
  return { c, cx: (x0 + x1) / 2, cy: (y0 + y1) / 2 + BAND[0], empty: x1 < 0 };
}
const fill = (x, txt, px, col) => { x.font = `${SZ}px ${K.HEAD}`; x.fillStyle = K.rgba(col); x.fillText(txt, px, BY); };
const clipRange = (x, a, b) => { x.beginPath(); x.rect(a, -1e4, b - a, 2e4); x.clip(); };
const markOf = (word, px, part) => piece(x => {           // the changing part alone: (before + part) minus (before)
  if (!part) return; fill(x, pre + part, px, K.RED); x.globalCompositeOperation = 'destination-out'; if (pre) fill(x, pre, px, [0, 0, 0]); x.globalCompositeOperation = 'source-over';
  if (pre) { const a = px + K.adv(pre, SZ); x.globalCompositeOperation = 'destination-in'; x.fillStyle = '#000'; x.fillRect(a - SZ * .6, -1e4, K.W, 2e4); x.globalCompositeOperation = 'source-over'; }
});
const P_A = markOf(wA, xA, pa), P_B = markOf(wB, xB, pb);
// the parts that stay: cut from the old word, minus the changing part's own pixels (a bindu or matra can sit inside a
// neighbour's advance, e.g. the ं over चि in चिंता)
const minusA = x => { if (P_A.empty) return; x.globalCompositeOperation = 'destination-out'; for (const [dx, dy] of [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]]) x.drawImage(P_A.c, dx, BAND[0] + dy); x.globalCompositeOperation = 'source-over'; };
const P_PRE = piece(x => { if (!pre) return; x.save(); clipRange(x, xA - SZ * .2, xA + K.adv(pre, SZ)); fill(x, wA, xA, K.INK2); x.restore(); minusA(x); });
const P_POST = piece(x => { if (!post) return; const a = xA + K.adv(pre + pa, SZ); x.save(); clipRange(x, a, K.W); fill(x, wA, xA, K.INK2); x.restore(); minusA(x); });
const postShift = (xB + K.adv(pre + pb, SZ)) - (xA + K.adv(pre + pa, SZ)), preShift = xB - xA;

// ───────── the timeline, line by line
const LINES = SPEC.lines;
const lwOf = (text, size) => { const c = new OffscreenCanvas(8, 8).getContext('2d'); c.font = `${size}px ${K.HAND}`; return c.measureText(text).width; };
T.stamp = HOOK ? [.05, .18, .31] : [.15, .45, .75];                    // with a hook card the word is in by 0.7 s
let e = .45, slot = 0;
const WR = [];                                            // written lines: {k, text, y, size, t0, t1, cleared}
for (let i = 0; i < LINES.length; i++) {
  const L = LINES[i], gap = L.gap ?? (i === 0 ? 0 : .3);
  if (L.cue === 'swap' && T.liftEnd) e = Math.max(e, T.liftEnd - .2);
  e = vo(L, e + gap);
  if (L.clear) { WR.forEach(w => w.cleared = w.cleared ?? T[L.id + 's']); slot = 0; }
  if (L.write) {
    let size = L.write.length > 26 ? 48 : L.write.length > 18 ? 52 : 58; const w0 = lwOf(L.write, size); if (w0 > MAXW) size = Math.floor(size * MAXW / w0);
    const nSlots = HOOK ? 2 : 3;                                          // a hook layout sits lower: two written lines, then they roll
    if (slot >= nSlots) { WR.filter(w => !w.cleared).forEach(w => { w.cleared = T[L.id + 's']; }); slot = 0; }
    WR.push({ k: L.id, text: L.write, y: BY + (HOOK ? 150 + slot * 80 : 170 + slot * 86), size, t0: T[L.id + 's'] + .05, t1: T[L.id] + .1 }); slot += 1;
  }
  if (L.cue === 'lift') { T.lift0 = at(L.id, pa ? .5 : .3); T.lift1 = T.lift0 + .55; T.liftEnd = T.lift1; T.liftLine = L.id; }
  if (L.cue === 'swap') {
    T.out0 = T[L.id + 's'] + .05; T.out1 = T.out0 + (pa ? .45 : 0); T.in0 = pb ? Math.max(T.out1, at(L.id, pa ? .7 : .45)) : T.out1; T.in1 = T.in0 + (pb ? .32 : 0);
    T.slide0 = pb ? T.in0 : T.out0 + .15; T.slide1 = pb ? T.in1 : T.out1 + .2; T.land = pb ? T.in1 : T.slide1; T.swapLine = L.id;
    if (i + 1 < LINES.length) LINES[i + 1].gap = Math.max(LINES[i + 1].gap ?? .3, T.land + .15 - T[L.id]);
  }
  if (L.cue === 'resolve') { T.resolve0 = T[L.id + 's'] + .1; T.resolve1 = T.resolve0 + 1.0; T.resolveLine = L.id; }
}
const last = LINES[LINES.length - 1].id;
T.DUR = +(T[last] + (HOOK ? 1.9 : 2.4)).toFixed(2);
if (HOOK) { T.hook0 = 0; T.hook1 = (T[HOOK.until] ?? T[LINES[1]?.id] ?? 3) + .2; }
T.lift0 ??= T.out0 - .9; T.lift1 ??= T.out0 - .3; T.resolve0 ??= T[last + 's']; T.resolve1 ??= T.resolve0 + 1;
WR.forEach(w => { const i = WR.indexOf(w); w.grey = WR.slice(i + 1).find(o => !o.cleared || o.cleared > w.t0)?.t0; });

// the scene (its own module), drawn under the headline
const SCENE = await (await import(`./scenes/${SPEC.scene || 'default'}.js`)).build(K, T, SPEC, ctx);

EV.push({ t: T.stamp[0] + .2, type: 'stamp' }, { t: T.stamp[2] + .2, type: 'stamp' }, { t: T.lift0, type: 'grow', d: T.lift1 - T.lift0 }, { t: T.land, type: 'land' },
  { t: T.resolve0, type: 'stand', d: T.resolve1 - T.resolve0 }, { t: T.resolve0 + .2, type: 'resolve' });
if (pa) EV.push({ t: T.out0, type: 'drop', d: T.out1 - T.out0 }); if (pb) EV.push({ t: T.in0, type: 'drop', d: T.in1 - T.in0 });
WR.forEach(w => EV.push({ t: w.t0, type: 'write', d: w.t1 - w.t0 }));
EV.push(...(SCENE.events || []));
EV.sort((a, b) => a.t - b.t);

// ───────── drawing helpers
const REST = [1260, 980];
let jobs = [];
function pencilAt(t, fronts) {
  const cur = fronts.find(f => f.p); if (cur) return cur.p;
  const before = jobs.filter(j => j[1] <= t).pop(), after = jobs.find(j => j[0] > t);
  const from = before && t - before[1] < 1.6 ? before[2] : REST, to = after && after[0] - t < 1.0 ? after[3] : REST;
  const a = before ? before[1] : 0, b = after && after[0] - t < 1.0 ? after[0] : a + 1.6, u = ss((t - a) / Math.max(.1, b - a));
  return [lerp(from[0], to[0], u), lerp(from[1], to[1], u)];
}
function drawPiece(P, dx, dy, rot, sc, a) {
  if (P.empty || a <= 0) return;
  ctx.save(); ctx.globalAlpha *= a; ctx.translate(P.cx + dx, P.cy + dy); ctx.rotate(rot); ctx.scale(sc, sc); ctx.translate(-P.cx, -P.cy);
  ctx.drawImage(P.c, 0, BAND[0]); ctx.restore();
}
const lw = w => { const c = new OffscreenCanvas(8, 8).getContext('2d'); c.font = `${w.size}px ${K.HAND}`; return c.measureText(w.text).width; };

function frame(t) {
  const cam = camAt(t);
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = '#d9cbb0'; ctx.fillRect(0, 0, K.W, K.H);
  const cr = Math.cos(cam.rot) * cam.z, sr = Math.sin(cam.rot) * cam.z;
  ctx.setTransform(cr, sr, -sr, cr, K.W / 2 - (cr * cam.cx - sr * cam.cy), K.H / 2 - (sr * cam.cx + cr * cam.cy));
  ctx.drawImage(PAPER, 0, 0);
  const fronts = [];
  // headline
  const st = i => eob((t - T.stamp[i]) / .4), sa = i => clamp((t - T.stamp[i]) / .12);
  const slide = ss((t - T.slide0) / (T.slide1 - T.slide0));
  drawPiece(P_PRE, preShift * slide, -(1 - st(0)) * 260, 0, 1, sa(0));
  drawPiece(P_POST, postShift * slide, -(1 - st(2)) * 260, 0, 1, sa(2));
  if (pa && t < T.out1 + .05) {                           // the old part: stamps in red, lifts and wobbles, flies away
    const lift = ss((t - T.lift0) / (T.lift1 - T.lift0)), out = clamp((t - T.out0) / (T.out1 - T.out0)), wob = lift * (1 - out) * Math.sin(t * 9) * .09;
    drawPiece(P_A, -out * out * 700, -(1 - st(1)) * 260 - lift * 110 - out * 420, wob - out * 1.2, 1 + lift * .08, sa(1) * (1 - ss((out - .5) / .5)));
  }
  if (pb && t > T.lift0) {                                 // the new part: appears above (insertion) or waits; drops in
    const d = clamp((t - T.in0) / (T.in1 - T.in0)), g = pa ? (t > T.in0 ? 1 : 0) : ss((t - T.lift0) / (T.lift1 - T.lift0)), hover = (1 - d) * Math.sin(t * 5.5) * .07;
    if (g > 0) drawPiece(P_B, 0, -(1 - d * d) * (pa ? 420 : 330), hover, lerp(.3, 1, g), Math.min(1, g * 2));
  }
  // the hook card: up at frame 1, written in a third of a second, gone when its line has been said
  if (HOOK && t < T.hook1 + .4) {
    const a = 1 - ss((t - T.hook1) / .4), size = Math.min(66, Math.floor(66 * MAXW / lwOf(HOOK.text, 66))), y = BY - SZ * 1.02;
    K.scribble(ctx, HOOK.text, CX, y - (1 - a) * 40, size, 1, { align: 'center', alpha: .95 * a, col: K.INK2 });   // whole at frame 1
    const w = lwOf(HOOK.text, size), u = clamp(t / .3);
    if (u > 0) K.drawPen(ctx, K.penStroke([[CX - w / 2, y + 16], [CX + w / 2, y + 12]], { w: 5, wob: 1.5, seed: 4, over: 6 }), u, K.INK2, .8 * a);
  }
  // written lines
  for (const w of WR) {
    if (t < w.t0) continue;
    let a = .92; if (w.grey && t > w.grey) a = .5; if (w.cleared) a *= 1 - ss((t - w.cleared) / .45);
    if (a <= .01) continue;
    const p = clamp((t - w.t0) / (w.t1 - w.t0)), tip = K.scribble(ctx, w.text, CX, w.y, w.size, p, { align: 'center', alpha: a });
    if (p < 1) fronts.push({ p: tip });
  }
  fronts.push(...SCENE.draw(t, Math.floor(t * 12) % 3).map(p => ({ p })));
  const tip = pencilAt(t, fronts);
  if (tip[0] < 1200) K.pencil(ctx, tip[0], tip[1]);
}
jobs = [...(SCENE.jobs || []), ...WR.map(w => { const h = lw(w) / 2; return [w.t0, w.t1, [CX + h, w.y - w.size * .3], [CX - h, w.y - w.size * .3]]; })].sort((a, b) => a[0] - b[0]);

// ───────── the camera, built from the beats: [t, cx, cy, z, roll, ease]
const rx = (pa ? P_A : P_B).cx, ry = BY - SZ * .45, focus = SCENE.focus || [540, 1250];
const KEYS = [
  ...(HOOK ? [[0, CX, BY - SZ * .55, 1.22, 0], [T.stamp[2] + .5, CX + 5, BY - SZ * .5, 1.24, 0], [T.hook1 - .1, CX + 10, BY - SZ * .3, 1.32, -.008],   // the whole hook card in frame
              [T.hook1 + .7, 540, 960, 1.05, 0, 'out']]
            : [[0, rx, ry - 50, 2.3, 0], [T.stamp[2] + .1, rx + 40, ry - 40, 2.1, 0], [T.stamp[2] + .9, CX + 20, BY + 50, 1.4, -.01, 'out']]),
  [T[LINES[0].id], 540, 960, 1.05, 0],
  [T.lift0 - 2.6, 545, 900, 1.2, .012], [T.lift0 - 1.2, 550, 880, 1.26, -.012],
  [T.lift0 - .4, 540, 960, 1.06, 0], [T.lift0, rx, ry - 80, 1.95, .015, 'whip'], [T.out0 ?? T.in0, rx + 10, ry - 110, 2.05, .01],
  [T.land + .05, CX + 30, BY + 50, 1.32, 0, 'out'], [T.land + 1.6, CX + 30, BY + 30, 1.42, -.008],
  [T.resolve0, focus[0], focus[1] - 150, 1.18, 0], [T.resolve1 + .3, focus[0], focus[1] - 120, 1.22, .006],
  ...(LINES.length > 2 ? [[T[LINES[LINES.length - 2].id + 's'] + .3, focus[0], focus[1] - 60, 1.36, .008]] : []),   // the ask: push in on the result
  [T[last + 's'] + .2, 540, 960, 1.05, 0, 'out'],
  ...(HOOK ? [[T.DUR - 1.0, 540, 960, 1.08, 0], [T.DUR, CX, BY - SZ * .55, 1.22, 0, 'whip']]      // the loop: back to the first frame's framing
           : [[T.DUR, 560, 1060, 1.16, 0]]),
].filter(k => Number.isFinite(k[0])).sort((a, b) => a[0] - b[0]);
const EASE = { io: u => ss(u), whip: u => { u = clamp(u); return u < .5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2; }, out: u => 1 - Math.pow(1 - clamp(u), 3) };
const HITS = [[T.stamp[0] + .2, 1], [T.stamp[2] + .2, .8], [T.land, 1.4], ...(SCENE.hits || [])];
const bumpF = (t, c, w) => { const d = Math.abs(t - c) / w; return d >= 1 ? 0 : ss(1 - d); };
function camAt(t) {
  let k = 0; while (k + 1 < KEYS.length - 1 && t > KEYS[k + 1][0]) k++;
  const a = KEYS[k], b = KEYS[k + 1], u = b[0] > a[0] ? (EASE[b[5] || 'io'])(clamp((t - a[0]) / (b[0] - a[0]))) : 1;
  let cx = lerp(a[1], b[1], u), cy = lerp(a[2], b[2], u), z = lerp(a[3], b[3], u), rot = lerp(a[4], b[4], u);
  for (const [h, amp] of HITS) { const d = t - h; if (d > 0 && d < .45) { const e2 = Math.exp(-d * 9) * amp; cx += Math.sin(d * 70) * 12 * e2; cy += Math.cos(d * 55) * 9 * e2; rot += Math.sin(d * 60) * .012 * e2; z += .05 * e2; } }
  for (const p of SCENE.punches || []) z += .03 * bumpF(t, p + .06, .2);
  cx += (K.n2(t * .35, 1) - .5) * 9; cy += (K.n2(t * .3, 7) - .5) * 9; rot += (K.n2(t * .25, 3) - .5) * .006;
  z = Math.max(z, 1.05);
  const hw = K.W / (2 * z), hh = K.H / (2 * z);
  return { cx: clamp(cx, hw + 8, K.W - hw - 8), cy: clamp(cy, hh + 8, K.H - hh - 8), z, rot };
}

window.DUR = T.DUR; window.EV = EV; window.T = T;
window.render = t => frame(t);
window.TEXTS = t => {
  const out = [], c = camAt(t), S = (x, y) => [K.W / 2 + (x - c.cx) * c.z, K.H / 2 + (y - c.cy) * c.z];
  for (const w of WR) {
    if (t < w.t0 || (w.cleared && t > w.cleared + .45)) continue;
    const h = lw(w) / 2, [a, b] = S(CX - h - 6, w.y - w.size), [d, e2] = S(CX + h + 6, w.y + 10);
    out.push({ id: w.k, text: w.text, x0: a, y0: b, x1: d, y1: e2 });
  }
  if (HOOK && t < T.hook1) { const sz = Math.min(66, Math.floor(66 * MAXW / lwOf(HOOK.text, 66))), h = lwOf(HOOK.text, sz) / 2, y = BY - SZ * 1.02, [a, b] = S(CX - h, y - sz), [d, e2] = S(CX + h, y + 12); out.push({ id: 'hook', text: HOOK.text, x0: a, y0: b, x1: d, y1: e2 }); }
  return out;
};
window.READY = true;
