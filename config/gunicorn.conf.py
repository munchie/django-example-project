import multiprocessing

bind            = "127.0.0.1:8000"
workers         = multiprocessing.cpu_count() * 2 + 1
worker_class    = "gevent"
django_settings = "settings.production"
pythonpath      = "/srv/sites/webapp/myproject"
user            = "www-data"
group           = "www-data"
accesslog       = "/var/log/gunicorn/access_webapp.log"
errorlog        = "/var/log/gunicorn/error_webapp.log"
loglevel        = "debug"
