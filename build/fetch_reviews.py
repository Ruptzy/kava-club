"""Pull real Google reviews into /reviews.json (run daily by .github/workflows/reviews.yml).

Environment:
  GOOGLE_PLACES_KEY  - required. An API key with "Places API (New)" enabled.
  GOOGLE_PLACE_ID    - optional override for the club's listing.

Two sources, both real and both named:
  1. The club's own listing - anything written there.
  2. The venue's listing (Kava Social Club) - only reviews that actually mention chess,
     shown with the reviewer's name and marked as left on the venue's page.
The venue's rating and review count are never borrowed; only the club's are shown.
Two Place Details calls a day, far inside Google's free allowance.
"""
import json, os, re, sys, urllib.request, urllib.error

KEY = os.environ.get('GOOGLE_PLACES_KEY', '').strip()
CLUB = os.environ.get('GOOGLE_PLACE_ID', '').strip() or 'ChIJ-bv_E6gXw4gREBFXmc5jeEY'
VENUE = 'ChIJJ_JIjM8Xw4gRq5iQ1IqexXM'   # Kava Social Club, the room the club plays in
CHESS = re.compile(r'\bchess\b', re.I)
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reviews.json')

if not KEY:
    sys.exit('GOOGLE_PLACES_KEY is not set (add it as a GitHub Actions secret)')


def details(place_id):
    req = urllib.request.Request(
        'https://places.googleapis.com/v1/places/%s?languageCode=en' % place_id,
        headers={'X-Goog-Api-Key': KEY,
                 'X-Goog-FieldMask': 'displayName,rating,userRatingCount,googleMapsUri,reviews'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit('Google refused the request (%s): %s' % (e.code, e.read().decode('utf-8', 'replace')[:500]))


def parse(p, via=None, only_chess=False):
    out = []
    raw = p.get('reviews', [])
    print('   Google returned %d review objects' % len(raw))
    for rv in raw:
        text = ((rv.get('text') or {}).get('text')
                or (rv.get('originalText') or {}).get('text') or '').strip()
        if not text or (only_chess and not CHESS.search(text)):
            continue
        item = {
            'author': (rv.get('authorAttribution') or {}).get('displayName', 'Google user'),
            'rating': rv.get('rating', 5),
            'text': text,
            'time': rv.get('publishTime', '')[:10],
            'when': rv.get('relativePublishTimeDescription', ''),
        }
        if via:
            item['via'] = via
        out.append(item)
    return out


club = details(CLUB)
name = (club.get('displayName') or {}).get('text', '')
if 'chess' not in name.lower():
    sys.exit('Refusing: %s is "%s", not the chess club.' % (CLUB, name))
mine = parse(club)
print('%s: %s stars, %s ratings, %d written' % (name, club.get('rating'), club.get('userRatingCount', 0), len(mine)))

venue = details(VENUE)
vname = (venue.get('displayName') or {}).get('text', 'the venue')
theirs = parse(venue, via=vname, only_chess=True)
print('%s: %d of the reviews Google returned mention chess' % (vname, len(theirs)))

mine.sort(key=lambda x: x['time'], reverse=True)
theirs.sort(key=lambda x: x['time'], reverse=True)
reviews = mine + theirs          # the club's own always lead

doc = {'name': name, 'rating': club.get('rating'), 'count': club.get('userRatingCount', 0),
       'url': club.get('googleMapsUri', ''), 'placeId': CLUB, 'reviews': reviews}
old = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
new = json.dumps(doc, ensure_ascii=False, indent=1) + '\n'
if new != old:
    open(OUT, 'w', encoding='utf-8').write(new)
    print('reviews.json updated: %d reviews to show' % len(reviews))
else:
    print('reviews.json unchanged')
