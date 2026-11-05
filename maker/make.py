"""Make one Shabd Sketch reel from nothing and queue it for the best time: the whole job, on GitHub.
  python -m maker.make                 Claude picks a new word and writes it → render → queue (approved) at the next best slot
  python -m maker.make --word "मन → मान"   a word of your choice
  python -m maker.make --spec file.json    render a ready spec (no Claude)
  python -m maker.make --no-queue          render only (a test)

Steps: what has worked (reports/insights.json) and which words are used (maker/made.json, queue/, posted/)
→ Claude (Claude Code, the CLAUDE_CODE_OAUTH_TOKEN subscription) writes spec + caption → checked here
→ studio/films/<slug>/build.sh (voice, mix, picture, reading check) → the video goes to the "media" release
→ queue/<slug>/post.json with the next free best slot (ig.best_time); AUTO_APPROVE=1 (default) marks it approved."""
import argparse, datetime as dt, json, os, re, shutil, statistics, subprocess, sys, tempfile, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from ig import best_time  # noqa: E402

STUDIO = os.path.join(ROOT, 'studio'); TEMPLATE = os.path.join(STUDIO, 'films', '_template')
MADE = os.path.join(ROOT, 'maker', 'made.json')
MAX_AHEAD = int(os.environ.get('MAX_AHEAD', '3'))         # don't make more while this many approved reels are waiting
AUTO = os.environ.get('AUTO_APPROVE', '1') == '1'
SEED_WORDS = ['कल → काल', 'सपना → अपना', 'हार → हर', 'चिंता → चिता', 'सब्र → सब']   # made before this maker existed


def jload(p, d):
    try: return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError): return d


def used_words():
    words = list(SEED_WORDS) + [m['word'] for m in jload(MADE, [])]
    for where in ('queue', 'posted'):
        d = os.path.join(ROOT, where)
        for n in os.listdir(d) if os.path.isdir(d) else []:
            t = jload(os.path.join(d, n, 'post.json'), {}).get('title')
            if t: words.append(t)
    return sorted(set(w.strip() for w in words))


def waiting():
    q = os.path.join(ROOT, 'queue')
    return [n for n in os.listdir(q) if jload(os.path.join(q, n, 'post.json'), {}).get('approved')] if os.path.isdir(q) else []


def performance():
    snap = jload(os.path.join(ROOT, 'reports', 'insights.json'), {})
    posts = [p for p in snap.get('posts', []) if (p.get('insights') or {}).get('views') is not None]
    if not posts: return 'No posted reels with numbers yet.'
    med = statistics.median(p['insights']['views'] for p in posts) or 1
    rows = sorted(posts, key=lambda p: -p['insights']['views'])
    return '\n'.join(f"- {p['insights']['views'] / med:.1f}× median · views {p['insights']['views']} · shares {p['insights'].get('shares')} · "
                     f"saves {p['insights'].get('saved')} · caption: {p.get('caption', '')[:70]}" for p in rows[:12])


# ───────── Claude
def ai(prompt, model='sonnet'):
    cli = shutil.which('claude') or sys.exit('claude CLI not found (npm i -g @anthropic-ai/claude-code)')
    env = {k: v for k, v in os.environ.items() if not k.startswith('ANTHROPIC_') and not k.startswith('CLAUDE_CODE_USE_')}
    r = subprocess.run([cli, '-p', '--model', model, '--output-format', 'text', '--tools', '', '--safe-mode'], input=prompt, text=True,
                       encoding='utf-8', capture_output=True, cwd=tempfile.gettempdir(), env=env, timeout=600)
    if r.returncode: raise RuntimeError(f'claude failed: {(r.stderr or r.stdout)[:400]}')
    out = r.stdout
    a, b = out.find('{'), out.rfind('}')
    return json.loads(out[a:b + 1])


RULES = open(os.path.join(ROOT, 'maker', 'brief.md'), encoding='utf-8').read()


def write_spec(word=None, feedback=''):
    example = jload(os.path.join(TEMPLATE, 'spec.example.json'), {})
    prompt = f"""{RULES}

## The example (a reel that is already made; copy its shape, never its words)
{json.dumps(example, ensure_ascii=False, indent=1)}

## Words already used (never repeat one, nor its change)
{', '.join(used_words())}

## How the channel's reels have done (views against the channel's own median)
{performance()}

## Your task
{'Make the reel for this word change: ' + word if word else 'Pick a NEW word change that fits all the rules, the one most likely to be shared by young Hindi speakers, and make its reel.'}
{('Your last attempt was rejected: ' + feedback + ' Fix that.') if feedback else ''}

Answer with ONLY this JSON object, nothing before or after:
{{"slug": "latin-letters-a-to-z-and-dashes, e.g. man-maan", "spec": {{…the spec, same keys as the example…}}, "caption": "…the Instagram caption…"}}"""
    return ai(prompt)


# ───────── checks (the template's rules, so a bad spec never reaches the renderer)
DEV = re.compile(r'[ऀ-ॿ]')


def check(o):
    errs = []
    slug, spec, cap = o.get('slug', ''), o.get('spec') or {}, o.get('caption', '')
    if not re.fullmatch(r'[a-z]+(-[a-z]+)*', slug or ''): errs.append('slug must be latin a-z words joined by dashes')
    if os.path.exists(os.path.join(ROOT, 'queue', slug)) or os.path.exists(os.path.join(ROOT, 'posted', slug)): errs.append(f'slug {slug} is used')
    f, t = spec.get('from'), spec.get('to')
    if not (isinstance(f, list) and isinstance(t, list) and len(f) == 3 and len(t) == 3 and all(isinstance(x, str) for x in f + t)):
        errs.append('from and to must each be [before, part, after] strings')
    else:
        if f[0] != t[0] or f[2] != t[2]: errs.append('from and to must share "before" and "after"; only the middle part changes')
        if f[1] == t[1]: errs.append('the middle part must change')
        if not (f[1] or t[1]): errs.append('one of the parts must be non-empty')
        if ''.join(f) == ''.join(t): errs.append('the two words are the same')
        title = f"{''.join(f)} → {''.join(t)}"
        if title in used_words(): errs.append(f'{title} is already used')
    lines = spec.get('lines') or []
    if not 9 <= len(lines) <= 15: errs.append('9 to 15 lines')
    ids = [L.get('id') for L in lines]
    if ids != [f'N{i + 1}' for i in range(len(lines))]: errs.append('ids must be N1, N2, … in order')
    cues = [L.get('cue') for L in lines if L.get('cue')]
    if cues != ['lift', 'swap', 'resolve']: errs.append('exactly one cue each of lift, swap, resolve, in that order')
    for L in lines:
        if not DEV.search(L.get('text', '')): errs.append(f"{L.get('id')}: text must be Hindi in Devanagari")
        if len(L.get('text', '')) > 70: errs.append(f"{L.get('id')}: spoken line over 70 characters")
        if L.get('write') and len(L['write']) > 26: errs.append(f"{L.get('id')}: written line over 26 characters")
    h = spec.get('hook') or {}
    if not h.get('text') or len(h['text'].split()) > 6: errs.append('hook.text: 1 to 6 words')
    if h.get('until') not in ids[:3]: errs.append('hook.until must be N1, N2 or N3')
    if spec.get('look') not in ('man', 'woman'): errs.append('look: man or woman')
    if not cap or len(cap) > 1500: errs.append('caption: 1 to 1500 characters')
    if cap.count('#') > 5: errs.append('caption: at most 5 hashtags')
    if 'http' in cap: errs.append('caption: no links')
    return errs


def normalise(o):
    s = o['spec']
    s.update(scene='default', safe=True, voice=s.get('voice') or 'hi-IN-SwaraNeural', rate=s.get('rate') or '+8%')
    s['title'] = f"{''.join(s['from'])} → {''.join(s['to'])} · शब्द-चित्र"
    for L in s['lines']:
        for k in list(L):
            if k not in ('id', 'text', 'write', 'cue', 'clear', 'rate', 'gap', 'say'): del L[k]
        L['text'] = unicodedata.normalize('NFC', L['text'])
        if L.get('cue') in ('lift', 'swap'): L.pop('write', None)    # the camera is on the red part then: no time to read
    return o


# ───────── render
def render(slug, spec):
    dest = os.path.join(STUDIO, 'films', slug)
    if os.path.exists(dest): shutil.rmtree(dest)
    shutil.copytree(TEMPLATE, dest, ignore=shutil.ignore_patterns('spec.example.json', 'new-reel.sh', 'out'))
    os.makedirs(os.path.join(dest, 'out'))
    if not os.path.isfile(os.path.join(dest, 'js', 'scenes', f"{spec.get('scene', 'default')}.js")): spec['scene'] = 'default'
    json.dump(spec, open(os.path.join(dest, 'spec.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    r = subprocess.run(['sh', os.path.join(dest, 'build.sh')], env={**os.environ, 'LIB': STUDIO}, text=True, encoding='utf-8',
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(r.stdout[-6000:])
    if r.returncode:
        tail = r.stdout[-1500:]
        raise RenderError(tail)
    ev = jload(os.path.join(dest, 'events.json'), {})
    return dest, ev.get('dur', 0)


class RenderError(RuntimeError):
    pass


def queue(slug, o, dest, dur):
    spec, cap = o['spec'], o['caption']
    q = os.path.join(ROOT, 'queue', slug); os.makedirs(q, exist_ok=True)
    video = os.path.join(dest, f'{slug}.mp4')
    subprocess.run(['gh', 'release', 'view', 'media'], capture_output=True).returncode and subprocess.run(
        ['gh', 'release', 'create', 'media', '--title', 'media', '--notes', 'Reel videos waiting to be posted (deleted once posted).'], check=True)
    subprocess.run(['gh', 'release', 'upload', 'media', video, '--clobber'], check=True)
    for f, to in (('poster.jpg', 'cover.jpg'), (f'{slug}.srt', f'{slug}.srt'), ('spec.json', 'spec.json')):
        if os.path.isfile(os.path.join(dest, f)): shutil.copy(os.path.join(dest, f), os.path.join(q, to))
    title = f"{''.join(spec['from'])} → {''.join(spec['to'])}"
    when = best_time.next_slot()
    meta = {'type': 'reel', 'asset': f'{slug}.mp4', 'title': title, 'caption': cap, 'publish_at': when.isoformat(),
            'approved': AUTO, 'share_to_feed': True, 'made_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'duration': dur}
    json.dump(meta, open(os.path.join(q, 'post.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    made = jload(MADE, []); made.append({'slug': slug, 'word': title, 'hook': spec['hook']['text'], 'at': meta['made_at']})
    json.dump(made, open(MADE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'queued {slug} ({title}, {dur:.1f} s) for {when:%a %d %b %H:%M} IST, {"approved" if AUTO else "waiting for approval"}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--word'); ap.add_argument('--spec'); ap.add_argument('--no-queue', action='store_true'); ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    if not (a.force or a.word or a.spec or a.no_queue) and len(waiting()) >= MAX_AHEAD:
        print(f'{len(waiting())} approved reels are already waiting (max {MAX_AHEAD}); nothing to make'); return
    feedback = ''
    for attempt in range(4):
        if a.spec:
            o = jload(a.spec, {}); o = o if 'spec' in o else {'slug': os.path.splitext(os.path.basename(a.spec))[0], 'spec': o, 'caption': o.get('caption', '')}
        else:
            try: o = write_spec(a.word, feedback)
            except (RuntimeError, ValueError) as e: feedback = f'(the answer was not valid JSON: {e})'; print(feedback); continue
        errs = [] if a.spec else check(o)
        if errs:
            feedback = '; '.join(errs); print(f'attempt {attempt + 1}: {feedback}'); continue
        o = normalise(o) if not a.spec else o
        print(f"making {o['slug']}: {o['spec']['title']} · hook: {o['spec'].get('hook', {}).get('text')}")
        try:
            dest, dur = render(o['slug'], o['spec'])
        except RenderError as e:
            if a.spec: raise
            feedback = f'the render failed (often a written line too long to read in time, or a line the voice cannot say): {str(e)[-600:]}'
            print(f'attempt {attempt + 1}: render failed'); continue
        if not 18 <= dur <= 70:
            feedback = f'the reel came out {dur:.0f} s long; aim for 25 to 45 s'; print(feedback)
            if not a.spec: continue
        if a.no_queue: print(f'rendered {dest}'); return
        queue(o['slug'], o, dest, dur); return
    sys.exit(f'gave up after 4 attempts: {feedback}')


if __name__ == '__main__':
    main()
