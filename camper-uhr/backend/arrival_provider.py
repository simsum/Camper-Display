"""Bounded, read-only place/Wikipedia lookup, usable on Pi with stdlib only."""
import html
import json
import math
import re
import threading
import time
from urllib.parse import urlencode, urlparse, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler

HOSTS = {'nominatim.openstreetmap.org', 'www.wikidata.org', 'commons.wikimedia.org',
         'de.wikipedia.org', 'it.wikipedia.org', 'en.wikipedia.org',
         'upload.wikimedia.org', 'thumb.wikimedia.org', 'api.open-meteo.com'}
UA = 'CamperUhr/0.6 (private camper arrival display; read-only)'
_osm_lock = threading.Lock()
_osm_last = 0.0


def safe_url(url):
    p = urlparse(url)
    return p.scheme == 'https' and p.hostname in HOSTS and not p.username and not p.password and p.port in (None,443)


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not safe_url(newurl):
            raise ValueError('Unzulässige Weiterleitung')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def read_url(url, limit=2_000_000):
    if not safe_url(url):
        raise ValueError('Unzulässige Datenquelle')
    with build_opener(SafeRedirect()).open(Request(url, headers={'User-Agent':UA}), timeout=6) as response:
        data = response.read(limit+1)
        if len(data)>limit:
            raise ValueError('Antwort zu groß')
        return data


def get_json(url, **params):
    global _osm_last
    if params:
        url += '?' + urlencode(params)
    if urlparse(url).hostname == 'nominatim.openstreetmap.org':
        with _osm_lock:
            time.sleep(max(0, 1.1-(time.monotonic()-_osm_last)))
            _osm_last=time.monotonic()
            return json.loads(read_url(url))
    return json.loads(read_url(url))


def clean(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]*>', '', str(value or '')))).strip()


def claim(entity, prop):
    entries=[c for c in entity.get('claims',{}).get(prop,[]) if c.get('rank')!='deprecated' and 'datavalue' in c.get('mainsnak',{})]
    preferred=[c for c in entries if c.get('rank')=='preferred']
    entries=preferred or entries
    def date(c):
        return next((q.get('datavalue',{}).get('value',{}).get('time','') for q in c.get('qualifiers',{}).get('P585',[])), '')
    return max(entries,key=date) if entries else None


def value(entity, prop):
    c=claim(entity,prop)
    return c['mainsnak']['datavalue']['value'] if c else None


def quantity(entity,prop,unit):
    v=value(entity,prop)
    if not isinstance(v,dict) or not v.get('unit','').endswith('/'+unit):
        return None
    return float(v['amount'])


def photo(filename):
    # Article-selected photograph only; no logo, map, flag or SVG fallback.
    if not re.search(r'\.(jpe?g|png)$',filename,re.I) or re.search(r'(stemma|wappen|coat.of.arms|flag|map.of|logo)',filename,re.I):
        return {}
    payload=get_json('https://commons.wikimedia.org/w/api.php',action='query',format='json',
                     prop='imageinfo',iiprop='url|extmetadata|size',iiurlwidth=1280,titles='File:'+filename)
    page=next(iter(payload.get('query',{}).get('pages',{}).values()),{})
    info=(page.get('imageinfo') or [{}])[0];meta=info.get('extmetadata',{})
    license_name=clean(meta.get('LicenseShortName',{}).get('value'))
    artist=clean(meta.get('Artist',{}).get('value'))
    license_url=meta.get('LicenseUrl',{}).get('value','')
    public=license_name in ('CC0','Public domain','Public Domain')
    # Unknown or special conditions: omit the image rather than guess.
    if not public and not re.fullmatch(r'CC BY(?:-SA)? [1-4]\.0',license_name):
        return {}
    if not public and (not artist or not license_url.startswith('https://creativecommons.org/')):
        return {}
    if len(artist)>220:
        return {}
    url=info.get('thumburl')
    if not url or info.get('thumbwidth',9999)>1280 or info.get('thumbheight',9999)>1600:
        return {}
    data=read_url(url,1_500_000)
    if not (data.startswith(b'\xff\xd8\xff') or data.startswith(b'\x89PNG\r\n\x1a\n')):
        return {}
    return {'_image':data,'image_mime':'image/jpeg' if data[:2]==b'\xff\xd8' else 'image/png',
            'image_credit': 'WIKI' if public else f'WIKI · {artist} · {license_name} · Ausschnitt',
            'image_source':info.get('descriptionurl',''), 'image_license_url':license_url}


def lookup(lat,lon,altitude=None):
    if not all(isinstance(x,(int,float)) and math.isfinite(x) for x in (lat,lon)) or not (-90<=lat<=90 and -180<=lon<=180):
        raise ValueError('Ungültige Koordinaten')
    result={'place':'Eurem Standort','region':'','extract':'','facts':[], 'altitude_m':altitude,
            'altitude_label':'GPS-Höhe','sunset':None,'wiki_url':'','image_credit':'','image_source':'',
            'source_credit':'','errors':[]}
    try:
        place=get_json('https://nominatim.openstreetmap.org/reverse',lat=lat,lon=lon,
                       format='jsonv2',zoom=10,addressdetails=1,extratags=1,**{'accept-language':'de'})
        address=place.get('address',{});tags=place.get('extratags',{})
        result['place']=clean(place.get('name')) or result['place']
        result['region']=' · '.join(dict.fromkeys(clean(address[k]) for k in ('state','country') if address.get(k)))
        result['source_credit']='Ort: © OpenStreetMap'
        qid=tags.get('wikidata','')
        if not re.fullmatch(r'Q[1-9][0-9]*',qid):
            raise ValueError('Keine eindeutige Wikipedia-Zuordnung')
        entity=get_json(f'https://www.wikidata.org/wiki/Special:EntityData/{qid}.json')['entities'][qid]
        site=next((s for s in ('dewiki','itwiki','enwiki') if s in entity.get('sitelinks',{})),None)
        if not site:raise ValueError('Kein Ortsartikel')
        lang=site[:-4];title=entity['sitelinks'][site]['title']
        page=next(iter(get_json(f'https://{lang}.wikipedia.org/w/api.php',action='query',format='json',
            prop='extracts|pageimages|pageprops',exintro=1,explaintext=1,exsentences=3,
            piprop='name',titles=title,redirects=1).get('query',{}).get('pages',{}).values()),{})
        if page.get('pageprops',{}).get('wikibase_item')!=qid or 'disambiguation' in page.get('pageprops',{}):
            raise ValueError('Artikel nicht eindeutig')
        extract=clean(page.get('extract'))
        if len(extract)>330:extract=extract[:327].rsplit(' ',1)[0]+' …'
        result.update(extract=extract,wiki_url=f'https://{lang}.wikipedia.org/wiki/'+quote(title.replace(' ','_')),language=lang)
        result['source_credit']='Wikipedia · CC BY-SA 4.0 · gekürzt | Ort: © OpenStreetMap'
        population=claim(entity,'P1082')
        if population:
            amount=population['mainsnak']['datavalue']['value']['amount']
            year=next((q['datavalue']['value']['time'][1:5] for q in population.get('qualifiers',{}).get('P585',[]) if 'datavalue' in q),None)
            if year:result['facts'].append({'label':f'Einwohner · {year}','value':f'{int(float(amount)):,}'.replace(',','.')})
        # German lead text may have a newer dated count than Wikidata.
        current=re.search(r'mit ([0-9. ]+) Einwohnern? \(Stand[^)]*?([12][0-9]{3})\)',extract)
        if current:
            fact={'label':'Einwohner · '+current[2],'value':f'{int(current[1].replace(".","").replace(" ","")):,}'.replace(',','.')}
            if result['facts'] and current[2] >= result['facts'][0]['label'][-4:]:result['facts'][0]=fact
            elif not result['facts']:result['facts'].append(fact)
        area=quantity(entity,'P2046','Q712226')
        if area is not None:result['facts'].append({'label':'Gemeindefläche','value':f'{area:.2f}'.replace('.',',')+' km²'})
        if altitude is None:
            result['altitude_m']=quantity(entity,'P2044','Q11573');result['altitude_label']='Ortshöhe'
        try:
            result.update(photo(page.get('pageimage') or value(entity,'P18') or ''))
            if '_image' not in result and value(entity,'P18') and value(entity,'P18')!=page.get('pageimage'):
                result.update(photo(value(entity,'P18')))
        except Exception:
            result['errors'].append('Foto nicht verfügbar')
    except Exception:
        result['errors'].append('Ortsinformationen nicht vollständig verfügbar')
    try:
        solar=get_json('https://api.open-meteo.com/v1/forecast',latitude=lat,longitude=lon,
                       daily='sunset',timezone='auto',forecast_days=1)
        result['sunset']=solar['daily']['sunset'][0]
    except Exception:
        result['errors'].append('Sonnenuntergang nicht verfügbar')
    return result
