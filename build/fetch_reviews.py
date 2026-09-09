"""Pull the club's Google reviews into /reviews.json (run daily by .github/workflows/reviews.yml).

Environment:
  GOOGLE_PLACES_KEY  - required. An API key with "Places API (New)" enabled.
  GOOGLE_PLACE_ID    - optional. If missing, the club is looked up by name + address
                       and the Place ID found is printed and stored in reviews.json.

Google returns at most five reviews per place; we keep the newest first and never edit the text.
"""
import json, os, sys, urllib.request, urllib.error

KEY = os.environ.get('GOOGLE_PLACES_KEY', '').strip()
PLACE = os.environ.get('GOOGLE_PLACE_ID', '').strip()
QUERY = 'Kava Social Chess Club, 540 13th St W, Bradenton, FL 34205'
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
        sys.exit('Google refused the request (%s): %s' % (e.code, e.read().decode('utf-8', 'replace')[:400]))


def find_place():
    """Text-search for the club so nobody has to hunt down a Place ID by hand."""
    res = call('https://places.googleapis.com/v1/places:searchText',
               'places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount',
               {'textQuery': QUERY, 'maxResultCount': 5, 'languageCode': 'en'})
    hits = res.get('places', [])
    if not hits:
        sys.exit('No Google listing matched "%s". Check the business name on the profile.' % QUERY)
    print('Google listings matching the club:')
    for h in hits:
        print('  %s  %s — %s (%s stars, %s ratings)' % (
            h.get('id', '?'), (h.get('displayName') or {}).get('text', '?'),
            h.get('formattedAddress', '?'), h.get('rating', '-'), h.get('userRatingCount', 0)))
    # prefer a listing whose name mentions chess; otherwise the top hit
    for h in hits:
        if 'chess' in (h.get('displayName') or {}).get('text', '').lower():
            return h['id']
    return hits[0]['id']


place_id = PLACE or find_place()
print('Using Place ID: ' + place_id)

p = call('https://places.googleapis.com/v1/places/%s?languageCode=en' % place_id,
         'rating,userRatingCount,googleMapsUri,reviews')

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

doc = {'rating': p.get('rating'), 'count': p.get('userRatingCount', 0), 'url': p.get('googleMapsUri', ''),
       'placeId': place_id, 'reviews': reviews}
old = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
new = json.dumps(doc, ensure_ascii=False, indent=1) + '\n'
if new != old:
    open(OUT, 'w', encoding='utf-8').write(new)
    print('reviews.json updated: %s stars, %s ratings, %d reviews with text' % (doc['rating'], doc['count'], len(reviews)))
else:
    print('reviews.json unchanged')
