import logging
from urllib.parse import unquote
from pprint import pformat

from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, redirect, reverse
from django.views import View
from django.views.generic import DeleteView
from flickrapi import FlickrAPI, FlickrError

from flickr.flickrutils import photo_url, photo_page_url, photostream_url
import flickr.flickrutils
from flickr.utils import set_query_param
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
        f = init_flickrapi(request)

        response = f.interestingness.getList()
        photos = response['photos']['photo']

        context = {
            'photos': photos,
            'utils': flickr.flickrutils,
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


# Flickr auth

def require_flickr_auth(view):
    """"View decorator, redirects users to Flickr when no access token found."""

    def protected_view(request, *args, **kwargs):
        token = request.session.get('token')

        f = FlickrAPI(settings.FLICKR_KEY, settings.FLICKR_SECRET,
            token=token, store_token=False)

        if token is None:
            callback_url = build_callback_url(request)
            f.get_request_token(oauth_callback=callback_url)

            authorize_url = f.auth_url(perms='read')
            log.debug('authorize URL: {}'.format(authorize_url))

            request.session['request_token'] = f.flickr_oauth.resource_owner_key
            request.session['request_token_secret'] = f.flickr_oauth.resource_owner_secret
            request.session['requested_permissions'] = f.flickr_oauth.requested_permissions

            return HttpResponseRedirect(authorize_url)

        return view(request, *args, **kwargs)

    return protected_view


def build_callback_url(request):
    next_url = request.get_full_path()
    callback_url = request.build_absolute_uri(reverse('flickr-auth'))
    callback_url = set_query_param(callback_url, 'next', next_url)
    callback_url = unquote(callback_url)
    log.debug('callback URL: {}'.format(callback_url))
    return callback_url


def flickr_auth(request):
    redirect_url = request.GET['next']
    log.debug('redirect URL: {}'.format(redirect_url))

    verifier = request.GET.get('oauth_verifier')
    log.debug('verifier: {}'.format(verifier))

    f = FlickrAPI(settings.FLICKR_KEY, settings.FLICKR_SECRET,
        token=None, store_token=False)

    f.flickr_oauth.resource_owner_key = request.session['request_token']
    f.flickr_oauth.resource_owner_secret = request.session['request_token_secret']
    f.flickr_oauth.requested_permissions = request.session['requested_permissions']
    del request.session['request_token']
    del request.session['request_token_secret']
    del request.session['requested_permissions']

    f.get_access_token(verifier)

    token = f.token_cache.token
    log.debug('token: {}'.format(token.__dict__))

    request.session['token'] = token

    return redirect(redirect_url)


@require_flickr_auth
def hello(request):
    return HttpResponse('Hello')


def logout(request):
    if 'token' in request.session:
        del request.session['token']

    return redirect('/')


def init_flickrapi(request):
    token = request.session.get('token')

    f = FlickrAPI(settings.FLICKR_KEY, settings.FLICKR_SECRET,
        token=token, store_token=False, format='parsed-json')

    return f


# Flickr API calls

@require_flickr_auth
def user_favs(request):
    f = init_flickrapi(request)

    response = f.favorites.getList()
    log.debug('Response\n{}}'.format(pformat(response)))

    photos = response['photos']['photo']

    context = {
            'photos': photos,
            'utils': flickr.flickrutils,
        }
    return render(request, 'flickr/favourites.html', context)
