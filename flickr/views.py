from django.shortcuts import render
from django.views import View

from flickr.utils import photo_url, photo_page_url
from config.flickrapi import get_flickr

flickr = get_flickr()


class Interestingness(View):
    def get(self, request):
        res = flickr.interestingness.getList()
        photos = res['photos']['photo']

        context = {
            'photos': photos,
            'photo_url': photo_url,
            'photo_page_url': photo_page_url,
        }
        return render(request, 'flickr/photos.html', context)

