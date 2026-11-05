// Shabd Sketch · शब्द-चित्र: the pieces every frame is made of. Warm paper; one heavy Hindi headline whose changing
// matra is a separate red piece that can move; small Hindi lines written on by a visible pencil; sketched figures and
// props in pen and wash (engine.js, from the Urban Sketch style). Vertical frame, 1080 × 1920 page units.
import { penStroke, drawPen, drawPrims, figure, sketchShape, wash, fbm, n2, rng, hex, mix3, rgba, lerp, clamp, ss, R3, TAU } from './engine.js';
const { V } = R3;

export const W = 1080, H = 1920;
export const INK2 = [30, 26, 24], RED = hex('#c0392b'), GRAPHITE = [58, 54, 52];
export const HEAD = 'ShabdHead', HAND = 'ShabdHand';

// ───────── paper: warm cream, slow mottling, fine tooth, darker towards the edges (baked once)
export function bakePaper() {
  const s = 4, w = W / s, h = H / s, c = new OffscreenCanvas(w, h), x = c.getContext('2d'), img = x.createImageData(w, h);
  for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
    const m = fbm(i / 60, j / 60, 3, 4) - .5, u = i / w - .5, v = j / h - .5, vig = Math.pow(Math.min(1, Math.hypot(u * 1.25, v * .95) * 1.55), 2.2);
    const k = 1 + m * .06 - vig * .16, q = 4 * (j * w + i);
    img.data[q] = 240 * k; img.data[q + 1] = 228 * k; img.data[q + 2] = 205 * k; img.data[q + 3] = 255;
  }
  x.putImageData(img, 0, 0);
  const out = new OffscreenCanvas(W, H), o = out.getContext('2d'); o.imageSmoothingQuality = 'high'; o.drawImage(c, 0, 0, W, H);
  const t = o.getImageData(0, 0, W, H), R = rng(5);                    // tooth
  for (let i = 0; i < W * H; i++) { const d = (R() - .5) * 7; t.data[4 * i] += d; t.data[4 * i + 1] += d; t.data[4 * i + 2] += d * .9; }
  o.putImageData(t, 0, 0);
  return out;
}

// ───────── the headline: heavy type, one piece per part so a matra can move. parts: [{t, x, y, col, a, rot, clipFrom}]
const mc = new OffscreenCanvas(8, 8).getContext('2d');
export const adv = (txt, size) => { mc.font = `${size}px ${HEAD}`; return mc.measureText(txt).width; };
// draw one part of a word: `txt` drawn whole, then clipped to the advance range [from, to] (so a lone matra keeps its
// own shirorekha piece and never shows a dotted circle)
export function headPart(ctx, txt, x, by, size, o = {}) {
  const from = o.from ?? 0, to = o.to ?? adv(txt, size);
  ctx.save(); ctx.translate(x, by); if (o.rot) ctx.rotate(o.rot); if (o.sc) ctx.scale(o.sc, o.sc);
  ctx.beginPath(); ctx.rect(from - (o.from ? 0 : size * .1), -size * 1.3, to - from + (o.from ? 0 : size * .1) + (o.to ? 0 : size * .1), size * 1.8); ctx.clip();
  ctx.font = `${size}px ${HEAD}`; ctx.fillStyle = rgba(o.col ?? INK2, o.a ?? 1); ctx.fillText(txt, 0, 0);
  ctx.restore();
}

// ───────── small Hindi lines, written on left to right; returns the pencil tip position
export function scribble(ctx, text, x, by, size, p, o = {}) {
  if (p <= 0) return null;
  ctx.save(); ctx.font = `${size}px ${HAND}`;
  const w = ctx.measureText(text).width, a = o.align === 'center' ? x - w / 2 : x;
  ctx.beginPath(); ctx.rect(a - 6, by - size * 1.3, (w + 12) * clamp(p), size * 1.9); ctx.clip();
  ctx.fillStyle = rgba(o.col ?? GRAPHITE, o.alpha ?? .9); ctx.fillText(text, a, by);
  ctx.restore();
  const tx = a + w * clamp(p), wob = Math.sin(p * 90) * size * .18;
  return [tx, by - size * .3 + wob];
}

// ───────── the pencil: graphite tip at (x, y), body up and to the right; a soft shadow on the paper
export function pencil(ctx, x, y, o = {}) {
  const L = o.len ?? 360, r = o.r ?? 13, ang = o.ang ?? -.62;
  ctx.save(); ctx.translate(x, y); ctx.rotate(ang);
  const body = (dx, dy, col) => {
    ctx.fillStyle = col; ctx.beginPath(); ctx.moveTo(dx, dy); ctx.lineTo(dx + 58, dy - r); ctx.lineTo(dx + L, dy - r); ctx.lineTo(dx + L, dy + r); ctx.lineTo(dx + 58, dy + r); ctx.closePath(); ctx.fill();
  };
  ctx.save(); ctx.filter = 'blur(10px)'; ctx.globalAlpha = .28; body(20, 34, '#3a2e22'); ctx.restore();   // shadow
  ctx.fillStyle = '#e3c9a1'; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(58, -r); ctx.lineTo(58, r); ctx.closePath(); ctx.fill();   // sharpened wood
  ctx.fillStyle = '#2f2c2a'; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(18, -r * .32); ctx.lineTo(18, r * .32); ctx.closePath(); ctx.fill();   // graphite
  const g = ctx.createLinearGradient(0, -r, 0, r); g.addColorStop(0, '#5a5d66'); g.addColorStop(.45, '#3b3d44'); g.addColorStop(1, '#25262b');
  ctx.fillStyle = g; ctx.fillRect(58, -r, L - 120, 2 * r);
  ctx.fillStyle = 'rgba(255,255,255,.08)'; ctx.fillRect(58, -r * .55, L - 120, r * .25);
  ctx.fillStyle = '#b8b2a6'; ctx.fillRect(L - 62, -r, 30, 2 * r);                                       // ferrule
  ctx.fillStyle = '#d58a86'; ctx.beginPath(); ctx.roundRect(L - 34, -r, 34, 2 * r, [0, 6, 6, 0]); ctx.fill();   // eraser
  ctx.restore();
}

// ───────── props in pen and wash
const P = (pts, w, seed, o = {}) => ({ k: 'ink', st: penStroke(pts, { w, wob: w * .35, seed, over: w * 2, gap: .3, smooth: o.smooth ?? false }), col: o.col, alpha: o.alpha });
export function cot(x, y, w, seed = 1) {            // a charpai seen slightly from above: x, y = front-left foot on the floor
  const h = 175, d = 130, top = y - h, prims = [];
  const frame = [[x, top], [x + w, top], [x + w + d * .55, top - d * .5], [x + d * .55, top - d * .5]];
  prims.push({ k: 'knock', poly: frame, a: .9 }, { k: 'wash', poly: frame, col: hex('#d9bb86'), a: .55, seed, dx: 3, dy: 2 });
  for (let i = 1; i < 14; i++) { const u = i / 14; prims.push(P([[lerp(x, x + d * .55, 0) + w * u, top], [x + d * .55 + w * u - d * .1, top - d * .5]], 1.2, seed + i, { alpha: .45 })); }
  for (let i = 1; i < 5; i++) { const u = i / 5; prims.push(P([[x + d * .55 * u, top - d * .5 * u], [x + w + d * .55 * u, top - d * .5 * u]], 1.2, seed + 40 + i, { alpha: .45 })); }
  const rail = (a, b, sd) => { const poly = [[a[0], a[1] - 9], [b[0], b[1] - 9], [b[0], b[1] + 9], [a[0], a[1] + 9]]; prims.push({ k: 'wash', poly, col: hex('#a7713f'), a: .75, seed: sd }, P([[a[0], a[1] - 9], [b[0], b[1] - 9]], 2.6, sd), P([[a[0], a[1] + 9], [b[0], b[1] + 9]], 2.2, sd + 1)); };
  rail(frame[3], frame[2], seed + 60); rail(frame[0], frame[3], seed + 62); rail(frame[1], frame[2], seed + 64); rail(frame[0], frame[1], seed + 66);
  for (const [fx, fy, k] of [[x + 10, y, 1], [x + w - 10, y, 1], [x + w + d * .55 - 10, y - d * .5, .8]]) {
    const poly = [[fx - 13 * k, top + 4], [fx + 13 * k, top + 4], [fx + 10 * k, fy], [fx - 10 * k, fy]];
    prims.push({ k: 'knock', poly, a: .9 }, { k: 'wash', poly, col: hex('#8f5f34'), a: .75, seed: seed + fx | 0 }, P([poly[0], poly[3]], 2.4, seed + 70 + fx | 0), P([poly[1], poly[2]], 2.4, seed + 80 + fx | 0));
  }
  return prims;
}
export function wallClock(cx, cy, r, seed = 21) {   // a round wall clock (the hands are drawn per frame)
  const ring = Array.from({ length: 40 }, (_, i) => { const a = i / 40 * TAU; return [cx + Math.cos(a) * r, cy + Math.sin(a) * r]; });
  const prims = [{ k: 'knock', poly: ring, a: .9 }, { k: 'wash', poly: ring, col: hex('#f3ead6'), a: .5, seed, dx: 3, dy: 2 }, P([...ring, ring[0], ring[1]], 3, seed, { smooth: true })];
  for (let i = 0; i < 12; i++) { const a = i / 12 * TAU; prims.push(P([[cx + Math.sin(a) * r * .78, cy - Math.cos(a) * r * .78], [cx + Math.sin(a) * r * .9, cy - Math.cos(a) * r * .9]], i % 3 ? 1.4 : 2.4, seed + 1 + i)); }
  prims.push(P([[cx, cy - r], [cx, cy - r - 26]], 1.6, seed + 20, { alpha: .6 }));   // the nail it hangs on
  return prims;
}
export function floor(y, x0 = 60, x1 = 1020, seed = 3) {
  return [P([[x0, y], [x1 * .5, y + 3], [x1, y - 2]], 2, seed, { smooth: true }), P([[x0 + 120, y + 22], [x0 + 300, y + 24]], 1.2, seed + 1, { alpha: .5 }), P([[x1 - 380, y + 30], [x1 - 160, y + 28]], 1.2, seed + 2, { alpha: .5 })];
}
export function phone(cx, cy, ang, seed = 5) {
  const w = 34, h = 60, c = Math.cos(ang), s = Math.sin(ang), q = (u, v) => [cx + u * c - v * s, cy + u * s + v * c];
  const poly = [q(-w / 2, -h / 2), q(w / 2, -h / 2), q(w / 2, h / 2), q(-w / 2, h / 2)];
  return [{ k: 'wash', poly, col: hex('#2d3038'), a: .9, seed, j: .6, edge: 0 }, { k: 'wash', poly: [q(-w / 2 + 4, -h / 2 + 5), q(w / 2 - 4, -h / 2 + 5), q(w / 2 - 4, h / 2 - 8), q(-w / 2 + 4, h / 2 - 8)], col: hex('#9fc2d8'), a: .7, seed: seed + 1, j: .5, edge: 0 },
    P([...poly, poly[0]], 2, seed + 2)];
}

// ───────── the people: the young man on the cot, and the old man he becomes if he waits
export const LOOK = {
  young: { skin: hex('#c48b69'), top: hex('#6f8fb0'), bottom: hex('#55555d'), hair: hex('#231c19'), pants: 1, sleeve: 'long', torso: [.08, .086, .106], shoe: hex('#3a3434'), hairVol: 1.08 },
  old: { skin: hex('#bf8f73'), top: hex('#9aa6b2'), bottom: hex('#6b6a70'), hair: hex('#d8d3c8'), pants: 1, sleeve: 'long', torso: [.082, .09, .1], shoe: hex('#3a3434'), hairVol: .92 },
};
export const sitPhone = (o = {}) => ({ hipY: .27, hipZ: -.02, lean: .32 + (o.lean ?? 0), nod: -.5 + (o.nod ?? 0), headYaw: o.headYaw ?? 0, twist: o.twist ?? 0,
  footL: V(-.11, .02, .26), footR: V(.1, .02, .3), handL: V(-.035, .5, .2), handR: V(.035, .5, .21), elbL: V(-1, -.4, .2), elbR: V(1, -.4, .2) });
export const standUp = (o = {}) => ({ hipY: .515, lean: o.lean ?? .02, nod: o.nod ?? 0, headYaw: o.headYaw ?? 0, armL: .05, armR: -.05, bendL: .2, bendR: .2, abdL: .1, abdR: .1 });
export const oldStick = (o = {}) => ({ hipY: .47, hipZ: -.04, lean: .34, nod: .25, side: -.04, legL: .12, kneeL: .25, legR: -.08, kneeR: .18,
  handR: V(.2, .42, .16), elbR: V(1, -.2, -.5), armL: -.2, bendL: .9, abdL: .2, headYaw: o.headYaw ?? 0 });
export function person(look, pose, x, y, S, yaw, seed, boil) { return figure(look, pose, { x, y, S, yaw }, { seed, boil }); }

export { penStroke, drawPen, drawPrims, sketchShape, wash, hex, mix3, rgba, lerp, clamp, ss, TAU, n2, V };

// ───────── सपना → अपना: the girl, her step, the dream (line only) and the real house (brick by brick, in colour)
LOOK.girl = { skin: hex('#c78f6e'), top: hex('#c46f5e'), bottom: hex('#4f5a72'), hair: hex('#241b17'), pants: 1, sleeve: 'long', hairLong: 1, torso: [.084, .07, .092], shoe: hex('#3a3434') };
export const sitStep = (o = {}) => ({ hipY: .21, hipZ: -.03, lean: .12, nod: .32 + (o.nod ?? 0), headYaw: o.headYaw ?? 0,
  footL: V(-.1, .02, .27), footR: V(.09, .02, .29), handL: V(-.08, .29, .2), handR: V(.08, .29, .21), elbL: V(-1, -.3, .3), elbR: V(1, -.3, .3) });
export const bendBrick = (o = {}) => ({ hipY: .47, lean: .62, nod: -.2, footL: V(-.09, .02, 0), footR: V(.09, .02, .04),
  handL: V(-.06, .3 + (o.lift ?? 0), .36), handR: V(.06, .3 + (o.lift ?? 0), .37), elbL: V(-1, -.3, 0), elbR: V(1, -.3, 0) });
export const standSide = () => ({ hipY: .515, lean: .03, nod: 0, footL: V(-.09, .02, 0), footR: V(.09, .02, .04), handL: V(-.15, .47, .03), handR: V(.15, .47, .03), elbL: V(-.25, 0, -1), elbR: V(.25, 0, -1) });
export function step(x, y, w = 230, h = 120, seed = 41) {
  const front = [[x, y], [x + w, y], [x + w, y - h], [x, y - h]], top = [[x, y - h], [x + w, y - h], [x + w + 50, y - h - 34], [x + 50, y - h - 34]];
  return [{ k: 'knock', poly: front, a: .9 }, { k: 'wash', poly: front, col: hex('#a9a39a'), a: .6, seed }, { k: 'wash', poly: top, col: hex('#c9c3b8'), a: .55, seed: seed + 1 },
    P([...front, front[0]], 2.4, seed + 2), P([top[0], top[3], top[2], top[1]], 2.2, seed + 3)];
}
export function cloud(cx, cy, rx, ry, seed = 51) {      // a thought cloud: scalloped outline and three small bubbles
  const pts = []; const n = 9;
  for (let i = 0; i <= n * 8; i++) { const a = i / (n * 8) * TAU, bump = .1 * Math.abs(Math.sin(a * n / 2)); pts.push([cx + Math.cos(a) * rx * (1 + bump), cy + Math.sin(a) * ry * (1 + bump)]); }
  return [P(pts, 2.2, seed, { smooth: true })];
}
export function bubbles(pts, seed = 61) { return pts.map(([x, y, r], i) => P(Array.from({ length: 17 }, (_, k) => [x + Math.cos(k / 16 * TAU) * r, y + Math.sin(k / 16 * TAU) * r]), 1.8, seed + i, { smooth: true })); }
export function dreamHouse(cx, by, w, seed = 71) {      // line only, a little shaky: a house that is just an idea
  const h = w * .62, r = w * .5, x0 = cx - w / 2, x1 = cx + w / 2, o = { alpha: .85 };
  return [P([[x0, by], [x0, by - h], [x1, by - h], [x1, by], [x0, by]], 2, seed, o), P([[x0 - 14, by - h], [cx, by - h - r], [x1 + 14, by - h]], 2, seed + 1, o),
    P([[cx - w * .1, by], [cx - w * .1, by - h * .55], [cx + w * .1, by - h * .55], [cx + w * .1, by]], 1.6, seed + 2, o),
    P([[x0 + w * .12, by - h * .7], [x0 + w * .3, by - h * .7], [x0 + w * .3, by - h * .45], [x0 + w * .12, by - h * .45], [x0 + w * .12, by - h * .7]], 1.4, seed + 3, o)];
}
// the real house: bricks laid row by row (each brick its own wash and outline), then roof, door, window
export const BRICK = { w: 64, h: 32 };
export function brickList(x0, by, cols, rows, door) {
  const out = [];
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols + (r % 2 ? 0 : 0); c++) {
    const off = r % 2 ? BRICK.w / 2 : 0, x = x0 + c * BRICK.w + off, y = by - (r + 1) * BRICK.h;
    if (x + BRICK.w > x0 + cols * BRICK.w + 1) continue;
    if (door && x + BRICK.w > door[0] && x < door[1] && r < door[2]) continue;
    out.push([x, y]);
  }
  return out;
}
export function brick(x, y, seed) {
  const p = [[x + 2, y + 2], [x + BRICK.w - 2, y + 2], [x + BRICK.w - 2, y + BRICK.h - 2], [x + 2, y + BRICK.h - 2]];
  return [{ k: 'knock', poly: p, a: .9 }, { k: 'wash', poly: p, col: hex(seed % 3 ? '#b85a3e' : '#a84f37'), a: .78, seed, j: 1.5, dx: 2, dy: 1 }, P([...p, p[0]], 1.8, seed + 7)];
}
export function roof(x0, x1, y, h, seed = 81) {
  const p = [[x0 - 26, y], [(x0 + x1) / 2, y - h], [x1 + 26, y]];
  return [{ k: 'knock', poly: p, a: .9 }, { k: 'wash', poly: p, col: hex('#7d4a3a'), a: .8, seed, dx: 3, dy: 2 }, P([...p, p[0]], 2.6, seed + 1)];
}
export function doorWin(dx0, dx1, by, dh, wx, wy, seed = 91) {
  const d = [[dx0, by], [dx0, by - dh], [dx1, by - dh], [dx1, by]], w = [[wx, wy], [wx + 70, wy], [wx + 70, wy + 60], [wx, wy + 60]];
  return [{ k: 'wash', poly: d, col: hex('#6b4a33'), a: .85, seed }, P(d, 2.4, seed + 1), { k: 'wash', poly: w, col: hex('#e9c46a'), a: .75, seed: seed + 2 }, P([...w, w[0]], 2.2, seed + 3), P([[wx + 35, wy], [wx + 35, wy + 60]], 1.6, seed + 4), P([[wx, wy + 30], [wx + 70, wy + 30]], 1.6, seed + 5)];
}
