import datetime

from django.contrib.postgres.fields import JSONField
from django.db import models


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
