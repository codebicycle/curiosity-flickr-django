import datetime
import logging
import sys
from django.contrib.postgres.fields import JSONField
from django.db import models


logging.basicConfig()

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class Person(models.Model):
    flickrid = models.CharField(max_length=30, unique=True, db_index=True)
    updated_at = models.DateTimeField(null=True)
    photos = JSONField(default=list)
    info = JSONField(null=True)

    flickrapi = None

    def _needs_update(self):
        now = datetime.datetime.utcnow()
        delta = datetime.timedelta(days=1)
        threshold = now - delta
        if self.updated_at is None or self.updated_at < threshold:
            return True
        return False

    needs_update = property(_needs_update)


    @classmethod
    def create(cls, flickrid):
        person = cls(flickrid=flickrid)
        person._update_info()

        return person


    def __str__(self):
        return self.info['person']['username']['_content']

    def _update_info(self):
        self.info = self.flickrapi.people.getInfo(user_id=self.flickrid)

    def update(self):
        self._update_info()
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


class Following(models.Model):
    follower = models.ForeignKey(Person, on_delete=models.CASCADE,
        to_field='flickrid', related_name='+')
    followed = models.ForeignKey(Person, on_delete=models.CASCADE,
        to_field='flickrid', related_name='+')

    class Meta:
        unique_together = ("follower", "followed")

    def __str__(self):
        return self.followed.info['person']['username']['_content']


class Fav(models.Model):
    user = models.ForeignKey(Person, on_delete=models.CASCADE,
                               to_field='flickrid')
    photoid = models.CharField(max_length=30, db_index=True)
    info = JSONField(null=True)

    def __str__(self):
        return self.info
