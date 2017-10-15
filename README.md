
# Curiosity Flickr

Explore Flickr Api with Python and Django

## Dependencies

    pip install -r requirements/base.txt


## Development

### Django with Werkzeug debugger

1. Install Werkzeug and django-extensions

        pip install -r requirements/dev.txt

2. Add django_extensions to INSTALLED_APPS in your projects settings.py file:

        INSTALLED_APPS = (
            ...
            'django_extensions',
            ...
        )

3. Run server

        python manage.py runserver_plus
