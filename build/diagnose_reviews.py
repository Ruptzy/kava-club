"""One-off diagnostic: show every Google listing that could be the club, and exactly what
each one carries. Run from the diagnose workflow; prints only, writes nothing.
"""
import json, os, sys, urllib.request, urllib.error

KEY = os.environ.get('GOOGLE_PLACES_KEY', '').strip()
if not KEY:
    sys.exit('GOOGLE_PLACES_KEY is not set')

QUERIES = ['Kava Social Chess Club Bradenton',
           'Kava Social Chess Club',
           'Kava Social Club Bradenton',
           'chess Bradenton FL']


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
        print('  ! HTTP %s: %s' % (e.code, e.read().decode('utf-8', 'replace')[:300]))
        return {}


seen = {}
for q in QUERIES:
    res = call('https://places.googleapis.com/v1/places:searchText',
               'places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount',
               {'textQuery': q, 'maxResultCount': 10, 'languageCode': 'en'})
    for p in res.get('places', []):
        seen.setdefault(p['id'], p)

print('=== %d distinct listings found ===' % len(seen))
for pid, p in seen.items():
    name = (p.get('displayName') or {}).get('text', '?')
    print('\n--- %s' % name)
    print('    id      : %s' % pid)
    print('    address : %s' % p.get('formattedAddress', '?'))
    print('    rating  : %s from %s ratings' % (p.get('rating'), p.get('userRatingCount', 0)))
    d = call('https://places.googleapis.com/v1/places/%s?languageCode=en' % pid, 'reviews')
    revs = d.get('reviews', [])
    print('    reviews returned by the API: %d' % len(revs))
    for rv in revs:
        who = (rv.get('authorAttribution') or {}).get('displayName', '?')
        txt = ((rv.get('text') or {}).get('text') or (rv.get('originalText') or {}).get('text') or '').strip()
        print('      * %-22s %s  %s' % (who[:22], rv.get('relativePublishTimeDescription', ''), (txt[:70] + '...') if txt else '(no text)'))
