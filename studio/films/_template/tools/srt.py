"""<reel>.srt from the voice cues the page exports into events.json (type 'sub': t, t1, hi). usage: python tools/srt.py <out.srt>"""
import os, sys, json
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ev = json.load(open(os.path.join(HERE, 'events.json'), encoding='utf-8'))['ev']
cues = sorted((e for e in ev if e['type'] == 'sub'), key=lambda e: e['t'])
ts = lambda x: '%02d:%02d:%02d,%03d' % (x // 3600, x % 3600 // 60, x % 60, round(x % 1 * 1000) % 1000)
out = [f"{k + 1}\n{ts(max(0, e['t']))} --> {ts(min(e['t1'], cues[k + 1]['t']) if k + 1 < len(cues) else e['t1'])}\n{e['hi']}\n" for k, e in enumerate(cues)]
open(sys.argv[1], 'w', encoding='utf-8').write('\n'.join(out)); print(f'{sys.argv[1]}: {len(cues)} cues')
