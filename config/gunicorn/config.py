# Gunicorn configuration file for web1 instance

import multiprocessing

bind            = "0.0.0.0:8000"
daemon          = True
workers         = multiprocessing.cpu_count() * 2 + 1
worker_class    = "gevent"
django_settings = "settings.production"
pythonpath      = "/srv/sites/webapp/myproject"
user            = "www-data"
group           = "www-data"
accesslog       = "/var/log/gunicorn/access.log"
errorlog        = "/var/log/gunicorn/error.log"
loglevel        = "debug"
