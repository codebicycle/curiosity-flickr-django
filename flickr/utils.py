from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

def set_query_param(url, key, value):
    parts = list(urlparse(url))
    query_dict = parse_qs(parts[4])
    query_dict[key] = value
    parts[4] = urlencode(query_dict, doseq=True)
    new_url = urlunparse(parts)
    return new_url


def get_logged_in_user_id(request):
    token = request.session['token']
    user_id = token.user_nsid
    return user_id
