"""Caption check (the ig-caption + ig-human rules, for Hindi captions): returns a list of problems, empty = ready.
  python -m maker.captionlint caption.txt "चिंता" "चिता\""""
import re, sys

ASKS = {'comment': r'कमेंट|कॉमेंट|लिखो|लिखें|बताओ|बताइए', 'share': r'भेज|शेयर|टैग', 'save': r'सेव', 'follow': r'फ़ॉलो|फॉलो'}
DEAD_TAGS = {'#viral', '#fyp', '#foryou', '#explore', '#explorepage', '#trending', '#reels', '#instagood'}
SLOP = ['आइए जानते', 'यकीन मानिए', 'यक़ीन मानिए', 'जादुई', 'अद्भुत', 'इस वीडियो में', 'इस रील में', 'दोस्तों']
EMOJI = re.compile('[\U0001F300-\U0001FAFF☀-➿]')
INVISIBLE = re.compile('[​‌⁠﻿]')              # ZWJ (U+200D) is left alone: Devanagari uses it


def lint(cap, words=()):
    errs = []
    lines = [l for l in cap.strip().split('\n')]
    first = lines[0].strip() if lines else ''
    if len(first) > 125: errs.append(f'caption line 1 is {len(first)} characters; keep the ask or question inside the first 125')
    if first.startswith('#') or EMOJI.match(first): errs.append('caption line 1 must not start with a hashtag or an emoji')
    tags = re.findall(r'#\S+', cap)
    if not 3 <= len(tags) <= 5: errs.append(f'caption needs 3 hashtags (has {len(tags)})')
    if DEAD_TAGS & {t.lower() for t in tags}: errs.append('no generic hashtags like #viral #fyp #explore #trending')
    body = re.sub(r'#\S+', '', cap)
    asks = [k for k, rx in ASKS.items() if re.search(rx, body)]
    if not asks: errs.append('caption needs one ask (share with someone, or a one-word comment)')
    if len(asks) > 1: errs.append(f'caption has {len(asks)} asks ({", ".join(asks)}); keep exactly one')
    for w in words:
        if w and w not in body: errs.append(f'use the word "{w}" in a caption sentence (Instagram search reads captions)')
    if re.search(r'https?://|www\.', cap): errs.append('caption: no links')
    if len(EMOJI.findall(cap)) > 2: errs.append('caption: at most 2 emoji')
    if '—' in cap or '–' in cap: errs.append('caption: no em/en dashes (reads machine-written); use a comma or a full stop')
    if INVISIBLE.search(cap): errs.append('caption: remove invisible characters')
    for s in SLOP:
        if s in cap: errs.append(f'caption: "{s}" sounds machine-written; say it plainly')
    if len(cap) > 1500: errs.append('caption: at most 1500 characters')
    return errs


if __name__ == '__main__':
    print('\n'.join(lint(open(sys.argv[1], encoding='utf-8').read(), sys.argv[2:])) or 'READY')
