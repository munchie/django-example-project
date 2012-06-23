from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin
from common.views import index

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', index, name='home'),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
