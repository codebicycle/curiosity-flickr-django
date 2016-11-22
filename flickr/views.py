from urllib.parse import urlparse
import math

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect
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

        if 'submit_top_photos' in request.POST:
            return redirect('top', userid=userid)

        if 'submit_group_photos' in request.POST:
            return redirect('groups', userid=userid)

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


class UserGroupView(View):

    def post(self, request, userid, groupid):
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


class UserGroupsView(View):

    def get(self, request, userid):
        groups = flickr.people.getGroups(user_id=userid)

        group_list = groups['groups']['group']
        paginator = Paginator(group_list, 25)

        page = request.GET.get('page')
        try:
            pages = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            pages = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            pages = paginator.page(paginator.num_pages)

        context = {
            'userid': userid,
            'groups': pages.object_list,
            'pages': pages,
            'photo_url': photo_url,
            'photo_page_url': photo_page_url,
        }
        return render(request, 'flickr/groups.html', context)


class UserTopView(View):

    def get(self, request, userid):
        user_info = flickr.people.getInfo(user_id=userid)
        photo_count = user_info['person']['photos']['count']['_content']
        user_name = user_info['person']['username']['_content']
        photo_pages = math.ceil(photo_count / 500)
        print('{} | {} photos | {} pages'
              .format(user_name, photo_count, photo_pages))

        # 40 * 500 = 20000
        limit_photo_pages = min(40, photo_pages)
        photos = []
        for page in range(1, limit_photo_pages + 1):
            print('page', page)
            page_photos = flickr.people.getPhotos(user_id=userid,
                                                  per_page=500,
                                                  page=page,
                                                  extras='date_upload, views'
                                                  )
            photos.extend(page_photos['photos']['photo'])

        top_views = sorted(photos, reverse=True,
                           key=(lambda x: int(x['views'])))[:200]

        context = {
            'photos': top_views,
            'photo_url': photo_url,
            'photo_page_url': photo_page_url,
        }
        return render(request, 'flickr/photos.html', context)
