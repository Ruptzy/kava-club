# Kava Social Chess Club — design brief (handoff to Claude Design)

Redesign the homepage of **kavasocialchessclub.com** (currently live; source in github.com/Ruptzy/kava-club, assets in `img/`, `img/gallery/`, `img/logos/`, `media/`). Keep every fact, every locked decision and the voice below exactly. Improve composition, hierarchy and polish. The current page reads slightly "assembled"; the goal is a top-tier, cohesive, editorial page that still feels like *this* club.

---

## 1. Who this is

**Kava Social Chess Club**, Bradenton, Florida. A **social club first** — a place for adults to reconnect with a game they set down years ago, to meet people, to talk as much as play. Cooperative learning: stronger players teach instead of dominate. It is explicitly **not** a rating-obsessed or bragging culture; the standard is respect, sportsmanship, a handshake either way. Serious chess exists here for those who want it (league, lectures, simuls by FIDE Masters, nationally rated tournaments) but it is never the reason to come.

**Reader we're designing for:** a 30-something in Bradenton who played in school, hasn't touched a board in fifteen years, and is deciding whether to walk into a room of strangers on a Sunday night. Every section answers one of their questions, in the order they'd ask them.

**Director:** Harold Gonzalez — competitive player (2nd U1600 at the 2026 World Open; 1st U1400 Southern Class), math teacher, Data Science master's student, bilingual (English/Spanish), coaches privately.

## 2. Locked facts (must match Google, Facebook, Instagram, US Chess exactly)

- Name: **Kava Social Chess Club** · Est. **2021** · US Chess affiliate **A8712949**
- Venue & sponsor: **Kava Social Club**, 540 13th St W, Bradenton, FL 34205 (24-hour kava bar; alcohol-free) — thekavasocialclub.com
- Club phone (786) 250-8993 · kavasocialchess@gmail.com
- **Sundays 8PM–12AM, alternating weeks:** one Sunday is *social free play*, the next is *league night* (three-month seasons; 30 Aug 2026 was a league night, every 14 days)
- **Tuesdays 8PM–12AM:** study night (books, puzzles, grandmaster games, together)
- **Thursdays 7PM–11PM:** *Intermediate+ study night* at **Adobe Kava** (second venue; harder material, intermediate and up; address TBC)
- **21+** on club nights (venue rule). Rated tournaments **18+**. Private lessons **all ages**.
- **A purchase is required** at the venue — any item, doesn't have to be kava. Never say "free."
- Attendance: **scan a QR code at the door.** (Never "nobody signs in.")
- No membership, no dues. Sets and clocks provided. Clocks optional.
- The room: thatched-roof **back patio** (never "back room"), string lights, boards on every table.
- Bilingual: se habla español. A full Spanish page lives at `/es/`.
- Standings site (separate, keep linked, don't merge): **ladder.kavasocialchessclub.com** — brackets over 1400 / under 1400 / under 1000, Season 10, 2,800+ games recorded.
- Partners: Manasota Chess Center (Sarasota), Tampa Knights Chess Club, Orlando Regional Chess Alliance, Orlando Chess Club, Saint Petersburg Chess Club. Supporters: Chess67 (club/tournament/coaching software — our listing, sign-ups and lesson bookings run through it) and Chesslinebook (free opening notebook/trainer). Neither is ours.
- Lessons (Harold): Beginner **$40/hr**, USCF Tournament **$55/hr**; over the board in Bradenton & Sarasota, online elsewhere; English or Spanish; book on Chess67.

## 3. Brand system (taken from the club's logo and its existing league site — reuse verbatim)

- **Ground** `#0C0D0E` (near-black). Panels `#141618` / `#1B1E21` / `#23272B`. Rules `#24282C` / `#343A40`.
- **Text** cream `#FFF6E8`; secondary `#BDB5A9`; tertiary `#A39B8E` (never dimmer than this).
- **Accent** scarlet `#FE273A` (dim `#C41A2B`) — used sparingly: labels, one primary button per section, thin rules, the odd headline word. Never large fills.
- Semantic (calendar only): social green `#3BC79A`, study blue `#4F86E8`, Thursday amber `#F0883E`, special violet `#A78BFA`, lecture/simul cream.
- **Display type:** Archivo, variable width axis at **wdth 110–116, weight 900, uppercase**, tight leading. **Labels/meta/nav/buttons:** JetBrains Mono, uppercase, letter-spaced, **never below 12px**. Body: Archivo 400, 16.5–17px.
- **Texture:** the club's hall photo fixed behind the whole page under a `rgba(12,13,14,.93)` scrim (`background-attachment: fixed` on body). Cards semi-transparent so texture reads through.
- Buttons are pills (999px). Cards 4px radius, 1px rule border. Section header pattern everywhere: mono scarlet label + short scarlet rule → big uppercase headline → one-sentence dek, left-aligned, max ~44rem.
- **Logo:** red stylised knight in a black disc with cream "KAVA — SOCIAL CHESS CLUB" wordmark (`img/logo.png`, 1024px master on Harold's desktop). Favicon = the knight alone. The header shows the disc **large** (152px, shrinking to ~66px once scrolled).
- Photos: night-lit, purple/magenta, thatched roof — they carry the colour. Put dark scrims under any text on a photo. **Do not crop faces**; landscape photos shown whole unless they're deliberate full-bleed bands.

## 4. Voice

Plain, warm, short. First person plural. Lead with the room, not the rating. No "premier destination," no "your move to mastery," no defining ourselves against other clubs. Every paragraph one or two sentences. Specific beats clever. Spanish version reads natural (Latin-American), not translated.

Don'ts: "ignorable," "nobody has to care," "free," "back room," "nobody signs in," rating-forward framing, stock chess imagery, emoji, generic pillars-with-icons.

## 5. Page structure and approved copy (in order)

**Header** — big logo disc + wordmark "KAVA SOCIAL CHESS CLUB / Bradenton, Florida"; nav About · First night · Calendar · Lessons · Photos · Partners; Instagram/Facebook icon buttons; **ES** toggle; scarlet **Contact us** button. Under 1280px the nav collapses into a menu button (full-screen list). Nothing in the bar may ever wrap.

**Hero** — full-bleed photo of the packed patio (use `img/hero.jpg` — it is deliberately cropped; do not swap for the uncropped original). Heavy dark wash on the left so the headline sits on near-black.
- Label: BRADENTON, FLORIDA · EST. 2021
- H1: **Bradenton's social *chess club*** ("chess club" in scarlet)
- Dek: We meet at Kava Social Club, Sundays and Tuesdays until midnight. Every level is welcome — most of us hadn't played in years either.
- Buttons: Your first night (primary) · Get directions

**Facts bar** — four cells: WHEN Sun & Tue · 8PM–12AM | WHERE Kava Social Club, 540 13th St W | WHO 21+ · All levels · EN / ES | RATED US Chess affiliate

**About the club** — two stacked club-night photos beside the text.
- H2: A social club that happens to play chess
- Dek: Most people who walk in are adults picking the game back up after years away. No rating, no recent practice, and nobody here is going to test them.
- Three pillars: **Social first** — Friendships and working relationships have started at these tables. Plenty of people come as much to talk as to play. / **Every level, taught cooperatively** — Stronger players teach instead of dominate. A National Master plays here regularly and will sit down with a beginner. / **Serious when you want it** — Study nights, lectures, simuls from FIDE Masters, and nationally rated US Chess tournaments several times a year.

**Your first night** — wide banner photo of boards set up under the lights; then a short signed note beside a four-line list. (Explicitly NOT a numbered six-step grid — that read as an "AI list.")
- H2: You walk in. Four minutes later you're playing. — Dek: Nothing to sign up for and nothing to bring.
- Note: "Come in after eight, order something, and head to the back patio. Say it's your first night — someone will get you a game." — Harold Gonzalez, Club director
- Good to know: Sets and clocks are provided · Order one item — it doesn't have to be kava · No membership, no dues · Scan the QR at the door
- Two photo cards: **SUNDAY** 8PM–12AM · Alternating weeks — "One Sunday is social: free play, hang out, talk. The next is league night, part of a three-month season. Either way, just walk in." (tag: Start here) / **TUESDAY** 8PM–12AM · Study night — "The room works through books, puzzles and grandmaster games together. Stronger players explain rather than lecture."

**Calendar** ("What's on") — "Up next" row of the three nearest nights (date block: big day number, month in scarlet, weekday), then a full month grid with ‹ Today › and colour-coded chips per night type, a legend, and a side panel listing the selected day's events with an Add-to-Google-Calendar link. Recurring nights are computed (Sun alternating social/league from the 30 Aug 2026 anchor; Tue study; Thu Intermediate+ at Adobe Kava). **No public add-event control.** Colours: Social Sunday green, League scarlet-dim, Study blue, Thursday amber, Tournament scarlet, Lecture/simul cream, Special violet.

**Watch one** — the 68-second promo (`media/promo.mp4`, square, poster `img/promo-poster.jpg`) beside: label SIXTY-EIGHT SECONDS · H2 What a Sunday actually looks like · dek Shot by members on an ordinary night. No script, no actors. · three facts: Alcohol-free venue — kava, coffee, teas and soft drinks / Thatched-roof back patio, string lights, boards on every table / Open until midnight, twice a week, since 2021.

**Club league** — tinted band. H2: **Take it as seriously as you like.** Copy: "Every other Sunday is league night, and a season runs three months. Players sit in brackets — over 1400, under 1400, under 1000 — so you're matched with people around your own strength. Plenty of people care about the standings, and that's welcome. What you won't find is a culture built around ratings or bragging. The standard here is respect and sportsmanship, and a handshake either way." Stats: 10 three-month seasons · 2,800+ games recorded. Link: See this season's standings → ladder.kavasocialchessclub.com. Photo: the season's players behind the boards. Below: the four illustrated **bracket banners** (`img/bracket-*.png`, from the league site) shown large, two across, linking to the ladder.

**US Chess** — cream card with the US Chess Federation mark: "Official US Chess Federation affiliate · Affiliate ID A8712949 · Bradenton, Florida · View our listing on uschess.org" beside: label ACCREDITATION · H2 Our tournaments are nationally rated · "We're a registered US Chess affiliate. The rated events we run at Kava Social count toward your official US Chess rating, exactly like a tournament anywhere else in the country." · Rated tournaments several times a year, open to 18+ / No membership needed for club nights — only for rated events / Results submitted to US Chess after every event.

**Private lessons** — kept deliberately secondary. H2: Structured coaching, if you want it. Dek: "Club nights are free coaching and always will be. Private lessons are a separate, optional thing for people who want structured work between nights." Credentials list (director; 2nd U1600 2026 World Open; 1st U1400 Southern Class; math teacher, Data Science MSc student; over the board in Bradenton & Sarasota; online elsewhere · English & Spanish). Two photos of Harold (`img/coach.jpg`, `img/coach2.jpg`) side by side, uncropped. Two price cards: **Beginner $40/hr** — "For new and casual players. How the pieces move, the rules that trip people up, basic tactics, opening principles, simple endgames. Practice games with feedback." / **USCF Tournament $55/hr** — "For rated and aspiring tournament players. Game review, classical training games, an opening repertoire that suits you, a study plan, and the psychology of time pressure." Note: **All ages.** Club nights are 21+ because of the venue. Lessons are not. Text link: Book a lesson on Chess67.

**Photos** — H2: Five years of nights, tournaments and road trips. A **justified gallery** (every row one height, widths follow aspect, 4px gaps, no rounded corners, everything shown — reference: iiipoints.com/past-highlights/2025-gallery). Click opens a near-black viewer: small ✕ top-centre, "7 / 44" counter bottom-right, arrows/keys/swipe. 44 photos in `img/gallery/01.jpg…`; lead with 01 (tournament group), then 02 (trophy), then 03 (black-and-white long table).

**Our home** — H2: Proudly hosted by Kava Social Club. Card: storefront photo (`img/venue.jpg`, corner building, fills the card) | tiki badge logo (`img/logos/kava-social-club.png`) · PROUD SPONSOR SINCE 2021 · **KAVA SOCIAL CLUB** · "Downtown Bradenton's 24-hour kava bar. Traditional noble kava, specialty K-Teas and slow-steeped cold brew, in a room built for unwinding and talking to people — calm, social, and alcohol-free. Day or night, rain or shine, good vibes never close." · "They have given us their thatched-roof back patio every Sunday and Tuesday since 2021. There is no chess club without them." · 540 13th St W, Bradenton FL · Open 24/7 · Kava · K-Teas · Cold brew · Soft drinks · Second location opening in Pinellas Park · button Visit Kava Social Club.
Then **Clubs we play with** (Members travel to tournaments around the state): five logo tiles with name + city (`img/logos/manasota.png, tampa.png, orca.png, orlando.png, stpete.png`). Then **Platforms that support us** (People who have helped the club): Chess67 (`img/logos/chess67.svg`) — "Club software — registration, pairings and payments. Our listing, event sign-ups and lesson bookings run through it." / Chesslinebook (`img/logos/chesslinebook.png`) — "A free opening notebook and trainer. Import your games, drill your lines, see where they go wrong." Logos large.

**Contact** — tinted band. H2: Ask us anything. Then come Sunday. Dek: Never played, or haven't since school? Ask. Somebody answers, usually the same day. Four one-tap cards: Email kavasocialchess@gmail.com · Text (786) 250-8993 · Instagram @kavasocialchessclub · Facebook Kava Social Chess Club. Then a Google review row (stars, "Rated on Google", "Honest reviews help the next person decide to walk in", Leave a review / Read reviews) and one quote card: "Had a great time playing a Kava chess club tournament here." — Google review · Kava Social Club.

**Footer** — four columns: club + address + hours + "21+ · Se habla español" | Contact (email, phone, Directions) | Club (Season standings, US Chess affiliate, Chess67 listing, Kava Social Club) | Follow (Instagram, Facebook, Yelp). Legal line: © Kava Social Chess Club · Established 2021 · US Chess affiliate A8712949.

## 6. Constraints

- Phone-first; verify at 375px and 320px — no horizontal overflow, no clipped text, tap targets ≥40px. The header must never wrap at any width.
- All small type ≥12px; tertiary ink no dimmer than `#A39B8E`.
- Keep the page fast: hero preloaded, everything else lazy; video preload=metadata.
- Keep `<h1>` = "Bradenton's social chess club"; keep the section IDs (about, night, events, watch, standings, uschess, lessons, gallery, partners, contact) so links and the Spanish page keep working.
- Spanish page `/es/` mirrors structure 1:1 with its own copy (already translated; Harold reviewing).
- Don't reintroduce: numbered step grids, filter pills on the gallery, an "add event" control, any cropping of people's faces.

## 7. Still placeholder (leave slots, don't invent)

Google review link (real place ID pending) · Yelp URL · next rated tournament (date, fee, time control) · contact form (Web3Forms key pending; currently four contact cards instead) · Adobe Kava street address · whether Thursday becomes a headline third night site-wide.

## 8. References

- The club's own league site (same brand, expanded Archivo + JetBrains Mono, bracket art): ladder.kavasocialchessclub.com
- Gallery treatment: iiipoints.com/past-highlights/2025-gallery
- What NOT to be: orlandochessclub.org (generic "premier destination" club template)
