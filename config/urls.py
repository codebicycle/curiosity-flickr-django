"""config URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.views.generic import RedirectView

import flickr.views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', RedirectView.as_view(pattern_name='api'), name='home'),
    url(r'^api/$', flickr.views.api, name='api'),

    url(r'^people/$', flickr.views.PeopleView.as_view(), name='people'),

    url(r'^people/(?P<userid>.*)/groups/?$',
        flickr.views.UserGroupsView.as_view(), name='groups'),

    url(r'^people/(?P<userid>.*)/(?P<groupid>.*)$',
        flickr.views.UserGroupView.as_view()),

    url(r'^flickr-auth/$', flickr.views.flickr_auth, name='flickr-auth'),
    url(r'^auth/$', flickr.views.auth),
    url(r'^logout/$', flickr.views.logout),

    url(r'^(?P<method_name>flickr\..*)$', flickr.views.FlickrExplore.as_view(), name='flickr-explore'),
]
