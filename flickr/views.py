from django.shortcuts import render
from django.views import View

import flickrapi
from config.settings import FLICKR_KEY, FLICKR_SECRET
from flickr.utils import photo_url, photo_page_url

flickr = flickrapi.FlickrAPI(FLICKR_KEY, FLICKR_SECRET, format='parsed-json')


class PhotosView(View):
    def get(self, request):
        res = flickr.interestingness.getList()
        photos = res['photos']['photo']

        context = {
            'photos': photos,
            'photo_url': photo_url,
            'photo_page_url': photo_page_url,
        }
        return render(request, 'flickr/photos.html', context)

