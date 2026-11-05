"""Sound for any Shabd Sketch reel -> mix.wav (48 kHz stereo, exactly DUR seconds).
Run from the library root:  node core/render/events.mjs <reel folder> --size 1080x1920  then  python <reel folder>/audio.py
Voice: edge-tts (vo/*.wav, voice and rate from spec.json), the loudest thing. Pencil on paper: band-passed noise with fibre texture and
grain clicks, one burst per written or drawn stretch. Stamps, the old part flying out and the new one landing, any scene sounds: all
synthesised. Score: nylon guitar and pizzicato bass (core/audio/pluck.py), sparse: a minor sway until the word changes, a major resolve at the turn."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); LIB = os.path.abspath(os.path.join(HERE, '../..'))
sys.path.insert(0, LIB)
import numpy as np, soundfile as sf, soxr
from scipy.ndimage import uniform_filter1d, maximum_filter1d
from core.audio import sampler as S, pluck as P
from core.audio.sfx import SR, add, whoosh, noise, bp, hp, lp, t_, brown, thump

rng = np.random.default_rng(11)
EV = json.load(open(os.path.join(HERE, 'events.json'), encoding='utf-8'))
DUR = EV['dur']; ev = EV['ev']; N = int(round(DUR * SR))
of = lambda k: [e for e in ev if e['type'] == k]
first = lambda k: of(k)[0]
vo = {e['id']: e['t'] for e in ev if e['type'] == 'vo'}
vdur = json.load(open(os.path.join(HERE, 'vo/dur.json')))
voice, fx, mus = (np.zeros((N, 2), np.float32) for _ in range(3))

# ---------------------------------------------------------------- voice
for vid, t in vo.items():
    x, sr = sf.read(os.path.join(HERE, 'vo', vid + '.wav'), dtype='float32')
    if x.ndim > 1: x = x.mean(1)
    x = soxr.resample(x, sr, SR); x = hp(x, 90).astype(np.float32)
    x = x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * .085
    add(voice, x, t, 1.0, 0)
vpres = np.abs(voice[:, 0]); k = int(.25 * SR)
vpres = uniform_filter1d(vpres, k); vpres = np.clip(vpres / (vpres.max() + 1e-9) * 3, 0, 1)
vpres = maximum_filter1d(vpres, int(.3 * SR), origin=-int(.12 * SR))      # look ahead: the dip is in place before a word

# ---------------------------------------------------------------- pencil, paper, eraser
def pencil(d, v=.2):
    """graphite on paper for d seconds: fibre-textured hiss in strokes of 0.08–0.25 s, with grain clicks"""
    n = int(d * SR); y = np.zeros(n, np.float32); pos = 0
    while pos < n:
        L = int(rng.uniform(.08, .25) * SR); L = min(L, n - pos)
        s = bp(noise(L / SR), 1600, 7000) * (.6 + .4 * np.abs(np.sin(np.linspace(0, np.pi * rng.uniform(1, 3), L))))
        env = np.minimum(1, np.minimum(np.arange(L), L - np.arange(L)) / (.012 * SR))
        y[pos:pos + L] += (s * env * rng.uniform(.6, 1)).astype(np.float32); pos += L + int(rng.uniform(.01, .05) * SR)
    clicks = np.zeros(n); idx = rng.integers(0, max(1, n), int(d * 60)); clicks[idx] = rng.uniform(-1, 1, len(idx))
    y += (hp(clicks, 2500) * .25).astype(np.float32)
    return y * v
for e in of('write') + of('draw'):
    add(fx, pencil(e['d'], .16 if e['type'] == 'write' else .11), e['t'], 1.0, .25 if e['type'] == 'write' else -.1)
def stamp(v=1.0):                                                    # heavy type landing on paper: a paper slap and a low thud
    s = bp(noise(.12), 300, 3000) * np.exp(-t_(.12) / .018) * .5
    return (np.pad(s, (0, int(.4 * SR))) [:int(.52 * SR)] + np.pad(thump(.7 * v, 70), (0, int(.52 * SR)))[:int(.52 * SR)] * .9).astype(np.float32) * v
for e in of('stamp'): add(fx, stamp(1.2 if e.get('big') else 1.0), e['t'], 1.0, 0)
g = first('grow'); add(fx, (bp(noise(g['d']), 2000, 6000) * np.linspace(0, 1, int(round(g['d'] * SR))) * .05).astype(np.float32), g['t'], 1.0, 0)   # the स starts to lift
for d in of('drop'): add(fx, whoosh(d['d'] + .1, .6) * .45, d['t'], 1.0, 0)                  # the old part flies out / the new one falls in
add(fx, stamp(1.1) * 1.2, first('land')['t'] - .02, 1.0, 0)
for e in of('brick'):                                                                           # scene sounds a custom scene may send
    k = bp(noise(.09), 180, 1400) * np.exp(-t_(.09) / .02) * (.55 if e.get('slow') else .35)
    add(fx, (k + thump(.35 if e.get('slow') else .2, 95)[:len(k)] * .6).astype(np.float32), e['t'], 1.0, .35)
e = first('stand'); add(fx, (lp(brown(.5), 500) * np.exp(-t_(.5) / .2) * .4).astype(np.float32), e['t'] + .1, 1.0, -.2)   # cloth as the figure gets up
room = lp(brown(DUR), 700) * .005; fx[:, 0] += room[:N]; fx[:, 1] += np.roll(room, 997)[:N]

# ---------------------------------------------------------------- score: sparse nylon guitar and bass, G major (a hopeful one)
def gt(t, p, v=.6, pan=0, g=1.0, dur=3.0):
    if 0 <= t < DUR: add(mus, P.pluck('nylon_guitar', p, dur, v).astype(np.float32), t, g, pan)
def bs(t, p, v=.6, g=1.0):
    if 0 <= t < DUR: add(mus, P.pluck('upright_bass_pizz', p, 1.6, v).astype(np.float32), t, g, 0)
BEAT = 60 / 80
tl = first('land')['t']
gt(of('stamp')[1]['t'] + .05, 'D3', .6, 0, .9, 4)                                     # the word stands
t, i = vo[sorted(vo, key=vo.get)[1]] - BEAT, 0                                        # a soft minor sway until the change
while t < first('grow')['t'] - .2:
    gt(t, ['A3', 'F3', 'G3', 'E3'][i % 4], .4, -.2 if i % 2 else .2, .55, 2.5)
    if i % 2 == 0: bs(t, ['D2', 'Bb1', 'C2', 'A1'][(i // 2) % 4], .45, .55)
    t += BEAT * 2; i += 1
gt(first('grow')['t'], 'A4', .45, 0, .6, 3)                                            # the red part shows itself
gt(tl, 'D3', .7, 0, 1.0, 4); gt(tl + .01, 'A3', .55, 0, .8, 4); bs(tl, 'D2', .7, .9)  # the new word lands
tf = first('resolve')['t']                                                              # the turn: the figure resolves to D major
for j, (p, dt) in enumerate([('D3', 0), ('A3', .22), ('D4', .44), ('F#4', .66), ('A4', 1.1)]): gt(tf + dt, p, .62 - .03 * j, -.2 + .1 * j, .95, 4.5)
bs(tf, 'D2', .7, .9)

mus = S.room(mus, size=.4, mix=.18)
duck = (1 - .86 * vpres)[:, None]; fxd = (1 - .85 * vpres)[:, None]   # pencil and paper stay well under the words
mix = voice * 1.0 + fx * .9 * fxd + mus * .8 * duck

def lufs(x):
    from scipy.signal import lfilter
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, .73248077421585]
    b2, a2 = [1, -2, 1], [1, -1.99004745483398, .99007225036621]
    y = lfilter(b2, a2, lfilter(b1, a1, x, axis=0), axis=0); blk = int(.4 * SR); hop = int(.1 * SR)
    ms = np.array([np.mean(np.sum(y[i:i + blk] ** 2, 1)) for i in range(0, len(y) - blk, hop)])
    l = -.691 + 10 * np.log10(ms + 1e-12); ms = ms[l > -70]; l0 = -.691 + 10 * np.log10(ms.mean()) - 10
    ms = ms[-.691 + 10 * np.log10(ms + 1e-12) > l0]; return -.691 + 10 * np.log10(ms.mean())
def limit2(x, ceil, look=.004):
    n = int(look * SR); m = maximum_filter1d(np.abs(x).max(1), size=2 * n + 1)
    g = uniform_filter1d(np.minimum(1, ceil / np.maximum(m, 1e-9)), size=n); return x * g[:, None]
for _ in range(4): mix *= 10 ** ((-16 - lufs(mix)) / 20); mix = limit2(mix, .6)
over = soxr.resample(mix, SR, SR * 4); tp = 20 * np.log10(np.abs(over).max() + 1e-12)
if tp > -2.0: mix *= 10 ** ((-2.0 - tp) / 20)
mix = mix[:N].astype(np.float32)
if len(mix) < N: mix = np.pad(mix, ((0, N - len(mix)), (0, 0)))
sf.write(os.path.join(HERE, 'mix.wav'), mix, SR, subtype='PCM_24')
print(f'mix.wav  {DUR:.2f} s  {lufs(mix):.1f} LUFS')
