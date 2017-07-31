import datetime
import logging
import sys
from django.contrib.postgres.fields import JSONField
from django.db import models


logging.basicConfig()

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class Person(models.Model):
    flickrapi = None

    def _needs_update(self):
        now = datetime.datetime.utcnow()
        delta = datetime.timedelta(days=1)
        threshold = now - delta
        if self.updated_at is None or self.updated_at < threshold:
            return True
        return False

    flickrid = models.CharField(max_length=30, unique=True, db_index=True)
    updated_at = models.DateTimeField()
    photos = JSONField(default=list)
    info = JSONField()
    needs_update = property(_needs_update)

    def __str__(self):
        return self.info['person']['username']['_content']

    def update(self):
        self.info = self.flickrapi.people.getInfo(user_id=self.flickrid)
        self._update_photos()
        self.updated_at = datetime.datetime.utcnow()
        self.save()

    def _update_photos(self):
        user_name = self.info['person']['username']['_content']

        first_page = self._get_photo_page(page=1)
        pages = first_page['photos']['pages']
        total = first_page['photos']['total']
        log.info('{} | {} photos | {} pages'.format(user_name, total, pages))

        self.photos.extend(first_page['photos']['photo'])

        for page in range(2, pages + 1):
            log.info('Get photos from page {}.'.format(page))
            current_page = self._get_photo_page(page=page)
            self.photos.extend(current_page['photos']['photo'])

    def _get_photo_page(self, page=1):
        photo_page = self.flickrapi.people.getPhotos(
            user_id=self.flickrid,
            per_page=500,
            page=page,
            extras='date_upload, views',
            min_upload_date=self.updated_at
        )
        return photo_page


class Fav(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE,
                               to_field='flickrid')

    def __str__(self):
        return self.person.info['person']['username']['_content']
