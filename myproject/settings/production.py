from base import *


DEBUG = False
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'webapp',                      # Or path to database file if using sqlite3.
        'USER': 'webapp',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '10.10.10.20',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Celery beat configuration
CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"

try:
    from local_settings import *
except:
    pass