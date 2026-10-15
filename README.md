# PCMatch

Django marketplace with database-backed buyer sign-in, registration, home page,
product catalog and cart. Business operations belong to Python views and services.
The remaining screens retain their HTML layouts without simulated transactions
or browser-stored users, orders and payments.

## Run Locally (PowerShell)

The repaired environment uses Python 3.12. From the project directory:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

To create an environment on another machine, install Python 3.12 or later and run
`py -3.12 -m venv .venv` before installing dependencies. Virtual environments depend
on their base Python installation; do not copy a virtual environment between machines.
The previous environment is preserved in `.venv-backup-20261004`.

## Pages

- Buyer home (default entry): `/`
- Buyer: `/buyer/home/`
- Buyer sign-in / registration: `/auth/login/`
- Database cart: `/buyer/cart/`
- Checkout information: `/buyer/checkout/`
- Shop: `/shop/dashboard/`
- Staff UI: `/staff/dashboard/`
- Django admin: `/django-admin/`
- UI states: `/states/index/`

Buyer sign-in uses Django users and sessions. Adding a product requires sign-in;
an interrupted add resumes after successful sign-in or registration. Cart rows are
stored in `Cart`/`CartItem`, with one cart per user and one row per product.
The cart is rendered in Django HTML templates and works with JavaScript disabled.
Quantity changes and removal use CSRF-protected POST forms. Screens without a
backend implementation keep their original layouts with disabled business actions.
The cart's checkout button opens a Django-rendered review of the signed-in user's
profile, default delivery address (or first saved address), and current cart prices
and quantities. This review does not create an order or initiate a payment.

## Frontend Integration

`PCMatch/pages.py` explicitly lists page templates. `PCMatch/urls.py` serves them
with named URLs and page metadata. The frontend context processor publishes URLs
using Django `reverse()` and the configured static asset prefix as JSON in the head.
The original banners, category tiles, chat layout and other presentation content
are written directly in HTML templates. Product lists and cart previews use real
database data. JavaScript is limited to presentation, such as menus, carousels,
password visibility, drawers and selecting table rows. No script replaces the
document body, intercepts business forms or simulates successful transactions.

Comparison uses “Thêm so sánh” buttons and the original selection tray. Python
stores up to four products from one category in the Django session. The comparison
script submits only comparison forms to that backend and displays HTML rendered
by Django, so selections persist through filters and pagination. Native POST forms
also work when JavaScript is disabled.

Keep static presentation content in HTML when extending a screen. Implement
authentication, payments, orders, account updates, comments, reports and
recommendations in Python before enabling their business actions.

Use `{% url %}` for template links, `{% static %}` for template assets, and
native GET/POST forms for backend operations. Header and sidebar fragments
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
The buyer home lists newest and bestselling products from the database. The
catalog filters and sorts through `CatalogFilterForm`; the product detail and
comparison pages also render directly from Django data.

## Verify

```powershell
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe manage.py test
```

The tests cover page rendering, route coverage, internal links, static assets,
shared staff components, and redirects that preserve search parameters.
