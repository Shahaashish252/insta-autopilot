"""Hindi hook score (the ig-reel hookscore checks, rebuilt for Devanagari): 0-100 from five text-only checks.
It catches weak hooks (preambles, nothing concrete, too long to say); it does not predict views.
  python -m maker.hookscore "रात को फ़ोन लेकर सोना बंद करो।" ["another hook" ...]"""
import re, sys

PREAMBLE = ['दोस्तों', 'दोस्तो', 'नमस्ते', 'नमस्कार', 'आज हम', 'आज मैं', 'इस वीडियो', 'इस रील', 'क्या आप जानते', 'एक बात बताऊँ',
            'एक बात बताऊं', 'सुनिए', 'आइए', 'चलिए']
NUM = re.compile(r'[0-9०-९]|\b(एक|दो|तीन|चार|पाँच|पांच|छह|सात|आठ|नौ|दस|सौ|हज़ार|हजार|लाख|करोड़|आधा|पहली|पहला|हर)\b')
CONCRETE = ['फ़ोन', 'फोन', 'रात', 'सुबह', 'घंटे', 'मिनट', 'साल', 'दिन', 'पैसा', 'पैसे', 'एग्ज़ाम', 'मार्क्स', 'नींद', 'माँ', 'पापा',
            'दोस्त', 'नौकरी', 'शब्द', 'मात्रा', 'बिंदी', 'बिंदु', 'अक्षर', "'", '‘', '"']
STAKE = ['बंद करो', 'मत', 'बर्बाद', 'खो', 'गलती', 'ग़लती', 'डर', 'पछता', 'कभी नहीं', 'कोई नहीं', 'सच', 'राज़', 'राज', 'छुपा', 'हार',
         'टूट', 'जल', 'खत्म', 'ख़त्म', 'बदल गया', 'बदल जाता', 'इलाज', 'कीमत', 'वजह', 'क्यों', 'कितने']
YOU = re.compile(r'(तुम|तुम्हें|तुम्हारा|तुम्हारी|तुम्हारे|तू|तेरा|तेरी|तुझे|आप|आपका|आपकी|आपको|जो\s)')


def score(text):
    t = ' '.join(text.split()); words = t.split(); n = len(words)
    secs = len(t.replace(' ', '')) / 13.0                           # Swara at +8% says ~13 Devanagari characters a second
    length = 100 if 4 <= n <= 9 and secs <= 2.6 else max(0, 100 - 25 * max(abs(n - 6.5) - 2.5, 0) - 60 * max(secs - 2.6, 0))
    concrete = 100 if NUM.search(t) or any(c in t for c in CONCRETE) else 30
    stake = 100 if any(s in t for s in STAKE) else 35
    head = ' '.join(words[:3])
    front = 100 if (any(s in head for s in STAKE) or NUM.search(head) or any(c in head for c in CONCRETE) or YOU.search(head)) else 40
    you = 100 if YOU.search(t) or t.rstrip('।.!').endswith(('करो', 'मत करो', 'छोड़ो', 'सीखो', 'सुनो', 'देखो', '?')) else 45
    parts = {'length': round(length), 'concrete': concrete, 'stake': stake, 'front': front, 'you': you}
    total = round(0.25 * length + 0.2 * concrete + 0.2 * stake + 0.2 * front + 0.15 * you)
    if any(p in t for p in PREAMBLE): total, parts['preamble'] = min(total, 30), True
    return total, parts


if __name__ == '__main__':
    for h in sys.argv[1:]:
        s, p = score(h); print(f'{s:3d}  {h}   {p}')
