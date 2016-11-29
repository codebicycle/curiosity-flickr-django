import datetime

from django.contrib.postgres.fields import JSONField
from django.db import models

from config.flickrapi import init_flickr

FLICKR = init_flickr()


class Person(models.Model):
    def _needs_update(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = datetime.timedelta(days=1)
        threshold = now - delta
        if self.updated_at is None or self.updated_at < threshold:
            return True
        return False

    flickrid = models.CharField(max_length=30, unique=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    photos = JSONField(default=[])
    info = JSONField()
    needs_update = property(_needs_update)

    def __str__(self):
        return self.info['person']['username']['_content']

    def update(self):
        self.info = FLICKR.people.getInfo(user_id=self.flickrid)
        self._update_photos()

    def _update_photos(self):
        user_name = self.info['person']['username']['_content']
        first_page = self._get_photo_page(page=1)
        self.photos.extend(first_page['photos']['photo'])

        pages = first_page['photos']['pages']
        total = first_page['photos']['total']
        print('{} | {} photos | {} pages'.format(user_name, total, pages))

        for page in range(2, pages + 1):
            print('page', page)
            current_page = self._get_photo_page(page=page)
            self.photos.extend(current_page['photos']['photo'])

    def _get_photo_page(self, page=1):
        photo_page = FLICKR.people.getPhotos(user_id=self.flickrid,
                                             per_page=500,
                                             page=page,
                                             extras='date_upload, views',
                                             min_upload_date=self.updated_at
                                             )
        return photo_page
