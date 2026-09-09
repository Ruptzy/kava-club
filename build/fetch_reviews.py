"""Pull the club's Google reviews into /reviews.json (run daily by .github/workflows/reviews.yml).

Environment:
  GOOGLE_PLACES_KEY  - required. An API key with "Places API (New)" enabled.
  GOOGLE_PLACE_ID    - optional. If missing, the CLUB is looked up by name.

Safety rule: the club shares an address with its venue (Kava Social Club), whose listing
has hundreds of reviews about the kava bar. Those are not the chess club's reviews, so a
match is only accepted when the listing name mentions chess. Otherwise nothing is written
and the candidates are printed for a human to look at.
"""
import json, os, sys, urllib.request, urllib.error

KEY = os.environ.get('GOOGLE_PLACES_KEY', '').strip()
# the club's own listing, confirmed 2026-09-09. Pinning it means one API call a day
# (a Place Details lookup) instead of four - no text search, nothing to pay for.
DEFAULT_PLACE = 'ChIJ-bv_E6gXw4gREBFXmc5jeEY'
PLACE = os.environ.get('GOOGLE_PLACE_ID', '').strip() or DEFAULT_PLACE
QUERIES = ['Kava Social Chess Club Bradenton FL',
           'Kava Social Chess Club',
           'chess club Bradenton FL 34205']
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reviews.json')

if not KEY:
    sys.exit('GOOGLE_PLACES_KEY is not set (add it as a GitHub Actions secret)')


def call(url, fields, body=None):
    headers = {'X-Goog-Api-Key': KEY, 'X-Goog-FieldMask': fields}
    data = None
    if body is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit('Google refused the request (%s): %s' % (e.code, e.read().decode('utf-8', 'replace')[:500]))


def find_place():
    seen, cands = set(), []
    for q in QUERIES:
        res = call('https://places.googleapis.com/v1/places:searchText',
                   'places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount',
                   {'textQuery': q, 'maxResultCount': 10, 'languageCode': 'en'})
        for h in res.get('places', []):
            if h.get('id') and h['id'] not in seen:
                seen.add(h['id'])
                cands.append(h)
    print('Google listings found:')
    for h in cands:
        print('  %s  %s - %s (%s stars, %s ratings)' % (
            h['id'], (h.get('displayName') or {}).get('text', '?'),
            h.get('formattedAddress', '?'), h.get('rating', '-'), h.get('userRatingCount', 0)))
    for h in cands:
        if 'chess' in (h.get('displayName') or {}).get('text', '').lower():
            return h['id']
    print('\nNo listing with "chess" in its name came back from the Places API.')
    print('The venue\'s listing is NOT a substitute - its reviews are about the kava bar.')
    print('Nothing written. Set GOOGLE_PLACE_ID to the club\'s own Place ID to override.')
    return None


place_id = PLACE or find_place()
if not place_id:
    sys.exit(0)   # not an error: leave the page showing whatever it already has
print('Using Place ID: ' + place_id)

p = call('https://places.googleapis.com/v1/places/%s?languageCode=en' % place_id,
         'displayName,rating,userRatingCount,googleMapsUri,reviews')
name = (p.get('displayName') or {}).get('text', '')
if not PLACE and 'chess' not in name.lower():
    sys.exit('Refusing: Place ID %s is "%s", not the chess club.' % (place_id, name))

reviews = []
for rv in p.get('reviews', []):
    text = (rv.get('text') or {}).get('text', '').strip()
    if not text:
        continue
    reviews.append({
        'author': (rv.get('authorAttribution') or {}).get('displayName', 'Google user'),
        'rating': rv.get('rating', 5),
        'text': text,
        'time': rv.get('publishTime', '')[:10],
        'when': rv.get('relativePublishTimeDescription', ''),
    })
reviews.sort(key=lambda x: x['time'], reverse=True)

doc = {'name': name, 'rating': p.get('rating'), 'count': p.get('userRatingCount', 0),
       'url': p.get('googleMapsUri', ''), 'placeId': place_id, 'reviews': reviews}
old = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
new = json.dumps(doc, ensure_ascii=False, indent=1) + '\n'
if new != old:
    open(OUT, 'w', encoding='utf-8').write(new)
    print('reviews.json updated: %s - %s stars, %s ratings, %d reviews with text'
          % (name, doc['rating'], doc['count'], len(reviews)))
else:
    print('reviews.json unchanged')
