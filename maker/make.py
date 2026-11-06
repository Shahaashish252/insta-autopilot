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
from maker import progress as P  # noqa: E402
from maker.hookscore import score as hook_score  # noqa: E402
from maker.captionlint import lint as caption_lint  # noqa: E402

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
VIRAL = open(os.path.join(ROOT, 'maker', 'viral.md'), encoding='utf-8').read()
HOOK_MIN = 65
note = lambda f, empty: (open(os.path.join(ROOT, 'maker', f), encoding='utf-8').read().split('-->', 1)[-1].strip()
                         if os.path.isfile(os.path.join(ROOT, 'maker', f)) else empty)


def write_spec(word=None, feedback=''):
    example = jload(os.path.join(TEMPLATE, 'spec.example.json'), {})
    prompt = f"""{RULES}

{VIRAL}

## What works on this channel (weekly review of its own numbers; follow it unless it breaks a rule above)
{note('learnings.md', 'No review yet (new channel): follow the playbook.')}

## Hook formulas working in the niche right now (use the shapes, never anyone's words)
{note('swipe.md', 'No niche data yet.')}

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
{{"slug": "latin-letters-a-to-z-and-dashes, e.g. man-maan",
 "hooks": [{{"formula": "name from the playbook", "line": "spoken hook", "card": "on-screen hook, max 6 words"}}, …three, each a different formula…],
 "spec": {{…the spec, same keys as the example; N1.text is the strongest of your three hooks' "line" and hook.text its "card"…}},
 "caption": "…the Instagram caption…"}}
Hooks are scored here (4-9 words said in under 2.5 s, concrete, something at stake, payload up front, talks to "तुम";
no preamble); N1 must score at least {HOOK_MIN} and be your best-scoring hook."""
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
    hooks = o.get('hooks') or []
    if len(hooks) != 3 or len({(x.get('formula') or '').strip().lower() for x in hooks}) != 3 or not all(x.get('line') for x in hooks):
        errs.append('hooks: exactly three, each with a different formula and a line')
    elif lines:
        scored = [(hook_score(x['line'])[0], x['line']) for x in hooks]
        n1, best = lines[0].get('text', '').strip(), max(scored)
        if n1 not in [x['line'].strip() for x in hooks]: errs.append('N1.text must be one of your three hooks, word for word')
        else:
            mine = hook_score(n1)
            if mine[0] < HOOK_MIN: errs.append(f'N1 hook scores {mine[0]} (needs {HOOK_MIN}): {mine[1]}; make it shorter, concrete, with a stake, said to "तुम"')
            elif mine[0] < best[0] - 10: errs.append(f'N1 is not your strongest hook: "{best[1]}" scores {best[0]}')
    if isinstance(f, list) and isinstance(t, list) and len(f) == len(t) == 3:
        errs += caption_lint(cap, [''.join(f), ''.join(t)])
    else: errs += caption_lint(cap)
    for L in lines:
        if '—' in L.get('text', '') or '—' in (L.get('write') or ''): errs.append(f"{L.get('id')}: no em dash (—); use … or a comma")
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
    # build.sh runs voice → speech check → timing → music → reading check → picture → master → subtitles → cover;
    # its output says where it is, which becomes the live progress on the dashboard
    proc = subprocess.Popen(['sh', os.path.join(dest, 'build.sh')], env={**os.environ, 'LIB': STUDIO}, text=True, encoding='utf-8',
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1)
    log, cur, frames = [], None, {}

    def go(key, detail=None):
        nonlocal cur
        if cur and cur != key: P.stage(cur, 'done')
        cur = key; P.stage(key, 'running', detail)
    go('voice')
    for line in proc.stdout:
        print(line, end=''); log.append(line); l = line.strip()
        if l.startswith('mismatches:'): P.stage('speech', 'running', l); go('timing')
        elif re.match(r'^(OK|BAD|\?\?)\s+N\d+ \|', l) and cur == 'voice': go('speech')
        elif l.startswith('events '): m = re.match(r'events (\d+) dur ([\d.]+)', l); go('music', f'{m[1]} sound cues, {float(m[2]):.1f} s' if m else None)
        elif l.startswith('mix.wav'): P.stage('music', 'running', l); go('reading')
        elif l == 'readcheck ok': go('picture', '0 %'); P.stage('reading', 'done', 'every line readable')
        elif re.match(r'^w\d+ \d+/\d+', l):
            w, x, y = re.match(r'^w(\d+) (\d+)/(\d+)', l).groups(); frames[w] = (int(x), int(y))
            done, tot = sum(v[0] for v in frames.values()), sum(v[1] for v in frames.values())
            P.stage('picture', 'running', f'{100 * done // max(tot, 1)} % ({done}/{tot} frames, {len(frames)} workers)', force=False)
        elif l.startswith('done ') and cur == 'picture': go('master')
    proc.wait()
    out = ''.join(log)
    if proc.returncode:
        if cur: P.stage(cur, 'failed', out.strip().splitlines()[-1][:200] if out.strip() else 'failed')
        raise RenderError(out[-1500:])
    if cur: P.stage(cur, 'done')
    ev = jload(os.path.join(dest, 'events.json'), {})
    return dest, ev.get('dur', 0)


class RenderError(RuntimeError):
    pass


def queue(slug, o, dest, dur):
    spec, cap = o['spec'], o['caption']
    q = os.path.join(ROOT, 'queue', slug); os.makedirs(q, exist_ok=True)
    video = os.path.join(dest, f'{slug}.mp4')
    P.stage('upload', 'running', f'{os.path.getsize(video) / 1e6:.0f} MB')
    subprocess.run(['gh', 'release', 'view', 'media'], capture_output=True).returncode and subprocess.run(
        ['gh', 'release', 'create', 'media', '--title', 'media', '--notes', 'The reels made on GitHub (played on the dashboard; posted from here).'], check=True)
    subprocess.run(['gh', 'release', 'upload', 'media', video, '--clobber'], check=True)
    P.stage('upload', 'done')
    for f, to in (('poster.jpg', 'cover.jpg'), (f'{slug}.srt', f'{slug}.srt'), ('spec.json', 'spec.json')):
        if os.path.isfile(os.path.join(dest, f)): shutil.copy(os.path.join(dest, f), os.path.join(q, to))
    title = f"{''.join(spec['from'])} → {''.join(spec['to'])}"
    when = best_time.next_slot()
    n1 = spec['lines'][0]['text']; used = next((x for x in o.get('hooks') or [] if x.get('line', '').strip() == n1.strip()), {})
    meta = {'type': 'reel', 'asset': f'{slug}.mp4', 'title': title, 'caption': cap, 'publish_at': when.isoformat(),
            'approved': AUTO, 'share_to_feed': True, 'made_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'duration': dur,
            'hook_formula': used.get('formula'), 'hook_score': hook_score(n1)[0],
            'hooks': [{**x, 'score': hook_score(x.get('line', ''))[0]} for x in o.get('hooks') or []]}
    json.dump(meta, open(os.path.join(q, 'post.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    made = jload(MADE, []); made.append({'slug': slug, 'word': title, 'hook': spec['hook']['text'], 'hook_formula': meta['hook_formula'],
                                     'hook_score': meta['hook_score'], 'at': meta['made_at']})
    json.dump(made, open(MADE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'queued {slug} ({title}, {dur:.1f} s) for {when:%a %d %b %H:%M} IST, {"approved" if AUTO else "waiting for approval"}')
    P.stage('queued', 'done', f'{when:%a %d %b, %I:%M %p} IST'); P.info(publish_at=when.isoformat(), slug=slug, duration=dur)
    P.finish('done', f'{title} · posts {when:%a %d %b, %I:%M %p} IST')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--word'); ap.add_argument('--spec'); ap.add_argument('--no-queue', action='store_true'); ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    if not (a.force or a.word or a.spec or a.no_queue) and len(waiting()) >= MAX_AHEAD:
        msg = f'{len(waiting())} approved reels are already waiting (max {MAX_AHEAD}); nothing to make'
        print(msg); P.finish('skipped', msg); return
    feedback, attempts = '', []
    for attempt in range(4):
        if a.spec:
            o = jload(a.spec, {}); o = o if 'spec' in o else {'slug': os.path.splitext(os.path.basename(a.spec))[0], 'spec': o, 'caption': o.get('caption', '')}
        else:
            P.stage('write', 'running', f'attempt {attempt + 1}: Claude is choosing a word' + (f' ({a.word})' if a.word else ''))
            try: o = write_spec(a.word, feedback)
            except (RuntimeError, ValueError) as e:
                feedback = f'(the answer was not valid JSON: {e})'; print(feedback); attempts.append(feedback[:300]); P.info(attempts=attempts); continue
        errs = [] if a.spec else check(o)
        if errs:
            feedback = '; '.join(errs); print(f'attempt {attempt + 1}: {feedback}')
            attempts.append(f"{(o.get('spec') or {}).get('from')}: rejected ({feedback})"[:300]); P.info(attempts=attempts); continue
        o = normalise(o) if not a.spec else o
        print(f"making {o['slug']}: {o['spec']['title']} · hook: {o['spec'].get('hook', {}).get('text')}")
        sp = o['spec']; word = sp.get('title', o['slug']).split(' · ')[0]
        P.info(word=word, slug=o['slug'], hook=(sp.get('hook') or {}).get('text'), caption=o.get('caption'),
               hooks=[{**x, 'score': hook_score(x.get('line', ''))[0]} for x in o.get('hooks') or []],
               lines=[{'id': L['id'], 'text': L['text'], 'write': L.get('write'), 'cue': L.get('cue')} for L in sp['lines']])
        P.stage('write', 'done', word)
        for st in P._load().get('stages', []):                          # a retry runs these again
            if st['key'] in ('voice', 'speech', 'timing', 'music', 'reading', 'picture', 'master'): st.update(state='waiting', detail=None)
        try:
            dest, dur = render(o['slug'], o['spec'])
        except RenderError as e:
            if a.spec: raise
            feedback = f'the render failed (often a written line too long to read in time, or a line the voice cannot say): {str(e)[-600:]}'
            print(f'attempt {attempt + 1}: render failed')
            attempts.append(f"{o['spec'].get('title', o['slug']).split(' · ')[0]}: render failed ({str(e).strip().splitlines()[-1][:200] if str(e).strip() else ''})")
            P.info(attempts=attempts); continue
        if not 18 <= dur <= 70:
            feedback = f'the reel came out {dur:.0f} s long; aim for 25 to 45 s'; print(feedback)
            if not a.spec: continue
        if a.no_queue: print(f'rendered {dest}'); return
        queue(o['slug'], o, dest, dur); return
    P.finish('failed', f'gave up after 4 attempts: {feedback[:300]}')
    sys.exit(f'gave up after 4 attempts: {feedback}')


if __name__ == '__main__':
    main()
