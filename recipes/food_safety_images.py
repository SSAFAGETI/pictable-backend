from functools import lru_cache
from urllib.parse import quote

import requests
from django.conf import settings


FOODSAFETY_ORIGIN = 'https://www.foodsafetykorea.go.kr'
FOODSAFETY_API_BASE = 'https://openapi.foodsafetykorea.go.kr/api'


def _as_text(value):
    return str(value or '').strip()


def _normalize_recipe_name(value):
    return ''.join(_as_text(value).split())


def _search_terms(title):
    normalized = _as_text(title)
    words = [word for word in normalized.split() if word]
    candidates = [
        normalized,
        ' '.join(words[:2]),
        words[0] if words else '',
        words[-1] if words else '',
        normalized[:6],
        _normalize_recipe_name(normalized),
    ]
    seen = set()
    terms = []
    for term in candidates:
        if len(term) < 2 or term in seen:
            continue
        seen.add(term)
        terms.append(term)
    return terms


def normalize_food_safety_image_url(value):
    url = _as_text(value)
    if not url:
        return ''

    if url.startswith('http://www.foodsafetykorea.go.kr'):
        return 'https://www.foodsafetykorea.go.kr' + url[len('http://www.foodsafetykorea.go.kr'):]
    if url.startswith('https://www.foodsafetykorea.go.kr'):
        return url
    if url.startswith('/uploadimg/') or url.startswith('/common/ecmFileView.do'):
        return f'{FOODSAFETY_ORIGIN}{url}'
    if url.startswith('uploadimg/') or url.startswith('common/ecmFileView.do'):
        return f'{FOODSAFETY_ORIGIN}/{url}'
    return url


def _is_usable_image_url(url):
    return bool(url) and not ('/common/ecmFileView.do' in url and '?' not in url)


def _image_from_row(row):
    if not isinstance(row, dict):
        return ''

    for key in ('ATT_FILE_NO_MAIN', 'ATT_FILE_NO_MK', 'MANUAL_IMG01'):
        image = normalize_food_safety_image_url(row.get(key))
        if _is_usable_image_url(image):
            return image
    return ''


def _rows_from_body(body):
    if not isinstance(body, dict):
        return []
    service = body.get('COOKRCP01')
    if not isinstance(service, dict):
        return []
    rows = service.get('row')
    return rows if isinstance(rows, list) else []


def _best_image(rows, title):
    normalized_title = _normalize_recipe_name(title)
    if not normalized_title:
        return ''

    for matcher in (
        lambda name: name == normalized_title,
        lambda name: normalized_title in name,
        lambda name: name in normalized_title,
    ):
        for row in rows:
            row_name = _normalize_recipe_name(row.get('RCP_NM') if isinstance(row, dict) else '')
            if row_name and matcher(row_name):
                image = _image_from_row(row)
                if image:
                    return image

    return _image_from_row(rows[0]) if rows else ''


@lru_cache(maxsize=512)
def resolve_food_safety_image_url(title):
    api_key = _as_text(getattr(settings, 'FOOD_API_KEY', ''))
    if not api_key:
        return ''

    for term in _search_terms(title):
        try:
            response = requests.get(
                f'{FOODSAFETY_API_BASE}/{api_key}/COOKRCP01/json/1/8/RCP_NM={quote(term)}',
                timeout=3,
            )
            response.raise_for_status()
        except requests.RequestException:
            continue

        image = _best_image(_rows_from_body(response.json()), title)
        if image:
            return image

    return ''
