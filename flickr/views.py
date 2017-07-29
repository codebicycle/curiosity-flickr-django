import logging
from urllib.parse import urlparse

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import DeleteView
from flickrapi import FlickrError

from flickr.flickrutils import photo_url, photo_page_url, photostream_url
from .forms import PeopleForm
from .models import Person, FLICKR, Fav


logging.basicConfig()

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


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
        res = FLICKR.interestingness.getList()
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

        if 'submit_fav' in request.POST:
            try:
                person = Person.objects.get(flickrid=userid)
            except Person.DoesNotExist as e:
                person = Person(flickrid=userid)
                person.update()

            Fav.objects.get_or_create(person=person)
            return redirect('fav')

    def _userid(self, param):
        """
        :param: flickr user url or flickr user id:
                https://www.FLICKR.com/photos/jellybeanzgallery
                or
                38954353@N06
        :return: flickr user id:
                38954353@N06
        """
        parsed_url = urlparse(param)
        if not parsed_url.scheme:
            return param
        userid = FLICKR.urls.lookupUser(url=param)['user']['id']
        return userid


class UserGroupView(View):
    def post(self, request, userid, groupid):
        groupname = request.POST.get('group[name]')

        photos = []
        try:
            group_photos = FLICKR.groups.pools.getPhotos(group_id=groupid,
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
        groups = FLICKR.people.getGroups(user_id=userid)

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
            person.update()


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


class FavView(View):
    def get(self, request):
        favs = Fav.objects.all()

        selection = []
        for fav in favs:
            if fav.person.needs_update:
                fav.person.update()

            person = fav.person
            flickrid = person.flickrid
            username = person.info['person']['username']['_content']
            photos = person.photos
            latest = sorted(photos, reverse=True,
                            key=(lambda x: int(x['dateupload'])))[:10]

            selection.append({
                'flickrid': flickrid,
                'username': username,
                'photos': latest
            })

        context = {
            'favs': selection,
            'photo_url': photo_url,
            'photo_page_url': photo_page_url,
            'photostream_url': photostream_url,
        }
        # context = {'context': context}
        return render(request, 'flickr/fav.html', context)
