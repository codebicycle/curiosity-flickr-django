import flickrapi
from config.settings import (FLICKR_KEY, FLICKR_SECRET, FLICKR_ACCESS_TOKEN,
                             FLICKR_ACCESS_SECRET)


def get_flickr():
    access_token = flickrapi.auth.FlickrAccessToken(FLICKR_ACCESS_TOKEN,
                                                    FLICKR_ACCESS_SECRET,
                                                    'read')
    flickr = flickrapi.FlickrAPI(FLICKR_KEY, FLICKR_SECRET, token=access_token,
                                 format='parsed-json')
    return flickr
