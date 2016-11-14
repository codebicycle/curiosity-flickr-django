SIZES = {75: 's', 150: 'q', 100: 't', 240: 'm', 320: 'n', 500: '-',
         640: 'z', 800: 'c', 1024: 'b', 1600: 'h', 2048: 'k'}


def photo_url(photo_dict, size_suffix='z', longest_side=None):
    """

    :param longest_side:
    :param photo_dict: {'farm': 6,
                         'id': '30014555241',
                         'secret': 'cc74e7f525',
                         'server': '5631',}
    :param size_suffix:
    :return:
    """
    if longest_side:
        size_suffix = _get_size_suffix(int(longest_side))

    farm = photo_dict['farm']
    photoid = photo_dict['id']
    secret = photo_dict['secret']
    server = photo_dict['server']

    url_template = ('https://farm{farmid}.staticflickr.com/'
                    '{serverid}/{photoid}_{secret}_{size_suffix}.jpg')

    url = url_template.format(photoid=photoid, serverid=server,
                              farmid=farm, secret=secret,
                              size_suffix=size_suffix)
    return url


def _get_size_suffix(longest_side):
    if longest_side in SIZES:
        return SIZES[longest_side]

    desc_ordered_sizes = sorted(SIZES.keys(), reverse=True)
    for size in desc_ordered_sizes:
        if longest_side >= size:
            return SIZES[size]
    return SIZES[size]


def profile_url(userid):
    return 'https://www.flickr.com/people/{userid}/'.format(userid=userid)


def photostream_url(userid):
    return 'https://www.flickr.com/photos/{userid}/'.format(userid=userid)


def photo_page_url(userid=None, photoid=None):
    return 'https://www.flickr.com/photos/{userid}/{photoid}'.format(
        userid=userid, photoid=photoid)


def photosets_url(userid):
    return 'https://www.flickr.com/photos/{userid}/sets/'.format(userid=userid)


def photoset_url(userid=None, photosetid=None):
    return 'https://www.flickr.com/photos/{userid}/sets/{photosetid}'.format(
        userid=userid, photosetid=photosetid)
