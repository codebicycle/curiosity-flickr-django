import logging
from urllib.parse import unquote, urlparse
from pprint import pformat

from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import IntegrityError
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotFound
from django.shortcuts import render, redirect, reverse
from django.views import View
from django.views.generic import DeleteView
from flickrapi import FlickrAPI, FlickrError

from flickr.flickrutils import photo_url, photo_page_url, photostream_url
import flickr.flickrutils
from flickr.utils import set_query_param, get_logged_in_user_id
from flickr.forms import PeopleForm, FlickrForm
from flickr.models import Person, Fav, Following


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
            raise 'Form not valid.'

        userid_or_url = form.cleaned_data['user_id_or_url']
        userid = self._userid_from_url(userid_or_url, request)

        if 'submit_top_photos' in request.POST:
            return redirect('top', userid=userid)

        if 'submit_group_photos' in request.POST:
            return redirect('groups', userid=userid)

        if 'submit_follow' in request.POST:
            self._follow_user(userid, request)
            return redirect('following')

        if 'submit_favs' in request.POST:
            return redirect('favs', userid=userid)

        if 'submit_popular' in request.POST:
            return redirect('popular', userid=userid)


    def _userid_from_url(self, param, request):
        """
        :param: flickr user url or flickr user id:
                https://www.FLICKR.com/photos/jellybeanzgallery
                or
                38954353@N06
        :return: flickr user id:
                38954353@N06
        """
        parts = urlparse(param)
        if not parts.scheme:
            return param

        f = init_flickrapi(request)
        response = f.urls.lookupUser(url=param)
        userid = response['user']['id']
        return userid


    def _follow_user(self, followed_id, request):
        Person.flickrapi = init_flickrapi(request)
        try:
            followed = Person.objects.get(flickrid=followed_id)
        except Person.DoesNotExist as e:
            followed = Person.create(flickrid=followed_id)
            followed.save()

        follower_id = get_logged_in_user_id(request)
        following = Following(follower_id=follower_id, followed=followed)
        try:
            following.save()
        except IntegrityError as e:
            log.error(e)


class UserGroupView(View):
    def post(self, request, userid, groupid):
        groupname = request.POST.get('group[name]')

        f = init_flickrapi(request)
        photos = []
        try:
            response = f.groups.pools.getPhotos(group_id=groupid, user_id=userid, extras='views')
            photos = response['photos']['photo']
        except FlickrError as err:
            log.error('{} {}'.format(err, groupname))

        context = {
            'groupname': groupname,
            'photos': photos,
            'utils': flickr.flickrutils,
        }
        return render(request, 'flickr/_group.html', context)


class UserGroupsView(View):
    def get(self, request, userid):
        f = init_flickrapi(request)

        response = f.people.getGroups(user_id=userid)

        group_list = response['groups']['group']
        log.debug('{} groups for {}:\n{}'.format(len(group_list), userid,
            pformat(group_list[:10])))

        pages = paginate(request, collection=group_list, per_page=25)

        context = {
            'userid': userid,
            'groups': pages.object_list,
            'pages': pages,
            'utils': flickr.flickrutils,
        }
        return render(request, 'flickr/groups.html', context)


class UserTopView(View):
    def get(self, request, userid):
        Person.flickrapi = init_flickrapi(request)

        try:
            person = Person.objects.get(flickrid=userid)
        except Person.DoesNotExist as e:
            person = Person(flickrid=userid)

        photos = person.photos

        first_page = person._get_photo_page(page=1)
        pages = first_page['photos']['pages']
        total = first_page['photos']['total']


        if person.needs_update:
            person.update()

        top_views = sorted(person.photos, reverse=True,
                           key=(lambda x: int(x['views'])))
        log.debug('Top_views\n{}'.format(pformat(top_views)))

        pages = paginate(request, collection=top_views,  per_page=100)

        context = {
            'photos': pages.object_list,
            'pages': pages,
            'utils': flickr.flickrutils,
        }
        return render(request, 'flickr/photos.html', context)


# class FavView(View):
#     def get(self, request):
#         favs = Fav.objects.all()

#         selection = []
#         for fav in favs:
#             if fav.person.needs_update:
#                 fav.person.update()

#             person = fav.person
#             flickrid = person.flickrid
#             username = person.info['person']['username']['_content']
#             photos = person.photos
#             latest = sorted(photos, reverse=True,
#                             key=(lambda x: int(x['dateupload'])))[:10]

#             selection.append({
#                 'flickrid': flickrid,
#                 'username': username,
#                 'photos': latest
#             })

#         context = {
#             'favs': selection,
#             'photo_url': photo_url,
#             'photo_page_url': photo_page_url,
#             'photostream_url': photostream_url,
#         }
#         # context = {'context': context}
#         return render(request, 'flickr/fav.html', context)


# Flickr auth

def require_flickr_auth(view):
    """"View decorator, redirects users to Flickr when no access token found."""

    def protected_view(request, *args, **kwargs):
        token = request.session.get('token')

        f = FlickrAPI(settings.FLICKR_KEY, settings.FLICKR_SECRET,
            token=token, store_token=False)

        if token is None:
            callback_url = _build_callback_url(request)
            f.get_request_token(oauth_callback=callback_url)

            authorize_url = f.auth_url(perms='read')
            log.debug('authorize URL: {}'.format(authorize_url))

            request.session['request_token'] = f.flickr_oauth.resource_owner_key
            request.session['request_token_secret'] = f.flickr_oauth.resource_owner_secret
            request.session['requested_permissions'] = f.flickr_oauth.requested_permissions

            return HttpResponseRedirect(authorize_url)

        return view(request, *args, **kwargs)

    return protected_view


def _build_callback_url(request):
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

    f = init_flickrapi(request)

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

    user_id = token.user_nsid
    try:
        person = Person.objects.get(flickrid=user_id)
    except Person.DoesNotExist as e:
        Person.flickrapi = init_flickrapi(request)
        person = Person.create(flickrid=user_id)
        person.save()

    return redirect(redirect_url)


def logout(request):
    request.session.pop('token', None)

    return redirect('/')


def init_flickrapi(request):
    token = request.session.get('token')

    f = FlickrAPI(settings.FLICKR_KEY, settings.FLICKR_SECRET,
        token=token, store_token=False, format='parsed-json')

    return f


# Flickr API calls

@require_flickr_auth
def favs(request, userid=None):
    f = init_flickrapi(request)
    page = request.GET.get('page', 1)

    response = f.favorites.getList(user_id=userid, page=page, extras='owner_name,views')
    log.debug('Response\n{}'.format(pformat(response)))

    photos = response['photos']['photo']

    context = {
            'photos': photos,
            'utils': flickr.flickrutils,
        }
    return render(request, 'flickr/photos.html', context)


@require_flickr_auth
def popular(request, userid=None):
    """sort : faves, views, comments or interesting. Deafults to views."""

    f = init_flickrapi(request)
    page = request.GET.get('page', 1)
    sort = request.GET.get('sort', 'views')

    response = f.photos.getPopular(user_id=userid, sort=sort,
        page=page, extras='owner_name,views')
    log.debug('Response\n{}'.format(pformat(response)))

    photos = response['photos']['photo']

    context = {
            'photos': photos,
            'utils': flickr.flickrutils,
        }
    return render(request, 'flickr/photos.html', context)


def following(request):
    user_id = get_logged_in_user_id(request)
    followings = Following.objects.all()
    context = {
        'followings': followings,
        'utils': flickr.flickrutils,
    }

    return render(request, 'flickr/following.html', context)



class PhotoFavView(View):
    def post(self, request, photoid):
        user_id = get_logged_in_user_id(request)
        f = init_flickrapi(request)

        if not Fav.objects.filter(user_id=user_id, photoid=photoid).exists():
            info = f.photos.getInfo(photo_id=photoid)
            fav = Fav(user_id=user_id, photoid=photoid, info=info)
            fav.save()

        return redirect('fav-photos')


@require_flickr_auth
def fav(request):
    user_id = get_logged_in_user_id(request)

    favs = Fav.objects.filter(user_id=user_id).all()

    context = {
        'photos': favs,
        'utils': flickr.flickrutils,
    }
    return render(request, 'flickr/favs.html', context)


class FlickrExplore(View):
    def get(self, request, method_name):
        f = init_flickrapi(request)

        try:
            response = f.reflection.getMethodInfo(method_name=method_name)
        except FlickrError as err:
            log.error('{}'.format(err))
            return HttpResponseNotFound('<h1>404 Not Found</h1>')

        response_status = response['stat']
        log.debug('flickr.reflection.getMethodInfo status: {}'.format(response_status))

        form = FlickrForm(extra=response)

        context = {
            'form': form,
        }
        return render(request, 'flickr/flickr_explore.html', context)


    def post(self, request, method_name):
        f = init_flickrapi(request)
        response = f.reflection.getMethodInfo(method_name=method_name)

        form = FlickrForm(request.POST, extra=response)
        if form.is_valid():
            log.debug('Form is valid:\n{}'.format(form.cleaned_data))
        else:
            log.debug('Invalid form.')

        response = f.do_flickr_call(_method_name=method_name, **form.cleaned_data)

        context = {
            'response': response,
            'utils': flickr.flickrutils,
        }

        return render(request, 'flickr/api_response.html', context)
