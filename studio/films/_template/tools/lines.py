"""spec.json → lines.json for the voice tool (one line per narration line, the spec's voice and rate). usage: python tools/lines.py"""
import os, json
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = json.load(open(os.path.join(HERE, 'spec.json'), encoding='utf-8'))
out = [{k: v for k, v in {'id': L['id'], 'text': L['text'], 'say': L.get('say'), 'rate': L.get('rate'), 'asr': L.get('asr')}.items() if v} for L in S['lines']]
json.dump(out, open(os.path.join(HERE, 'lines.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"lines.json: {len(out)} lines · voice {S.get('voice', 'hi-IN-SwaraNeural')} {S.get('rate', '+6%')}")
