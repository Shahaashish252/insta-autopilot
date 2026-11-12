"""Carousels (swipe posts) from the channel's best word pairs, in the reels' look: warm paper, black ink, one red part.
  python carousels/slides.py            → carousels/<slug>/slides.html (+ caption.txt); render.mjs turns them into 01.jpg…
Each carousel: cover · stake · the change · two lesson slides · recap (the screenshot slide) · one ask."""
import html, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(os.path.dirname(HERE), 'studio', 'films', '_template', 'fonts').replace('\\', '/')
HANDLE, SERIES = '@anek.arthi', 'एक अक्षर का खेल'

# a word is [before, red part, after]; the red part is the one piece that changes
CAROUSELS = [
    {'slug': 'roop-rooh', 'from': ['रू', 'प', ''], 'to': ['रू', 'ह', ''],
     'hook': 'तुम शक्ल से बढ़कर हो', 'promise': 'आईना तुम्हें पूरा नहीं दिखाता।',
     'stake': 'लोग हर दिन तुम्हें शक्ल से नापते हैं। धीरे-धीरे तुम भी खुद को वैसे ही नापने लगते हो।',
     'change': ('प हटाओ, ह लगाओ', 'रूप का एक अक्षर बदलता है, और वो बन जाता है रूह।'),
     'points': [('रूप: जो दिखता है', 'उम्र के साथ बदलता है, फ़िल्टर से छुपता है, लोगों की राय से तय होता है।'),
                ('रूह: जो तुम हो', 'तुम्हारी नीयत, तुम्हारी मेहनत, तुम्हारा दिल। ये किसी फ़िल्टर से नहीं बदलते।')],
     'recap': ('रूप दिखता है, रूह टिकती है', ['रूप को लोग देखते हैं', 'रूह को लोग याद रखते हैं', 'रूप बदल जाता है',
                                          'रूह साथ रहती है']),
     'ask': 'जो खुद को सिर्फ़ शक्ल से नापता है, उसे ये भेजो।',
     'caption': ['जो खुद को सिर्फ़ शक्ल से नापता है, ये पोस्ट उसे भेजो।',
                 'रूप में बस एक अक्षर बदलो, प की जगह ह, और वो बन जाता है रूह।',
                 'रूप वो है जो लोग देखते हैं। रूह वो है जो लोग याद रखते हैं। आज खुद को उस पैमाने से नापो जो सच में टिकता है।',
                 '#शब्दोंकाखेल #हिंदीमोटिवेशन #रूपऔररूह']},
    {'slug': 'haar-har', 'from': ['ह', 'ा', 'र'], 'to': ['ह', '', 'र'],
     'hook': 'आज हार गए? ये पढ़ो', 'promise': 'एक छोटी-सी मात्रा का फ़र्क़।',
     'stake': 'हार के बाद सबसे भारी हार नहीं होती। वो आवाज़ होती है जो कहती है: बस, अब नहीं।',
     'change': ('मात्रा हटाओ', 'हार में से आ की छोटी-सी मात्रा हटाओ, तो बचता है हर।'),
     'points': [('हर हार में एक सबक़', 'जहाँ गिरे, वहीं पता चला कि कमी कहाँ थी। ये बात सिर्फ़ गिरने वाले जानते हैं।'),
                ('हर बार उठो', 'गिरना तय नहीं करता कि तुम कौन हो। उठना करता है। बस एक बार और।')],
     'recap': ('हार से हर तक', ['हार एक दिन है, ज़िंदगी नहीं', 'हर हार में एक सबक़', 'हर बार गिरो, हर बार उठो',
                              'मात्रा हटाओ, हिम्मत बचती है']),
     'ask': 'आज हार गए हो तो इसे सेव कर लो। अगली बार गिरो, तो फिर पढ़ना।',
     'caption': ['आज हार गए हो तो इसे सेव कर लो। अगली बार गिरो, तो फिर से पढ़ना।',
                 'हार से बस एक मात्रा हटाओ, और बचता है हर।',
                 'हर हार में एक सबक़ छुपा है। गिरना तय नहीं करता कि तुम कौन हो, उठना करता है।',
                 '#शब्दोंकाखेल #हिंदीमोटिवेशन #हारसेहर']},
    {'slug': 'man-maan', 'from': ['म', '', 'न'], 'to': ['म', 'ा', 'न'],
     'hook': 'एक मात्रा से मान बनो', 'promise': 'अपने मन की सुनना कमज़ोरी नहीं है।',
     'stake': 'सबको खुश रखते-रखते, तुमने आख़िरी बार अपने मन की कब सुनी थी?',
     'change': ('एक मात्रा जोड़ो', 'मन के म पर आ की एक मात्रा लगाओ, और वो बन जाता है मान।'),
     'points': [('हर बार चुप मत रहो', 'हर बार "कोई बात नहीं" कहना, धीरे-धीरे तुम्हारी अपनी बात को छोटा कर देता है।'),
                ('मान अंदर से आता है', 'जो अपने मन को इज़्ज़त देता है, उसे बाहर मान माँगना नहीं पड़ता।')],
     'recap': ('मन से मान तक', ['अपने मन की सुनो', 'ज़रूरत हो तो ना कहो', 'खुद को इज़्ज़त दो', 'मान अपने आप आएगा']),
     'ask': 'जो हमेशा सबके लिए चुप रह जाता है, उसे ये भेजो।',
     'caption': ['जो हमेशा सबके लिए चुप रह जाता है, ये पोस्ट उसे भेजो।',
                 'मन में बस एक मात्रा जोड़ो, और वो बन जाता है मान।',
                 'अपने मन की सुनना कमज़ोरी नहीं है। जो अपने मन को इज़्ज़त देता है, उसे बाहर मान माँगना नहीं पड़ता।',
                 '#शब्दोंकाखेल #हिंदीमोटिवेशन #मनऔरमान']},
]

E = html.escape


def word(w, cls=''):
    b, part, a = w
    return f'<span class="w {cls}">{E(b)}<span class="red">{E(part)}</span>{E(a)}</span>'


def pair(c, cls=''):
    # the new word is red (a lone matra can't be coloured on its own: browsers shape it with its letter)
    return f'<div class="pair {cls}"><span class="w">{E("".join(c["from"]))}</span><span class="arrow">→</span><span class="w red">{E("".join(c["to"]))}</span></div>'


CSS = '''
@font-face { font-family: Yatra; src: url("file:///%(f)s/YatraOne-Regular.ttf"); }
@font-face { font-family: Kalam; src: url("file:///%(f)s/Kalam-Bold.ttf"); }
:root { --paper:#f2e6ce; --edge:#e3d7c1; --ink:#1e1a17; --soft:#484441; --red:#c1392b; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #888; }
section { width: 1080px; height: 1350px; position: relative; overflow: hidden; font-family: Kalam, sans-serif; color: var(--ink);
  background: radial-gradient(ellipse at 50% 45%, var(--paper) 0%, var(--paper) 45%, var(--edge) 100%);
  display: flex; flex-direction: column; justify-content: center; padding: 150px 130px; gap: 40px; }
section::after { content: ""; position: absolute; left: 130px; right: 130px; bottom: 175px; border-top: 3px solid rgba(30,26,23,.18); }
.top, .bot { position: absolute; left: 70px; right: 70px; display: flex; justify-content: space-between; font-size: 34px; color: var(--soft); }
.top { top: 60px; } .bot { bottom: 60px; }
.num { font-family: Yatra; }
.pair { font-family: Yatra; display: flex; align-items: baseline; gap: 34px; line-height: 1.25; }
.pair .arrow { font-family: Kalam; color: var(--soft); font-size: .5em; }
.red { color: var(--red); }
.cover .pair { font-size: 220px; justify-content: center; }
.cover h1 { font-family: Kalam; font-size: 86px; text-align: center; line-height: 1.25; }
.cover p { font-size: 50px; text-align: center; color: var(--soft); line-height: 1.4; }
.small-pair { font-size: 90px; }
h2 { font-family: Yatra; font-weight: normal; font-size: 92px; line-height: 1.25; }
.body { font-size: 58px; line-height: 1.5; color: var(--ink); }
.stake .body { font-size: 70px; line-height: 1.45; }
.change .pair { font-size: 190px; }
ul { list-style: none; display: flex; flex-direction: column; gap: 30px; }
li { font-size: 60px; line-height: 1.3; padding-left: 70px; position: relative; }
li::before { content: "✓"; position: absolute; left: 0; color: var(--red); font-family: Kalam; }
.cta .ask { font-size: 76px; line-height: 1.4; }
.cta .ask u { text-decoration-color: var(--red); text-decoration-thickness: 6px; text-underline-offset: 14px; }
.cta .follow { font-family: Yatra; font-size: 56px; color: var(--red); }
.cta .handle { font-size: 52px; color: var(--soft); }
'''


def build(c):
    slides = []
    n = 7
    frame = lambda i, inner, cls='': (f'<section class="{cls}"><div class="top"><span>{SERIES}</span><span class="num">{i}/{n}</span></div>'
                                      f'{inner}<div class="bot"><span>{HANDLE}</span><span>{"स्वाइप करो →" if i < n else ""}</span></div></section>')
    slides.append(frame(1, f'{pair(c)}<h1>{E(c["hook"])}</h1><p>{E(c["promise"])}</p>', 'cover'))
    slides.append(frame(2, f'<div class="body">{E(c["stake"])}</div>', 'stake'))
    slides.append(frame(3, f'{pair(c)}<h2>{E(c["change"][0])}</h2><div class="body">{E(c["change"][1])}</div>', 'change'))
    for i, (h, b) in enumerate(c['points'], 4):
        slides.append(frame(i, f'{pair(c, "small-pair")}<h2>{E(h)}</h2><div class="body">{E(b)}</div>'))
    h, items = c['recap']
    slides.append(frame(6, f'<h2>{E(h)}</h2><ul>{"".join(f"<li>{E(x)}</li>" for x in items)}</ul>', 'recap'))
    slides.append(frame(7, f'{pair(c, "small-pair")}<div class="ask"><u>{E(c["ask"])}</u></div>'
                           f'<div class="follow">हर शाम 7 बजे, एक नया शब्द।</div><div class="handle">फ़ॉलो करो {HANDLE}</div>', 'cta'))
    return ('<!doctype html><html lang="hi"><head><meta charset="utf-8"><style>' + CSS.replace('%(f)s', FONTS) +
            '</style></head><body>' + ''.join(slides) + '</body></html>')


if __name__ == '__main__':
    for c in CAROUSELS:
        d = os.path.join(HERE, c['slug']); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'slides.html'), 'w', encoding='utf-8').write(build(c))
        open(os.path.join(d, 'caption.txt'), 'w', encoding='utf-8').write('\n\n'.join(c['caption']) + '\n')
        json.dump({'slug': c['slug'], 'title': f"{''.join(c['from'])} → {''.join(c['to'])}", 'slides': 7,
                   'alt': f"{''.join(c['from'])} से {''.join(c['to'])}: {c['hook']}. {c['promise']}"},
                  open(os.path.join(d, 'carousel.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(c['slug'])
