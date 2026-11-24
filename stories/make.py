"""Story images for scheduled reels: queue/<slug>/story.jpg (1080x1920), posted by ig.publish when the reel goes live.
  python stories/make.py [slug ...]   then   node stories/render.mjs
Look: the reel's own cover, blurred, under a paper card with the word pair (new word in red) and 'नई रील आ गई'."""
import html, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); Q = os.path.join(ROOT, 'queue')
FONTS = os.path.join(ROOT, 'studio', 'films', '_template', 'fonts').replace(os.sep, '/')
E = html.escape
CSS = '''@font-face { font-family: Yatra; src: url("file:///F/YatraOne-Regular.ttf"); }
@font-face { font-family: Kalam; src: url("file:///F/Kalam-Bold.ttf"); }
* { box-sizing: border-box; margin: 0; padding: 0; } body { background: #000; }
section { width: 1080px; height: 1920px; position: relative; overflow: hidden; font-family: Kalam, sans-serif; }
.bg { position: absolute; inset: -60px; background-size: cover; background-position: center; filter: blur(22px) brightness(.55); }
.shade { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(0,0,0,.35), rgba(0,0,0,.05) 40%, rgba(0,0,0,.45)); }
.card { position: absolute; left: 90px; right: 90px; top: 470px; padding: 70px 60px 80px; border-radius: 48px; text-align: center;
  background: radial-gradient(ellipse at 50% 40%, #f2e6ce 0%, #f2e6ce 55%, #e3d7c1 100%); box-shadow: 0 30px 80px rgba(0,0,0,.45); transform: rotate(-1.5deg); }
.tag { display: inline-block; background: #c1392b; color: #fff; font-size: 52px; padding: 8px 38px 14px; border-radius: 40px; }
.pair { font-family: Yatra; font-size: 170px; line-height: 1.35; color: #1e1a17; margin: 40px 0 10px; white-space: nowrap; }
.pair .arrow { font-family: Kalam; font-size: 90px; color: #484441; margin: 0 22px; } .pair .red { color: #c1392b; }
.hook { font-size: 56px; line-height: 1.4; color: #1e1a17; }
.tap { margin-top: 46px; font-size: 50px; color: #c1392b; }
.foot { position: absolute; left: 0; right: 0; bottom: 380px; text-align: center; color: #f2e6ce; font-size: 46px; text-shadow: 0 4px 16px rgba(0,0,0,.6); }
.foot b { font-family: Yatra; font-weight: normal; }'''
def section(slug, m):
    a, b = [w.strip() for w in m['title'].split('→')]
    hook = m['caption'].split('\n')[0].split(',')[0].strip()           # "जो ... हैं" — who this reel is for
    if len(hook) > 60: hook = hook[:58].rsplit(' ', 1)[0] + '...'
    cover = os.path.join(Q, slug, 'cover.jpg').replace(os.sep, '/')
    pair_px = 170 if len(a + b) <= 9 else 130
    return (f'<section data-slug="{slug}"><div class="bg" style="background-image:url(\'file:///{cover}\')"></div><div class="shade"></div>'
            f'<div class="card"><span class="tag">नई रील आ गई</span>'
            f'<div class="pair" style="font-size:{pair_px}px">{E(a)}<span class="arrow">→</span><span class="red">{E(b)}</span></div>'
            f'<div class="hook">{E(hook)}…</div><div class="tap">👆 ऊपर नाम पर टैप करो, रील देखो</div></div>'
            f'<div class="foot">एक अक्षर का खेल · हर शाम 7 बजे<br><b>@anek.arthi</b></div></section>')
if __name__ == '__main__':
    slugs = sys.argv[1:] or sorted(d for d in os.listdir(Q) if os.path.isfile(os.path.join(Q, d, 'post.json')))
    out = []
    for s in slugs:
        m = json.load(open(os.path.join(Q, s, 'post.json'), encoding='utf-8'))
        if os.path.isfile(os.path.join(Q, s, 'cover.jpg')): out.append(section(s, m))
    os.makedirs(os.path.join(HERE, '_build'), exist_ok=True)
    open(os.path.join(HERE, '_build', 'stories.html'), 'w', encoding='utf-8').write(
        '<!doctype html><html lang="hi"><head><meta charset="utf-8"><style>' + CSS.replace('file:///F/', f'file:///{FONTS}/') + '</style></head><body>' + ''.join(out) + '</body></html>')
    print(len(out), 'stories')
