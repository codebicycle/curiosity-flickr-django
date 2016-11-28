from urllib.parse import urlparse
import math

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect
from django.views import View
from flickrapi import FlickrError

from config.flickrapi import get_flickr
from flickr.utils import photo_url, photo_page_url
from .forms import PeopleForm
from .models import Person

flickr = get_flickr()


def paginate(request=None, collection=None, per_page=100):
    page = request.GET.get('page') if request is not None else 1
    paginator = Paginator(collection, per_page)
    try:
        pages = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        pages = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        pages = paginator.page(paginator.num_pages)

    return pages


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
        :param: flickr user url or flickr user id:
                https://www.flickr.com/photos/jellybeanzgallery
                or
                38954353@N06
        :return: flickr user id:
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
        pages = paginate(request, collection=group_list, per_page=25)

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
        try:
            person = Person.objects.get(flickrid=userid)
        except Person.DoesNotExist as e:
            person = Person(flickrid=userid)

        if person.needs_update:
            self._update_person(person)
            person.save()

        top_views = sorted(person.photos, reverse=True,
                           key=(lambda x: int(x['views'])))

        pages = paginate(request, collection=top_views,  per_page=100)

        context = {
            'photos': pages.object_list,
            'pages': pages,
            'photo_url': photo_url,
            'photo_page_url': photo_page_url,
        }
        return render(request, 'flickr/photos.html', context)

    def _update_person(self, person):
        person.info = flickr.people.getInfo(user_id=person.flickrid)
        user_name = person.info['person']['username']['_content']

        first_page = self._get_photos(person.flickrid, person.updated_at,
                                      page=1)
        person.photos.extend(first_page['photos']['photo'])

        pages = first_page['photos']['pages']
        total = first_page['photos']['total']
        print('{} | {} photos | {} pages'.format(user_name, total, pages))

        for page in range(2, pages + 1):
            print('page', page)
            current_page = self._get_photos(person.flickrid, person.updated_at,
                                            page=page)
            person.photos.extend(current_page['photos']['photo'])

    def _get_photos(self, flickrid, min_upload_date, page=1):
        response = flickr.people.getPhotos(user_id=flickrid,
                                           per_page=500,
                                           page=page,
                                           extras='date_upload, views',
                                           min_upload_date=min_upload_date
                                           )
        return response
