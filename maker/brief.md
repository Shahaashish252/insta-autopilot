# Brief: a Shabd Sketch (शब्द-चित्र) reel for @anek.arthi

You write the spec for one vertical Instagram reel. The renderer turns it into the video by itself: a calm Hindi
female voice says every line; a heavy Hindi word sits on warm paper; its one red part (a letter, a matra or a bindu)
lifts off, flies away or drops in, and the word becomes a second real word that carries the lesson; a pencil writes the
short version of some lines; a sketched person sits dejected on a step and stands up when the lesson lands.
Audience: young Hindi speakers in India (students, first jobs), watching on a phone, often muted at first.

## The word change (the most important choice)

- Both words are **real, common Hindi words** a 16-year-old knows, and the change is **one visible piece**: remove,
  add or swap a single matra, bindu/chandrabindu, half-letter or letter. Examples of the shape (all already used):
  कल → काल (add ा), सपना → अपना (स → अ), हार → हर (remove ा), चिंता → चिता (remove ं), सब्र → सब (remove ्र).
- The pair must carry a **true, useful life lesson** that feels like an "aha": the second word comments on the first.
  Directions that work (check the used list first): मन → मान, धन → धुन, कर्म → कम. Never force a pun: if the lesson
  needs explaining, pick another pair. Prefer lessons that touch the heart: family (माँ, पापा, गाँव, घर), standing by people in pain,
  relationships, debt and promises, patience, excuses, self-respect; productivity themes (phone habits, exams) less often.
  The biggest reel in our niche (33× its account's median) was exactly our format: पर + ा = पार ("इसमें बस एक मात्रा
  जोड़ो और पार हो जाओ"): a tiny change with a big promise, said in the first line.
- `from` and `to` are `[before, part, after]`: they share `before` and `after` exactly; only the middle `part`
  changes, and one of the two parts may be empty. Cut by Unicode, as it is typed: सब्र = ["सब", "्र", ""] → ["सब", "", ""];
  कल → काल = ["क", "", "ल"] → ["क", "ा", "ल"]; सपना → अपना = ["", "स", "पना"] → ["", "अ", "पना"];
  चिंता → चिता = ["चि", "ं", "ता"] → ["चि", "", "ता"].

## The script (`lines`)

- 10 to 13 lines, ids N1, N2, … in order; each `text` is spoken, short, plain conversational Hindi (Devanagari, the way
  a friend talks; Urdu-origin everyday words are fine). Under 60 characters per line. Total 25 to 40 seconds.
- **N1 is the hook**, said in the first second: a Negative Command ("…बंद करो"), a surprising claim, or a question that
  stings; with a number if there is one. N2 makes the promise ("जवाब इस एक शब्द में है").
- Then: the first word said alone (N3, may have `"rate": "-6%"` to slow it), the problem in a concrete everyday picture
  (two lines), the `"cue": "lift"` line (the red part is noticed: "पर इस शब्द की एक छोटी-सी मात्रा…"), the `"cue": "swap"`
  line (the change happens: "ये बिंदु हटाओ।"), then a line with `"clear": true` that says "X, बन जाता है Y", then the
  `"cue": "resolve"` line (the lesson, the person stands up), one more line that lands it, **one ask** (share with a
  specific person: "जिसे आज ये सुनना था, उसे भेज दो।" — shares are what this channel gets most), and **a loop line**
  that repeats the hook's words so the replay feels seamless.
- `write`: the short on-screen version, on most lines (muted viewers), at most 22 characters, never on N1–N3 (the hook
  card covers those) and never on the lift or swap lines (the camera is on the red part then). Use "…" freely; no full stops needed.
- Never copy any creator's words, never quote a living person, no religion-baiting, no politics, no medical or money
  promises, nothing about death or self-harm beyond the gentle proverb level (चिंता चिता समान is the limit).

## Other keys

- `hook`: `{"text": "on-screen hook, max 6 words, a number if possible", "until": "N2"}`.
- `look`: "man" or "woman" (the sketched person; alternate between reels).
- `voice`: "hi-IN-SwaraNeural"; `rate`: "+8%". `scene`: "default".

## The caption

Hindi (Devanagari). Line 1 (≤ 120 characters, shows before "more"): the ask or a question that invites a one-word
comment, not a repeat of the hook. Then 2–3 short paragraphs (the change, the lesson, one line of encouragement), one
blank line between each. Last line: exactly 3 hashtags, e.g. #शब्दोंकाखेल #हिंदीमोटिवेशन plus one about the word. No links,
no emoji at the start, at most 2 emoji in all.

## Before you answer, check yourself

Is each word real and common? Does the change show one visible piece? Does the lesson hold without a stretch? Does N1
stop a scroll in one second? Is there exactly one ask, and does the last line echo the hook?
