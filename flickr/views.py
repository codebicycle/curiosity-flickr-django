from urllib.parse import urlparse

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from django.views import View
from flickrapi import FlickrError

from config.flickrapi import get_flickr
from flickr.utils import photo_url, photo_page_url
from .forms import PeopleForm

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


class PeopleView(View):
    def get(self, request):
        form = PeopleForm()
        context = {
            'form': form,
        }
        return render(request, 'flickr/groups.html', context)

    def post(self, request):
        form = PeopleForm(request.POST)
        if not form.is_valid():
            raise 'form not valid'

        userid = self._userid(form.cleaned_data['user_id_or_url'])
        groups = flickr.people.getGroups(user_id=userid)

        group_list = groups['groups']['group']
        paginator = Paginator(group_list, 25)

        page = request.POST.get('page')
        try:
            pages = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            pages = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            pages = paginator.page(paginator.num_pages)

        context = {
            'form': form,
            'group_url': request.build_absolute_uri('group'),
            'userid': userid,
            'groups': pages.object_list,
            'pages': pages,
            'photo_url': photo_url,
            'photo_page_url': photo_page_url,
        }
        return render(request, 'flickr/groups.html', context)

    def _userid(self, param):
        """
        :param: url or flickr user id
                38954353@N06
                https://www.flickr.com/photos/jellybeanzgallery/29883393633/in/explore-2016-10-23/

        :return: flickr user id
                38954353@N06
        """
        parsed_url = urlparse(param)
        if not parsed_url.scheme:
            return param
        userid = flickr.urls.lookupUser(url=param)['user']['id']
        return userid


class GroupView(View):
    def post(self, request):
        groupid = request.POST.get('group[nsid]')
        userid = request.POST.get('userid')
        groupname = request.POST.get('group[name]')

        photos = []
        try:
            group_photos = flickr.groups.pools.getPhotos(group_id=groupid,
                                                         user_id=userid)
            photos = group_photos['photos']['photo']
        except FlickrError as err:
            print(err, groupname)

        context = {
            'groupname': groupname,
            'photos': photos,
            'photo_url': photo_url,
            'photo_page_url': photo_page_url,
        }
        return render(request, 'flickr/_group.html', context)
