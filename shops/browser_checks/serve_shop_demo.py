import os
import sqlite3
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
os.environ['DJANGO_SETTINGS_MODULE'] = 'PCMatch.settings'
from django.conf import settings

copy = root / 'artifacts/shop_browser.sqlite3'
copy.parent.mkdir(exist_ok=True)
with sqlite3.connect(f'file:{root / "db.sqlite3"}?mode=ro', uri=True) as source:
    with sqlite3.connect(copy) as target:
        source.backup(target)
settings.DATABASES['default']['NAME'] = copy
import django
django.setup()
from django.contrib.auth import get_user_model
from django.core.management import call_command

get_user_model().objects.create_user(username='shop-browser-check', email='shopbrowser@example.test',
    password='ShopBrowser!9472', full_name='Shop Browser', role='BUYER', status='ACTIVE')
call_command('runserver', '127.0.0.1:8767', use_reloader=False)
