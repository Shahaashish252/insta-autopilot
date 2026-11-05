// The default scene for any word: a person on a stone step. Drawn on by the pencil while the first line is said
// (line, then colour); idle, head down; looks up at the word when it starts to change ("lift"); gets up at "resolve"
// and turns a little towards us. spec.look: "man" | "woman".
// A custom scene is a module with the same interface: build(K, T, spec, ctx) → { draw(t, boil) → [pen fronts],
// jobs: [[t0, t1, endPoint, startPoint]] for the pencil's glide, events, focus: [x, y] for the camera, hits, punches }.
// After each draw, this.head = {c: [x, y], r} and this.rise (0 sitting … 1 standing), so a wrapping scene can add props.
import { mixPose } from '../poses.js';
export function build(K, T, spec, ctx) {
  const { lerp, clamp, ss, V } = K, FY = 1600, SC = 660, X0 = 330, X1 = 470;
  const look = spec.look === 'woman' ? K.LOOK.girl : K.LOOK.young;
  const fast = !!spec.hook, draw0 = fast ? .1 : .3, draw1 = fast ? 1.9 : 2.7, wash0 = fast ? 1.2 : 1.9, wash1 = fast ? 2.6 : 3.6;   // a hook-first reel draws faster
  function drawOn(prims, p, c) {
    const inks = prims.filter(q => q.k === 'ink'), tot = inks.reduce((a, q) => a + q.st.L, 0);
    let left = p * tot, front = null; const amt = new Map();
    for (const q of inks) { const f = clamp(left / q.st.L); amt.set(q, f); if (f > 0 && f < 1 && !front) front = q.st.P[Math.min(q.st.P.length - 1, Math.floor(f * (q.st.P.length - 1)))]; left -= q.st.L; }
    K.drawPrims(ctx, prims, { color: c, ink: q => amt.get(q) ?? 1, knock: clamp(c * 1.5) });
    return p > 0 && p < 1 ? front : null;
  }
  return {
    focus: [X1, FY - 380],
    jobs: [[draw0, draw1, [X0 + 100, FY - 380], [200, FY]]],
    events: [{ t: draw0, type: 'draw', d: draw1 - draw0 }],
    draw(t, boil) {
      const p = clamp((t - draw0) / (draw1 - draw0)), c = ss((t - wash0) / (wash1 - wash0));
      const up = ss((t - T.lift0 + .3) / .6), rise = ss((t - T.resolve0) / (T.resolve1 - T.resolve0));
      let pose = { ...K.sitStep({ nod: lerp(-1.0, -.02, up) + Math.sin(t * .9) * .03 }), lean: lerp(.42, .12, up),
        handL: V(-.07, lerp(.33, .29, up), .21), handR: V(.07, lerp(.33, .29, up), .22) };
      if (rise > 0) pose = mixPose(pose, K.standSide(), rise);
      const f1 = drawOn([...K.floor(FY), ...K.step(X0 - 115, FY)], clamp(p * 1.7), c);
      const x = lerp(X0, X1, rise), y = lerp(FY - 130, FY - 30, rise);
      const fig = K.person(look, pose, x, y, SC, Math.PI * lerp(.88, .97, rise), 17, boil);
      const f2 = drawOn(fig, clamp(p * 1.7 - .7), c);
      this.head = fig.head; this.rise = rise;                          // for props that follow the figure (a custom scene can wrap this one)
      return [f1, f2];
    },
  };
}
