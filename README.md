# PCMatch

Django-served frontend demo. Buyer, shop and staff data still use browser storage;
the UI is ready for incremental integration with Django views and models.

## Run Locally (PowerShell)

The repaired environment uses Python 3.12. From the project directory:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

To create an environment on another machine, install Python 3.12 or later and run
`py -3.12 -m venv .venv` before installing dependencies. Virtual environments depend
on their base Python installation; do not copy a virtual environment between machines.
The previous environment is preserved in `.venv-backup-20261004`.

## Pages

- Sitemap: `/`
- Buyer: `/buyer/home/`
- Demo sign-in: `/auth/login/`
- Shop: `/shop/dashboard/`
- Staff UI: `/staff/dashboard/`
- Django admin: `/django-admin/`
- UI states: `/states/index/`

The demo sign-in uses a demo account created in the same browser, independently
of Django admin accounts. Shop and staff demo pages are not yet backend-authorized.

## Frontend Integration

`PCMatch/pages.py` explicitly lists page templates. `PCMatch/urls.py` serves them
with named URLs and page metadata. The frontend context processor publishes URLs
using Django `reverse()` and the configured static asset prefix as JSON in the head.
`static/js/routing.js` provides URL helpers for buyer and shop modules.

Use `{% url %}` for template links, `{% static %}` for template assets, and
`pageUrl()` / `assetUrl()` inside static JavaScript. Header and sidebar fragments
for staff pages are included by Django, without a separate network request.

When adding a page, register its template and include
`includes/frontend_config.html` inside its head. Set `data-page="{{ page_name }}"`
and `data-section="{{ page_section }}"` on its html element. When a page gets a real
backend view, replace its `TemplateView` route while retaining its URL name.

## Uploaded Images

Uploaded files use `MEDIA_ROOT = BASE_DIR / 'media'` and `MEDIA_URL = '/media/'`.
An ImageField's `upload_to` selects its subdirectory, such as
`media/product_thumbnail/` or `media/avatar/`. These files are excluded from Git.
Django serves `/media/` while `DEBUG` is enabled for local development.
Production must serve uploaded files through the web server or a storage backend.

Product image fields can be edited in Django admin. A custom upload form must use
`enctype="multipart/form-data"`, and its view must pass `request.FILES` to the form.
Browser demo pages still use their existing JavaScript data and static images.

## Verify

```powershell
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe manage.py test PCMatch
```

The tests cover page rendering, route coverage, internal links, static assets,
shared staff components, and redirects that preserve search parameters.
