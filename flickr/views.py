import itertools
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

        if 'submit_group_photos' in request.POST:
            return redirect('groups', userid=userid)


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


# Flickr auth

def require_flickr_auth(view):
    """"View decorator, redirects users to Flickr when no access token found."""

    def protected_view(request, *args, **kwargs):
        token = request.session.get('token')
        if token is None:
            f = FlickrAPI(settings.FLICKR_KEY, settings.FLICKR_SECRET,
                token=token, store_token=False)
            callback_url = _build_callback_url(request)
            f.get_request_token(oauth_callback=callback_url)

            authorize_url = f.auth_url(perms='read')
            log.debug('require_flickr_auth()')
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

    return redirect(redirect_url)


@require_flickr_auth
def auth(request):
    return redirect('/')


def logout(request):
    request.session.pop('token', None)
    return redirect('/')


def init_flickrapi(request):
    token = request.session.get('token')

    f = FlickrAPI(settings.FLICKR_KEY, settings.FLICKR_SECRET,
        token=token, store_token=False, format='parsed-json')

    return f


# Flickr API calls

class FlickrExplore(View):
    def get(self, request, method_name, **kwargs):

        form = kwargs.get('form')
        if not form:
            try:
                form = self._dynamic_form(request, method_name)
            except FlickrError:
                return HttpResponseNotFound('<h1>404 Not Found</h1>')

        response = kwargs.get('response')

        context = {
            'form': form,
            'response': response,
            'utils': flickr.flickrutils,
        }
        return render(request, 'flickr/flickr_explore.html', context)


    def post(self, request, method_name):
        f = init_flickrapi(request)
        method_info = f.reflection.getMethodInfo(method_name=method_name)

        form = FlickrForm(request.POST, extra=method_info)

        if form.is_valid():
            log.debug(f'form: {form.cleaned_data}')

        response = f.do_flickr_call(_method_name=method_name, **form.cleaned_data)

        return self.get(request, method_name=method_name, response=response, form=form)


    def _dynamic_form(self, request, method_name):
        method_info = self._get_method_info(request, method_name)
        form = FlickrForm(extra=method_info)
        return form


    def _get_method_info(self, request, method_name):
        f = init_flickrapi(request)
        try:
            method_info = f.reflection.getMethodInfo(method_name=method_name)
        except FlickrError as err:
            log.error('{}'.format(err))
            raise err

        status = method_info['stat']
        log.debug('flickr.reflection.getMethodInfo status: {}'.format(status))

        return method_info


def api(request):
    f = init_flickrapi(request)
    response = f.reflection.getMethods()
    status = response.get('stat')

    if status != 'ok':
        log.debug(f'Bad status\n{response}')

    methods = (method['_content'] for method in response['methods']['method'])
    between_dots = lambda _str: _str[7: _str.rindex('.')]
    methods = itertools.groupby(methods, key=between_dots)

    context = {
        'methods': methods,
    }

    return render(request, 'flickr/api.html', context)
