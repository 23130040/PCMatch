# PCMatch

Django marketplace with database-backed buyer sign-in, registration, home page,
product catalog and cart. Business operations belong to Python views and services.
Buyer and staff screens retain their HTML layouts without simulated transactions.
Shop screens render directly through Django templates and read existing database records.

## Run Locally (PowerShell)

The repaired environment uses Python 3.12. From the project directory:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

## VNPay Sandbox

Set `VNPAY_TMN_CODE`, `VNPAY_HASH_SECRET` and `VNPAY_RETURN_URL` in the local
environment. The return URL must be the public HTTPS URL for
`/payments/vnpay/return/`. Configure the separate VNPay IPN/notification URL in
the merchant portal as the public HTTPS URL for `/payments/vnpay/ipn/`; for local
development, the server needs a public tunnel so VNPay can reach this endpoint.
Keep the hash secret private and use sandbox credentials for local testing.

Checkout records the order and payment as `PENDING`, reserves stock, and redirects
to VNPay. Both the signed browser return and the signed IPN verify the merchant,
reference and amount before recording `PAID` or a confirmed terminal failure. The
IPN handles payments even when the buyer does not return to the site. Confirmed
failure cancels the order and restores stock; pending, reversed or suspicious
results stay pending for reconciliation. A paid order then follows the normal
admin order confirmation and shop fulfillment flow. VNPay checkout requires an
order total of at least 5,000 VND.

To create an environment on another machine, install Python 3.12 or later and run
`py -3.12 -m venv .venv` before installing dependencies. Virtual environments depend
on their base Python installation; do not copy a virtual environment between machines.
The previous environment is preserved in `.venv-backup-20261004`.

## Pages

- Buyer home (default entry): `/`
- Buyer: `/buyer/home/`
- Sign out: `/auth/logout/` (buyer), `/shop/logout/` (seller), `/staff/logout/` (admin)
- Shared sign-in (buyer): `/auth/login/`
- Shared registration: `/auth/login/?mode=register`
- Database cart: `/buyer/cart/`
- Checkout information: `/buyer/checkout/`
- Shop sign-in: `/shop/login/`
- Shop: `/shop/dashboard/`
- Admin sign-in: `/staff/login/`
- Staff UI: `/staff/dashboard/`
- Django admin: `/django-admin/`

Buyer, Shop and staff share one Django account store, but they are three
separate portals and each role only opens its own area:

- buyer area (`is_active_buyer`, roles `BUYER`/`CUSTOMER`) → `/buyer/...`
- shop area (`is_active_seller`, role `SELLER`) → `/shop/...`
- staff area (`is_staff_user`, `ADMIN` or `is_staff`) → `/staff/...`

Because of this, one session never leaks into another portal: after signing in
at `/staff/login/`, opening `/buyer/account/` redirects to
`/auth/login/?next=...` and opening `/shop/dashboard/` redirects to
`/shop/login/?next=...`, so each portal always asks for its own sign-in.

Sign-out is per portal: `auth_logout`, `shop_logout` and `staff_logout` end the
session and return to `/auth/login/`, `/shop/login/` and `/staff/login/`. They
accept `GET` as well as `POST` and the sign-out control is a plain link, because
Django rotates the CSRF token on every login: a POST form rendered before a
login elsewhere in the same browser would fail with “CSRF token from POST
incorrect”. Signing out only ends a session and has no other side effect.
`auth_logout` remains CSRF-protected for POST requests.

Shop has its own sign-in page (`templates/shop/login.html`, form in
`shops/forms.py`) that calls `shops.views.shop_login` and authenticates the same
`users.User` accounts used elsewhere — it is a separate screen, not a separate
account store. The admin
channel has its own sign-in page (`templates/staff/login.html`, form
`StaffLoginForm` in `users/forms.py`) served by `users.views.staff_login` at
`/staff/login/`. It offers a "Ghi nhớ đăng nhập" (remember-me) session and,
when `User.two_factor_enabled` is set, a second OTP step whose code is emailed
to the account (printed to the console in development and shown on the page
while `DEBUG` is on). Unknown accounts, wrong passwords and non-staff accounts
get distinct messages. Only staff/`ADMIN` accounts are
admitted and a successful sign-in redirects to `/staff/dashboard/`. `staff_required`
sends unauthorised visitors to `/staff/login/`, not the buyer form. `shop/forgot/`
still redirects to the shared auth page; admin password recovery lives at
`/staff/forgot/` and `/staff/reset/<token>/`. Buyer screens continue to use
`templates/auth/login.html`; `/auth/register/` redirects to the shared
registration mode for old links. Registration creates an ordinary buyer account;
it does not grant staff access or create a Shop.

## Seller Onboarding

Clicking “Đăng ký làm người bán” on `/shop/login/` starts a four-step wizard that
creates a seller account and a Shop, then waits for admin approval:

- `/shop/register/` — step 1: seller account (unique username/email, strong password).
- `/shop/verify/email/` — step 2a: “Vui lòng kiểm tra email để kích hoạt tài khoản”.
  The activation link (`/shop/verify/email/<token>/`) marks the email verified. The
  link is printed by the console email backend and, while `DEBUG` is on, also shown
  on the page.
- `/shop/verify/phone/` — step 2b: phone number and OTP (code kept in the session;
  shown on the page in `DEBUG`).
- `/shop/onboarding/profile/` — step 3: unique shop name, contact info, logo upload.
- `/shop/onboarding/legal/` — step 4: CMND/CCCD and business-licence uploads, then
  the shop is set to `PENDING` and `/shop/onboarding/pending/` shows
  “Shop của bạn đang chờ xét duyệt bởi admin”.
- `/shop/dashboard/` — available only once `Shop.status == 'ACTIVE'`; otherwise the
  seller is redirected back to the onboarding step. `/shop/notifications/` lists the
  notifications, including “Chúc mừng, shop của bạn đã sẵn sàng!”.

### Admin shop approval

`/staff/shop/` (`shops.views.staff_shop_list`) lists the real shops with a search
box (name, owner, email, phone), status tabs and pagination. Each row posts one
CSRF-protected action:

- `/staff/shop/<id>/approve/` — `PENDING`/`SUSPENDED` → `ACTIVE`. `Shop.save()`
  creates the `SHOP_APPROVED` notification and emails the owner, so the seller can
  open `/shop/dashboard/`. Approving twice does not send a second notification.
- `/staff/shop/<id>/suspend/` — sets `SUSPENDED` and records a `SHOP_SUSPENDED`
  notification; the seller is sent back to `/shop/onboarding/pending/`.

`/shop/onboarding/pending/` redirects to `/shop/dashboard/` once the shop is
approved, so a seller who was waiting lands on the shop home page after signing
in. Django admin approval still works and behaves identically.

Admin approves a shop in Django admin (`/django-admin/`) with the “Phê duyệt shop
đã chọn” action. `Shop.save()` detects the transition to `ACTIVE`, records a
`Notification` and emails the owner “Shop của bạn đã được phê duyệt thành công”.
Adding a product requires sign-in;
an interrupted add resumes after successful sign-in or registration. Cart rows are
stored in `Cart`/`CartItem`, with one cart per user and one row per product.
The cart is rendered in Django HTML templates and works with JavaScript disabled.
Quantity changes and removal use CSRF-protected POST forms. Buyer and staff screens
without a backend implementation keep their layouts with disabled business actions.
The cart's checkout button opens a Django-rendered review of the signed-in user's
profile, default delivery address (or first saved address), and current cart prices
and quantities. This review does not create an order or initiate a payment.

## Frontend Integration

`PCMatch/pages.py` explicitly lists page templates. `PCMatch/urls.py` serves them
with named URLs and page metadata. The frontend context processor publishes URLs
using Django `reverse()` and the configured static asset prefix as JSON in the head.
The original banners, category tiles, chat layout and other presentation content
are written directly in HTML templates. Product lists and cart previews use real
database data. JavaScript is limited to presentation, such
as menus, carousels, password visibility, drawers and selecting table rows. No
script replaces the document body. Buyer and staff scripts do not intercept
business forms or simulate successful transactions.

Comparison uses “Thêm so sánh” buttons and the original selection tray. Python
stores up to four products from one category in the Django session. The comparison
script submits only comparison forms to that backend and displays HTML rendered
by Django, so selections persist through filters and pagination. Native POST forms
also work when JavaScript is disabled.

Shop layouts live directly in `templates/shop/*.html`. Shared backend partials
in `templates/includes/shop/` provide the base, header, sidebar, pagination,
product form/status, revenue chart and build-detail form. Django renders headings,
tables, forms and empty states before JavaScript runs; no HTML is published as
JSON templates or generated by a browser renderer. `shop-interface.js` only
controls the sidebar, password visibility and row selection.

`shops/views.py` reads the signed-in user's first owned Shop and scopes products,
orders, questions and returns to that shop. Order details and revenue show only
that shop's items, including when an order contains several shops. Revenue uses
delivered items and excludes shipping/platform fees. Filters use native GET
forms. Shop uses the shared Django authentication view;
a newly registered account still needs a linked Shop.
Actions without a backend implementation retain disabled HTML controls. Build
requests/proposals retain their layouts and forms without fabricated records.
The prototype states page and all Shop browser-storage/demo rendering modules
have been removed. Buyer, auth and admin layouts remain available.

Keep static presentation content in HTML when extending Buyer or staff screens.
Implement authentication, payments, orders, account updates, comments, reports and
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

Optional Shop browser checks require Node.js with Playwright and Chrome. From
the project root, start `.venv\Scripts\python.exe shops/browser_checks/serve_shop_checks.py`
in one terminal, then run `node shops/browser_checks/verify_shop_pages.cjs` in
another. The server uses a copy at `artifacts/backend_shop_browser.sqlite3` with a test
account; it leaves the working database untouched. Checks cover all Shop layouts
with JavaScript disabled, database-backed lists
and details, native filters/authentication, mobile layouts and UI interactions.
The Django suite also checks isolation between shops and mixed-shop order totals.
