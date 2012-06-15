#!/usr/bin/env python

# manage.py should only be used for local development. In production use django-admin.py
import settings.development
from django.core.management import execute_manager
execute_manager(settings.development)
