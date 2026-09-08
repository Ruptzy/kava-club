# Kava Social Chess Club — website

Public site for the club, served by GitHub Pages at **https://kavasocialchessclub.com**.
The league/standings site is a separate repo (`kava-ladder`) at **ladder.kavasocialchessclub.com** — never merge them; the ladder is republished from Harold's phone.

## What this is
- Hand-written static HTML/CSS/JS. No framework, no build step for the page itself.
- `index.html` is generated from a template by `build_site.py` (kept in Claude's scratchpad for now — to be moved into `build/` here). Assets live in `img/`, `img/gallery/`, `img/logos/`, `media/`.
- Brand tokens are the ladder's: `--void #0C0D0E`, `--cream #FFF6E8`, `--scarlet #FE273A`; display = Archivo (variable width, `wdth` 110–116, weight 900, uppercase); labels = JetBrains Mono; hall photo behind a `.93` scrim via `background-attachment: fixed` on `body`.

## Locked facts (must match Google Business Profile, Facebook, Instagram, US Chess exactly)
- Kava Social Chess Club · 540 13th St W, Bradenton, FL 34205 · (786) 250-8993 · kavasocialchess@gmail.com
- Meets at **Kava Social Club** (the venue and proud sponsor; thekavasocialclub.com).
- **Sundays alternate**: social free play one week, league night the next (three-month seasons; 30 Aug 2026 was a league night, every 14 days). **Tuesdays** study night. Both 8PM–12AM.
- **Thursdays 7–11PM: Intermediate+ study night at Adobe Kava** (second venue; address still needed; site-wide "three nights" wording not yet applied — Harold to confirm).
- Club nights are **21+** (venue rule). Rated tournaments **18+**. Lessons **all ages**.
- A purchase is required at the venue (any item — not just kava). Never say "free".
- US Chess affiliate **A8712949**. Established 2021 (first recorded night in the data is 25 Sep 2022 — not the founding date).
- Se habla español — Harold and members are bilingual; a `/es/` section is planned.

## Voice
Social first. The league is one of two kinds of Sunday, never the reason to come. Never call the standings "ignorable" — say caring is welcome, bragging isn't, respect and sportsmanship are the standard. Lead with the room, not the rating.

## Calendar
Recurring nights are computed in the page (`recurring()` in the calendar script). Booked events (tournaments, lectures, simuls) come from a data source: on the Claude artifact version that is the `db` capability; on this public site there is no source yet — the planned admin console will write `events.json` here. The Google-review button, Yelp link and the next tournament date are still placeholders pending Harold.

## Roadmap
Multi-page build (`/beginners/`, `/lessons/`, `/events/`, `/partners/`, `/gallery/`, `/faq/`, `/es/`, `/nights/` recaps), Web3Forms contact form, admin console, weekly recap generator from ladder data.
