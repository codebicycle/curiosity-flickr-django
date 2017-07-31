from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

def set_query_param(url, key, value):
    parts = list(urlparse(url))
    query_dict = parse_qs(parts[4])
    query_dict[key] = value
    parts[4] = urlencode(query_dict, doseq=True)
    new_url = urlunparse(parts)
    return new_url
